import cv2
import numpy as np
import tensorflow as tf
import mediapipe as mp
import random
import time

from src.utils.landmark_normalizer import normalize_landmarks

# ================= LOAD MODEL ================= #

model = tf.keras.models.load_model("models/landmark_model.keras")
labels = np.load("models/landmark_labels.npy")

# ================= MEDIAPIPE ================= #

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

mp_draw = mp.solutions.drawing_utils

# ================= SETTINGS ================= #

REQUIRED_STABLE = 7
COOLDOWN = 2
MAX_QUESTIONS = 30

# ================= VARIABLES ================= #

stable_label = ""
stable_count = 0

target = random.choice(labels)

score = 0
total = 0

last_action_time = 0

quiz_active = True

# ================= CAMERA ================= #

cap = cv2.VideoCapture(0)

# ================= LOOP ================= #

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
            is_left = (hand_info.classification[0].label == "Left")

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

    # ================= STABILITY ================= #

    if label == stable_label:
        stable_count += 1
    else:
        stable_label = label
        stable_count = 1

    result_text = "Show the sign"

    # ================= QUIZ LOGIC ================= #

    if quiz_active:

        if current_time - last_action_time > COOLDOWN:

            if stable_count > REQUIRED_STABLE and confidence > 0.7:

                total += 1

                if stable_label == target:
                    result_text = "Correct ✅"
                    score += 1
                else:
                    result_text = "Try Again ❌"

                # New target
                target = random.choice(labels)

                stable_count = 0
                last_action_time = current_time

                # End quiz
                if total >= MAX_QUESTIONS:
                    quiz_active = False

        else:
            result_text = "Wait..."

    else:
        result_text = "QUIZ COMPLETE"

    # ================= DISPLAY ================= #

    cv2.putText(frame, f"Target: {target}",
                (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1, (0,255,0), 2)

    cv2.putText(frame, result_text,
                (20, 100),
                cv2.FONT_HERSHEY_SIMPLEX,
                1, (255,255,0), 2)

    cv2.putText(frame, f"Score: {score}/{total}",
                (20, 150),
                cv2.FONT_HERSHEY_SIMPLEX,
                1, (0,255,255), 2)

    # ================= FINAL RESULT ================= #

    if not quiz_active:
        accuracy = (score / total) * 100 if total > 0 else 0

        cv2.putText(frame, "QUIZ COMPLETE",
                    (20, 200),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1, (0,255,0), 2)

        cv2.putText(frame, f"Final Score: {score}/{total}",
                    (20, 250),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1, (255,255,0), 2)

        cv2.putText(frame, f"Accuracy: {accuracy:.2f}%",
                    (20, 300),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1, (255,255,0), 2)

        cv2.putText(frame, "Press R to Restart",
                    (20, 350),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1, (0,255,255), 2)

    # ================= CONTROLS ================= #

    key = cv2.waitKey(1) & 0xFF

    if key == ord('q'):
        break

    if key == ord('r') and not quiz_active:
        # Restart quiz
        score = 0
        total = 0
        quiz_active = True
        target = random.choice(labels)

    cv2.imshow("Learning Mode (Quiz)", frame)

cap.release()
cv2.destroyAllWindows()