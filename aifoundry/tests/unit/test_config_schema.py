"""
Tests para config_schema.py — validación Pydantic de config.json de agentes.
"""

import pytest
from pydantic import ValidationError
from aifoundry.app.core.agents.scraper.config_schema import AgentConfig, CountryConfig


class TestCountryConfig:
    def test_valid(self):
        c = CountryConfig(language="es", providers=["Endesa"])
        assert c.language == "es"
        assert c.providers == ["Endesa"]

    def test_empty_providers_default(self):
        c = CountryConfig(language="fr")
        assert c.providers == []

    def test_language_stripped_lowered(self):
        c = CountryConfig(language="  ES  ")
        assert c.language == "es"

    def test_empty_language_fails(self):
        with pytest.raises(ValidationError, match="language"):
            CountryConfig(language="   ")

    def test_extra_field_forbidden(self):
        with pytest.raises(ValidationError, match="extra"):
            CountryConfig(language="es", typo_field="oops")


class TestAgentConfigValid:
    def test_minimal(self, minimal_agent_config_dict):
        cfg = AgentConfig(**minimal_agent_config_dict)
        assert cfg.product == "test_product"
        assert cfg.freshness == "pw"  # default
        assert cfg.extraction_prompt == ""
        assert cfg.system_prompt_template is None
        assert cfg.social_networks is None

    def test_full_electricity(self):
        cfg = AgentConfig(
            product="electricidad",
            query_template="precio {product} {provider}",
            countries={
                "ES": {"language": "es", "providers": ["Endesa", "Iberdrola"]},
                "PT": {"language": "pt", "providers": ["EDP"]},
            },
            freshness="pw",
            extraction_prompt="Extrae tarifas",
            validation_prompt="Valida precios",
        )
        assert cfg.get_country_codes() == ["ES", "PT"]
        assert cfg.get_providers("ES") == ["Endesa", "Iberdrola"]
        assert cfg.get_language("PT") == "pt"

    def test_with_social_networks(self):
        cfg = AgentConfig(
            product="social",
            query_template="{product}",
            countries={"ES": {"language": "es"}},
            social_networks=["Instagram", "X"],
        )
        assert cfg.social_networks == ["Instagram", "X"]

    def test_with_system_prompt_template(self):
        cfg = AgentConfig(
            product="test",
            query_template="{product}",
            countries={"ES": {"language": "es"}},
            system_prompt_template="Custom: {product}",
        )
        assert cfg.system_prompt_template == "Custom: {product}"


class TestAgentConfigHelpers:
    def test_get_providers_unknown_country(self, minimal_agent_config_dict):
        cfg = AgentConfig(**minimal_agent_config_dict)
        assert cfg.get_providers("ZZ") == []

    def test_get_language_unknown_country(self, minimal_agent_config_dict):
        cfg = AgentConfig(**minimal_agent_config_dict)
        assert cfg.get_language("ZZ") == "es"  # fallback

    def test_get_country_codes(self, minimal_agent_config_dict):
        cfg = AgentConfig(**minimal_agent_config_dict)
        assert cfg.get_country_codes() == ["ES"]


class TestAgentConfigInvalid:
    def test_missing_product(self):
        with pytest.raises(ValidationError, match="product"):
            AgentConfig(
                query_template="q",
                countries={"ES": {"language": "es"}},
            )

    def test_missing_query_template(self):
        with pytest.raises(ValidationError, match="query_template"):
            AgentConfig(
                product="test",
                countries={"ES": {"language": "es"}},
            )

    def test_empty_product(self):
        with pytest.raises(ValidationError, match="product"):
            AgentConfig(
                product="   ",
                query_template="q",
                countries={"ES": {"language": "es"}},
            )

    def test_empty_countries(self):
        with pytest.raises(ValidationError, match="countries"):
            AgentConfig(
                product="test",
                query_template="q",
                countries={},
            )

    def test_invalid_freshness(self):
        with pytest.raises(ValidationError, match="freshness"):
            AgentConfig(
                product="test",
                query_template="q",
                countries={"ES": {"language": "es"}},
                freshness="invalid",
            )

    def test_extra_field_forbidden(self):
        with pytest.raises(ValidationError, match="extra"):
            AgentConfig(
                product="test",
                query_template="q",
                countries={"ES": {"language": "es"}},
                unknown_field="oops",
            )

    def test_valid_freshness_values(self):
        """Todas las opciones válidas de freshness."""
        for f in ["pd", "pw", "pm", "py", ""]:
            cfg = AgentConfig(
                product="test",
                query_template="q",
                countries={"ES": {"language": "es"}},
                freshness=f,
            )
            assert cfg.freshness == f