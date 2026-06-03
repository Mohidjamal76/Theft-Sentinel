import numpy as np
from sklearn.ensemble import RandomForestClassifier
import joblib

class TheftClassifier:
    def __init__(self, model_path="trained_models/theft_classifier.pkl"):
        self.model_path = model_path
        self.model = None
        try:
            self.model = joblib.load(model_path)
            print("🔮 ML theft classifier loaded.")
        except Exception:
            print("⚠ No ML classifier found. Running without ML predictions.")

    def train(self, X, y, save=True):
        print("🧠 Training RandomForest theft classifier...")
        self.model = RandomForestClassifier(
            n_estimators=350,
            max_depth=12,
            class_weight="balanced",
        )
        self.model.fit(X, y)

        if save:
            joblib.dump(self.model, self.model_path)
            print("💾 Saved classifier to:", self.model_path)

    def predict(self, seq):
        """
        Returns probability of theft in range [0, 1].
        """
        if self.model is None:
            return 0.0
        flat = seq.flatten()[None, :]
        prob = self.model.predict_proba(flat)[0][1]
        return float(prob)
