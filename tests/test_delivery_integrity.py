"""Validate public hand-in artifacts while keeping personal oral practice offline."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def test_private_presentation_material_not_tracked_in_active_tree():
    for relative in (
        "DEMO_PRESENTACION.md",
        "docs/ENSAYO_SUSTENTACION.md",
        "docs/PREGUNTAS_DEFENSA.md",
        "docs/GLOSARIO_DEFENSA.md",
        "docs/PRESENTACION_FINAL.md",
        "docs/ORAL_EVIDENCE.md",
        "docs/DEFENSA_PAIII_NIVEL4.md",
    ):
        assert not (ROOT / relative).is_file(), relative


def test_public_academic_delivery_artifacts_exist():
    for relative in (
        "README.md",
        "docs/INFORME_FINAL.md",
        "docs/DEMO_PROTOCOL.md",
        "docs/DELIVERY_MANIFEST.md",
        "docs/RUBRICA_OFICIAL_PAIII_2026.md",
        "docs/architecture.md",
        "docs/genai_evaluation.md",
        "docs/genai_model_selection.md",
        "docs/ethics_security.md",
        "docs/training.md",
        "docs/datasets.md",
        "docs/model_card.md",
        "reports/genai/qwen_vs_gptoss_2026/comparison_report.md",
    ):
        assert (ROOT / relative).is_file(), relative


def test_current_internal_rubric_evidence_paths_resolve():
    audit = json.loads((ROOT / "reports/audit_2026-11-08/rubric_review.json").read_text(encoding="utf-8"))
    assert len(audit["criteria"]) == 27
    # Historical audit paths may point to public presentation material subsequently
    # classified as local-only. Validate scientific artifacts, not private oral slides.
    private = {"docs/PRESENTACION_FINAL.md", "docs/ORAL_EVIDENCE.md", "docs/DEFENSA_PAIII_NIVEL4.md"}
    for item in audit["criteria"]:
        for relative in item["evidence"]:
            if relative in private:
                continue
            assert (ROOT / relative).exists(), (item["code"], relative)
    assert audit["official_rubric"]["available"] is False


def test_public_report_keeps_reproducible_technical_evidence():
    report = (ROOT / "docs/INFORME_FINAL.md").read_text(encoding="utf-8")
    assert "Ollama" in report
    assert "Mendeley" in report
    assert "Qwen3 8B" in report
