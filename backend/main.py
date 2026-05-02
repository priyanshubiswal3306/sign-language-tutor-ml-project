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
static_model = tf.keras.models.load_model("../models/landmark_model.keras")
static_labels = np.load("../models/landmark_labels.npy", allow_pickle=True)

sequence_model = tf.keras.models.load_model("../models/sequence_model.keras")
sequence_labels = np.load("../models/sequence_labels.npy", allow_pickle=True)
print("✅ Models loaded successfully!")


# ================= WEBSOCKET ENDPOINT =================
@app.websocket("/ws/predict")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("🟢 React Frontend Connected to WebSocket!")
    
    # Session Variables for Sequence Model
    sequence = []
    prediction_history = []
    cooldown_frames = 0
    
    HISTORY_LENGTH = 10
    CONFIDENCE_THRESH = 0.85

    while True:
        try:
            data = await websocket.receive_text()
            payload = json.loads(data)
            
            mode = payload.get("mode") 
            landmarks = payload.get("landmarks") 
            is_left = payload.get("isLeft", False) # Used for static mode
            
            if not landmarks:
                continue

            # --------------------------------------------------
            # MODE 1: STATIC (ALPHABET)
            # --------------------------------------------------
            if mode == "static":
                # CRITICAL FIX: Apply your normalizer before predicting!
                normalized = normalize_landmarks(landmarks, is_left_hand=is_left)
                input_data = np.array([normalized]).reshape(1, -1)
                
                prediction = static_model.predict(input_data, verbose=0)
                class_index = np.argmax(prediction[0])
                confidence = float(prediction[0][class_index])
                
                await websocket.send_json({
                    "type": "prediction",
                    "label": str(static_labels[class_index]),
                    "confidence": confidence
                })

            # --------------------------------------------------
            # MODE 2: DYNAMIC (PHRASES)
            # --------------------------------------------------
            elif mode == "dynamic":
                # Split the 126 coordinates back into left and right hands
                left_raw = landmarks[:63]
                right_raw = landmarks[63:]
                
                # CRITICAL FIX: Apply normalizer to each hand, or pad with zeros if hand is missing
                left_norm = normalize_landmarks(left_raw, is_left_hand=True) if sum(left_raw) != 0 else [0.0] * 63
                right_norm = normalize_landmarks(right_raw, is_left_hand=False) if sum(right_raw) != 0 else [0.0] * 63
                
                row = left_norm + right_norm
                sequence.append(row)
                sequence = sequence[-60:]
                
                if cooldown_frames > 0:
                    cooldown_frames -= 1
                    await websocket.send_json({"type": "status", "message": "Wait..."})
                    continue
                
                if len(sequence) == 60 and cooldown_frames == 0:
                    sequence_data = np.expand_dims(sequence, axis=0)
                    res = sequence_model.predict(sequence_data, verbose=0)[0]
                    
                    prediction_history.append(res)
                    prediction_history = prediction_history[-HISTORY_LENGTH:]
                    
                    avg_probs = np.mean(prediction_history, axis=0)
                    best_class_idx = np.argmax(avg_probs)
                    best_class_score = avg_probs[best_class_idx]
                    predicted_word = str(sequence_labels[best_class_idx])
                    
                    if best_class_score > CONFIDENCE_THRESH:
                        if predicted_word != 'neutral':
                            await websocket.send_json({
                                "type": "prediction",
                                "label": predicted_word,
                                "confidence": float(best_class_score)
                            })
                            cooldown_frames = 30
                            prediction_history.clear()
                        else:
                            await websocket.send_json({"type": "status", "message": "Listening..."})

        except WebSocketDisconnect:
            print("🛑 Client disconnected from WebSocket.")
            break
        except Exception as e:
            # Prevents the connection from dying if one frame causes a math error
            print(f"⚠️ Frame Error (Ignoring): {e}")