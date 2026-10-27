from __future__ import annotations

import json

from prunin_ai.data.dslib import prepare_empirical_data


def main() -> None:
    print(json.dumps(prepare_empirical_data(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()