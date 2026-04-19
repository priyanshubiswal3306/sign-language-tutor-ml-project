import tensorflow as tf
from tensorflow.keras import layers, models
from src.config.config import IMG_SIZE, MODEL_PATH, EPOCHS


class ModelTrainer:
    def __init__(self, num_classes):
        self.num_classes = num_classes

    def build_model(self, data_augmentation):
        model = models.Sequential([
            data_augmentation,

            layers.Conv2D(32, (3,3), activation='relu', input_shape=(IMG_SIZE, IMG_SIZE, 3)),
            layers.MaxPooling2D(),

            layers.Conv2D(64, (3,3), activation='relu'),
            layers.MaxPooling2D(),

            layers.Conv2D(128, (3,3), activation='relu'),
            layers.MaxPooling2D(),

            layers.Flatten(),
            layers.Dense(128, activation='relu'),
            layers.Dropout(0.5),

            layers.Dense(self.num_classes, activation='softmax')
        ])

        return model

    def train(self, train_data, val_data, data_augmentation):
        model = self.build_model(data_augmentation)

        model.compile(
            optimizer='adam',
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy']
        )

        history = model.fit(
            train_data,
            validation_data=val_data,
            epochs=EPOCHS
        )

        model.save(MODEL_PATH)

        return model, history