"""Validate hand-in structure without claiming official rubric certification."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def test_private_presentation_material_not_tracked_in_active_tree():
    for relative in (
        "DEMO_PRESENTACION.md",
        "docs/ENSAYO_SUSTENTACION.md",
        "docs/PREGUNTAS_DEFENSA.md",
        "docs/GLOSARIO_DEFENSA.md",
    ):
        assert not (ROOT / relative).is_file(), relative


def test_public_academic_delivery_artifacts_exist():
    for relative in (
        "README.md",
        "docs/INFORME_FINAL.md",
        "docs/PRESENTACION_FINAL.md",
        "docs/DEMO_PROTOCOL.md",
        "docs/ORAL_EVIDENCE.md",
        "docs/DELIVERY_MANIFEST.md",
        "docs/architecture.md",
        "docs/genai_evaluation.md",
        "docs/ethics_security.md",
        "docs/training.md",
        "docs/datasets.md",
        "docs/model_card.md",
    ):
        assert (ROOT / relative).is_file(), relative


def test_current_internal_rubric_evidence_paths_resolve():
    audit = json.loads((ROOT / "reports/audit_2026-11-08/rubric_review.json").read_text(encoding="utf-8"))
    assert len(audit["criteria"]) == 27
    for item in audit["criteria"]:
        for relative in item["evidence"]:
            assert (ROOT / relative).exists(), (item["code"], relative)
    assert audit["official_rubric"]["available"] is False


def test_public_presentation_describes_current_provider_contract():
    report = (ROOT / "docs/INFORME_FINAL.md").read_text(encoding="utf-8")
    presentation = (ROOT / "docs/PRESENTACION_FINAL.md").read_text(encoding="utf-8")
    for text in (report, presentation):
        assert "OpenAI" in text
        assert "Ollama" in text
    assert "Mendeley" in presentation
