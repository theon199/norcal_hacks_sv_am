"""Required test 1: reconstructed default comparison on a stratified 80/20 split, seed 42."""

from labmirror import config
from labmirror.engine.splits import FittedSplit, run_paired_split
from labmirror.engine.validation import PreparedData
from labmirror.schemas import ClaimSpec


def run_default_split(data: PreparedData, claim: ClaimSpec) -> FittedSplit:
    return run_paired_split(data, claim, config.DEFAULT_SEED)
