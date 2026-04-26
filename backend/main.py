from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

import numpy as np
import cv2
import tensorflow as tf
import mediapipe as mp
import sys
import os

# 🔥 Fix imports from root project
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.utils.landmark_normalizer import normalize_landmarks

app = FastAPI()

# 🔥 Allow React to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= LOAD MODELS =================

# Letter model (existing)
letter_model = tf.keras.models.load_model("../models/landmark_model.keras")
letter_labels = np.load("../models/landmark_labels.npy")

# 🔥 NEW: Sequence model
sequence_model = tf.keras.models.load_model("../models/sequence_model.keras")
sequence_labels = np.load("../models/sequence_labels.npy")

# ================= MEDIAPIPE =================
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=2)

# ================= SEQUENCE BUFFER =================
sequence_buffer = []
SEQ_LENGTH = 30

# ================= ROUTES =================
@app.get("/")
def home():
    return {"message": "Backend running"}

@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    global sequence_buffer

    contents = await file.read()

    np_arr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)

    letter_label = ""
    normalized_landmarks = None

    # ================= LANDMARK EXTRACTION =================
    if results.multi_hand_landmarks:
        hands_detected = results.multi_hand_landmarks

        # sort hands (left-right consistency)
        hands_detected = sorted(hands_detected, key=lambda h: h.landmark[0].x)

        row = []

        for i in range(2):
            if i < len(hands_detected):
                lm = hands_detected[i]

                temp = []
                for p in lm.landmark:
                    temp.extend([p.x, p.y, p.z])

                # normalize EACH hand
                temp = normalize_landmarks(temp, is_left_hand=False)
                row.extend(temp)
            else:
                row.extend([0.0] * 63)

        if len(row) == 126:
            normalized_landmarks = row

            # ================= LETTER MODEL =================
            data = np.array(row[:63]).reshape(1, -1)  # use first hand for letters

            preds = letter_model.predict(data, verbose=0)
            letter_label = letter_labels[np.argmax(preds)]

    # ================= SEQUENCE MODEL =================
    sequence_prediction = None

    if normalized_landmarks is not None:
        sequence_buffer.append(normalized_landmarks)

        if len(sequence_buffer) > SEQ_LENGTH:
            sequence_buffer.pop(0)

        if len(sequence_buffer) == SEQ_LENGTH:
            seq_input = np.array(sequence_buffer).reshape(1, SEQ_LENGTH, 126)

            preds = sequence_model.predict(seq_input, verbose=0)

            confidence = np.max(preds)
            label_index = np.argmax(preds)

            if confidence > 0.85:
                sequence_prediction = sequence_labels[label_index]

                # 🔥 prevent repeated triggering
                sequence_buffer.clear()

    # ================= FINAL OUTPUT =================
    if sequence_prediction:
        return {"label": sequence_prediction}

    return {"label": letter_label}