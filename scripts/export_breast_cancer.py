"""Export scikit-learn's bundled Breast Cancer Wisconsin (Diagnostic) dataset to CSV.

Source: sklearn.datasets.load_breast_cancer (UCI ML Repository; W. Wolberg, W. Street, O. Mangasarian).
No values are altered. Column names have spaces replaced by underscores; the target is written as text.

    python scripts/export_breast_cancer.py backend/labmirror/demo_data/breast_cancer_wisconsin.csv
"""

import sys
from pathlib import Path

from sklearn.datasets import load_breast_cancer


def main(out: Path) -> None:
    bunch = load_breast_cancer(as_frame=True)
    df = bunch.frame.copy()
    df.columns = [c.replace(" ", "_") for c in df.columns]
    df["tumor_class"] = df.pop("target").map({0: "malignant", 1: "benign"})
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False, lineterminator="\n")
    print(f"wrote {out} ({len(df)} rows, {df.shape[1]} columns)")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
