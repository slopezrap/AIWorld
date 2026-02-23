"""
Fixtures compartidas para tests de AIFoundry.
"""

import pytest


@pytest.fixture
def electricity_config():
    """Config típica del agente de electricidad."""
    return {
        "product": "electricidad",
        "provider": "Endesa",
        "country_code": "ES",
        "language": "es",
        "query": "precio electricidad Endesa España febrero 2026",
        "freshness": "pw",
        "extraction_prompt": "Extrae tarifas y precios",
        "validation_prompt": "Valida rango 0.01-1.00 €/kWh",
    }


@pytest.fixture
def salary_config():
    """Config típica del agente de salarios."""
    return {
        "product": "salarios",
        "provider": "H&M",
        "country_code": "ES",
        "language": "es",
        "query": "salarios H&M España 2026",
        "freshness": "py",
    }


@pytest.fixture
def social_config():
    """Config típica del agente de social_comments."""
    return {
        "product": "comentarios en redes sociales",
        "provider": "",
        "country_code": "FR",
        "language": "fr",
        "freshness": "py",
    }


@pytest.fixture
def minimal_agent_config_dict():
    """Dict mínimo válido para AgentConfig."""
    return {
        "product": "test_product",
        "query_template": "buscar {product} {provider}",
        "countries": {
            "ES": {"language": "es"},
        },
    }