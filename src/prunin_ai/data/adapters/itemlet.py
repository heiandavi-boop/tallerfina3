from __future__ import annotations
from pathlib import Path
import pandas as pd
from ..common import normalize_columns, first_existing


def load_itemlet(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if p.suffix.lower() == ".parquet":
        df = pd.read_parquet(p)
    else:
        df = pd.read_csv(p, low_memory=False)
    df = normalize_columns(df)
    project_col = first_existing(df, ["project", "project_key", "project_id"])
    if project_col:
        df["source_project_id"] = df[project_col].astype(str)
    df["data_source"] = "itemlet_zenodo_19411554"
    df["is_synthetic"] = False
    return df
