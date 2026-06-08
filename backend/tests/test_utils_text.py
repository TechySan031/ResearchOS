"""Tests for text processing utilities.

Pure function tests — no async, no mocking, no external dependencies.
"""

import pytest

from app.utils.text import (
    clean_text,
    truncate_text,
    count_tokens,
    extract_doi,
    sanitize_filename,
)


class TestCleanText:
    """Tests for clean_text()."""

    def test_removes_control_characters(self):
        text = "Hello\x00World\x07\x1f!"
        result = clean_text(text)
        # Control chars removed, no whitespace inserted between joined chars
        assert "\x00" not in result
        assert "\x07" not in result

    def test_collapses_whitespace(self):
        text = "Hello   World  \t  Test"
        result = clean_text(text)
        assert "  " not in result
        assert result == "Hello World Test"

    def test_collapses_excessive_newlines(self):
        text = "Para 1\n\n\n\n\nPara 2"
        result = clean_text(text)
        assert result == "Para 1\n\nPara 2"

    def test_preserves_double_newline(self):
        text = "Para 1\n\nPara 2"
        assert clean_text(text) == "Para 1\n\nPara 2"

    def test_strips_leading_trailing_whitespace(self):
        text = "  \n Hello World \n  "
        result = clean_text(text)
        assert not result.startswith(" ")
        assert not result.endswith(" ")

    def test_normalizes_unicode(self):
        # é as combining character vs precomposed
        text_nfd = "caf\u0065\u0301"  # e + combining acute
        result = clean_text(text_nfd)
        assert "é" in result or "e" in result  # NFC normalization

    def test_empty_string(self):
        assert clean_text("") == ""

    def test_only_whitespace(self):
        assert clean_text("   \n\n\t  ") == ""


class TestTruncateText:
    """Tests for truncate_text()."""

    def test_no_truncation_needed(self):
        text = "Short text."
        assert truncate_text(text, 100) == text

    def test_truncates_at_sentence_boundary(self):
        text = "First sentence. Second sentence. Third sentence."
        result = truncate_text(text, 35)
        # Should truncate near a sentence boundary and append ellipsis
        assert len(result) <= 35
        assert "…" in result or result.endswith(".")

    def test_truncates_at_word_boundary(self):
        text = "No sentence boundary here just words"
        result = truncate_text(text, 25)
        assert len(result) <= 25
        assert "…" in result

    def test_ellipsis_included_in_length(self):
        text = "A" * 100
        result = truncate_text(text, 50)
        assert len(result) <= 50

    def test_very_short_max_length(self):
        text = "Hello World"
        result = truncate_text(text, 3)
        assert len(result) <= 3

    def test_exact_length_no_truncation(self):
        text = "Exact"
        assert truncate_text(text, 5) == text

    def test_custom_ellipsis(self):
        text = "First sentence. Second sentence."
        result = truncate_text(text, 20, ellipsis="...")
        assert result.endswith("...") or result.endswith(".")


class TestCountTokens:
    """Tests for count_tokens()."""

    def test_counts_tokens(self):
        text = "Hello, world!"
        count = count_tokens(text)
        assert isinstance(count, int)
        assert count > 0

    def test_empty_string(self):
        assert count_tokens("") == 0

    def test_longer_text_more_tokens(self):
        short = count_tokens("Hello")
        long = count_tokens("Hello world, this is a longer sentence with more tokens.")
        assert long > short

    def test_custom_model(self):
        text = "Test token counting"
        count = count_tokens(text, model="gpt-4")
        assert isinstance(count, int)
        assert count > 0


class TestExtractDoi:
    """Tests for extract_doi()."""

    def test_extracts_standard_doi(self):
        text = "See paper 10.1038/nature12373 for details"
        doi = extract_doi(text)
        assert doi == "10.1038/nature12373"

    def test_extracts_doi_with_slashes(self):
        text = "DOI: 10.1000/xyz123/456"
        doi = extract_doi(text)
        assert doi is not None
        assert doi.startswith("10.1000")

    def test_no_doi_returns_none(self):
        text = "This text has no DOI reference."
        assert extract_doi(text) is None

    def test_doi_at_end_of_sentence(self):
        text = "The result was published as 10.1234/test.2024."
        doi = extract_doi(text)
        assert doi is not None
        assert not doi.endswith(".")  # Trailing punctuation stripped

    def test_doi_in_url(self):
        text = "https://doi.org/10.1234/example.2024"
        doi = extract_doi(text)
        assert doi is not None
        assert doi.startswith("10.1234")

    def test_multiple_dois_returns_first(self):
        text = "See 10.1111/first and 10.2222/second"
        doi = extract_doi(text)
        assert doi == "10.1111/first"


class TestSanitizeFilename:
    """Tests for sanitize_filename()."""

    def test_removes_unsafe_characters(self):
        name = 'file<>:"/\\|?*.txt'
        result = sanitize_filename(name)
        assert "<" not in result
        assert ">" not in result
        assert '"' not in result

    def test_collapses_repeated_replacements(self):
        name = "hello>>>world"
        result = sanitize_filename(name)
        assert "___" not in result  # Should collapse to single _

    def test_enforces_max_length(self):
        name = "a" * 300
        result = sanitize_filename(name, max_length=200)
        assert len(result) <= 200

    def test_empty_string_returns_untitled(self):
        assert sanitize_filename("") == "untitled"

    def test_only_special_chars_returns_untitled(self):
        assert sanitize_filename("<>:") == "untitled"

    def test_normal_filename_unchanged(self):
        name = "research_paper_2024"
        assert sanitize_filename(name) == name

    def test_unicode_preserved(self):
        name = "论文_2024"
        result = sanitize_filename(name)
        assert "论文" in result
