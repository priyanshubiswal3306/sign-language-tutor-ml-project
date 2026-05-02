import os
import numpy as np
import random

# ================= SETUP =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, '..', 'data', 'sequence_dataset')

# How many augmented copies to make for EACH original video
AUGMENTATIONS_PER_VIDEO = 20  # 20 originals * 20 augments = 400 total videos per phrase!

# ================= AUGMENTATION FUNCTIONS =================
def apply_spatial_noise(data, noise_level=0.005):
    """Injects tiny random variations into the x, y, z coordinates."""
    noise = np.random.normal(0, noise_level, data.shape)
    return data + noise

def apply_temporal_shift(data, max_shift=5):
    """Shifts the frames slightly forward or backward in time to simulate starting early/late."""
    shift = random.randint(-max_shift, max_shift)
    
    # If shift is 0, do nothing
    if shift == 0:
        return data
        
    augmented_data = np.zeros_like(data)
    
    if shift > 0:
        # Shift forward: Pad the beginning with the first frame
        augmented_data[:shift] = data[0]
        augmented_data[shift:] = data[:-shift]
    else:
        # Shift backward: Pad the end with the last frame
        shift = abs(shift)
        augmented_data[:-shift] = data[shift:]
        augmented_data[-shift:] = data[-1]
        
    return augmented_data

# ================= MAIN LOGIC =================
print("🚀 Starting Data Augmentation...")

# Ensure the data directory exists before proceeding
if not os.path.exists(DATA_PATH):
    print(f"❌ Error: Data path '{DATA_PATH}' does not exist.")
    exit()

# Loop through every phrase folder in your dataset
phrases = [f for f in os.listdir(DATA_PATH) if os.path.isdir(os.path.join(DATA_PATH, f))]

for phrase in phrases:
    phrase_path = os.path.join(DATA_PATH, phrase)
    
    # Get all original .npy files. 
    # Because collect_sequence.py saves them as numbers (1.npy, 2.npy), we specifically look for those.
    # This prevents the script from infinitely augmenting its own 'aug_' files if you run it twice!
    original_files = [f for f in os.listdir(phrase_path) if f.endswith('.npy') and f[:-4].isdigit()]
    
    if not original_files:
        print(f"⚠️ No original files found in '{phrase}'. Skipping...")
        continue
        
    print(f"\nProcessing '{phrase}' ({len(original_files)} original videos found)...")
    
    augmentation_count = 0
    
    for filename in original_files:
        file_path = os.path.join(phrase_path, filename)
        original_data = np.load(file_path)
        
        # Generate N augmented variations for this specific video
        for i in range(AUGMENTATIONS_PER_VIDEO):
            # Apply both augmentations randomly
            new_data = apply_temporal_shift(original_data)
            new_data = apply_spatial_noise(new_data)
            
            # Save the new file with a prefix so we know it's artificially generated
            base_name = filename[:-4] # Remove the .npy extension
            new_filename = f"aug_{base_name}_{i}.npy"
            np.save(os.path.join(phrase_path, new_filename), new_data)
            
            augmentation_count += 1
            
    print(f"✅ Generated {augmentation_count} new augmented sequences for '{phrase}'.")

print("\n🎉 Augmentation Complete! Your dataset is now massive and ready for training.")