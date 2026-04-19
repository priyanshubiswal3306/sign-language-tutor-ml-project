import cv2
import numpy as np
import tensorflow as tf
import mediapipe as mp
from src.config.config import IMG_SIZE, MODEL_PATH
from src.components.data_ingestion import DataIngestion


class SmartWebcamPredictor:
    def __init__(self):
        # Load model
        self.model = tf.keras.models.load_model(MODEL_PATH)

        # Load class names
        ingestion = DataIngestion()
        _, _, self.class_names = ingestion.load_data()

        # MediaPipe setup
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(max_num_hands=1)
        self.mp_draw = mp.solutions.drawing_utils

        # 🔥 Prediction smoothing buffer
        self.pred_buffer = []
        self.buffer_size = 5

    def preprocess(self, img):
        img = cv2.resize(img, (IMG_SIZE, IMG_SIZE))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = img / 255.0
        img = np.expand_dims(img, axis=0)
        return img

    def run(self):
        cap = cv2.VideoCapture(0)

        if not cap.isOpened():
            print("Error: Cannot access webcam")
            return

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(rgb_frame)

            label = ""
            confidence = 0

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:

                    # Get bounding box
                    x_list = []
                    y_list = []

                    for lm in hand_landmarks.landmark:
                        x_list.append(int(lm.x * w))
                        y_list.append(int(lm.y * h))

                    xmin, xmax = min(x_list), max(x_list)
                    ymin, ymax = min(y_list), max(y_list)

                    # 🔥 Increased padding (better context)
                    pad = 40
                    xmin = max(0, xmin - pad)
                    ymin = max(0, ymin - pad)
                    xmax = min(w, xmax + pad)
                    ymax = min(h, ymax + pad)

                    # Crop hand
                    hand_img = frame[ymin:ymax, xmin:xmax]

                    if hand_img.size != 0:
                        img = self.preprocess(hand_img)
                        preds = self.model.predict(img, verbose=0)

                        class_index = np.argmax(preds)
                        confidence = np.max(preds)

                        # 🔥 Add to buffer
                        self.pred_buffer.append(class_index)
                        if len(self.pred_buffer) > self.buffer_size:
                            self.pred_buffer.pop(0)

                        # 🔥 Majority voting
                        final_index = max(set(self.pred_buffer), key=self.pred_buffer.count)
                        label = self.class_names[final_index]

                    # Draw bounding box
                    cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), (0, 255, 0), 2)

                    # Draw landmarks
                    self.mp_draw.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)

            # 🔥 Confidence threshold display
            if confidence > 0.7:
                text = f"{label} ({confidence:.2f})"
            else:
                text = "Detecting..."

            cv2.putText(frame, text,
                        (20, 50),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1, (0, 255, 0), 2)

            cv2.imshow("Smart Sign Detection", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    app = SmartWebcamPredictor()
    app.run()