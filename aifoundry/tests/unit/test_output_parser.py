"""
Tests unitarios del módulo de output parsing.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from pydantic import BaseModel, Field

from aifoundry.app.core.agents.scraper.output_parser import OutputParser


class FakeResponse(BaseModel):
    """Modelo Pydantic fake para tests."""

    provider: str = Field(description="Provider")
    summary: str = Field(description="Summary")


class TestOutputParserParseText:
    """Tests de parsing de texto libre."""

    def test_extracts_urls(self):
        parser = OutputParser()
        result = parser.parse_text(
            "Datos en https://example.com/page y https://other.com/data"
        )
        assert "urls" in result
        assert "https://example.com/page" in result["urls"]

    def test_detects_playwright(self):
        parser = OutputParser()
        result = parser.parse_text("Usé browser_navigate para acceder")
        assert result.get("used_playwright") is True

    def test_empty_text(self):
        parser = OutputParser()
        result = parser.parse_text("Sin datos relevantes.")
        assert isinstance(result, dict)


class TestOutputParserExtractStructured:
    """Tests de extracción de structured output."""

    async def test_native_structured_from_result(self):
        """Extrae structured_response del resultado si existe."""
        fake = FakeResponse(provider="Test", summary="OK")
        parser = OutputParser(response_model=FakeResponse)

        result = {"structured_response": fake}
        structured = await parser.extract_structured(
            result=result,
            output="texto",
            llm=MagicMock(),
            config={"product": "test"},
        )

        assert structured is fake
        assert structured.provider == "Test"

    async def test_fallback_to_post_processing(self):
        """Si no hay structured_response, usa with_structured_output."""
        mock_llm = MagicMock()
        fake_result = FakeResponse(provider="Fallback", summary="OK")
        mock_structured_llm = MagicMock()
        mock_structured_llm.ainvoke = AsyncMock(return_value=fake_result)
        mock_llm.with_structured_output = MagicMock(return_value=mock_structured_llm)

        parser = OutputParser(response_model=FakeResponse)

        result = {}  # Sin structured_response
        structured = await parser.extract_structured(
            result=result,
            output="texto de prueba",
            llm=mock_llm,
            config={"product": "test", "provider": "P", "country_code": "ES"},
        )

        assert structured is fake_result
        mock_llm.with_structured_output.assert_called_once_with(FakeResponse)

    async def test_legacy_structured_output(self):
        """use_structured_output=True usa post-processing."""
        mock_llm = MagicMock()
        fake_result = MagicMock()
        mock_structured_llm = MagicMock()
        mock_structured_llm.ainvoke = AsyncMock(return_value=fake_result)
        mock_llm.with_structured_output = MagicMock(return_value=mock_structured_llm)

        parser = OutputParser(use_structured_output=True)

        structured = await parser.extract_structured(
            result={},
            output="datos de prueba",
            llm=mock_llm,
            config={"product": "salarios"},
        )

        assert structured is fake_result

    async def test_no_structured_output(self):
        """Sin response_model ni use_structured_output retorna None."""
        parser = OutputParser()

        structured = await parser.extract_structured(
            result={},
            output="texto",
            llm=MagicMock(),
            config={"product": "test"},
        )

        assert structured is None

    async def test_conversion_error_returns_none(self):
        """Si with_structured_output falla, retorna None."""
        mock_llm = MagicMock()
        mock_llm.with_structured_output = MagicMock(
            side_effect=Exception("LLM error")
        )

        parser = OutputParser(response_model=FakeResponse)

        structured = await parser.extract_structured(
            result={},
            output="texto",
            llm=mock_llm,
            config={"product": "test"},
        )

        assert structured is None

    async def test_legacy_no_product_returns_none(self):
        """Legacy mode sin product en config retorna None."""
        parser = OutputParser(use_structured_output=True)

        structured = await parser.extract_structured(
            result={},
            output="texto",
            llm=MagicMock(),
            config={},  # Sin product
        )

        assert structured is None