import cv2
import mediapipe as mp
import numpy as np
import os

# ================= SETUP =================
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.5, min_tracking_confidence=0.5)
mp_draw = mp.solutions.drawing_utils

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, '..', 'data', 'sequence_dataset')
SEQUENCE_LENGTH = 60 # Number of frames per video

# ================= GET INPUT =================
action = input("Enter the phrase you are recording (e.g., 'hello'): ").lower()
no_sequences = int(input("How many videos do you want to record? (e.g., 20): "))

action_path = os.path.join(DATA_PATH, action)
os.makedirs(action_path, exist_ok=True)
dirmax = np.max([int(d[:-4]) for d in os.listdir(action_path) if d.endswith('.npy') and d[:-4].isdigit()]) if any(d.endswith('.npy') and d[:-4].isdigit() for d in os.listdir(action_path)) else 0

cap = cv2.VideoCapture(0)
print(f"\n🎥 GET READY! Recording {no_sequences} videos for '{action}'.")

quit_collection = False # Global flag to track if user hit 'Q'

# ================= RECORDING LOOP =================
for sequence in range(dirmax + 1, dirmax + 1 + no_sequences):
    
    # 1. PAUSE AND WAIT FOR USER PERMISSION BEFORE EACH VIDEO
    print(f"Waiting to record sequence {sequence}... Press SPACE to start, or 'Q' to quit.")
    while True:
        ret, frame = cap.read()
        
        # SAFETY NET: Ignore dropped/empty frames from the webcam
        if not ret or frame is None:
            cv2.waitKey(10)
            continue
            
        frame = cv2.flip(frame, 1)
        
        cv2.putText(frame, f'Ready for Video {sequence}', (120,200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255, 0), 4, cv2.LINE_AA)
        cv2.putText(frame, 'Press SPACE to Start | Press Q to Quit', (60,250), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2, cv2.LINE_AA)
        cv2.imshow('OpenCV Feed', frame)
        
        key = cv2.waitKey(10) & 0xFF
        if key == ord(' '):  # Start recording
            break
        elif key == ord('q'): # Quit entirely
            quit_collection = True
            break
            
    if quit_collection:
        print("\n🛑 Collection aborted by user.")
        break # Break out of the main recording loop

    # 2. START THE 60-FRAME RECORDING
    sequence_data = []
    last_known_left = [0.0] * 63
    last_known_right = [0.0] * 63

    frame_num = 0
    # Use a while loop instead of a for loop so we don't count dropped frames
    while frame_num < SEQUENCE_LENGTH:
        ret, frame = cap.read()
        
        # SAFETY NET: Ignore dropped/empty frames during recording
        if not ret or frame is None:
            cv2.waitKey(10)
            continue
            
        frame = cv2.flip(frame, 1)

        image, results = frame, hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        
        # UI Feedback during recording
        cv2.putText(image, f'RECORDING VIDEO {sequence} | Frame {frame_num+1}/{SEQUENCE_LENGTH}', (15,30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)

        # Extraction and Forward-Fill Logic
        if results.multi_hand_landmarks:
            for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                mp_draw.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                
                coords = []
                for lm in hand_landmarks.landmark:
                    coords.extend([lm.x, lm.y, lm.z])
                
                label = handedness.classification[0].label 
                if label == 'Right': 
                    last_known_left = coords
                else: 
                    last_known_right = coords

        final_row = np.concatenate([last_known_left, last_known_right])
        sequence_data.append(final_row)
        
        cv2.imshow('OpenCV Feed', image)
        
        # 3. ALLOW QUITTING MID-RECORDING
        if cv2.waitKey(10) & 0xFF == ord('q'):
            quit_collection = True
            break
            
        frame_num += 1 # Only increase the counter if a valid frame was processed

    if quit_collection:
        print("\n🛑 Recording interrupted mid-video. Partial data discarded.")
        break

    # 4. SAFETY CHECK: ONLY SAVE IF IT HAS EXACTLY 60 FRAMES
    if len(sequence_data) == SEQUENCE_LENGTH:
        npy_path = os.path.join(action_path, str(sequence))
        np.save(npy_path, sequence_data)
        print(f"✅ Saved video {sequence} successfully!")

# Cleanup
cap.release()
cv2.destroyAllWindows()
print("\nCamera closed.")