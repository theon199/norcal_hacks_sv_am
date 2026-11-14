"""Required test 3: robustness to Gaussian noise on numeric test features.

Uses the default-split fitted pipelines and the default test rows. For each numeric feature j,
sigma_j is the training-set standard deviation of the raw column (NaN ignored). Each of NOISE_DRAWS
seeded draws adds N(0, (NOISE_SCALE * sigma_j)^2) to the raw test values; NaN stays NaN and
categorical features are untouched. This is one specific noise model, not a physical one.
"""

from typing import Optional

import numpy as np
from sklearn.metrics import accuracy_score

from labmirror import config
from labmirror.engine.splits import FittedSplit
from labmirror.engine.validation import PreparedData
from labmirror.schemas import NoiseModelResult, NoiseResult


def noise_config() -> dict:
    return {
        "distribution": "Gaussian, mean 0",
        "scale": f"{config.NOISE_SCALE} x training-set standard deviation, per numeric feature",
        "n_draws": config.NOISE_DRAWS,
        "rng": f"numpy default_rng({config.NOISE_RNG_SEED} + draw index)",
        "applied_to": "numeric features of the default-split test rows only; models are not refitted",
        "skip_rule": "features whose training standard deviation is zero or not finite are left unchanged",
    }


def run_noise(data: PreparedData, default: FittedSplit) -> Optional[NoiseResult]:
    """Returns None when the dataset has no numeric feature that can be perturbed."""
    X_train = data.X.iloc[default.train_idx]
    X_test = data.X.iloc[default.test_idx]
    y_test = data.y[default.test_idx]

    sigmas: dict[str, float] = {}
    skipped: list[str] = []
    for name in data.numeric_features:
        sigma = float(np.nanstd(X_train[name].to_numpy(dtype=float)))
        if np.isfinite(sigma) and sigma > 0:
            sigmas[name] = sigma
        else:
            skipped.append(name)
    if not sigmas:
        return None

    roles = ("candidate", "baseline")
    clean = {r: float(accuracy_score(y_test, default.pipelines[r].predict(X_test))) for r in roles}
    noisy: dict[str, list[float]] = {r: [] for r in roles}
    for draw in range(config.NOISE_DRAWS):
        rng = np.random.default_rng(config.NOISE_RNG_SEED + draw)
        X_noisy = X_test.copy()
        for name, sigma in sigmas.items():   # fixed feature order keeps draws reproducible
            X_noisy[name] = X_noisy[name].to_numpy(dtype=float) + rng.normal(
                0.0, config.NOISE_SCALE * sigma, size=len(X_noisy)
            )
        for r in roles:
            noisy[r].append(float(accuracy_score(y_test, default.pipelines[r].predict(X_noisy))))

    per_model = [
        NoiseModelResult(
            model=r,
            clean_accuracy=clean[r],
            noisy_mean_accuracy=float(np.mean(noisy[r])),
            noisy_min=float(np.min(noisy[r])),
            noisy_max=float(np.max(noisy[r])),
            delta_pp=(float(np.mean(noisy[r])) - clean[r]) * 100.0,
        )
        for r in roles
    ]
    return NoiseResult(
        noise_scale=config.NOISE_SCALE,
        n_draws=config.NOISE_DRAWS,
        rng_seed=config.NOISE_RNG_SEED,
        perturbed_features=list(sigmas),
        skipped_features=skipped,
        per_model=per_model,
        clean_lift_pp=(clean["candidate"] - clean["baseline"]) * 100.0,
        noisy_mean_lift_pp=(float(np.mean(noisy["candidate"])) - float(np.mean(noisy["baseline"]))) * 100.0,
    )
