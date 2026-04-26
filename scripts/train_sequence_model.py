import numpy as np
import os
from sklearn.preprocessing import LabelEncoder
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.utils import to_categorical

# ================= PATHS =================
DATA_PATH = r"C:\Personal\Projects\sign_language_tutor\data\sequence_dataset"
MODEL_PATH = r"C:\Personal\Projects\sign_language_tutor\models\sequence_model.keras"
LABELS_PATH = r"C:\Personal\Projects\sign_language_tutor\models\sequence_labels.npy"

# ================= LOAD DATA =================
X = []
y = []

labels = os.listdir(DATA_PATH)

print("Loading data...")

for label in labels:
    folder = os.path.join(DATA_PATH, label)

    if not os.path.isdir(folder):
        continue

    for file in os.listdir(folder):
        path = os.path.join(folder, file)

        data = np.load(path)

        X.append(data)
        y.append(label)

X = np.array(X)
y = np.array(y)

print("Data shape:", X.shape)

# ================= ENCODE LABELS =================
encoder = LabelEncoder()
y_encoded = encoder.fit_transform(y)

y_categorical = to_categorical(y_encoded)

# ================= BUILD MODEL =================
model = Sequential([
    LSTM(64, return_sequences=True, input_shape=(30, 126)),
    Dropout(0.2),

    LSTM(64),
    Dropout(0.2),

    Dense(64, activation="relu"),
    Dense(len(labels), activation="softmax")
])

model.compile(
    optimizer="adam",
    loss="categorical_crossentropy",
    metrics=["accuracy"]
)

model.summary()

# ================= TRAIN =================
print("\nTraining...")

model.fit(
    X,
    y_categorical,
    epochs=25,
    batch_size=8
)

# ================= SAVE =================
os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)

model.save(MODEL_PATH)
np.save(LABELS_PATH, encoder.classes_)

print("\nModel saved ✅")