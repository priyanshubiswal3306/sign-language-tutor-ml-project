from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
import tensorflow as tf
from collections import deque
import json
import math
import sys
import os

# Fix imports from root project so we can use the custom normalizer
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
print("Loading models... Please wait.")
static_model = tf.keras.models.load_model("../models/landmark_model.keras")
static_labels = np.load("../models/landmark_labels.npy", allow_pickle=True)

sequence_model = tf.keras.models.load_model("../models/sequence_model.keras")
sequence_labels = np.load("../models/sequence_labels.npy", allow_pickle=True)
print("✅ Models loaded successfully!")

# ================= UTILS =================
def calculate_movement(current_frame, past_frame):
    """Calculates the distance the wrists have moved between two frames to determine if signing is happening."""
    if not current_frame or not past_frame:
        return 0
    
    # Wrist coordinates are usually the first 3 values (x,y,z) of the array
    # We check left hand (indices 0:3) and right hand (indices 63:66)
    movement = 0
    for i in [0, 1, 2, 63, 64, 65]: 
        movement += abs(current_frame[i] - past_frame[i])
    return movement


# ================= WEBSOCKET ENDPOINT =================
@app.websocket("/ws/predict")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # Initialize the sliding window (holds exactly 60 frames, pushes old ones out automatically)
    frame_buffer = deque(maxlen=60)
    frame_counter = 0

    try:
        while True:
            # 1. Receive lightweight JSON from React (NO VIDEO FILES!)
            data = await websocket.receive_text()
            payload = json.loads(data)
            
            mode = payload.get("mode") # "static" (Alphabet) or "dynamic" (Phrases)
            landmarks = payload.get("landmarks") # Array of 63 or 126 floats
            
            if not landmarks:
                continue

            # --------------------------------------------------
            # MODE 1: ALPHABET / SPELLING BEE (Single Frame)
            # --------------------------------------------------
            if mode == "static":
                input_data = np.array([landmarks])
                prediction = static_model.predict(input_data, verbose=0)
                class_index = np.argmax(prediction[0])
                confidence = float(prediction[0][class_index])
                
                await websocket.send_json({
                    "type": "prediction",
                    "label": str(static_labels[class_index]),
                    "confidence": confidence
                })

            # --------------------------------------------------
            # MODE 2: PHRASES (60-Frame Sliding Window)
            # --------------------------------------------------
            elif mode == "dynamic":
                frame_buffer.append(landmarks)
                frame_counter += 1
                
                # Only run prediction if buffer is full AND we process every 5th frame (saves CPU)
                if len(frame_buffer) == 60 and frame_counter % 5 == 0:
                    
                    # ACTION TRIGGER: Are the hands actually moving?
                    movement_score = calculate_movement(frame_buffer[-1], frame_buffer[-10])
                    
                    # If movement is too low, the user is just resting their hands
                    if movement_score < 0.05: # You may need to tune this threshold!
                        await websocket.send_json({
                            "type": "status",
                            "message": "Waiting for movement..."
                        })
                        continue
                    
                    # Hands are moving! Run the sequence prediction
                    sequence_data = np.array([list(frame_buffer)])
                    prediction = sequence_model.predict(sequence_data, verbose=0)
                    class_index = np.argmax(prediction[0])
                    confidence = float(prediction[0][class_index])
                    
                    # Only send if confidence is high enough
                    if confidence > 0.70:
                        await websocket.send_json({
                            "type": "prediction",
                            "label": str(sequence_labels[class_index]),
                            "confidence": confidence
                        })
                        # Clear buffer slightly after a confident prediction to prevent immediate double-guesses
                        for _ in range(30): 
                            frame_buffer.popleft() 

    except WebSocketDisconnect:
        print("Client disconnected from WebSocket.")
    except Exception as e:
        print(f"WebSocket Error: {e}")