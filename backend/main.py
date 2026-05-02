from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
import tensorflow as tf
import json
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
print("⏳ Loading models... Please wait.")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

static_model = tf.keras.models.load_model(os.path.join(BASE_DIR, "../models/landmark_model.keras"))
static_labels = np.load(os.path.join(BASE_DIR, "../models/landmark_labels.npy"), allow_pickle=True)

# Note: Ensure this matches the name you saved your phrase model as! 
sequence_model = tf.keras.models.load_model(os.path.join(BASE_DIR, "../models/sequence_model.keras"))
sequence_labels = np.load(os.path.join(BASE_DIR, "../models/sequence_labels.npy"), allow_pickle=True)

print("✅ Models loaded successfully!")

# ================= WEBSOCKET ENDPOINT =================
@app.websocket("/ws/predict")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("🟢 React Frontend Connected to WebSocket!")
    
    # --- Session Variables for Dynamic Mode ---
    sequence = []
    prediction_history = []
    cooldown_frames = 0
    
    # Stability Tuning Parameters
    HISTORY_LENGTH = 10
    CONFIDENCE_THRESH = 0.85

    try:
        while True:
            # 1. Receive lightweight JSON from React
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
            # MODE 2: PHRASES (Sliding Window & Probability Smoothing)
            # --------------------------------------------------
            elif mode == "dynamic":
                
                # 1. Update Sliding Window
                sequence.append(landmarks)
                sequence = sequence[-60:]
                
                # 2. Handle Cooldown
                if cooldown_frames > 0:
                    cooldown_frames -= 1
                    # Let the frontend know we are cooling down so it doesn't wait in silence
                    await websocket.send_json({
                        "type": "status",
                        "message": "Wait..."
                    })
                    continue
                
                # 3. Prediction Logic (Only if window is full and no cooldown)
                if len(sequence) == 60 and cooldown_frames == 0:
                    
                    # Convert to batch format for prediction: (1, 60, 126)
                    sequence_data = np.expand_dims(sequence, axis=0)
                    res = sequence_model.predict(sequence_data, verbose=0)[0]
                    
                    # Add to history and calculate the rolling average
                    prediction_history.append(res)
                    prediction_history = prediction_history[-HISTORY_LENGTH:]
                    
                    avg_probs = np.mean(prediction_history, axis=0)
                    best_class_idx = np.argmax(avg_probs)
                    best_class_score = avg_probs[best_class_idx]
                    predicted_word = str(sequence_labels[best_class_idx])
                    
                    # 4. Decision & Output Logic
                    if best_class_score > CONFIDENCE_THRESH:
                        # Ignore the neutral class completely
                        if predicted_word != 'neutral':
                            
                            # Send confident prediction to React!
                            await websocket.send_json({
                                "type": "prediction",
                                "label": predicted_word,
                                "confidence": float(best_class_score)
                            })
                            
                            # Trigger cooldown to prevent word spamming
                            cooldown_frames = 30
                            
                            # Wipe the prediction history clean so the high average
                            # doesn't accidentally trigger a second prediction
                            prediction_history.clear()
                        else:
                            # If it's neutral, just tell React we are tracking but not signing
                            await websocket.send_json({
                                "type": "status",
                                "message": "Listening..."
                            })

    except WebSocketDisconnect:
        print("🛑 Client disconnected from WebSocket.")
    except Exception as e:
        print(f"⚠️ WebSocket Error: {e}")