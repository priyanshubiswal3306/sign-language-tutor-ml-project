import numpy as np
import os
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.utils import to_categorical
from tensorflow.keras.callbacks import EarlyStopping

# ================= PATHS =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "..", "data", "sequence_dataset")
MODEL_PATH = os.path.join(BASE_DIR, "..", "models", "sequence_model.keras")
LABELS_PATH = os.path.join(BASE_DIR, "..", "models", "sequence_labels.npy")

# ================= LOAD DATA =================
X, y = [], []
labels = [d for d in os.listdir(DATA_PATH) if os.path.isdir(os.path.join(DATA_PATH, d))]

print("Loading normalized sequence data...")

for label in labels:
    folder = os.path.join(DATA_PATH, label)
    for file in os.listdir(folder):
        if file.endswith(".npy"):
            path = os.path.join(folder, file)
            data = np.load(path)
            X.append(data)
            y.append(label)

X = np.array(X)
y = np.array(y)

print(f"Total sequences loaded: {X.shape[0]}")
print(f"Data shape: {X.shape}") # Should be (Num_Samples, 60, 126)

# ================= ENCODE LABELS =================
encoder = LabelEncoder()
y_encoded = encoder.fit_transform(y)
y_categorical = to_categorical(y_encoded)

X_train, X_test, y_train, y_test = train_test_split(X, y_categorical, test_size=0.1, random_state=42)

# ================= BUILD MODEL =================
model = Sequential([
    # Input shape updated to 60 frames
    LSTM(128, return_sequences=True, input_shape=(60, 126)),
    Dropout(0.5), 
    
    LSTM(64),
    Dropout(0.5),

    Dense(64, activation="relu"),
    Dense(len(labels), activation="softmax")
])

model.compile(optimizer="adam", loss="categorical_crossentropy", metrics=["accuracy"])
model.summary()

# ================= TRAIN =================
print("\nTraining Model...")
early_stopping = EarlyStopping(monitor='val_loss', patience=15, restore_best_weights=True)

history = model.fit(
    X_train, y_train,
    validation_data=(X_test, y_test),
    epochs=100, 
    batch_size=16,
    callbacks=[early_stopping]
)

# ================= SAVE =================
model.save(MODEL_PATH)
np.save(LABELS_PATH, encoder.classes_)

print("\n🎉 Sequence Model trained and saved successfully!")