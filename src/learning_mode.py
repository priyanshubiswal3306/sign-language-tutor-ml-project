import cv2
import numpy as np
import tensorflow as tf
import mediapipe as mp
import random
import time
import pyttsx3
import queue

from src.utils.landmark_normalizer import normalize_landmarks

# 🔊 Initialize voice engine
engine = pyttsx3.init(driverName='sapi5')
engine.setProperty('rate', 150)
engine.setProperty('volume', 1.0)

speech_queue = queue.Queue()

def speak(text):
    # Only queue if empty (prevents spam)
    if speech_queue.empty():
        speech_queue.put(text)

def process_speech():
    if not speech_queue.empty():
        text = speech_queue.get()
        print("Speaking:", text)
        engine.say(text)
        engine.runAndWait()

# Load model
model = tf.keras.models.load_model("models/landmark_model.keras")
labels = np.load("models/landmark_labels.npy")

# MediaPipe
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

mp_draw = mp.solutions.drawing_utils

# 🔥 Stability
stable_label = ""
stable_count = 0
REQUIRED_STABLE = 7

# 🔥 Learning system
target = random.choice(labels)
score = 0
total = 0

# 🔥 Cooldown
last_action_time = 0
COOLDOWN = 2  # seconds

cap = cv2.VideoCapture(0)

# 🔊 Speak first instruction
speak(f"Show {target}")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)

    label = ""
    confidence = 0

    current_time = time.time()

    if results.multi_hand_landmarks:
        for hand_landmarks, hand_info in zip(
            results.multi_hand_landmarks,
            results.multi_handedness
        ):
            hand_label = hand_info.classification[0].label
            is_left = (hand_label == "Left")

            mp_draw.draw_landmarks(
                frame,
                hand_landmarks,
                mp_hands.HAND_CONNECTIONS
            )

            row = []
            for lm in hand_landmarks.landmark:
                row.extend([lm.x, lm.y, lm.z])

            if len(row) == 63:
                normalized = normalize_landmarks(row, is_left_hand=is_left)
                data = np.array(normalized).reshape(1, -1)

                preds = model.predict(data, verbose=0)
                class_index = np.argmax(preds)
                confidence = np.max(preds)

                label = labels[class_index]

    # 🔥 Stability logic
    if label == stable_label:
        stable_count += 1
    else:
        stable_label = label
        stable_count = 1

    result_text = "Show the sign"

    # 🔥 Cooldown logic
    if current_time - last_action_time > COOLDOWN:

        if stable_count > REQUIRED_STABLE and confidence > 0.7:

            total += 1

            if stable_label == target:
                result_text = "Correct ✅"
                score += 1
                speak("Correct")
            else:
                result_text = "Try Again ❌"
                speak("Try again")

            # 🔥 New target
            target = random.choice(labels)
            stable_count = 0
            last_action_time = current_time

            # 🔊 Speak next target
            speak(f"Show {target}")

    else:
        result_text = "Wait..."

    # 🔊 Process speech queue (IMPORTANT)
    process_speech()

    # 🔥 Display
    cv2.putText(frame, f"Target: {target}",
                (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1, (0, 255, 0), 2)

    cv2.putText(frame, result_text,
                (20, 100),
                cv2.FONT_HERSHEY_SIMPLEX,
                1, (255, 255, 0), 2)

    cv2.putText(frame, f"Score: {score}/{total}",
                (20, 150),
                cv2.FONT_HERSHEY_SIMPLEX,
                1, (0, 255, 255), 2)

    cv2.imshow("Learning Mode (Voice Enabled)", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()