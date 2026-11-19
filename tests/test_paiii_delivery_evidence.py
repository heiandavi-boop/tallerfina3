"""PAIII evidence gate regression tests; no local model or network required."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check_paiii_delivery_evidence.py"
spec = importlib.util.spec_from_file_location("paiii_delivery_gate", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_versioned_paiii_evidence_passes_readonly_gate():
    assert module.check(ROOT) == []


def test_gate_rejects_incomplete_or_simulated_results(tmp_path):
    source = ROOT / "reports/genai/qwen_vs_gptoss_2026"
    target = tmp_path / "reports/genai/qwen_vs_gptoss_2026"
    target.mkdir(parents=True)
    for filename in ("benchmark_summary.json", "execution_manifest.json"):
        (target / filename).write_bytes((source / filename).read_bytes())
    manifest = json.loads((target / "execution_manifest.json").read_text())
    manifest["simulated"] = True
    manifest["completeness"]["missing"] = 2
    (target / "execution_manifest.json").write_text(json.dumps(manifest))
    human = tmp_path / "reports/human_validation/productivity_summary.json"
    human.parent.mkdir(parents=True)
    human.write_bytes((ROOT / "reports/human_validation/productivity_summary.json").read_bytes())
    for path in ("docs/RUBRICA_OFICIAL_PAIII_2026.md", "docs/INFORME_FINAL.md", "docs/genai_model_selection.md"):
        destination = tmp_path / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((ROOT / path).read_bytes())
    findings = module.check(tmp_path)
    assert any("non-simulated" in issue for issue in findings)
    assert any("90 non-duplicated" in issue for issue in findings)
