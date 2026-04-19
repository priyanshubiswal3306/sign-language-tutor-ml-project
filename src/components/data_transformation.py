import tensorflow as tf
from tensorflow.keras import layers


class DataTransformation:
    def __init__(self):
        # Normalization layer
        self.normalization_layer = layers.Rescaling(1./255)

        # Data augmentation
        self.data_augmentation = tf.keras.Sequential([
            layers.RandomFlip("horizontal"),
            layers.RandomRotation(0.1),
            layers.RandomZoom(0.1),
        ])

    def transform(self, train_data, val_data):
        # Apply normalization
        train_data = train_data.map(lambda x, y: (self.normalization_layer(x), y))
        val_data = val_data.map(lambda x, y: (self.normalization_layer(x), y))

        return train_data, val_data, self.data_augmentation