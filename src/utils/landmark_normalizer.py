import numpy as np

def normalize_landmarks(landmarks, is_left_hand=False):
    """
    landmarks: list of 63 values (x,y,z * 21)
    is_left_hand: True if detected hand is left
    """

    coords = np.array(landmarks).reshape(21, 3)

    # 🔥 Mirror left hand → convert to right-hand format
    if is_left_hand:
        coords[:, 0] = -coords[:, 0]

    # 🔥 Translate (wrist as origin)
    wrist = coords[0]
    coords = coords - wrist

    # 🔥 Scale normalization
    max_dist = np.max(np.linalg.norm(coords, axis=1))
    if max_dist > 0:
        coords = coords / max_dist

    return coords.flatten()