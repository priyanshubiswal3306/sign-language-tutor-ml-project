from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

import numpy as np
import cv2
import tensorflow as tf
import mediapipe as mp
import tempfile
import sys
import os

# Fix imports from root project
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.utils.landmark_normalizer import normalize_landmarks

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= LOAD MODELS =================
print("Loading models...")
static_model = tf.keras.models.load_model("../models/landmark_model.keras")
static_labels = np.load("../models/landmark_labels.npy", allow_pickle=True)

sequence_model = tf.keras.models.load_model("../models/sequence_model.keras")
sequence_labels = np.load("../models/sequence_labels.npy", allow_pickle=True)

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=2, min_detection_confidence=0.5)

print("Models loaded successfully!")

@app.get("/")
def home():
    return {"message": "Backend running"}

# ================= ENDPOINT 1: STATIC (LETTERS) =================
@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    contents = await file.read()
    np_arr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)

    label = ""
    if results.multi_hand_landmarks:
        for hand_landmarks, hand_info in zip(results.multi_hand_landmarks, results.multi_handedness):
            is_left = (hand_info.classification[0].label == "Left")
            row = []
            for lm in hand_landmarks.landmark:
                row.extend([lm.x, lm.y, lm.z])

            if len(row) == 63:
                normalized = normalize_landmarks(row, is_left_hand=is_left)
                data = np.array(normalized).reshape(1, -1)
                preds = static_model.predict(data, verbose=0)
                label = str(static_labels[np.argmax(preds)])

    return {"label": label} 

# ================= ENDPOINT 2: SEQUENCE (PHRASES) =================
@app.post("/predict_sequence")
async def predict_sequence(file: UploadFile = File(...)):
    temp_dir = tempfile.gettempdir()
    temp_video_path = os.path.join(temp_dir, "temp_sequence.webm")
    
    with open(temp_video_path, "wb") as buffer:
        buffer.write(await file.read())

    cap = cv2.VideoCapture(temp_video_path)
    frames = []

    # Updated to extract 60 frames
    while len(frames) < 60: 
        ret, frame = cap.read()
        if not ret: break
            
        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = hands.process(rgb)
        
        row = []
        if result.multi_hand_landmarks:
            hands_detected = result.multi_hand_landmarks
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
    
    if os.path.exists(temp_video_path):
        os.remove(temp_video_path)
        
    if len(frames) != 60:
        return {"label": "", "error": f"Sequence too short ({len(frames)}/60)"}

    sequence_data = np.array([frames])
    prediction = sequence_model.predict(sequence_data, verbose=0)
    class_index = np.argmax(prediction[0])
    confidence = float(prediction[0][class_index])
    
    if confidence > 0.7:
        predicted_label = str(sequence_labels[class_index])
    else:
        predicted_label = ""
        
    return {"label": predicted_label, "confidence": confidence}