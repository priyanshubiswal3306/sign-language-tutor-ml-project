import cv2
import numpy as np
import tensorflow as tf
from src.config.config import IMG_SIZE, MODEL_PATH
from src.components.data_ingestion import DataIngestion


class WebcamPredictor:
    def __init__(self):
        # Load model
        self.model = tf.keras.models.load_model(MODEL_PATH)

        # Load class names
        ingestion = DataIngestion()
        _, _, self.class_names = ingestion.load_data()

    def preprocess(self, frame):
        img = cv2.resize(frame, (IMG_SIZE, IMG_SIZE))
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

            # Flip for natural mirror view
            frame = cv2.flip(frame, 1)

            # Preprocess
            img = self.preprocess(frame)

            # Predict
            predictions = self.model.predict(img, verbose=0)
            class_index = np.argmax(predictions)
            confidence = np.max(predictions)

            label = self.class_names[class_index]

            # Display text
            text = f"{label} ({confidence:.2f})"

            cv2.putText(frame, text, (20, 50),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1, (0, 255, 0), 2)

            # Show frame
            cv2.imshow("Sign Language Detector", frame)

            # Press Q to exit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    app = WebcamPredictor()
    app.run()