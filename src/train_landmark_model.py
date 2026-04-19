import os
import pandas as pd
import numpy as np
import tensorflow as tf
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from tensorflow.keras import layers, models

DATA_DIR = "data/landmarks"

X = []
y = []

# Load data
for file in os.listdir(DATA_DIR):
    if file.endswith(".csv"):
        label = file.split(".")[0]

        file_path = os.path.join(DATA_DIR, file)
        df = pd.read_csv(file_path, header=None)

        for row in df.values:
            X.append(row)
            y.append(label)

X = np.array(X)
y = np.array(y)

print("Total samples:", len(X))

# Encode labels
encoder = LabelEncoder()
y_encoded = encoder.fit_transform(y)

# Save label mapping
os.makedirs("models", exist_ok=True)
np.save("models/landmark_labels.npy", encoder.classes_)

# Split
X_train, X_val, y_train, y_val = train_test_split(
    X, y_encoded, test_size=0.2, random_state=42
)

# Model
model = models.Sequential([
    layers.Dense(128, activation='relu', input_shape=(63,)),
    layers.Dropout(0.3),

    layers.Dense(64, activation='relu'),
    layers.Dropout(0.3),

    layers.Dense(len(encoder.classes_), activation='softmax')
])

model.compile(
    optimizer='adam',
    loss='sparse_categorical_crossentropy',
    metrics=['accuracy']
)

# Train
history = model.fit(
    X_train, y_train,
    validation_data=(X_val, y_val),
    epochs=20,
    batch_size=32
)

# Save model
model.save("models/landmark_model.keras")

print("\n✅ Model trained and saved!")