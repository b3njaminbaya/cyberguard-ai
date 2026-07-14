import json
from collections import defaultdict
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from .features import ALL_FEATURES, CATEGORICAL_FEATURES, NUMERIC_FEATURES, TARGET

DATA_PATH = Path(__file__).parent.parent / "data" / "UNSW_NB15_training-set.csv"
MODEL_PATH = Path(__file__).parent / "model.joblib"
METRICS_PATH = Path(__file__).parent / "metrics.json"
EXPLAIN_PATH = Path(__file__).parent / "explainability.json"


def _aggregate_feature_importance(preprocessor, importances) -> dict[str, float]:
    """RandomForest reports importance per one-hot column (194 of them, mostly
    single protocol values). Sum those back to the original 39 feature names
    so 'proto' has one importance score, not 130 near-zero ones."""
    names = preprocessor.get_feature_names_out()
    totals: dict[str, float] = defaultdict(float)
    for name, importance in zip(names, importances):
        if name.startswith("remainder__"):
            key = name.removeprefix("remainder__")
        else:
            # cat__proto_tcp -> proto, cat__service_http -> service, etc.
            key = name.removeprefix("cat__").rsplit("_", 1)[0]
        totals[key] += float(importance)
    return dict(totals)


def train_model() -> dict:
    """Trains the classifier on the real UNSW-NB15 dataset and saves it to
    MODEL_PATH/METRICS_PATH, plus feature-importance and Normal-baseline
    stats to EXPLAIN_PATH for the explainability endpoints. Returns the
    classification report dict. Takes ~60-90s on a modern laptop — this is
    CPU-bound work, not I/O, so it's a real synchronous cost wherever it's
    called from."""
    df = pd.read_csv(DATA_PATH)
    df["attack_cat"] = df["attack_cat"].str.strip()

    X = df[ALL_FEATURES]
    y = df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
        ],
        remainder="passthrough",
    )

    model = Pipeline(
        steps=[
            ("preprocess", preprocessor),
            (
                "classify",
                RandomForestClassifier(
                    n_estimators=200, max_depth=None, n_jobs=-1, random_state=42
                ),
            ),
        ]
    )

    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
    print(classification_report(y_test, y_pred, zero_division=0))

    joblib.dump(model, MODEL_PATH)
    METRICS_PATH.write_text(json.dumps(report, indent=2))
    print(f"\nSaved model -> {MODEL_PATH}")
    print(f"Saved metrics -> {METRICS_PATH}")

    # Explainability artifacts: what the model weighs overall, and what
    # "normal" looks like per numeric feature, so a single flagged event's
    # values can be compared against a real baseline instead of asserted.
    classifier = model.named_steps["classify"]
    feature_importance = _aggregate_feature_importance(
        model.named_steps["preprocess"], classifier.feature_importances_
    )
    normal_rows = df[df[TARGET] == "Normal"]
    baseline = {
        col: {"mean": float(normal_rows[col].mean()), "std": float(normal_rows[col].std() or 1.0)}
        for col in NUMERIC_FEATURES
    }
    EXPLAIN_PATH.write_text(
        json.dumps({"feature_importance": feature_importance, "normal_baseline": baseline}, indent=2)
    )
    print(f"Saved explainability data -> {EXPLAIN_PATH}")

    return report


if __name__ == "__main__":
    train_model()
