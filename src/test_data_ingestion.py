from src.components.data_ingestion import DataIngestion
from src.components.data_transformation import DataTransformation
from src.components.model_trainer import ModelTrainer

if __name__ == "__main__":
    ingestion = DataIngestion()
    train_data, val_data, class_names = ingestion.load_data()

    transformation = DataTransformation()
    train_data, val_data, augmentation = transformation.transform(train_data, val_data)

    trainer = ModelTrainer(num_classes=len(class_names))
    model, history = trainer.train(train_data, val_data, augmentation)

    print("\n✅ Model training completed")