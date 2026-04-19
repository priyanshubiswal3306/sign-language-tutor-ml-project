import os
from src.components.data_ingestion import DataIngestion
from src.predict import Predictor

if __name__ == "__main__":
    # Load class names
    ingestion = DataIngestion()
    _, _, class_names = ingestion.load_data()

    predictor = Predictor(class_names)

    # 🔹 Choose any class folder (change if you want)
    class_folder = "data/asl_alphabet_train/B"

    # 🔹 Automatically pick first image
    image_name = os.listdir(class_folder)[115]
    image_path = os.path.join(class_folder, image_name)

    print(f"\nTesting on image: {image_path}")

    # Predict
    label, confidence = predictor.predict(image_path)

    print(f"\nPrediction: {label}")
    print(f"Confidence: {round(confidence, 3)}")