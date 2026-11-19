"""Backend-side access controls (R6.2-Cr7). Defaults preserve local single-user behavior."""
from __future__ import annotations

import hmac
import os

OPEN_PATHS = frozenset({"/api/health", "/api/ready", "/metrics"})


def configured_token() -> str | None:
    token = os.getenv("PRUNIN_API_TOKEN", "").strip()
    return token or None


def requires_token(path: str) -> bool:
    return path.startswith("/api/") and path not in OPEN_PATHS


def token_matches(authorization: str | None, expected: str) -> bool:
    if not authorization or not authorization.startswith("Bearer "):
        return False
    return hmac.compare_digest(authorization[7:].strip().encode(), expected.encode())


def resolve_cors_origins(environment: str | None = None, raw: str | None = None) -> list[str]:
    """Local default is permissive; production refuses wildcard and defaults to same-origin only."""
    environment = (environment if environment is not None else os.getenv("PRUNIN_ENV", "local")).strip().lower()
    raw = raw if raw is not None else os.getenv("PRUNIN_CORS_ORIGINS")
    origins = [item.strip() for item in (raw or "").split(",") if item.strip()]
    if environment == "production":
        if "*" in origins:
            raise RuntimeError("PRUNIN_CORS_ORIGINS='*' is not allowed when PRUNIN_ENV=production")
        return origins
    return origins or ["*"]


