import tensorflow as tf
from src.config.config import DATA_PATH, IMG_SIZE, BATCH_SIZE


class DataIngestion:
    def __init__(self):
        self.data_path = DATA_PATH
        self.img_size = IMG_SIZE
        self.batch_size = BATCH_SIZE

    def load_data(self):
        train_data = tf.keras.preprocessing.image_dataset_from_directory(
            self.data_path,
            validation_split=0.2,
            subset="training",
            seed=123,
            image_size=(self.img_size, self.img_size),
            batch_size=self.batch_size
        )

        val_data = tf.keras.preprocessing.image_dataset_from_directory(
            self.data_path,
            validation_split=0.2,
            subset="validation",
            seed=123,
            image_size=(self.img_size, self.img_size),
            batch_size=self.batch_size
        )

        class_names = train_data.class_names

        return train_data, val_data, class_names