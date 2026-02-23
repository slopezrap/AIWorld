"""
Tests para utils/text.py — funciones de procesamiento de texto.
"""

import pytest
from aifoundry.app.utils.text import (
    parse_json_response,
    clean_markdown_code_blocks,
    extract_urls,
    truncate_text,
)


# ─── TRUNCATE TEXT ───────────────────────────────────────────────────────────

class TestTruncateText:
    def test_short_text_unchanged(self):
        assert truncate_text("hello", 100) == "hello"

    def test_exact_length_unchanged(self):
        assert truncate_text("12345", 5) == "12345"

    def test_long_text_truncated(self):
        result = truncate_text("abcdefghij", 5)
        assert result == "abcde..."

    def test_custom_suffix(self):
        result = truncate_text("abcdefghij", 5, suffix=" [truncado]")
        assert result == "abcde [truncado]"

    def test_empty_string(self):
        assert truncate_text("", 100) == ""

    def test_default_max_length(self):
        short = "x" * 4999
        assert truncate_text(short) == short
        long_text = "x" * 5001
        assert len(truncate_text(long_text)) == 5003  # 5000 + "..."


# ─── CLEAN MARKDOWN CODE BLOCKS ─────────────────────────────────────────────

class TestCleanMarkdownCodeBlocks:
    def test_json_block(self):
        text = '```json\n{"key": "value"}\n```'
        assert clean_markdown_code_blocks(text) == '{"key": "value"}'

    def test_plain_block(self):
        text = "```\nsome code\n```"
        assert clean_markdown_code_blocks(text) == "some code"

    def test_no_blocks(self):
        text = "plain text"
        assert clean_markdown_code_blocks(text) == "plain text"

    def test_nested_blocks(self):
        text = "```json\n```json\ndata\n```\n```"
        result = clean_markdown_code_blocks(text)
        assert "```" not in result


# ─── EXTRACT URLS ────────────────────────────────────────────────────────────

class TestExtractUrls:
    def test_basic_url(self):
        urls = extract_urls("Visita https://example.com para más info")
        assert urls == ["https://example.com"]

    def test_multiple_urls(self):
        text = "URL1: https://a.com URL2: https://b.com URL3: https://c.com"
        urls = extract_urls(text)
        assert len(urls) == 3

    def test_max_urls_limit(self):
        text = " ".join(f"https://site{i}.com" for i in range(20))
        urls = extract_urls(text, max_urls=5)
        assert len(urls) == 5

    def test_excludes_search_engines(self):
        text = "https://example.com https://google.com/search?q=test https://brave.com/results"
        urls = extract_urls(text)
        assert urls == ["https://example.com"]

    def test_custom_exclude_patterns(self):
        text = "https://a.com https://b.com https://evil.com"
        urls = extract_urls(text, exclude_patterns=["evil"])
        assert "https://evil.com" not in urls

    def test_deduplicates(self):
        text = "https://a.com y otra vez https://a.com"
        urls = extract_urls(text)
        assert len(urls) == 1

    def test_strips_trailing_punctuation(self):
        text = "Visita https://example.com."
        urls = extract_urls(text)
        assert urls == ["https://example.com"]

    def test_empty_text(self):
        assert extract_urls("") == []

    def test_no_urls(self):
        assert extract_urls("texto sin enlaces") == []


# ─── PARSE JSON RESPONSE ────────────────────────────────────────────────────

class TestParseJsonResponse:
    def test_pure_json(self):
        result = parse_json_response('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_with_surrounding_text(self):
        text = 'Aquí va: {"precios": [1, 2]} fin'
        result = parse_json_response(text)
        assert result == {"precios": [1, 2]}

    def test_json_in_code_block(self):
        text = '```json\n{"key": "value"}\n```'
        result = parse_json_response(text)
        assert result == {"key": "value"}

    def test_no_json(self):
        assert parse_json_response("texto sin json") is None

    def test_empty_input(self):
        assert parse_json_response("") is None
        assert parse_json_response(None) is None

    def test_dict_with_raw_response(self):
        result = parse_json_response({"raw_response": '{"data": 1}'})
        assert result == {"data": 1}

    def test_no_data_found(self):
        assert parse_json_response("NO_DATA_FOUND") is None

    def test_invalid_json(self):
        assert parse_json_response("{invalid json}") is None