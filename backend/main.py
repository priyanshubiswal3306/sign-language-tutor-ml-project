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
    
    sequence = []
    prediction_history = []
    cooldown_frames = 0
    
    HISTORY_LENGTH = 10
    CONFIDENCE_THRESH = 0.85

    # Notice the try block is now INSIDE the while loop!
    while True:
        try:
            data = await websocket.receive_text()
            payload = json.loads(data)
            
            mode = payload.get("mode") 
            landmarks = payload.get("landmarks") 
            
            if not landmarks:
                continue

            # --- STATIC MODE ---
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

            # --- DYNAMIC MODE ---
            elif mode == "dynamic":
                sequence.append(landmarks)
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
            break # Exit the loop if the browser closes
        except Exception as e:
            # THIS IS THE MAGIC FIX: If TF throws an error, print it, but keep listening!
            print(f"⚠️ Frame Error (Ignoring): {e}")