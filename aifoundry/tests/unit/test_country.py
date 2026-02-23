"""
Tests para utils/country.py — información de países y config Brave.
"""

import pytest
from aifoundry.app.utils.country import (
    get_country_info,
    get_brave_country_code,
    get_currency_info,
    get_brave_search_lang,
    get_brave_ui_lang,
    get_brave_config,
)


class TestGetCountryInfo:
    def test_spain(self):
        info = get_country_info("ES")
        assert info["name"] == "España"
        assert info["currency"] == "EUR"
        assert info["language"] == "es"

    def test_portugal(self):
        info = get_country_info("PT")
        assert info["name"] == "Portugal"
        assert info["language"] == "pt"

    def test_france(self):
        info = get_country_info("FR")
        assert info["name"] == "Francia"
        assert info["language"] == "fr"

    def test_uk(self):
        info = get_country_info("UK")
        assert info["currency"] == "GBP"
        assert info["currency_symbol"] == "£"

    def test_case_insensitive(self):
        info = get_country_info("es")
        assert info["name"] == "España"

    def test_unknown_country_defaults(self):
        info = get_country_info("ZZ")
        assert info["name"] == "ZZ"
        assert info["currency"] == "EUR"
        assert info["language"] == "en"

    def test_returns_copy(self):
        """Verifica que modificar el resultado no afecta al original."""
        info1 = get_country_info("ES")
        info1["name"] = "Modified"
        info2 = get_country_info("ES")
        assert info2["name"] == "España"


class TestGetBraveCountryCode:
    def test_uk_to_gb(self):
        assert get_brave_country_code("UK") == "GB"

    def test_spain_unchanged(self):
        assert get_brave_country_code("ES") == "ES"

    def test_unknown_passthrough(self):
        assert get_brave_country_code("XX") == "XX"


class TestGetCurrencyInfo:
    def test_spain_eur(self):
        info = get_currency_info("ES")
        assert info["currency"] == "EUR"
        assert info["symbol"] == "€"

    def test_uk_gbp(self):
        info = get_currency_info("UK")
        assert info["currency"] == "GBP"
        assert info["symbol"] == "£"

    def test_poland_pln(self):
        info = get_currency_info("PL")
        assert info["currency"] == "PLN"
        assert info["symbol"] == "zł"


class TestBraveSearchLang:
    def test_spanish(self):
        assert get_brave_search_lang("es") == "es"

    def test_portuguese(self):
        assert get_brave_search_lang("pt") == "pt-pt"

    def test_english(self):
        assert get_brave_search_lang("en") == "en"

    def test_unknown_defaults_en(self):
        assert get_brave_search_lang("xx") == "en"


class TestBraveUiLang:
    def test_spain(self):
        assert get_brave_ui_lang("ES") == "es-ES"

    def test_portugal(self):
        assert get_brave_ui_lang("PT") == "pt-BR"

    def test_uk(self):
        assert get_brave_ui_lang("UK") == "en-GB"

    def test_unknown_defaults_en_us(self):
        assert get_brave_ui_lang("ZZ") == "en-US"


class TestGetBraveConfig:
    def test_spain_full_config(self):
        cfg = get_brave_config("ES")
        assert cfg == {
            "country": "ES",
            "search_lang": "es",
            "ui_lang": "es-ES",
        }

    def test_portugal_full_config(self):
        cfg = get_brave_config("PT")
        assert cfg == {
            "country": "PT",
            "search_lang": "pt-pt",
            "ui_lang": "pt-BR",
        }

    def test_uk_full_config(self):
        cfg = get_brave_config("UK")
        assert cfg == {
            "country": "GB",
            "search_lang": "en",
            "ui_lang": "en-GB",
        }