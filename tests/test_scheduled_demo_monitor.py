"""Guard against misleading scheduled-monitor claims and unsafe retraining in CI."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_scheduled_demo_monitor_is_readonly_and_archives_results():
    path = ROOT / ".github/workflows/scheduled-demo-drift.yml"
    source = path.read_text(encoding="utf-8")
    workflow = yaml.safe_load(source)
    # YAML parsers using YAML 1.1 can interpret 'on' as True.
    triggers = workflow.get("on", workflow.get(True, {}))
    assert "schedule" in triggers and "workflow_dispatch" in triggers
    assert workflow["permissions"] == {"contents": "read"}
    assert "scripts/check_drift.py" in source
    assert "--artifact artifacts/demo-0.1.0" in source
    assert "actions/upload-artifact@v4" in source
    assert "retraining_triggered" in source
    assert "--authorize" not in source
    assert "mlops_pipeline.py" not in source
    assert "OPENAI_API_KEY" not in source
