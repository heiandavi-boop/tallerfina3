from __future__ import annotations
from pathlib import Path
import pandas as pd
from ..common import normalize_columns


def load_squad_subset(path: str | Path) -> pd.DataFrame:
    """Carga un subconjunto CSV de SQuaD. No se recomienda cargar el dataset completo en memoria."""
    df = normalize_columns(pd.read_csv(path, low_memory=False))
    df["data_source"] = "squad_zenodo_17566691"
    df["is_synthetic"] = False
    return df
