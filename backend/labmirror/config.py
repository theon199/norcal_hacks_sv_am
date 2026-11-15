"""Constants and environment settings. Scientific constants are fixed by docs/IMPLEMENTATION_PLAN.md §5."""

import os
from pathlib import Path

SCHEMA_VERSION = "1.0"

# --- Dataset limits -------------------------------------------------------
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "20"))
MIN_ROWS = 100
# Lowered from 20,000 rows after the A3.4 perf check: on the free Render instance a 20,000 x 50 audit hit the
# 120 s limit and 5,000 x 20 took 72 s. The cell budget (rows x selected features) keeps every allowed audit
# near the 5,000 x 20 cost while still allowing wide, short datasets such as Breast Cancer (569 x 30).
MAX_ROWS = 5_000
MAX_CELLS = 100_000
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

# --- Noise test (plan §5.4) ----------------------------------------------
NOISE_SCALE = 0.10
NOISE_DRAWS = 20
NOISE_RNG_SEED = 1000      # draw d uses default_rng(NOISE_RNG_SEED + d)

# --- Diagnostics (plan §5.5) ---------------------------------------------
CRITICAL_DUPLICATE_SHARE = 0.10
COARSE_FEATURE_SPACE_SHARE = 0.50   # below this share of distinct feature vectors, repeats are expected
IMBALANCE_WARNING_SHARE = 0.20
IMBALANCE_INFO_SHARE = 0.35
SMALL_TEST_CLASS = 10
HEURISTIC_CAVEAT = "This is a heuristic check. It cannot prove leakage, and passing it cannot prove the absence of leakage."
NO_ISSUE_STATEMENT = (
    "No issues were found in the checks performed. These checks cannot establish the absence of leakage."
)

# --- Verdict (plan §5.6; declared before any fixture existed) -------------
CONSISTENT_MIN_SEEDS = 4
NOISE_MATERIALITY_PP = 2.0

# --- Optional LLM layer (plan Phase 4) -----------------------------------
# Off unless both are set. Opt-in so a deploy with a key does not show AI text before the UI labels it.
LLM_ENABLED = bool(os.environ.get("ANTHROPIC_API_KEY")) and os.environ.get("LABMIRROR_LLM") == "1"
LLM_MODEL = os.environ.get("LLM_MODEL", "claude-opus-5-5")
LLM_TIMEOUT_S = float(os.environ.get("LLM_TIMEOUT_S", "20"))

# --- Jobs -----------------------------------------------------------------
MAX_QUEUED = 5
