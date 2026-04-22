import numpy as np

def normalize_landmarks(landmarks, is_left_hand=False):
    coords = np.array(landmarks).reshape(21, 3)

    # Mirror left hand
    if is_left_hand:
        coords[:, 0] = -coords[:, 0]

    # Translate (wrist = origin)
    wrist = coords[0]
    coords = coords - wrist

    # Scale normalize
    max_dist = np.max(np.linalg.norm(coords, axis=1))
    if max_dist > 0:
        coords = coords / max_dist

    return coords.flatten()