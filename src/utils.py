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
    Handles both Western (.!?) and CJK (。！？) sentence terminators.
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
        # Split on Western sentence-ending punctuation followed by whitespace + capital
        raw = re.split(r"(?<=[.!?])\s+(?=[A-Z\"'\u201c\u2018])", para)
        # Further split on CJK sentence-ending punctuation (。！？)
        final: list[str] = []
        for chunk in raw:
            parts = re.split(r"(?<=[。！？])\s*(?=\S)", chunk)
            final.extend(parts)
        for s in final:
            s = s.strip()
            if s:
                sentences.append(s)
    return sentences


def detect_language(text: str) -> str:
    """Detect whether text is primarily Chinese or English.

    Returns a Kokoro lang_code: ``'z'`` for Mandarin Chinese, ``'a'`` for
    American English (the default).  Detection is a simple CJK-character
    ratio heuristic — no external dependencies required.
    """
    if not text:
        return "a"
    # Count CJK Unified Ideographs (U+4E00–U+9FFF)
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    # Compare against total non-whitespace characters
    total = sum(1 for ch in text if not ch.isspace())
    if total == 0:
        return "a"
    ratio = cjk / total
    return "z" if ratio > 0.3 else "a"


# Default voices per language — used when the user-selected voice is
# incompatible with the detected language.
_DEFAULT_VOICES: dict[str, str] = {
    "a": "af_heart",   # American English
    "b": "bf_emma",    # British English
    "z": "zf_xiaoni",  # Mandarin Chinese
    "j": "jf_alpha",   # Japanese
}

# Voice prefix → compatible language codes
_VOICE_LANG: dict[str, set[str]] = {
    "a": {"a"},   # af_*, am_* → American English
    "b": {"b"},   # bf_*, bm_* → British English
    "z": {"z"},   # zf_*, zm_* → Chinese
    "j": {"j"},   # jf_*, jm_* → Japanese
}


def resolve_voice(voice: str, lang_code: str) -> str:
    """Return *voice* if it is compatible with *lang_code*, otherwise pick a default.

    Voices are prefixed with a language letter (e.g. ``af_heart`` → ``a``).
    If the prefix doesn't match *lang_code*, we fall back to the default
    voice for that language and print a notice.
    """
    voice_lang_prefix = voice[0] if voice else ""
    compatible_langs = _VOICE_LANG.get(voice_lang_prefix, set())
    if lang_code in compatible_langs:
        return voice
    fallback = _DEFAULT_VOICES.get(lang_code, "af_heart")
    import sys
    print(
        f"Voice '{voice}' is not compatible with detected language "
        f"(lang_code='{lang_code}'). Using '{fallback}' instead.",
        file=sys.stderr,
    )
    return fallback


def make_output_stem(input_path: Path, output_dir: Path) -> Path:
    """Return base Path (no extension) for output files derived from input_path."""
    return output_dir / input_path.stem


def slugify(title: str) -> str:
    r"""Convert a page title to a filesystem-safe slug (max 60 chars).

    Preserves CJK characters (Chinese/Japanese/Korean) alongside ASCII
    alphanumerics so that non-Latin titles produce meaningful filenames.

    Examples:
        "My Great Article! (2026)" → "my-great-article-2026"
        "[战锤40k] 阿里曼：放逐者" → "战锤40k-阿里曼-放逐者"
    """
    title = title.lower()
    # Keep ASCII alphanumerics, CJK Unified Ideographs, Hiragana, Katakana,
    # Hangul Syllables, whitespace, and hyphens.  Strip everything else.
    title = re.sub(
        r"[^a-z0-9\s\-"
        r"\u4e00-\u9fff"   # CJK Unified Ideographs
        r"\u3040-\u309f"   # Hiragana
        r"\u30a0-\u30ff"   # Katakana
        r"\uac00-\ud7af"   # Hangul Syllables
        r"]",
        "",
        title,
    )
    title = re.sub(r"[\s-]+", "-", title)
    title = title.strip("-")
    return title[:60]
