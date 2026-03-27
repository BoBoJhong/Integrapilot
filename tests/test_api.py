"""API 煙霧測試（不需 LLM）。"""

from fastapi.testclient import TestClient

from web_api import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert data.get("service") == "integrapilot"
    assert "ui_dist" in data


def test_mounts_shape():
    r = client.get("/api/mounts")
    assert r.status_code == 200
    data = r.json()
    assert "projects" in data
    assert isinstance(data["projects"], list)


def test_reports_list():
    r = client.get("/api/reports")
    assert r.status_code == 200
    assert "reports" in r.json()


def test_report_not_found():
    r = client.get("/api/reports/nonexistent-report-xyz.md")
    assert r.status_code == 404


def test_agents_list():
    r = client.get("/api/agents")
    assert r.status_code == 200
    agents = r.json().get("agents", [])
    assert isinstance(agents, list)
    assert any(a.get("id") == "integration-advisor" for a in agents)
