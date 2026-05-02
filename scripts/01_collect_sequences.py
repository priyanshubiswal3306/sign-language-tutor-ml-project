import cv2
import mediapipe as mp
import numpy as np
import os

# ================= SETUP =================
mp_hands = mp.solutions.hands
# max_num_hands MUST be 2 for phrases!
hands = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.5, min_tracking_confidence=0.5)
mp_draw = mp.solutions.drawing_utils

DATA_PATH = os.path.join('data', 'phrase_sequences')
SEQUENCE_LENGTH = 60 # Number of frames per video

# ================= GET INPUT =================
action = input("Enter the phrase you are recording (e.g., 'hello', 'thank_you'): ").lower()
no_sequences = int(input("How many videos do you want to record? (e.g., 20): "))

# Create folder for this phrase
action_path = os.path.join(DATA_PATH, action)
os.makedirs(action_path, exist_ok=True)

# Find the next available folder number so we don't overwrite old data
dirmax = np.max([int(d) for d in os.listdir(action_path)]) if os.listdir(action_path) else 0

cap = cv2.VideoCapture(0)

print(f"\n🎥 GET READY! Recording {no_sequences} videos for '{action}'.")
print("Press SPACE to start the sequence collection...\n")

# Wait for user to press space before starting
while True:
    ret, frame = cap.read()
    cv2.putText(frame, 'Press SPACE to start', (120,200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255, 0), 4, cv2.LINE_AA)
    cv2.imshow('OpenCV Feed', frame)
    if cv2.waitKey(10) & 0xFF == ord(' '):
        break

# ================= RECORDING LOOP =================
for sequence in range(dirmax + 1, dirmax + 1 + no_sequences):
    
    sequence_data = []
    
    # 🧠 THE FORWARD-FILL MEMORY VARIABLES
    # If a hand isn't detected in frame 1, it starts at 0.0
    last_known_left = [0.0] * 63
    last_known_right = [0.0] * 63

    for frame_num in range(SEQUENCE_LENGTH):
        ret, frame = cap.read()
        frame = cv2.flip(frame, 1) # Mirror image

        # Convert to RGB for MediaPipe
        image, results = frame, hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        
        # Draw text so you know what is happening
        if frame_num == 0: 
            cv2.putText(image, 'STARTING COLLECTION...', (120,200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255, 0), 4, cv2.LINE_AA)
            cv2.putText(image, f'Collecting video {sequence}', (15,12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)
            cv2.imshow('OpenCV Feed', image)
            cv2.waitKey(2000) # 2 second pause between videos so you can reset your hands
        else: 
            cv2.putText(image, f'Collecting video {sequence} | Frame {frame_num}/60', (15,12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)

        # --------------------------------------------------
        # THE MAGIC LOGIC: Extract and Forward-Fill
        # --------------------------------------------------
        if results.multi_hand_landmarks:
            for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                mp_draw.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                
                # Extract the 63 coordinates
                coords = []
                for lm in hand_landmarks.landmark:
                    coords.extend([lm.x, lm.y, lm.z])
                
                # Check which hand it is and update our memory!
                # Note: MediaPipe handedness is flipped when using cv2.flip
                label = handedness.classification[0].label 
                if label == 'Right': # This is actually the Left hand on screen
                    last_known_left = coords
                else: # This is actually the Right hand on screen
                    last_known_right = coords

        # Combine them into our 126-feature array
        # If MediaPipe missed a hand this frame, it just uses the last_known coordinates!
        final_row = np.concatenate([last_known_left, last_known_right])
        sequence_data.append(final_row)
        
        cv2.imshow('OpenCV Feed', image)
        cv2.waitKey(10)

    # Save this 60-frame video as a numpy array file (.npy is much faster than CSV for sequences)
    npy_path = os.path.join(action_path, str(sequence))
    np.save(npy_path, sequence_data)

cap.release()
cv2.destroyAllWindows()
print("\n✅ Collection Complete!")