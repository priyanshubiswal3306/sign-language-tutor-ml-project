import streamlit as st
import cv2
import numpy as np
import tensorflow as tf
import mediapipe as mp
import random
import time
import os
import base64

from src.utils.landmark_normalizer import normalize_landmarks

# ================= CONFIG ================= #

st.set_page_config(page_title="Sign Language Tutor", layout="wide")

st.title("🤟 AI Sign Language Tutor")

mode = st.sidebar.selectbox(
    "Select Mode",
    ["Guide", "Detection", "Learning"]
)

# ================= CSS (UI IMPROVEMENT) ================= #

st.markdown("""
<style>
.square-img {
    width: 150px;
    height: 150px;
    background-color: #ffffff;
    border-radius: 15px;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 10px;
    margin-bottom: 10px;
    box-shadow: 0px 2px 8px rgba(0,0,0,0.2);
}

.square-img img {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
    filter: brightness(1.8) contrast(1.2);
}
</style>
""", unsafe_allow_html=True)

# ================= LOAD MODEL ================= #

@st.cache_resource
def load_model():
    model = tf.keras.models.load_model("models/landmark_model.keras")
    labels = np.load("models/landmark_labels.npy")
    return model, labels

model, labels = load_model()

# ================= MEDIAPIPE ================= #

mp_hands = mp.solutions.hands
hands = mp_hands.Hands()
mp_draw = mp.solutions.drawing_utils

# ================= HELPER ================= #

def load_image_as_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

# ================= GUIDE ================= #

if mode == "Guide":
    st.header("📘 Beginner Guide (A–Z)")
    st.write("Learn basic hand signs for each letter.")

    letters = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    cols = st.columns(6)

    for i, letter in enumerate(letters):
        with cols[i % 6]:
            st.subheader(letter)

            img_path = f"data/guide_images/Sign_language_{letter}.svg.png"

            if os.path.exists(img_path):
                img_base64 = load_image_as_base64(img_path)

                st.markdown(f"""
                <div class="square-img">
                    <img src="data:image/png;base64,{img_base64}">
                </div>
                """, unsafe_allow_html=True)

                st.caption(f"Sign for letter {letter}")
            else:
                st.error(f"Missing: {img_path}")

# ================= DETECTION ================= #

elif mode == "Detection":
    st.header("📷 Live Detection")

    run = st.checkbox("Start Camera")

    FRAME_WINDOW = st.image([])

    cap = cv2.VideoCapture(0)

    while run:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        results = hands.process(rgb)

        label = ""

        if results.multi_hand_landmarks:
            for hand_landmarks, hand_info in zip(
                results.multi_hand_landmarks,
                results.multi_handedness
            ):
                is_left = (hand_info.classification[0].label == "Left")

                row = []
                for lm in hand_landmarks.landmark:
                    row.extend([lm.x, lm.y, lm.z])

                if len(row) == 63:
                    normalized = normalize_landmarks(row, is_left_hand=is_left)
                    data = np.array(normalized).reshape(1, -1)

                    preds = model.predict(data, verbose=0)
                    label = labels[np.argmax(preds)]

                mp_draw.draw_landmarks(
                    frame, hand_landmarks, mp_hands.HAND_CONNECTIONS
                )

        cv2.putText(frame, f"Letter: {label}",
                    (20, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1, (0,255,0), 2)

        FRAME_WINDOW.image(frame, channels="BGR")

    cap.release()

# ================= LEARNING MODE ================= #

elif mode == "Learning":
    st.header("🎯 Learning Mode (30 Questions)")

    start = st.button("Start Quiz")

    if start:
        cap = cv2.VideoCapture(0)

        REQUIRED_STABLE = 7
        COOLDOWN = 2
        MAX_QUESTIONS = 30

        stable_label = ""
        stable_count = 0

        target = random.choice(labels)

        score = 0
        total = 0
        last_action_time = 0

        FRAME_WINDOW = st.image([])

        while total < MAX_QUESTIONS:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            results = hands.process(rgb)

            label = ""
            confidence = 0

            current_time = time.time()

            if results.multi_hand_landmarks:
                for hand_landmarks, hand_info in zip(
                    results.multi_hand_landmarks,
                    results.multi_handedness
                ):
                    is_left = (hand_info.classification[0].label == "Left")

                    row = []
                    for lm in hand_landmarks.landmark:
                        row.extend([lm.x, lm.y, lm.z])

                    if len(row) == 63:
                        normalized = normalize_landmarks(row, is_left_hand=is_left)
                        data = np.array(normalized).reshape(1, -1)

                        preds = model.predict(data, verbose=0)
                        class_index = np.argmax(preds)
                        confidence = np.max(preds)

                        label = labels[class_index]

                    mp_draw.draw_landmarks(
                        frame, hand_landmarks, mp_hands.HAND_CONNECTIONS
                    )

            if label == stable_label:
                stable_count += 1
            else:
                stable_label = label
                stable_count = 1

            if current_time - last_action_time > COOLDOWN:
                if stable_count > REQUIRED_STABLE and confidence > 0.7:

                    total += 1

                    if stable_label == target:
                        score += 1

                    target = random.choice(labels)
                    stable_count = 0
                    last_action_time = current_time

            cv2.putText(frame, f"Target: {target}",
                        (20, 50),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1, (0,255,0), 2)

            cv2.putText(frame, f"Score: {score}/{total}",
                        (20, 100),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1, (255,255,0), 2)

            FRAME_WINDOW.image(frame, channels="BGR")

        cap.release()

        st.success(f"Quiz Complete! Score: {score}/{total}")