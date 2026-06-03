import numpy as np

class SequenceCollector:
    def __init__(self, window=10):
        """
        window:
            number of frames to use per sequence (10 for test mode, 30 for final)
        history[track_id] stores last <window> feature vectors.
        """
        self.window = window
        self.history = {}  # track_id -> list of feature vectors

    def add(self, track_id, feature_vector):
        seq = self.history.setdefault(track_id, [])
        seq.append(feature_vector)

        # keep only last <window> frames
        if len(seq) > self.window:
            self.history[track_id] = seq[-self.window:]

    def get_sequence(self, track_id, min_frames=None):
        """
        Returns:
            - 1D numpy array of length (window * feature_dim), padded if needed
            - None if not enough frames

        Behavior:
            - If min_frames is None -> require full window frames
            - If min_frames < window:
                - allow early classification once history >= min_frames
                - but pad sequence to length = window using last frame
        """
        if track_id not in self.history:
            return None

        seq = list(self.history[track_id])

        # default: require full window for training
        if min_frames is None:
            min_frames = self.window

        if len(seq) < min_frames:
            return None

        # keep only last <window> frames
        if len(seq) > self.window:
            seq = seq[-self.window:]

        # pad if shorter than window (for realtime ML)
        if len(seq) < self.window:
            last = seq[-1]
            pad_count = self.window - len(seq)
            seq.extend([last] * pad_count)

        arr = np.array(seq, dtype=np.float32)   # shape: (window, feature_dim)
        return arr.flatten()                    # shape: (window * feature_dim,)
