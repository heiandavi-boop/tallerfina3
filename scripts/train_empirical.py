from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from prunin_ai.training.empirical_training_service import run_empirical_training


def main() -> None:
    result = run_empirical_training(lambda stage, message: print(f"[{stage}] {message}", flush=True))
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()