from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from .features import ALL_FEATURES, SEVERITY_BY_CATEGORY

MODEL_PATH = Path(__file__).parent / "model.joblib"
_model = None


def _get_model():
    global _model
    if _model is None:
        _model = joblib.load(MODEL_PATH)
    return _model


def score_event(features: dict[str, Any]) -> dict[str, Any]:
    """Score one log event's feature dict against the trained classifier.

    Returns the predicted attack category (or "Normal"), a confidence score,
    a severity bucket, and whether it should be recorded as a threat.
    """
    model = _get_model()
    row = pd.DataFrame([{key: features.get(key) for key in ALL_FEATURES}])
    proba = model.predict_proba(row)[0]
    classes = model.classes_
    best_idx = proba.argmax()
    label = classes[best_idx]
    confidence = float(proba[best_idx])
    return {
        "label": label,
        "score": confidence,
        "severity": SEVERITY_BY_CATEGORY.get(label, "medium"),
        "is_threat": label != "Normal",
    }
