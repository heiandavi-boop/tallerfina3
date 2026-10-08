from __future__ import annotations
from pathlib import Path
import pandas as pd
from ..common import normalize_columns


def load_collaboration_csv(path: str | Path) -> pd.DataFrame:
    df = normalize_columns(pd.read_csv(path, low_memory=False))
    df["data_source"] = "github_collaboration_zenodo_15681547"
    df["is_synthetic"] = False
    return df
