import cv2
import numpy as np
import tensorflow as tf
import mediapipe as mp

from src.utils.landmark_normalizer import normalize_landmarks

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

# 🔥 Word system
sentence = ""
last_added = ""

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

    # 🔥 Accept letter only when stable
    if stable_count > REQUIRED_STABLE and confidence > 0.7:
        display_text = stable_label

        # 🔥 Add to sentence (avoid repeats)
        if stable_label != last_added:
            sentence += stable_label
            last_added = stable_label
    else:
        display_text = "Detecting..."

    # 🎮 Keyboard controls
    key = cv2.waitKey(1) & 0xFF

    if key == ord(' '):  # SPACE
        sentence += " "
        last_added = ""

    elif key == 8:  # BACKSPACE
        sentence = sentence[:-1]

    elif key == ord('c'):  # CLEAR
        sentence = ""
        last_added = ""

    elif key == ord('q'):  # QUIT
        break

    # 🔥 Display
    cv2.putText(frame, f"Letter: {display_text}",
                (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1, (0, 255, 0), 2)

    cv2.putText(frame, f"Text: {sentence}",
                (20, 100),
                cv2.FONT_HERSHEY_SIMPLEX,
                1, (255, 255, 0), 2)

    cv2.imshow("Sign Language Tutor", frame)

cap.release()
cv2.destroyAllWindows()