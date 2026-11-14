"""Load a CSV, hash it, type its columns and build a DatasetSummary."""

import hashlib
import io
import re

import numpy as np
import pandas as pd
from pandas.api import types as ptypes

from labmirror import config
from labmirror.engine import EngineError
from labmirror.schemas import ColumnInfo, DatasetSummary, Preview


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load_csv(raw: bytes) -> pd.DataFrame:
    if not raw or not raw.strip():
        raise EngineError("no_file", "The file is empty. Upload a CSV with a header row and data rows.")
    if len(raw) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise EngineError("file_too_large", f"The file is larger than {config.MAX_UPLOAD_MB} MB.")
    df = None
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            df = pd.read_csv(io.BytesIO(raw), encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
        except Exception as exc:  # pandas parser errors
            raise EngineError("malformed_csv", f"Could not parse the file as CSV: {exc}") from exc
    if df is None:
        raise EngineError("malformed_csv", "Could not decode the file. Save it as UTF-8 CSV and try again.")
    df.columns = [str(c).strip() for c in df.columns]
    if len(set(df.columns)) != len(df.columns):
        raise EngineError("malformed_csv", "The CSV has duplicate column names. Rename them so each is unique.")
    if df.shape[1] < 2:
        raise EngineError("malformed_csv", "The CSV needs at least two columns: one target and one feature.")
    if df.shape[1] > config.MAX_COLUMNS:
        raise EngineError("too_many_columns", f"The CSV has {df.shape[1]} columns; the limit is {config.MAX_COLUMNS}.")
    if len(df) < config.MIN_ROWS:
        raise EngineError("too_few_rows", f"The CSV has {len(df)} rows; at least {config.MIN_ROWS} are required.")
    if len(df) > config.MAX_ROWS:
        raise EngineError("too_many_rows", f"The CSV has {len(df)} rows; the limit is {config.MAX_ROWS}.")
    return df


def is_numeric(series: pd.Series) -> bool:
    return ptypes.is_numeric_dtype(series) and not ptypes.is_bool_dtype(series)


def _name_tokens(name: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", name.lower()) if t}


def _is_sequential_integer(series: pd.Series) -> bool:
    """True for integer columns that are a contiguous run of unique values, like a row counter."""
    if not ptypes.is_integer_dtype(series) or series.isna().any():
        return False
    n = len(series)
    return series.nunique() == n and int(series.max()) - int(series.min()) == n - 1


def profile_column(series: pd.Series) -> ColumnInfo:
    name = str(series.name)
    non_null = series.dropna()
    n = len(series)
    n_unique = int(non_null.nunique())
    missing_fraction = float(series.isna().mean()) if n else 0.0
    flags: list[str] = []

    if n_unique <= 1:
        kind = "unusable"
        flags.append("constant")
    elif is_numeric(series):
        kind = "numeric"
    elif n_unique <= config.MAX_CATEGORIES:
        kind = "categorical"
    else:
        kind = "unusable"
        mean_len = float(non_null.astype(str).str.len().mean())
        flags.append("free_text" if mean_len > config.FREE_TEXT_MEAN_LENGTH else "high_cardinality")

    tokens = _name_tokens(name)
    unique_fraction = n_unique / len(non_null) if len(non_null) else 0.0
    looks_like_id = (
        bool(tokens & config.IDENTIFIER_NAME_TOKENS)
        or _is_sequential_integer(series)
        or (not is_numeric(series) and unique_fraction > config.IDENTIFIER_UNIQUE_FRACTION)
    )
    if looks_like_id and "constant" not in flags:
        flags.append("identifier_like")
    lowered = name.lower()
    if any(term in lowered for term in config.LEAKAGE_NAME_TERMS):
        flags.append("leakage_name")

    return ColumnInfo(name=name, kind=kind, n_unique=n_unique, missing_fraction=missing_fraction, flags=flags)


def _preview(df: pd.DataFrame) -> Preview:
    head = df.head(config.PREVIEW_ROWS)
    rows = [["" if pd.isna(v) else str(v)[:80] for v in row] for row in head.itertuples(index=False, name=None)]
    return Preview(columns=[str(c) for c in df.columns], rows=rows)


def profile_dataset(
    df: pd.DataFrame, *, dataset_id: str, sha256: str, filename: str, is_demo: bool = False
) -> DatasetSummary:
    columns = [profile_column(df[c]) for c in df.columns]
    binary_targets = [
        c.name for c in columns if c.n_unique == 2 and c.missing_fraction == 0.0
    ]
    return DatasetSummary(
        dataset_id=dataset_id,
        sha256=sha256,
        filename=filename,
        is_demo=is_demo,
        n_rows=int(len(df)),
        n_columns=int(df.shape[1]),
        columns=columns,
        duplicate_row_count=int(df.duplicated().sum()),
        binary_target_candidates=binary_targets,
        preview=_preview(df),
    )


def default_exclusions(summary: DatasetSummary, target: str) -> list[str]:
    """Columns the UI pre-ticks for exclusion: unusable or identifier-like, never the target."""
    return [
        c.name
        for c in summary.columns
        if c.name != target and (c.kind == "unusable" or "identifier_like" in c.flags)
    ]


def label_str(value) -> str:
    """Stable string form of a class label (so 1 and 1.0 do not diverge across runs)."""
    if isinstance(value, (bool, np.bool_)):
        return str(bool(value))
    if isinstance(value, (float, np.floating)) and float(value).is_integer():
        return str(int(value))
    return str(value)
