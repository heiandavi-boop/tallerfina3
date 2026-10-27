from __future__ import annotations

import hashlib
import json
import re
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "dslib"
REPOSITORY = "https://github.com/MarioVanhoucke/DSLIB-Dynamic-Scheduling-Empirical-Project-Library"
RELEASE_API = f"https://api.github.com/repos/MarioVanhoucke/DSLIB-Dynamic-Scheduling-Empirical-Project-Library/releases/tags/DSLIB_v3.4"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_release() -> dict[str, Any]:
    request = urllib.request.Request(RELEASE_API, headers={"Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    release = read_release()
    asset = next((item for item in release.get("assets", []) if item["name"].endswith(".zip")), None)
    if asset is None:
        raise RuntimeError("La publicación DSLIB más reciente no incluye un archivo ZIP.")

    archive_path = RAW_DIR / asset["name"]
    expected_hash = str(asset.get("digest") or "").removeprefix("sha256:")
    if not expected_hash:
        raise RuntimeError("La publicación no ofrece SHA-256; no se descargará sin integridad verificable.")

    if archive_path.exists():
        actual_hash = sha256_file(archive_path)
        if actual_hash != expected_hash:
            raise RuntimeError(
                f"El archivo existente no coincide con la publicación ({actual_hash}); "
                "se conserva intacto. Use una carpeta/version distinta para descargar otra copia."
            )
    else:
        temporary_path = archive_path.with_suffix(archive_path.suffix + ".part")
        request = urllib.request.Request(asset["browser_download_url"], headers={"User-Agent": "PRUNIN-AI-Core"})
        digest = hashlib.sha256()
        try:
            with urllib.request.urlopen(request, timeout=60) as response, temporary_path.open("wb") as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
                    digest.update(chunk)
            if digest.hexdigest() != expected_hash:
                raise RuntimeError("El SHA-256 descargado no coincide con el publicado por GitHub.")
            temporary_path.replace(archive_path)
        finally:
            temporary_path.unlink(missing_ok=True)
        actual_hash = digest.hexdigest()

    with zipfile.ZipFile(archive_path) as archive:
        bad_member = archive.testzip()
        if bad_member:
            raise RuntimeError(f"El ZIP tiene un miembro corrupto: {bad_member}")
        project_count = sum(
            bool(re.fullmatch(r"[^/]+/Excel/[^/]+\.xlsx", name, flags=re.IGNORECASE))
            for name in archive.namelist()
        )

    downloaded_at = datetime.fromtimestamp(archive_path.stat().st_mtime, timezone.utc).isoformat()
    manifest = {
        "source": "DSLIB / Dynamic Scheduling Empirical Project Library (PSLIB)",
        "source_url": REPOSITORY,
        "release_url": release.get("html_url"),
        "version": release.get("tag_name"),
        "published_at": release.get("published_at"),
        "download_date": downloaded_at,
        "license": "Not specified in the publisher's repository or release metadata",
        "files": [
            {
                "path": str(archive_path.relative_to(ROOT)),
                "sha256": actual_hash,
                "bytes": archive_path.stat().st_size,
            }
        ],
        "project_count": project_count,
        "notes": [
            "Project count is computed from per-project Excel workbooks in this release archive.",
            "The publisher's README reports 231 projects for the current release.",
            "Cite Batselier & Vanhoucke (2015), doi:10.1016/j.ijproman.2014.09.004.",
            "No license was declared in the repository/release; do not redistribute the source archive without permission.",
        ],
    }
    manifest_path = RAW_DIR / "dataset_manifest.json"
    temporary_manifest = manifest_path.with_suffix(".json.part")
    temporary_manifest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary_manifest.replace(manifest_path)
    print(json.dumps({"archive": str(archive_path), "version": manifest["version"], "project_count": project_count, "sha256": actual_hash, "manifest": str(manifest_path)}, indent=2))


if __name__ == "__main__":
    main()