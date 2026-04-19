import cv2
import mediapipe as mp
import csv
import os

# Setup MediaPipe
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

mp_draw = mp.solutions.drawing_utils

# Create directory
os.makedirs("data/landmarks", exist_ok=True)

# Input label
label = input("Enter label (A, B, C...): ").upper()
file_path = f"data/landmarks/{label}.csv"

cap = cv2.VideoCapture(0)

print(f"\nCollecting data for: {label}")
print("Press 'S' to save | 'Q' to quit\n")

sample_count = 0

with open(file_path, mode='a', newline='') as f:
    writer = csv.writer(f)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb)

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:

                # Draw landmarks
                mp_draw.draw_landmarks(
                    frame,
                    hand_landmarks,
                    mp_hands.HAND_CONNECTIONS
                )

                # Extract features
                row = []
                for lm in hand_landmarks.landmark:
                    row.extend([lm.x, lm.y, lm.z])

                key = cv2.waitKey(1)

                if key == ord('s'):
                    writer.writerow(row)
                    sample_count += 1
                    print(f"Saved sample {sample_count}")

        # Display info
        cv2.putText(frame, f"Label: {label}", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)

        cv2.putText(frame, f"Samples: {sample_count}", (20, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,0), 2)

        cv2.imshow("Collect Landmarks", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()