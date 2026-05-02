import cv2
import mediapipe as mp
import numpy as np
import tensorflow as tf
import os

# ================= SETUP =================
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.7, min_tracking_confidence=0.7)
mp_draw = mp.solutions.drawing_utils

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, '..', 'models', 'phrase_model.keras')
LABEL_PATH = os.path.join(BASE_DIR, '..', 'models', 'phrase_labels.npy')

# Load the brain and the labels
model = tf.keras.models.load_model(MODEL_PATH)
actions = np.load(LABEL_PATH)

# ================= LIVE STREAM LOGIC =================
sequence = [] # This is our "Sliding Window"
sentence = []
predictions = []
threshold = 0.8 # Only show prediction if confidence is > 80%

cap = cv2.VideoCapture(0)

print("🚀 Real-time Inference Started! Press 'q' to stop.")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break

    frame = cv2.flip(frame, 1)
    image, results = frame, hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

    # Memory variables for the "Forward Fill" logic
    last_known_left = [0.0] * 63
    last_known_right = [0.0] * 63

    if results.multi_hand_landmarks:
        for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
            mp_draw.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            
            coords = []
            for lm in hand_landmarks.landmark:
                coords.extend([lm.x, lm.y, lm.z])
            
            # Map Handedness (Note: Flip logic applies)
            label = handedness.classification[0].label 
            if label == 'Right': last_known_left = coords
            else: last_known_right = coords

    # 1. Create the 126-feature row and add to sliding window
    current_row = np.concatenate([last_known_left, last_known_right])
    sequence.append(current_row)
    sequence = sequence[-60:] # Keep only the latest 60 frames

    # 2. Prediction Logic
    if len(sequence) == 60:
        # Reshape to (1, 60, 126) for the model
        res = model.predict(np.expand_dims(sequence, axis=0), verbose=0)[0]
        predictions.append(np.argmax(res))
        
        # 3. Stability Logic (Check if the last 10 predictions are the same)
        if np.unique(predictions[-10:])[0] == np.argmax(res):
            if res[np.argmax(res)] > threshold:
                predicted_word = actions[np.argmax(res)]
                
                # Add to sentence if it's new
                if len(sentence) > 0:
                    if predicted_word != sentence[-1]:
                        sentence.append(predicted_word)
                else:
                    sentence.append(predicted_word)

        if len(sentence) > 5: # Keep the sentence display short
            sentence = sentence[-5:]

    # UI Overlay
    cv2.rectangle(image, (0,0), (640, 40), (245, 117, 16), -1)
    cv2.putText(image, ' '.join(sentence), (3,30), 
               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
    
    cv2.imshow('SignTutor Real-Time Test', image)

    if cv2.waitKey(10) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()