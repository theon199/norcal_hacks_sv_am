import numpy as np
import pandas as pd
import pytest

from labmirror.schemas import AuditRequest, ClaimSpec


@pytest.fixture
def mixed_df() -> pd.DataFrame:
    """300 rows, numeric + categorical features with missing values, an ID column and a binary target."""
    rng = np.random.default_rng(7)
    n = 300
    x1 = rng.normal(size=n)
    x2 = rng.normal(loc=5, scale=3, size=n)
    color = rng.choice(["red", "green", "blue"], size=n)
    y = ((x1 + 0.5 * (color == "red") + rng.normal(scale=0.8, size=n)) > 0.3).astype(int)
    df = pd.DataFrame(
        {
            "record_id": np.arange(1000, 1000 + n),
            "x1": x1,
            "x2": x2,
            "color": color,
            "notes": [f"free text entry number {i} " * 4 for i in range(n)],
            "outcome": np.where(y == 1, "yes", "no"),
        }
    )
    df.loc[rng.choice(n, 20, replace=False), "x2"] = np.nan
    df.loc[rng.choice(n, 15, replace=False), "color"] = np.nan
    return df


@pytest.fixture
def claim() -> ClaimSpec:
    return ClaimSpec(target="outcome", candidate="random_forest", baseline="logistic_regression", threshold_pp=5.0)


@pytest.fixture
def request_for(claim):
    def make(excluded=("record_id", "notes")) -> AuditRequest:
        return AuditRequest(dataset_id="t", claim=claim, excluded_columns=list(excluded))

    return make
