from pathlib import Path
import shutil
import subprocess

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "deploy/k8s/prunin-ai-core.yaml"


def _objects():
    return {item["kind"]: item for item in yaml.safe_load_all(MANIFEST.read_text(encoding="utf-8")) if item}


def test_kubernetes_objects_probes_resources_and_selectors_are_consistent():
    objects = _objects()
    assert {"Deployment", "Service", "HorizontalPodAutoscaler", "PodDisruptionBudget"} <= set(objects)
    deployment = objects["Deployment"]["spec"]
    pod = deployment["template"]["spec"]
    container = pod["containers"][0]
    app_labels = deployment["selector"]["matchLabels"]
    assert deployment["replicas"] == 3
    assert deployment["strategy"]["type"] == "RollingUpdate"
    assert all(deployment["template"]["metadata"]["labels"].get(key) == value for key, value in app_labels.items())
    assert objects["Service"]["spec"]["selector"] == app_labels
    assert objects["PodDisruptionBudget"]["spec"]["selector"]["matchLabels"] == app_labels
    assert container["readinessProbe"]["httpGet"]["path"] == "/api/ready"
    assert container["livenessProbe"]["httpGet"]["path"] == "/api/health"
    for resource in ("requests", "limits"):
        assert {"cpu", "memory"} <= set(container["resources"][resource])
    assert pod["securityContext"]["runAsNonRoot"] is True
    assert container["securityContext"]["allowPrivilegeEscalation"] is False
    assert container["securityContext"]["readOnlyRootFilesystem"] is True
    assert pod["terminationGracePeriodSeconds"] >= 30
    dockerfile = (ROOT / "Dockerfile.playground").read_text(encoding="utf-8")
    assert "--timeout-graceful-shutdown 30" in dockerfile


def test_hpa_targets_deployment_with_cpu_scaling():
    objects = _objects()
    hpa = objects["HorizontalPodAutoscaler"]["spec"]
    assert hpa["scaleTargetRef"]["kind"] == "Deployment"
    assert hpa["scaleTargetRef"]["name"] == objects["Deployment"]["metadata"]["name"]
    assert hpa["minReplicas"] == 3
    assert hpa["maxReplicas"] == 10
    assert any(
        metric["type"] == "Resource"
        and metric["resource"]["name"] == "cpu"
        and metric["resource"]["target"]["averageUtilization"] > 0
        for metric in hpa["metrics"]
    )
    assert objects["PodDisruptionBudget"]["spec"]["minAvailable"] == 2


@pytest.mark.skipif(shutil.which("kubectl") is None, reason="kubectl no está instalado")
def test_kubectl_client_dry_run_when_available():
    completed = subprocess.run(
        ["kubectl", "apply", "--dry-run=client", "--validate=false", "-f", str(MANIFEST)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    output = completed.stdout + completed.stderr
    if completed.returncode and any(token in output.lower() for token in ("kubeconfig", "connection refused", "no configuration has been provided")):
        pytest.skip("kubectl está disponible, pero no hay conexión/configuración de cluster local")
    assert completed.returncode == 0, output