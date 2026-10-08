from __future__ import annotations
import re
import numpy as np
import pandas as pd


def normalize_name(name: str) -> str:
    name = str(name).strip().lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    return re.sub(r"_+", "_", name).strip("_")


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [normalize_name(c) for c in out.columns]
    return out


def first_existing(df: pd.DataFrame, aliases: list[str]) -> str | None:
    cols = set(df.columns)
    for alias in aliases:
        a = normalize_name(alias)
        if a in cols:
            return a
    return None


def numeric_series(df: pd.DataFrame, aliases: list[str], default=np.nan) -> pd.Series:
    col = first_existing(df, aliases)
    if not col:
        return pd.Series(default, index=df.index, dtype="float64")
    return pd.to_numeric(df[col], errors="coerce")


def text_series(df: pd.DataFrame, aliases: list[str]) -> pd.Series:
    col = first_existing(df, aliases)
    if not col:
        return pd.Series(pd.NA, index=df.index, dtype="object")
    return df[col].astype("string").str.strip().str.lower()


def scale_to_unit_interval(s: pd.Series) -> pd.Series:
    x = pd.to_numeric(s, errors="coerce")
    valid = x.dropna()
    if valid.empty:
        return x
    lo, hi = float(valid.min()), float(valid.max())
    if 0.0 <= lo and hi <= 1.0:
        return x.clip(0, 1)
    if 0.0 <= lo and hi <= 5.0:
        return (x / 5.0).clip(0, 1)
    if 0.0 <= lo and hi <= 10.0:
        return (x / 10.0).clip(0, 1)
    if 0.0 <= lo and hi <= 100.0:
        return (x / 100.0).clip(0, 1)
    # No inventar escala si no se reconoce el dominio.
    return pd.Series(np.nan, index=s.index, dtype="float64")
