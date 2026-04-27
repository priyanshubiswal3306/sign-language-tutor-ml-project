import cv2
import mediapipe as mp
import numpy as np
import os
import sys
import uuid

# Fix paths to import your custom normalizer
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(BASE_DIR, "..")))

from src.utils.landmark_normalizer import normalize_landmarks

# Paths & Config
DATASET_PATH = os.path.join(BASE_DIR, "..", "data", "sequence_dataset")
SEQ_LENGTH = 60 # Changed to 60 frames (~2 seconds)

# Init MediaPipe
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=2, min_detection_confidence=0.5)

def collect_data():
    action = input("Enter the phrase you are recording (e.g., 'Thank you', 'Hello'): ").strip()
    if not action:
        print("Action cannot be empty!")
        return

    save_dir = os.path.join(DATASET_PATH, action)
    os.makedirs(save_dir, exist_ok=True)
    
    existing_files = len(os.listdir(save_dir))
    print(f"\n✅ Ready to record '{action}'. You currently have {existing_files} sequences.")
    print("👉 Press SPACEBAR to start a 60-frame recording sequence.")
    print("👉 Press 'q' to quit.\n")

    cap = cv2.VideoCapture(0)

    while True:
        ret, frame = cap.read()
        if not ret: break

        frame = cv2.flip(frame, 1)
        display_frame = frame.copy()
        
        # Display instructions
        cv2.putText(display_frame, f"Recording: {action}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
        cv2.putText(display_frame, f"Count: {len(os.listdir(save_dir))}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
        cv2.putText(display_frame, "Press SPACE to Record", (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow("Sequence Collector", display_frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord(' '): # Spacebar pressed
            # Visual Warning before recording starts
            for i in range(3, 0, -1):
                warn_frame = frame.copy()
                cv2.putText(warn_frame, f"Get Ready... {i}", (150, 250), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 165, 255), 4)
                cv2.imshow("Sequence Collector", warn_frame)
                cv2.waitKey(500) 

            sequence_data = []
            
            # Record exactly SEQ_LENGTH frames
            for frame_num in range(SEQ_LENGTH):
                ret, frame = cap.read()
                frame = cv2.flip(frame, 1)
                
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = hands.process(rgb)

                if results.multi_hand_landmarks:
                    for hl in results.multi_hand_landmarks:
                        mp_drawing.draw_landmarks(frame, hl, mp_hands.HAND_CONNECTIONS)

                cv2.putText(frame, f"🔴 RECORDING... Frame {frame_num}/{SEQ_LENGTH}", (10, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
                cv2.imshow("Sequence Collector", frame)
                cv2.waitKey(10) 

                row = []
                if results.multi_hand_landmarks:
                    hands_detected = list(zip(results.multi_hand_landmarks, results.multi_handedness))
                    hands_detected = sorted(hands_detected, key=lambda h: h[0].landmark[0].x)
                    
                    for hand_landmarks, hand_info in hands_detected[:2]:
                        is_left = (hand_info.classification[0].label == "Left")
                        
                        raw_coords = []
                        for lm in hand_landmarks.landmark:
                            raw_coords.extend([lm.x, lm.y, lm.z])
                            
                        # Apply custom normalizer
                        normalized = normalize_landmarks(raw_coords, is_left_hand=is_left)
                        row.extend(normalized)
                        
                    if len(hands_detected) == 1:
                        row.extend([0.0] * 63)
                else:
                    row = [0.0] * 126
                
                sequence_data.append(row)

            if len(sequence_data) == SEQ_LENGTH:
                save_path = os.path.join(save_dir, f"{uuid.uuid4().hex}.npy")
                np.save(save_path, np.array(sequence_data))
                print(f"Saved sequence! Total: {len(os.listdir(save_dir))}")

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    collect_data()