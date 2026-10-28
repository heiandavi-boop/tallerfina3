from __future__ import annotations

from typing import Any, Literal


DataDomain = Literal["unknown", "real_project", "academic_synthetic"]


class ModelRecommendationEngine:
    def recommend(self, project_input: dict[str, Any], academic_runtime: Any,
                  models: list[dict[str, Any]], data_domain: DataDomain = "unknown") -> dict[str, Any]:
        records = {record["id"]: record for record in models}
        academic = records.get("academic", {})
        empirical = records.get("empirical", {})
        academic_features = (
            list(academic_runtime.manifest.get("numeric_features", []))
            + list(academic_runtime.manifest.get("categorical_features", []))
        )
        academic_missing = [
            name for name in academic_features
            if project_input.get(name) is None or project_input.get(name) == ""
        ]
        academic_coverage = (len(academic_features) - len(academic_missing)) / max(len(academic_features), 1)
        minimum_coverage = float(academic_runtime.metadata().get("minimum_feature_coverage", 0.6))
        empirical_features = ["planned_duration_weeks", "planned_budget"]
        empirical_missing = [
            name for name in empirical_features
            if project_input.get(name) is None or project_input.get(name) == ""
        ]
        empirical_compatible = (
            not empirical_missing
            and float(project_input["planned_duration_weeks"]) > 0
            and float(project_input["planned_budget"]) > 0
        )
        empirical_available = empirical.get("status") == "ready"
        empirical_beats_baseline = bool(empirical.get("metrics")) and all(
            target.get("test", {}).get("mae") is not None
            and target.get("test", {}).get("baseline", {}).get("mae") is not None
            and target["test"]["mae"] < target["test"]["baseline"]["mae"]
            for target in empirical.get("metrics", {}).values()
        )

        if data_domain == "real_project" and empirical_available and empirical_compatible:
            recommended = "empirical"
            basis = "domain_alignment"
            reason = (
                "Declaraste un proyecto real y el input cubre duración planificada y BAC, "
                "las features observadas de Empirical. Esto mejora la alineación de dominio, "
                "no demuestra mayor precisión; el TEST empírico no supera su baseline mediano."
            )
        elif academic_coverage < minimum_coverage and empirical_available and empirical_compatible:
            recommended = "empirical"
            basis = "input_compatibility"
            reason = (
                f"El input cubre {academic_coverage:.0%} de las features Academic, por debajo del "
                f"mínimo {minimum_coverage:.0%}; Empirical recibe sus dos features baseline. "
                "La compatibilidad no implica mejor desempeño predictivo."
            )
        else:
            recommended = "academic" if academic.get("status") == "ready" else "empirical" if empirical_available and empirical_compatible else None
            basis = "academic_evidence_and_compatibility"
            reason = (
                "Academic mantiene el flujo completo y evidencia predictiva dentro de su dominio. "
                "Empirical no mostró mejora sobre su baseline mediano; sus métricas no son "
                "directamente comparables con Academic."
            ) if recommended == "academic" else "No hay un modelo disponible compatible con el input recibido."

        selected = records.get(recommended, {}) if recommended else {}
        return {
            "recommended_model_id": recommended,
            "version": selected.get("version"),
            "confidence": "low",
            "basis": basis,
            "declared_data_domain": data_domain,
            "automatic_winner": False,
            "automatic_activation": False,
            "reason": reason,
            "input_compatibility": {
                "academic": {"available": academic.get("status") == "ready", "coverage": round(academic_coverage, 4), "minimum_coverage": minimum_coverage, "missing_features": academic_missing},
                "empirical": {"available": empirical_available, "compatible": empirical_compatible, "missing_features": empirical_missing, "features": empirical_features},
            },
            "empirical_beats_its_baseline": empirical_beats_baseline,
            "metrics_note": "Métricas de datasets y targets distintos no constituyen una comparación head-to-head.",
        }