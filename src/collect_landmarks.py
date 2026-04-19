import cv2
import mediapipe as mp
import csv
import os

# Setup MediaPipe
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1)
mp_draw = mp.solutions.drawing_utils

# Create data folder
os.makedirs("data/landmarks", exist_ok=True)

# Ask user for label
label = input("Enter label (A, B, C...): ").upper()

file_path = f"data/landmarks/{label}.csv"

cap = cv2.VideoCapture(0)

print(f"\nCollecting data for: {label}")
print("Press 's' to save frame | 'q' to quit\n")

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
                mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                # Extract 21 landmarks
                row = []
                for lm in hand_landmarks.landmark:
                    row.extend([lm.x, lm.y, lm.z])

                # Save on key press
                key = cv2.waitKey(1)
                if key == ord('s'):
                    writer.writerow(row)
                    print("Saved sample")

        cv2.putText(frame, f"Label: {label}", (20, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)

        cv2.imshow("Collect Landmarks", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()