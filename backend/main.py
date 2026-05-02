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
    print("🟢 React Frontend Connected!")
    
    while True:
        try:
            data = await websocket.receive_text()
            payload = json.loads(data)
            mode = payload.get("mode") 

            # --------------------------------------------------
            # MODE 1: STATIC (ALPHABET)
            # --------------------------------------------------
            if mode == "static":
                hands_data = payload.get("hands", [])
                if not hands_data:
                    continue
                
                # Original static model was trained WITHOUT cv2.flip
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
                frames = payload.get("sequence", [])
                if len(frames) != 60:
                    continue
                
                processed_sequence = []
                for frame_hands in frames:
                    row = []
                    if frame_hands:
                        # 1. EMULATE cv2.flip(1) FROM YOUR TRAINING SCRIPT
                        # We must invert the X axis (1.0 - x) and swap Left/Right labels
                        flipped_hands = []
                        for h in frame_hands:
                            f_label = "Left" if h["label"] == "Right" else "Right"
                            f_landmarks = []
                            # Iterate through x, y, z blocks
                            for i in range(0, 63, 3):
                                f_landmarks.extend([1.0 - h["landmarks"][i], h["landmarks"][i+1], h["landmarks"][i+2]])
                            flipped_hands.append({"label": f_label, "landmarks": f_landmarks})

                        # 2. Sort Left-to-Right based on the new flipped coordinates
                        sorted_hands = sorted(flipped_hands, key=lambda h: h["landmarks"][0])
                        
                        # 3. Normalize and build the 126-length array
                        for h in sorted_hands[:2]:
                            is_left = (h["label"] == "Left")
                            normalized = normalize_landmarks(h["landmarks"], is_left_hand=is_left)
                            row.extend(normalized)
                            
                        # Pad if only 1 hand
                        if len(sorted_hands) == 1:
                            row.extend([0.0] * 63)
                    else:
                        # Pad if 0 hands
                        row = [0.0] * 126
                        
                    processed_sequence.append(row)

                # Predict
                sequence_data = np.array([processed_sequence])
                preds = sequence_model.predict(sequence_data, verbose=0)
                class_index = np.argmax(preds[0])
                confidence = float(preds[0][class_index])
                predicted_word = str(sequence_labels[class_index])

                if confidence > 0.70:
                    if predicted_word != 'neutral':
                        await websocket.send_json({
                            "type": "prediction", 
                            "label": predicted_word, 
                            "confidence": confidence
                        })
                    else:
                        await websocket.send_json({"type": "status", "message": "Listening..."})
                else:
                    await websocket.send_json({"type": "status", "message": f"Thinking... ({confidence*100:.0f}%)"})

        except WebSocketDisconnect:
            print("🛑 Frontend Disconnected.")
            break
        except Exception as e:
            print(f"⚠️ Math/Format Error (Ignoring): {e}")