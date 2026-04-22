import cv2
import numpy as np
import tensorflow as tf
import mediapipe as mp
import random
import queue
import threading
import pyttsx3
import sys

# Assuming this is your custom module. Let me know if you need this rebuilt too!
try:
    from src.utils.landmark_normalizer import normalize_landmarks
except ImportError:
    print("Warning: Could not import 'normalize_landmarks'. Make sure your src/utils path is correct.")
    sys.exit(1)

# ==========================================
# 1. VOICE ASSISTANT CLASS (THREAD-SAFE)
# ==========================================
class VoiceAssistant:
    def __init__(self, rate=150):
        self.speech_queue = queue.Queue()
        self.rate = rate
        # Start the background thread immediately
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def _worker(self):
        while True:
            text = self.speech_queue.get()
            if text is None:
                break

            print(f"🎤 Speaking: {text}")
            # Reinitialize engine for each item to avoid state issues
            engine = pyttsx3.init(driverName='sapi5')
            engine.setProperty('rate', self.rate)
            engine.say(text)
            engine.runAndWait()
            engine.stop()  # Explicitly release the engine
            self.speech_queue.task_done()
            
    def speak(self, text):
        """Adds text to the queue to be spoken."""
        self.speech_queue.put(text)

    def stop(self):
        """Safely shuts down the audio thread."""
        self.speech_queue.put(None)
        self.thread.join()

# ==========================================
# 2. SETUP & INITIALIZATION
# ==========================================

# Initialize Audio
voice = VoiceAssistant(rate=150)

# Load Model & Labels
try:
    model = tf.keras.models.load_model("models/landmark_model.keras")
    labels = np.load("models/landmark_labels.npy")
except Exception as e:
    print(f"Error loading model or labels: {e}")
    voice.stop()
    sys.exit(1)

# Initialize MediaPipe
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)
mp_draw = mp.solutions.drawing_utils

# ==========================================
# 3. GAME LOGIC VARIABLES
# ==========================================
REQUIRED_STABLE_FRAMES = 7
stable_label = ""
stable_count = 0

score = 0
total = 0

target = random.choice(labels)
ready_for_next = True 
result_text = "Show the sign"

# Announce the first target
voice.speak(f"Show {target}")

# ==========================================
# 4. MAIN VIDEO LOOP
# ==========================================
cap = cv2.VideoCapture(0)

print("Starting video loop. Press 'q' to quit.")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame.")
        break

    # Mirror the frame for a natural feel
    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)

    label = ""
    confidence = 0.0
    hand_detected = results.multi_hand_landmarks is not None

    if hand_detected:
        for hand_landmarks, hand_info in zip(results.multi_hand_landmarks, results.multi_handedness):
            # Determine if it's left or right hand
            is_left = (hand_info.classification[0].label == "Left")

            # Draw landmarks
            mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            # Extract coordinates
            row = []
            for lm in hand_landmarks.landmark:
                row.extend([lm.x, lm.y, lm.z])

            # Process and Predict
            if len(row) == 63:
                normalized = normalize_landmarks(row, is_left_hand=is_left)
                data = np.array(normalized).reshape(1, -1)

                preds = model.predict(data, verbose=0)
                class_index = np.argmax(preds)
                confidence = np.max(preds)
                label = labels[class_index]

    # --- STABILITY & GAME LOGIC ---
    if hand_detected:
        if label == stable_label:
            stable_count += 1
        else:
            stable_label = label
            stable_count = 1

        if ready_for_next and stable_count > REQUIRED_STABLE_FRAMES and confidence > 0.7:
            total += 1

            if stable_label == target:
                result_text = "Correct ✅"
                score += 1
                voice.speak("Correct")
            else:
                result_text = "Try again ❌"
                voice.speak("Try again")

            # Pick a new target
            target = random.choice(labels)
            voice.speak(f"Show {target}")

            # Reset state and lock until hand is removed
            stable_count = 0
            ready_for_next = False 

    else:
        # Unlock the game state when no hands are in the frame
        ready_for_next = True
        result_text = "Show the sign"
        stable_count = 0

    # --- UI / DISPLAY ---
    cv2.putText(frame, f"Target: {target}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.putText(frame, result_text, (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
    cv2.putText(frame, f"Score: {score}/{total}", (20, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
    
    # Optional: Display current detection for debugging
    if hand_detected:
        cv2.putText(frame, f"Detected: {label} ({confidence:.2f})", (20, 450), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)

    cv2.imshow("Sign Language Learning", frame)

    # Quit condition
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# ==========================================
# 5. CLEANUP
# ==========================================
print("Shutting down...")
cap.release()
cv2.destroyAllWindows()
voice.stop() # Gracefully kill the audio thread
print("Done.")