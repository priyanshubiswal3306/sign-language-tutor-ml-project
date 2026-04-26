from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

import numpy as np
import cv2
import tensorflow as tf
import mediapipe as mp
import sys
import os

# Fix import path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.utils.landmark_normalizer import normalize_landmarks

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= LOAD MODELS =================

# Letter model
letter_model = tf.keras.models.load_model("../models/landmark_model.keras")
letter_labels = np.load("../models/landmark_labels.npy")

# Phrase model
sequence_model = tf.keras.models.load_model("../models/sequence_model.keras")
sequence_labels = np.load("../models/sequence_labels.npy")

# ================= MEDIAPIPE =================
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=2)

# ================= SEQUENCE BUFFER =================
sequence_buffer = []
SEQ_LENGTH = 30

@app.get("/")
def home():
    return {"message": "Backend running"}

# =========================================================
# 🔤 LETTER PREDICTION (UNCHANGED)
# =========================================================
@app.post("/predict-letter")
async def predict_letter(file: UploadFile = File(...)):
    contents = await file.read()

    np_arr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)

    label = ""

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            row = []
            for lm in hand_landmarks.landmark:
                row.extend([lm.x, lm.y, lm.z])

            if len(row) == 63:
                normalized = normalize_landmarks(row, is_left_hand=False)
                data = np.array(normalized).reshape(1, -1)

                preds = letter_model.predict(data, verbose=0)
                label = letter_labels[np.argmax(preds)]

    return {"label": label}


# =========================================================
# ✋ PHRASE (SEQUENCE MODEL)
# =========================================================
@app.post("/predict-phrase")
async def predict_phrase(file: UploadFile = File(...)):
    global sequence_buffer

    contents = await file.read()

    np_arr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)

    if results.multi_hand_landmarks:
        hands_detected = results.multi_hand_landmarks
        hands_detected = sorted(hands_detected, key=lambda h: h.landmark[0].x)

        row = []

        for i in range(2):
            if i < len(hands_detected):
                lm = hands_detected[i]

                temp = []
                for p in lm.landmark:
                    temp.extend([p.x, p.y, p.z])

                temp = normalize_landmarks(temp, is_left_hand=False)
                row.extend(temp)
            else:
                row.extend([0.0] * 63)

        if len(row) == 126:
            sequence_buffer.append(row)

            if len(sequence_buffer) > SEQ_LENGTH:
                sequence_buffer.pop(0)

            # DEBUG
            print("Buffer:", len(sequence_buffer))

            if len(sequence_buffer) == SEQ_LENGTH:
                seq_input = np.array(sequence_buffer).reshape(1, SEQ_LENGTH, 126)

                preds = sequence_model.predict(seq_input, verbose=0)

                confidence = np.max(preds)
                label_index = np.argmax(preds)

                print("Phrase:", sequence_labels[label_index], "Conf:", confidence)

                if confidence > 0.6:
                    sequence_buffer.clear()
                    return {"label": sequence_labels[label_index]}

    return {"label": ""}