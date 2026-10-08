from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit


def require_local_training_input(value: str, repository_root: str | Path) -> Path:
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc:
        raise ValueError("train_core.py solo acepta archivos locales; no se permiten URLs.")
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = Path(repository_root) / path
    path = path.resolve()
    if not path.is_file():
        raise FileNotFoundError(f"No existe el archivo local de entrenamiento: {path}")
    raw_root = (Path(repository_root) / "data/raw").resolve()
    if path == raw_root or raw_root in path.parents:
        raise ValueError("No se permite entrenar desde data/raw; use un dataset preparado en data/processed.")
    return path