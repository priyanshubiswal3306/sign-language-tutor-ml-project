import cv2
import mediapipe as mp
import numpy as np
import os

# ================= CONFIG =================
DATA_PATH = r"C:\Personal\Projects\sign_language_tutor\data\sequence_data"
OUTPUT_PATH = r"C:\Personal\Projects\sign_language_tutor\data\sequence_dataset"
SEQ_LENGTH = 30

# ================= INIT =================
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.5
)

os.makedirs(OUTPUT_PATH, exist_ok=True)

# ================= FUNCTION =================
def extract_sequence(video_path):
    cap = cv2.VideoCapture(video_path)

    frames = []

    while len(frames) < SEQ_LENGTH:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        result = hands.process(rgb)

        row = []

        if result.multi_hand_landmarks:
            hands_detected = result.multi_hand_landmarks

            # Sort hands left-right
            hands_detected = sorted(hands_detected, key=lambda h: h.landmark[0].x)

            for i in range(2):
                if i < len(hands_detected):
                    lm = hands_detected[i]
                    for p in lm.landmark:
                        row.extend([p.x, p.y, p.z])
                else:
                    row.extend([0.0] * 63)
        else:
            row = [0.0] * 126

        frames.append(row)

    cap.release()

    if len(frames) == SEQ_LENGTH:
        return np.array(frames)

    return None


# ================= MAIN =================
for label in os.listdir(DATA_PATH):
    label_path = os.path.join(DATA_PATH, label)

    if not os.path.isdir(label_path):
        continue

    save_path = os.path.join(OUTPUT_PATH, label)
    os.makedirs(save_path, exist_ok=True)

    print(f"\nProcessing: {label}")

    files = os.listdir(label_path)

    for i, file in enumerate(files):
        video_path = os.path.join(label_path, file)

        seq = extract_sequence(video_path)

        if seq is not None:
            np.save(os.path.join(save_path, f"{i}.npy"), seq)
            print(f"Saved: {label}/{i}.npy")
        else:
            print(f"Skipped: {file}")

print("\nDONE ✅")