from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

import numpy as np
import cv2
import tensorflow as tf
import mediapipe as mp
import tempfile
import sys
import os
from collections import deque

# Fix imports from root project so we can use the custom normalizer
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.utils.landmark_normalizer import normalize_landmarks

app = FastAPI()

# Allow React to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= LOAD MODELS =================
print("⏳ Loading models... Please wait.")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

static_model = tf.keras.models.load_model(os.path.join(BASE_DIR, "../models/landmark_model.keras"))
static_labels = np.load(os.path.join(BASE_DIR, "../models/landmark_labels.npy"), allow_pickle=True)

sequence_model = tf.keras.models.load_model(os.path.join(BASE_DIR, "../models/sequence_model.keras"))
sequence_labels = np.load(os.path.join(BASE_DIR, "../models/sequence_labels.npy"), allow_pickle=True)

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=2, min_detection_confidence=0.5)

print("✅ Models loaded successfully!")

@app.get("/")
def home():
    return {"message": "Sign Language Tutor Backend is running!"}

# ================= ENDPOINT 1: STATIC (LETTERS/WORDS) =================
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

    # Extract exactly 60 frames
    while len(frames) < 60: 
        ret, frame = cap.read()
        if not ret: break
            
        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = hands.process(rgb)
        
        row = []
        if result.multi_hand_landmarks:
            # Pair landmarks with handedness
            hands_detected = list(zip(result.multi_hand_landmarks, result.multi_handedness))
            
            # Sort hands left-to-right to ensure consistency
            hands_detected = sorted(hands_detected, key=lambda h: h[0].landmark[0].x)
            
            for hand_landmarks, hand_info in hands_detected[:2]:
                is_left = (hand_info.classification[0].label == "Left")
                
                raw_coords = []
                for lm in hand_landmarks.landmark:
                    raw_coords.extend([lm.x, lm.y, lm.z])
                
                normalized = normalize_landmarks(raw_coords, is_left_hand=is_left)
                row.extend(normalized)
                
            # Pad if only one hand is detected
            if len(hands_detected) == 1:
                row.extend([0.0] * 63)
        else:
            # Pad if no hands are detected
            row = [0.0] * 126 
            
        frames.append(row)
    cap.release()
    
    # Clean up the temporary file
    if os.path.exists(temp_video_path):
        os.remove(temp_video_path)
        
    # Abort if the recording didn't capture enough frames
    if len(frames) != 60:
        return {"label": "", "error": f"Sequence too short ({len(frames)}/60)"}

    # Reshape the data for the LSTM model
    sequence_data = np.array([frames])
    
    # Get prediction
    prediction = sequence_model.predict(sequence_data, verbose=0)
    class_index = np.argmax(prediction[0])
    confidence = float(prediction[0][class_index])
    
    # --- DEBUGGING: PRINT THE MODEL'S "BRAIN" OUTPUT ---
    print("\n" + "="*30)
    print("🧠 MODEL PREDICTION BREAKDOWN")
    print("="*30)
    print(f"Top Guess: {sequence_labels[class_index]} ({confidence * 100:.1f}%)")
    print("-" * 30)
    
    for label, prob in zip(sequence_labels, prediction[0]):
        print(f"  {label.ljust(15)} : {prob * 100:>5.1f}%")
    print("="*30 + "\n")
    # ---------------------------------------------------
    
    # Only return the label to React if the AI is confident (> 70%)
    if confidence > 0.7:
        predicted_label = str(sequence_labels[class_index])
    else:
        predicted_label = ""
        
    return {"label": predicted_label, "confidence": confidence}

# ================= WEBSOCKET ROUTE FOR REAL-TIME PREDICTIONS =================
sequence_window = deque(maxlen=60)

@app.websocket("/ws/predict")
async def websocket_predict(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            payload = await websocket.receive_json()
            mode = payload.get("mode")
            landmarks = payload.get("landmarks", [])
            label = ""

            if mode == "static" and len(landmarks) == 63:
                normalized = normalize_landmarks(landmarks, is_left_hand=False)
                data = np.array(normalized).reshape(1, -1)
                preds = static_model.predict(data, verbose=0)
                label = str(static_labels[np.argmax(preds)])
                await websocket.send_json({"type": "prediction", "label": label})

            elif mode == "dynamic" and len(landmarks) == 126:
                sequence_window.append(landmarks)
                if len(sequence_window) == sequence_window.maxlen:
                    sequence_data = np.array([list(sequence_window)])
                    prediction = sequence_model.predict(sequence_data, verbose=0)
                    class_index = np.argmax(prediction[0])
                    confidence = float(prediction[0][class_index])
                    if confidence > 0.7:
                        label = str(sequence_labels[class_index])
                    await websocket.send_json({"type": "prediction", "label": label})
                else:
                    await websocket.send_json({"type": "status", "message": f"buffering {len(sequence_window)}/{sequence_window.maxlen}"})

            else:
                await websocket.send_json({"type": "status", "message": "waiting for valid landmarks..."})
    except WebSocketDisconnect:
        print("WebSocket client disconnected")
