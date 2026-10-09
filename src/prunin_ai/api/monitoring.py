from __future__ import annotations

import statistics
import time
from collections import deque
from threading import Lock
from typing import Any


class MonitoringRegistry:
    def __init__(self, max_samples: int = 1000):
        self.started_at = time.time()
        self._lock = Lock()
        self._latencies = deque(maxlen=max_samples)
        self.total_predictions = 0
        self.prediction_failures = 0
        self.genai_attempts = 0
        self.genai_successes = 0
        self.genai_fallbacks = 0

    def record_prediction(self, latency_ms: float, recommendations: dict[str, Any]) -> None:
        with self._lock:
            self.total_predictions += 1
            self._latencies.append(float(latency_ms))
            if recommendations.get("genai_attempted"):
                self.genai_attempts += 1
                if recommendations.get("genai_used"):
                    self.genai_successes += 1
                else:
                    self.genai_fallbacks += 1

    def record_failure(self, latency_ms: float) -> None:
        with self._lock:
            self.prediction_failures += 1
            self._latencies.append(float(latency_ms))

    @staticmethod
    def _percentile(values: list[float], q: float) -> float | None:
        if not values:
            return None
        ordered = sorted(values)
        index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * q)))
        return round(float(ordered[index]), 2)

    def prometheus_text(self, *, model_version: str, model_mode: str) -> str:
        snapshot = self.snapshot(model_version=model_version, model_mode=model_mode)
        latency = snapshot["inference_latency_ms"]
        lines = [
            "# HELP prunin_predictions_total Successful PRUNIN inference requests.",
            "# TYPE prunin_predictions_total counter",
            f"prunin_predictions_total {snapshot['total_predictions']}",
            "# HELP prunin_prediction_failures_total Failed PRUNIN inference requests.",
            "# TYPE prunin_prediction_failures_total counter",
            f"prunin_prediction_failures_total {snapshot['prediction_failures']}",
            "# HELP prunin_genai_attempts_total Generative AI attempts.",
            "# TYPE prunin_genai_attempts_total counter",
            f"prunin_genai_attempts_total {snapshot['genai_attempts']}",
            "# HELP prunin_genai_successes_total Accepted grounded GenAI responses.",
            "# TYPE prunin_genai_successes_total counter",
            f"prunin_genai_successes_total {snapshot['genai_successes']}",
            "# HELP prunin_genai_fallbacks_total GenAI attempts that fell back to deterministic recommendations.",
            "# TYPE prunin_genai_fallbacks_total counter",
            f"prunin_genai_fallbacks_total {snapshot['genai_fallbacks']}",
            "# HELP prunin_inference_latency_p95_ms Rolling in-memory p95 inference latency.",
            "# TYPE prunin_inference_latency_p95_ms gauge",
            f"prunin_inference_latency_p95_ms {latency['p95'] if latency['p95'] is not None else 0}",
            "# HELP prunin_process_uptime_seconds API process uptime.",
            "# TYPE prunin_process_uptime_seconds gauge",
            f"prunin_process_uptime_seconds {snapshot['uptime_seconds']}",
        ]
        return "\n".join(lines) + "\n"

    def snapshot(self, *, model_version: str, model_mode: str) -> dict[str, Any]:
        with self._lock:
            values = list(self._latencies)
            return {
                "model_version": model_version,
                "model_mode": model_mode,
                "uptime_seconds": round(time.time() - self.started_at, 2),
                "total_predictions": self.total_predictions,
                "prediction_failures": self.prediction_failures,
                "genai_attempts": self.genai_attempts,
                "genai_successes": self.genai_successes,
                "genai_fallbacks": self.genai_fallbacks,
                "inference_latency_ms": {
                    "sample_count": len(values),
                    "mean": round(float(statistics.fmean(values)), 2) if values else None,
                    "p50": self._percentile(values, 0.50),
                    "p95": self._percentile(values, 0.95),
                    "max": round(max(values), 2) if values else None,
                },
            }


monitoring = MonitoringRegistry()
