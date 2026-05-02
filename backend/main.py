from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
import tensorflow as tf
import traceback
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

sequence_model = tf.keras.models.load_model(os.path.join(BASE_DIR, "../models/sequence_model.keras"))
sequence_labels = np.load(os.path.join(BASE_DIR, "../models/sequence_labels.npy"), allow_pickle=True)

print("✅ Models loaded successfully!")

# ================= WEBSOCKET ENDPOINT =================
@app.websocket("/ws/predict")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("🟢 React Frontend Connected to WebSocket!")
    
    # Session Variables
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
            hands_data = payload.get("hands", []) # Now an array of hand objects
            
            # --------------------------------------------------
            # MODE 1: STATIC (ALPHABET)
            # --------------------------------------------------
            if mode == "static":
                if not hands_data:
                    continue
                
                # Take the dominant/first hand detected
                hand = hands_data[0]
                is_left = (hand["label"] == "Left")
                
                normalized = normalize_landmarks(hand["landmarks"], is_left_hand=is_left)
                input_data = np.array(normalized).reshape(1, -1)
                
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
                row = []
                
                if hands_data:
                    # Sort hands by X coordinate exactly like the original training script
                    sorted_hands = sorted(hands_data, key=lambda h: h["landmarks"][0])
                    
                    for hand in sorted_hands[:2]:
                        is_left = (hand["label"] == "Left")
                        normalized = normalize_landmarks(hand["landmarks"], is_left_hand=is_left)
                        row.extend(normalized)
                        
                    # Pad to 126 exactly like the original training script
                    if len(sorted_hands) == 1:
                        row.extend([0.0] * 63)
                else:
                    # No hands detected
                    row = [0.0] * 126
                    
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
                    else:
                        # Feed back the confidence so you know it's working!
                        await websocket.send_json({
                            "type": "status", 
                            "message": f"Thinking... ({best_class_score*100:.0f}%)"
                        })

        except WebSocketDisconnect:
            print("🛑 Client disconnected from WebSocket.")
            break
        except Exception as e:
            print(f"⚠️ Frame Error (Ignoring): {e}")
            traceback.print_exc() # Prints the exact math error to terminal if it happens