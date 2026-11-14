"""Leak-safe scikit-learn pipelines. Preprocessing is inside the Pipeline, so it is fitted on train only."""

from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from labmirror.config import MODEL_RANDOM_STATE

MODEL_SETTINGS = {
    "logistic_regression": {
        "estimator": "LogisticRegression",
        "params": {"C": 1.0, "solver": "lbfgs", "max_iter": 1000, "random_state": MODEL_RANDOM_STATE},
    },
    "random_forest": {
        "estimator": "RandomForestClassifier",
        "params": {"n_estimators": 100, "max_depth": None, "random_state": MODEL_RANDOM_STATE, "n_jobs": 1},
    },
    "dummy": {
        "estimator": "DummyClassifier",
        "params": {"strategy": "most_frequent"},
    },
}

MODEL_LABELS = {
    "logistic_regression": "Logistic Regression",
    "random_forest": "Random Forest",
    "dummy": "Most-frequent-class baseline",
}

PREPROCESSING_SETTINGS = {
    "numeric": ["SimpleImputer(strategy='median')", "StandardScaler()"],
    "categorical": ["SimpleImputer(strategy='most_frequent')", "OneHotEncoder(handle_unknown='ignore')"],
    "fitted_on": "training rows only, inside a scikit-learn Pipeline",
    "shared_by_all_models": True,
}

_ESTIMATORS = {
    "logistic_regression": LogisticRegression,
    "random_forest": RandomForestClassifier,
    "dummy": DummyClassifier,
}


def build_pipeline(model_key: str, numeric: list[str], categorical: list[str]) -> Pipeline:
    transformers = []
    if numeric:
        transformers.append(
            ("numeric", Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), numeric)
        )
    if categorical:
        transformers.append(
            (
                "categorical",
                Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="most_frequent")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical,
            )
        )
    estimator = _ESTIMATORS[model_key](**MODEL_SETTINGS[model_key]["params"])
    return Pipeline([("preprocess", ColumnTransformer(transformers)), ("model", estimator)])
