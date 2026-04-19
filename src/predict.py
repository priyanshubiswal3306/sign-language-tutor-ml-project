import tensorflow as tf
import numpy as np
import cv2
from src.config.config import IMG_SIZE, MODEL_PATH


class Predictor:
    def __init__(self, class_names):
        self.model = tf.keras.models.load_model(MODEL_PATH)
        self.class_names = class_names

    def preprocess(self, image_path):
        # Read image
        img = cv2.imread(image_path)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        if img is None:
            raise ValueError(f"Image not found at path: {image_path}")

        # Resize to model input size
        img = cv2.resize(img, (IMG_SIZE, IMG_SIZE))

        # Normalize
        img = img / 255.0

        # Add batch dimension
        img = np.expand_dims(img, axis=0)

        return img

    def predict(self, image_path):
        img = self.preprocess(image_path)

        predictions = self.model.predict(img, verbose=0)

        predicted_index = np.argmax(predictions)
        predicted_class = self.class_names[predicted_index]
        confidence = float(np.max(predictions))

        return predicted_class, confidence