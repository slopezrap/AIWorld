"""
Tests para schemas/agent_responses.py — esquemas de respuesta estructurada.
"""

import pytest
from aifoundry.app.schemas.agent_responses import (
    ScraperResponse,
    SalaryResponse,
    SalaryData,
    get_response_schema,
    RESPONSE_SCHEMAS,
)


class TestScraperResponse:
    def test_defaults(self):
        r = ScraperResponse()
        assert r.query_es == ""
        assert r.urls == []
        assert r.used_playwright is False
        assert r.validation_status == "pending"

    def test_with_data(self):
        r = ScraperResponse(
            query_es="precio electricidad",
            urls=["https://a.com", "https://b.com"],
            used_playwright=True,
            summary="Encontrados 5 resultados",
            validation_status="valid",
        )
        assert len(r.urls) == 2
        assert r.used_playwright is True
        assert r.validation_status == "valid"


class TestSalaryData:
    def test_minimal(self):
        s = SalaryData(position="Cajero")
        assert s.position == "Cajero"
        assert s.salary_min is None
        assert s.salary_period == "year"
        assert s.currency == "EUR"

    def test_full(self):
        s = SalaryData(
            position="Ingeniero",
            salary_min=30000,
            salary_max=50000,
            salary_avg=40000,
            salary_period="year",
            currency="EUR",
            source_url="https://example.com",
        )
        assert s.salary_avg == 40000
        assert s.source_url == "https://example.com"


class TestSalaryResponse:
    def test_minimal(self):
        r = SalaryResponse(
            provider="H&M",
            country="España",
            query_used="salarios H&M",
            summary="No se encontraron datos",
        )
        assert r.provider == "H&M"
        assert r.salaries == []
        assert r.confidence == "medium"

    def test_with_salaries(self):
        r = SalaryResponse(
            provider="Zara",
            country="España",
            query_used="salarios Zara",
            summary="5 puestos encontrados",
            salaries=[
                SalaryData(position="Cajero", salary_avg=18000),
                SalaryData(position="Manager", salary_avg=35000),
            ],
            confidence="high",
        )
        assert len(r.salaries) == 2
        assert r.salaries[0].position == "Cajero"


class TestGetResponseSchema:
    def test_salary_by_name(self):
        assert get_response_schema("salary") is SalaryResponse

    def test_salarios_alias(self):
        assert get_response_schema("salarios") is SalaryResponse

    def test_unknown_defaults_to_scraper(self):
        assert get_response_schema("electricity") is ScraperResponse
        assert get_response_schema("unknown") is ScraperResponse

    def test_case_insensitive(self):
        assert get_response_schema("SALARY") is SalaryResponse
        assert get_response_schema("Salarios") is SalaryResponse