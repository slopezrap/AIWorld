"""
Tests para get_system_prompt() — generación de system prompts.
"""

import pytest
from aifoundry.app.core.agents.scraper.prompts import get_system_prompt


class TestSystemPromptBasic:
    """Verifica que el prompt genérico se genera correctamente."""

    def test_contains_product(self, electricity_config):
        prompt = get_system_prompt(electricity_config)
        assert "electricidad" in prompt

    def test_contains_provider(self, electricity_config):
        prompt = get_system_prompt(electricity_config)
        assert "Endesa" in prompt

    def test_contains_country(self, electricity_config):
        prompt = get_system_prompt(electricity_config)
        assert "España" in prompt

    def test_contains_brave_params(self, electricity_config):
        prompt = get_system_prompt(electricity_config)
        assert "brave_web_search" in prompt
        assert 'freshness="pw"' in prompt
        assert 'search_lang="es"' in prompt
        assert 'country="ES"' in prompt

    def test_contains_query(self, electricity_config):
        prompt = get_system_prompt(electricity_config)
        assert "precio electricidad Endesa España febrero 2026" in prompt

    def test_contains_steps(self, electricity_config):
        prompt = get_system_prompt(electricity_config)
        assert "PASO 1" in prompt
        assert "PASO 5" in prompt


class TestSystemPromptLanguages:
    """Verifica comportamiento con diferentes idiomas."""

    def test_spanish_no_translation(self, electricity_config):
        prompt = get_system_prompt(electricity_config)
        assert "español tal cual" in prompt

    def test_french_needs_translation(self, social_config):
        prompt = get_system_prompt(social_config)
        assert "francés" in prompt

    def test_portuguese_brave_codes(self):
        config = {
            "product": "test",
            "country_code": "PT",
            "language": "pt",
            "freshness": "py",
        }
        prompt = get_system_prompt(config)
        assert 'search_lang="pt-pt"' in prompt
        assert 'ui_lang="pt-BR"' in prompt


class TestSystemPromptExtractionValidation:
    """Verifica inyección de extraction_prompt y validation_prompt."""

    def test_extraction_prompt_injected(self, electricity_config):
        prompt = get_system_prompt(electricity_config)
        assert "INSTRUCCIONES ESPECÍFICAS DE EXTRACCIÓN" in prompt
        assert "Extrae tarifas y precios" in prompt

    def test_validation_prompt_injected(self, electricity_config):
        prompt = get_system_prompt(electricity_config)
        assert "VALIDACIONES ESPECÍFICAS" in prompt
        assert "0.01-1.00" in prompt

    def test_no_extraction_without_prompt(self, salary_config):
        prompt = get_system_prompt(salary_config)
        assert "INSTRUCCIONES ESPECÍFICAS DE EXTRACCIÓN" not in prompt

    def test_no_validation_without_prompt(self, salary_config):
        prompt = get_system_prompt(salary_config)
        assert "VALIDACIONES ESPECÍFICAS" not in prompt


class TestSystemPromptCustomTemplate:
    """Verifica system_prompt_template custom."""

    def test_custom_template_used(self):
        config = {
            "product": "test",
            "country_code": "ES",
            "language": "es",
            "system_prompt_template": "Eres un agente para {product} en {country_name}.",
        }
        prompt = get_system_prompt(config)
        assert prompt == "Eres un agente para test en España."

    def test_custom_template_all_vars(self):
        config = {
            "product": "electricidad",
            "provider": "Endesa",
            "country_code": "ES",
            "language": "es",
            "freshness": "pw",
            "system_prompt_template": "{product}|{provider}|{country_name}|{language_name}|{freshness}",
        }
        prompt = get_system_prompt(config)
        assert prompt == "electricidad|Endesa|España|español|pw"

    def test_fallback_on_unknown_variable(self):
        config = {
            "product": "test",
            "country_code": "ES",
            "language": "es",
            "system_prompt_template": "Template con {variable_inexistente}",
        }
        prompt = get_system_prompt(config)
        # Debe caer al genérico por KeyError
        assert "brave_web_search" in prompt

    def test_no_template_uses_generic(self, electricity_config):
        prompt = get_system_prompt(electricity_config)
        assert "PASO 1" in prompt
        assert "PASO 5" in prompt


class TestSystemPromptDefaults:
    """Verifica defaults cuando faltan campos."""

    def test_minimal_config(self):
        prompt = get_system_prompt({})
        assert "producto" in prompt  # default product
        assert "España" in prompt  # default country ES

    def test_empty_provider(self):
        config = {"product": "test", "country_code": "ES", "language": "es"}
        prompt = get_system_prompt(config)
        assert "(genérico)" in prompt