"""Constants and environment settings. Scientific constants are fixed by docs/IMPLEMENTATION_PLAN.md §5."""

import os
from pathlib import Path

SCHEMA_VERSION = "1.0"

# --- Dataset limits -------------------------------------------------------
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "20"))
MIN_ROWS = 100
MAX_ROWS = 20_000
MAX_COLUMNS = 100          # at upload; the feature cap below applies at audit time
MIN_FEATURES = 2
MAX_FEATURES = 50
MIN_CLASS_COUNT = 20
MAX_CATEGORIES = 20
FREE_TEXT_MEAN_LENGTH = 50
IDENTIFIER_UNIQUE_FRACTION = 0.95
PREVIEW_ROWS = 8

IDENTIFIER_NAME_TOKENS = {"id", "uuid", "guid", "index", "key"}
LEAKAGE_NAME_TERMS = ("label", "outcome", "target", "result", "diagnosis", "status", "post_")

# --- Evaluation protocol --------------------------------------------------
TEST_SIZE = 0.2
DEFAULT_SEED = 42
SENSITIVITY_SEEDS = [11, 23, 37, 51, 79]
MODEL_RANDOM_STATE = 0
THRESHOLD_EPSILON = 1e-9

# --- Runtime --------------------------------------------------------------
JOB_TIMEOUT_S = int(os.environ.get("JOB_TIMEOUT_S", "120"))
DATA_DIR = Path(os.environ.get("DATA_DIR", Path(__file__).resolve().parents[1] / "data"))
DEMO_DIR = Path(os.environ.get("DEMO_DIR", Path(__file__).resolve().parent / "demo_data"))
RETENTION_HOURS = 24

DISCLOSURE = (
    "LabMirror independently re-evaluates a claim on the data and protocol shown here. "
    "It is not a reproduction of any published study unless that study's exact data, splits and code were used. "
    "Verdict labels are product labels derived from the stated rule; they are not statistical significance results. "
    'Counts such as "2 of 5 splits" describe the tested splits and are not probabilities. '
    "Passing these tests does not guarantee that a result generalizes."
)
