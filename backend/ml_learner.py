import os
import json
import math
from datetime import datetime

MODEL_WEIGHTS_FILE = "synapse_ml_weights.json"

DEFAULT_WEIGHTS = {
    "version": 1,
    "total_feedback_samples": 0,
    "weights": {
        "w_exact": 0.45,
        "w_semantic": 0.35,
        "w_coverage": 0.20
    },
    "calibration_bias": 0.0,
    "learned_stopwords": [],
    "recent_updates": []
}

class ActiveLearningClassifier:
    """
    Online Learning Classifier using Stochastic Gradient Descent (SGD) 
    with Logistic/Cross-Entropy Loss to adapt similarity scoring based on
    human reviewer verdicts ('Cleared' vs 'Flagged').
    """
    def __init__(self, filepath=MODEL_WEIGHTS_FILE):
        self.filepath = filepath
        self.learning_rate = 0.05
        self.data = self._load_weights()

    def _load_weights(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return DEFAULT_WEIGHTS.copy()

    def _save_weights(self):
        with open(self.filepath, "w") as f:
            json.dump(self.data, f, indent=2)

    def get_weights(self):
        return self.data["weights"]

    def predict_calibrated_score(self, exact_pct: float, semantic_pct: float, coverage_pct: float) -> dict:
        """
        Infers similarity using current trained weights and calibration bias.
        Formula: sigmoid(w_exact * x1 + w_semantic * x2 + w_cov * x3 + bias)
        """
        w = self.data["weights"]
        bias = self.data.get("calibration_bias", 0.0)

        # Normalized inputs [0, 1]
        x1 = exact_pct / 100.0
        x2 = semantic_pct / 100.0
        x3 = coverage_pct / 100.0

        linear_comb = (w["w_exact"] * x1) + (w["w_semantic"] * x2) + (w["w_coverage"] * x3) + bias
        # Clamp linear combination
        linear_comb = max(-10.0, min(10.0, linear_comb))
        
        # Softmax / Sigmoidal probability
        ml_prob = 1.0 / (1.0 + math.exp(-4.0 * (linear_comb - 0.5)))
        ml_score = round(ml_prob * 100.0, 1)

        return {
            "ml_calibrated_similarity": ml_score,
            "current_weights": w,
            "training_samples": self.data["total_feedback_samples"],
            "model_version": f"v{self.data['version']}"
        }

    def learn_from_reviewer_feedback(self, exact_pct: float, semantic_pct: float, coverage_pct: float, verdict: str, shared_terms: list = None):
        """
        Updates weights through Online Reinforcement / Gradient Descent:
        - If verdict is 'Flagged': target = 1.0 (Plagiarism true positive)
        - If verdict is 'Cleared': target = 0.0 (False positive / benign match)
        """
        if verdict not in ["Flagged", "Cleared"]:
            return None # Skip neutral statuses like 'Pending Review'

        target = 1.0 if verdict == "Flagged" else 0.0
        
        x1 = exact_pct / 100.0
        x2 = semantic_pct / 100.0
        x3 = coverage_pct / 100.0
        
        w = self.data["weights"]
        bias = self.data.get("calibration_bias", 0.0)

        # Current prediction
        pred = (w["w_exact"] * x1) + (w["w_semantic"] * x2) + (w["w_coverage"] * x3) + bias
        error = target - pred # Gradient direction

        # Update weights via Online SGD step
        lr = self.learning_rate
        w["w_exact"] = max(0.1, min(0.7, w["w_exact"] + lr * error * x1))
        w["w_semantic"] = max(0.1, min(0.7, w["w_semantic"] + lr * error * x2))
        w["w_coverage"] = max(0.05, min(0.5, w["w_coverage"] + lr * error * x3))
        
        # Normalize weights so they sum to 1.0
        total_w = w["w_exact"] + w["w_semantic"] + w["w_coverage"]
        w["w_exact"] = round(w["w_exact"] / total_w, 3)
        w["w_semantic"] = round(w["w_semantic"] / total_w, 3)
        w["w_coverage"] = round(1.0 - (w["w_exact"] + w["w_semantic"]), 3)

        # Adjust calibration bias
        bias = max(-0.5, min(0.5, bias + lr * error * 0.5))
        self.data["calibration_bias"] = round(bias, 4)

        # If a paper was 'Cleared' despite high overlap, learn shared terms as false-positive phrases
        if verdict == "Cleared" and shared_terms:
            learned = set(self.data.get("learned_stopwords", []))
            for t in shared_terms[:5]:
                if len(t) > 3:
                    learned.add(t.lower())
            self.data["learned_stopwords"] = list(learned)[:100]

        self.data["total_feedback_samples"] += 1
        self.data["version"] += 1

        update_log = {
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "verdict": verdict,
            "error_adjusted": round(error, 3),
            "new_weights": w.copy(),
            "sample_index": self.data["total_feedback_samples"]
        }
        
        recent = self.data.get("recent_updates", [])
        recent.append(update_log)
        self.data["recent_updates"] = recent[-15:] # Keep last 15 updates

        self._save_weights()
        return update_log

# Singleton model instance
ml_model = ActiveLearningClassifier()
