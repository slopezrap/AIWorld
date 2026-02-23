"""
Tests de integración para los endpoints de la API FastAPI.

Usa TestClient de FastAPI (no requiere servidor corriendo).
NO ejecuta agentes reales (solo tests de routing, validación, discovery).
"""

import pytest
from fastapi.testclient import TestClient

from aifoundry.app.main import app


@pytest.fixture(scope="module")
def client():
    """TestClient de FastAPI para toda la suite."""
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_structure(self, client):
        data = client.get("/health").json()
        assert data["status"] == "healthy"
        assert "llm_model" in data
        assert "mcp_servers" in data
        assert "agents_available" in data
        assert data["agents_available"] >= 1

    def test_health_has_version(self, client):
        data = client.get("/health").json()
        assert "version" in data


class TestListAgentsEndpoint:
    def test_list_agents_returns_200(self, client):
        resp = client.get("/agents")
        assert resp.status_code == 200

    def test_list_agents_structure(self, client):
        data = client.get("/agents").json()
        assert "agents" in data
        assert "total" in data
        assert data["total"] >= 3  # electricity, salary, social_comments

    def test_list_agents_contains_known_agents(self, client):
        data = client.get("/agents").json()
        names = [a["name"] for a in data["agents"]]
        assert "electricity" in names
        assert "salary" in names
        assert "social_comments" in names

    def test_agent_info_fields(self, client):
        data = client.get("/agents").json()
        agent = data["agents"][0]
        assert "name" in agent
        assert "product" in agent
        assert "countries" in agent


class TestGetAgentConfigEndpoint:
    def test_electricity_config_200(self, client):
        resp = client.get("/agents/electricity/config")
        assert resp.status_code == 200

    def test_electricity_config_structure(self, client):
        data = client.get("/agents/electricity/config").json()
        assert data["product"] == "electricidad"
        assert "countries" in data
        assert "ES" in data["countries"]

    def test_salary_config_200(self, client):
        resp = client.get("/agents/salary/config")
        assert resp.status_code == 200
        assert resp.json()["product"] == "salarios"

    def test_unknown_agent_404(self, client):
        resp = client.get("/agents/nonexistent/config")
        assert resp.status_code == 404

    def test_404_includes_available_agents(self, client):
        data = client.get("/agents/nonexistent/config").json()
        assert "Disponibles" in data["detail"]


class TestRunAgentEndpoint:
    """Tests de validación del endpoint POST /agents/{name}/run.
    
    NO ejecuta el agente real (eso requeriría LLM + MCP).
    Solo valida routing y validación de inputs.
    """

    def test_unknown_agent_404(self, client):
        resp = client.post(
            "/agents/nonexistent/run",
            json={"provider": "Test", "country_code": "ES"},
        )
        assert resp.status_code == 404

    def test_invalid_country_422(self, client):
        resp = client.post(
            "/agents/electricity/run",
            json={"provider": "Endesa", "country_code": "ZZ"},
        )
        assert resp.status_code == 422
        assert "ZZ" in resp.json()["detail"]

    def test_missing_provider_422(self, client):
        """Provider es required en el schema."""
        resp = client.post(
            "/agents/electricity/run",
            json={"country_code": "ES"},
        )
        assert resp.status_code == 422


class TestRootEndpoint:
    def test_root_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_root_has_service_info(self, client):
        data = client.get("/").json()
        assert "service" in data or "name" in data or "status" in data


class TestOpenAPI:
    def test_openapi_json(self, client):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        data = resp.json()
        assert "paths" in data

    def test_docs_page(self, client):
        resp = client.get("/docs")
        assert resp.status_code == 200