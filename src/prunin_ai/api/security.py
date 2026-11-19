"""Backend-side access controls (R6.2-Cr7). Defaults preserve local single-user behavior."""
from __future__ import annotations

import hmac
import os
import threading
import time
from collections import deque
from datetime import date
from typing import Callable

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


class OpenAIGuard:
    """Per-client sliding-window rate limit plus a process-wide daily call quota for OpenAI generations."""

    def __init__(self, per_minute: int, daily_max: int, clock: Callable[[], float] = time.monotonic, today: Callable[[], date] = date.today):
        self.per_minute = per_minute
        self.daily_max = daily_max
        self._clock = clock
        self._today = today
        self._lock = threading.Lock()
        self._windows: dict[str, deque[float]] = {}
        self._day = today()
        self._daily_calls = 0

    @classmethod
    def from_env(cls) -> "OpenAIGuard":
        return cls(
            per_minute=int(os.getenv("PRUNIN_OPENAI_RATE_LIMIT_PER_MIN", "20")),
            daily_max=int(os.getenv("PRUNIN_OPENAI_DAILY_MAX_CALLS", "500")),
        )

    def acquire(self, client: str) -> str | None:
        """Returns None when allowed, otherwise the failure code to report (HTTP 429)."""
        with self._lock:
            now = self._clock()
            if self._today() != self._day:
                self._day, self._daily_calls = self._today(), 0
            if self._daily_calls >= self.daily_max:
                return "openai_daily_quota_exceeded"
            window = self._windows.setdefault(client, deque())
            while window and now - window[0] >= 60:
                window.popleft()
            if len(window) >= self.per_minute:
                return "openai_rate_limited"
            window.append(now)
            self._daily_calls += 1
            return None

    def snapshot(self) -> dict[str, int | str]:
        with self._lock:
            return {"per_minute": self.per_minute, "daily_max": self.daily_max, "daily_calls": self._daily_calls, "day": self._day.isoformat()}
