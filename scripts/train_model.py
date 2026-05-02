import os
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping
from sklearn.model_selection import train_test_split
from tensorflow.keras.utils import to_categorical

# ================= SETUP =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, '..', 'data', 'sequence_dataset')
MODEL_SAVE_PATH = os.path.join(BASE_DIR, '..', 'models')

os.makedirs(MODEL_SAVE_PATH, exist_ok=True)

# ================= DATA LOADING =================
print("⏳ Loading and Shuffling dataset...")

actions = np.array([f for f in os.listdir(DATA_PATH) if os.path.isdir(os.path.join(DATA_PATH, f))])
label_map = {label:num for num, label in enumerate(actions)}

sequences, labels = [], []

for action in actions:
    action_path = os.path.join(DATA_PATH, action)
    files = [f for f in os.listdir(action_path) if f.endswith('.npy')]
    
    for file in files:
        res = np.load(os.path.join(action_path, file))
        sequences.append(res)
        labels.append(label_map[action])

X = np.array(sequences)
y = to_categorical(labels).astype(int)

# Split 80% Training / 20% Testing
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, shuffle=True)

print(f"✅ Loaded {X.shape[0]} sequences.")
print(f"🎯 Categories: {actions}")

# ================= STABLE LSTM ARCHITECTURE =================
model = Sequential()

# We use the default tanh activation for LSTMs to prevent Exploding Gradients
model.add(LSTM(64, return_sequences=True, input_shape=(60, 126)))
model.add(Dropout(0.2))

model.add(LSTM(128, return_sequences=False))
model.add(Dropout(0.2))

model.add(Dense(64, activation='relu'))
model.add(Dense(32, activation='relu'))
model.add(Dense(actions.shape[0], activation='softmax'))

# clipvalue=1.0 prevents the "Mathematical Explosion" (Loss jumping to 300+)
optimizer = tf.keras.optimizers.Adam(learning_rate=0.001, clipvalue=1.0)

model.compile(optimizer=optimizer, loss='categorical_crossentropy', metrics=['categorical_accuracy'])

# ================= TRAINING =================
early_stop = EarlyStopping(
    monitor='val_loss', 
    patience=15, 
    restore_best_weights=True,
    verbose=1
)

print("\n🚀 Training started (Stable Version)...")
model.fit(
    X_train, y_train, 
    epochs=100, 
    batch_size=32, 
    validation_data=(X_test, y_test), 
    callbacks=[early_stop]
)

# ================= SAVING =================
print("\n💾 Saving model and labels...")
model.save(os.path.join(MODEL_SAVE_PATH, 'phrase_model.keras'))
np.save(os.path.join(MODEL_SAVE_PATH, 'phrase_labels.npy'), actions)

print("🎉 DONE! This model should be significantly more accurate.")