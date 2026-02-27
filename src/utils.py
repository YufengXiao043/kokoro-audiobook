"""Shared utilities for the Kokoro audiobook pipeline."""

import re
from pathlib import Path


def clean_text(text: str) -> str:
    """Clean raw extracted text: fix whitespace, hyphenated line breaks, etc."""
    # Fix hyphenated line breaks from PDF columns: "remem-\nber" → "remember"
    text = re.sub(r"-\n(\w)", r"\1", text)
    # Collapse runs of whitespace (but preserve paragraph breaks)
    text = re.sub(r"[ \t]+", " ", text)
    # Normalize paragraph breaks: 2+ newlines → double newline
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove form-feed / page break characters
    text = text.replace("\f", "\n\n")
    # Strip leading/trailing whitespace
    text = text.strip()
    return text


def split_sentences(text: str) -> list[str]:
    """Split text into sentences suitable for TTS generation.

    Splits on sentence-ending punctuation, keeping the punctuation attached.
    Paragraphs separated by blank lines are always split.
    Returns a flat list of non-empty sentence strings.
    """
    sentences: list[str] = []
    # Split on paragraph boundaries first
    paragraphs = re.split(r"\n\n+", text)
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        # Split on sentence-ending punctuation followed by whitespace + capital
        # Pattern: end of sentence marker, then space(s), then start of next sentence
        raw = re.split(r"(?<=[.!?])\s+(?=[A-Z\"'\u201c\u2018])", para)
        for s in raw:
            s = s.strip()
            if s:
                sentences.append(s)
    return sentences


def make_output_stem(input_path: Path, output_dir: Path) -> Path:
    """Return base Path (no extension) for output files derived from input_path."""
    return output_dir / input_path.stem
