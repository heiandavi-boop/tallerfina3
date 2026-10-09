from prunin_ai.api.recommendations import grounded_fallback, validate_generated_payload


def test_generated_payload_accepts_only_allowlisted_evidence():
    payload = {
        "recommendations": [
            {"evidence_feature": "spi", "reason": "El cronograma muestra presión.", "action": "Revisar actividades atrasadas."}
        ],
        "summary": "Se requiere seguimiento del cronograma.",
    }
    result = validate_generated_payload(payload, {"spi", "cpi"})
    assert result["schema_valid"] is True
    assert result["evidence_features_valid"] is True
    assert result["unsupported_numeric_claim"] is False
    assert result["grounded"] is True


def test_generated_payload_rejects_unknown_evidence_and_new_numbers():
    payload = {
        "recommendations": [
            {"evidence_feature": "scope_growth_ratio", "reason": "El riesgo subió 20 por ciento.", "action": "Reducir alcance."}
        ],
        "summary": "Atender el riesgo.",
    }
    result = validate_generated_payload(payload, {"spi"})
    assert result["evidence_features_valid"] is False
    assert result["unsupported_numeric_claim"] is True
    assert result["grounded"] is False


def test_fallback_is_auditable_and_not_presented_as_genai():
    drivers = [
        {"feature": "spi", "label": "SPI", "direction": "increases_risk", "risk_impact": 0.2}
    ]
    result = grounded_fallback({}, {"health": "at_risk"}, drivers)
    assert result["engine"] == "grounded_fallback"
    assert result["genai_attempted"] is False
    assert result["genai_used"] is False
    assert result["evidence_features"] == ["spi"]
    assert result["grounding"]["raw_project_text_sent_to_llm"] is False
