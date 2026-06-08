"""Text processing utilities used across the ResearchOS pipeline.

All functions are pure and synchronous — they operate on strings in memory
and have no side-effects.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional

import tiktoken

# ── Pre-compiled patterns ────────────────────────────────────────────────────

_CONTROL_CHARS_RE = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]",
)
_MULTI_WHITESPACE_RE = re.compile(r"[ \t]+")
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")
_DOI_RE = re.compile(
    r"\b(10\.\d{4,9}/[-._;()/:A-Z0-9]+)\b",
    re.IGNORECASE,
)
_UNSAFE_FILENAME_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def clean_text(text: str) -> str:
    """Normalize whitespace and strip invisible control characters.

    Args:
        text: Raw input text (e.g. extracted from a PDF).

    Returns:
        Cleaned text with single spaces, normalized newlines, and no
        control characters.
    """
    # Remove control characters but keep \n and \t initially
    text = _CONTROL_CHARS_RE.sub("", text)
    # Normalize Unicode to NFC form
    text = unicodedata.normalize("NFC", text)
    # Collapse horizontal whitespace (spaces and tabs) to a single space
    text = _MULTI_WHITESPACE_RE.sub(" ", text)
    # Collapse 3+ consecutive newlines to exactly two
    text = _MULTI_NEWLINE_RE.sub("\n\n", text)
    return text.strip()


def truncate_text(
    text: str,
    max_length: int,
    *,
    ellipsis: str = "…",
) -> str:
    """Smartly truncate *text* at the nearest sentence boundary.

    If the text is already within ``max_length`` it is returned unchanged.
    Otherwise the function walks backwards from ``max_length`` to find the
    last sentence-ending punctuation (``.``, ``!``, ``?``) and cuts there.
    If no sentence boundary is found, it falls back to the last whitespace
    boundary.

    Args:
        text: Input text to truncate.
        max_length: Maximum character count (including the ellipsis).
        ellipsis: String appended when truncation occurs.

    Returns:
        The (possibly truncated) text.
    """
    if len(text) <= max_length:
        return text

    budget = max_length - len(ellipsis)
    if budget <= 0:
        return ellipsis[:max_length]

    window = text[:budget]

    # Prefer cutting at a sentence boundary
    for sep in (".", "!", "?"):
        idx = window.rfind(sep)
        if idx > 0:
            return window[: idx + 1] + ellipsis

    # Fall back to last whitespace
    idx = window.rfind(" ")
    if idx > 0:
        return window[:idx] + ellipsis

    # Hard cut
    return window + ellipsis


# ── Token counting ───────────────────────────────────────────────────────────

_TOKENIZER_CACHE: dict[str, tiktoken.Encoding] = {}


def _get_encoding(model: str) -> tiktoken.Encoding:
    """Return a cached tiktoken encoding for the given model name."""
    if model not in _TOKENIZER_CACHE:
        try:
            _TOKENIZER_CACHE[model] = tiktoken.encoding_for_model(model)
        except KeyError:
            # Fall back to cl100k_base (GPT-4 / ChatGPT family)
            _TOKENIZER_CACHE[model] = tiktoken.get_encoding("cl100k_base")
    return _TOKENIZER_CACHE[model]


def count_tokens(text: str, *, model: str = "gpt-4") -> int:
    """Count the number of tokens in *text* using tiktoken.

    Args:
        text: The string to tokenize.
        model: The model name whose tokenizer to use.  Defaults to
               ``"gpt-4"`` (cl100k_base encoding).

    Returns:
        Integer token count.
    """
    enc = _get_encoding(model)
    return len(enc.encode(text))


# ── DOI extraction ───────────────────────────────────────────────────────────


def extract_doi(text: str) -> Optional[str]:
    """Extract the first DOI from *text*.

    Args:
        text: Arbitrary text that may contain a DOI reference.

    Returns:
        The DOI string (e.g. ``"10.1000/xyz123"``) or ``None``.
    """
    match = _DOI_RE.search(text)
    if match:
        doi = match.group(1)
        # Strip trailing punctuation that often clings to DOIs in running text
        doi = doi.rstrip(".,;:)")
        return doi
    return None


# ── Filename sanitization ───────────────────────────────────────────────────


def sanitize_filename(
    name: str,
    *,
    max_length: int = 200,
    replacement: str = "_",
) -> str:
    """Convert an arbitrary string into a safe filename.

    Removes or replaces characters that are illegal on Windows / POSIX,
    collapses repeated separators, and enforces a maximum length.

    Args:
        name: The raw filename candidate.
        max_length: Maximum length of the returned filename (without
                    extension).
        replacement: Character(s) to substitute for unsafe characters.

    Returns:
        A filesystem-safe filename string.
    """
    name = unicodedata.normalize("NFC", name)
    # Replace unsafe chars
    name = _UNSAFE_FILENAME_RE.sub(replacement, name)
    # Collapse repeated replacement chars
    if replacement:
        collapse_re = re.compile(re.escape(replacement) + r"+")
        name = collapse_re.sub(replacement, name)
    # Strip leading/trailing separators and whitespace
    name = name.strip(f" .{replacement}")
    # Enforce length
    if len(name) > max_length:
        name = name[:max_length].rstrip(f" .{replacement}")
    # Final fallback
    return name or "untitled"
