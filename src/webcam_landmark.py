import cv2
import numpy as np
import tensorflow as tf
import mediapipe as mp

# Load model + labels
model = tf.keras.models.load_model("models/landmark_model.keras")
labels = np.load("models/landmark_labels.npy")

# MediaPipe setup
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

mp_draw = mp.solutions.drawing_utils

# 🔥 Stability variables
stable_label = ""
stable_count = 0
REQUIRED_STABLE = 7  # Increase for more stability

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)

    label = ""
    confidence = 0

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:

            # Draw landmarks
            mp_draw.draw_landmarks(
                frame,
                hand_landmarks,
                mp_hands.HAND_CONNECTIONS
            )

            # Extract 63 features
            row = []
            for lm in hand_landmarks.landmark:
                row.extend([lm.x, lm.y, lm.z])

            if len(row) == 63:
                data = np.array(row).reshape(1, -1)

                preds = model.predict(data, verbose=0)
                class_index = np.argmax(preds)
                confidence = np.max(preds)

                label = labels[class_index]

    # 🔥 Stability logic (debounce)
    if label == stable_label:
        stable_count += 1
    else:
        stable_label = label
        stable_count = 1

    # 🔥 Final output logic
    if stable_count > REQUIRED_STABLE and confidence > 0.7:
        display_text = f"{stable_label} ({confidence:.2f})"
    else:
        display_text = "Detecting..."

    # Display text
    cv2.putText(frame, display_text,
                (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1, (0, 255, 0), 2)

    cv2.imshow("Landmark Sign Detection (Stable)", frame)

    # Exit on Q
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()