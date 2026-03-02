"""run.py — Unified pipeline: extract + generate + auto-open player.

Usage:
    uv run python src/run.py "https://example.com/article"
    uv run python src/run.py input/mybook.pdf
    uv run python src/run.py input/mybook.txt
    uv run python src/run.py input/mybook.txt --voice af_bella --speed 1.1
    uv run python src/run.py "https://..." --no-open
"""

import argparse
import json
import sys
import webbrowser
from pathlib import Path
from urllib.parse import urlparse

from extract import extract_url, extract_pdf, is_url
from generate import generate_audio
from utils import split_sentences, make_output_stem, slugify, detect_language, resolve_voice


def generate_player_html(
    wav_path: Path,
    timestamps_path: Path,
    player_template: Path,
) -> Path:
    """Inject _AUTOLOAD data into a copy of player.html placed beside the audio.

    The generated output/<stem>_player.html opens and starts playing immediately
    with no file-picker interaction — the browser loads the WAV via a relative path
    and the timestamps are embedded inline as JSON.

    Returns the path to the generated file.
    """
    timestamps = json.loads(timestamps_path.read_text(encoding="utf-8"))
    audio_src = "./" + wav_path.name  # relative — both files live in output/

    # Serialize timestamps; escape </ to prevent premature </script> termination
    ts_json = json.dumps(timestamps, ensure_ascii=False, separators=(",", ":"))
    ts_json = ts_json.replace("</", "<\\/")

    autoload_block = (
        "<script>\n"
        f'window._AUTOLOAD={{audioSrc:"{audio_src}",timestamps:{ts_json}}};\n'
        "</script>"
    )

    html = player_template.read_text(encoding="utf-8")
    html = html.replace("</head>", autoload_block + "\n</head>", 1)

    out_path = wav_path.parent / (wav_path.stem + "_player.html")
    out_path.write_text(html, encoding="utf-8")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract and generate an audiobook from a PDF, URL, or text file."
    )
    parser.add_argument(
        "source",
        help="Path to a .pdf or .txt file, or an HTTP/HTTPS URL.",
    )
    parser.add_argument(
        "--voice",
        default="af_heart",
        help="Kokoro voice name (default: af_heart).",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Speech speed multiplier (default: 1.0).",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for output files (default: output/ in project root).",
    )
    parser.add_argument(
        "--lang",
        default=None,
        help="Language code: 'a' (American English), 'z' (Chinese). "
             "Auto-detected from text if not specified.",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Suppress auto-opening the player in the browser after generation.",
    )
    args = parser.parse_args()

    source: str = args.source
    project_root = Path(__file__).parent.parent
    input_dir = project_root / "input"
    input_dir.mkdir(exist_ok=True)

    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else project_root / "output"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Dispatch: URL / PDF / TXT ──────────────────────────────────────
    output_stem_name: str

    if is_url(source):
        text, title = extract_url(source)
        if title:
            output_stem_name = slugify(title)
            if not output_stem_name:  # slugify can return empty string on exotic titles
                output_stem_name = "extracted"
        else:
            domain = urlparse(source).netloc.replace(".", "-")
            output_stem_name = f"extracted_{domain}"

        # Write extracted text to input/ for reference and potential reuse
        txt_path = input_dir / f"{output_stem_name}.txt"
        txt_path.write_text(text, encoding="utf-8")
        print(f"Extracted text → {txt_path}", file=sys.stderr)

    elif source.lower().endswith(".pdf"):
        pdf_path = Path(source)
        if not pdf_path.exists():
            print(f"Error: File not found: {pdf_path}", file=sys.stderr)
            sys.exit(1)
        text = extract_pdf(pdf_path)
        output_stem_name = pdf_path.stem
        txt_path = input_dir / f"{output_stem_name}.txt"
        txt_path.write_text(text, encoding="utf-8")
        print(f"Extracted text → {txt_path}", file=sys.stderr)

    elif source.lower().endswith(".txt"):
        txt_path = Path(source)
        if not txt_path.exists():
            print(f"Error: File not found: {txt_path}", file=sys.stderr)
            sys.exit(1)
        text = txt_path.read_text(encoding="utf-8")
        output_stem_name = txt_path.stem

    else:
        print(f"Error: Unsupported input: {source!r}", file=sys.stderr)
        print("Supported inputs: HTTP/HTTPS URLs, .pdf files, .txt files", file=sys.stderr)
        sys.exit(1)

    # ── Split into sentences ───────────────────────────────────────────
    sentences = split_sentences(text)
    print(f"Found {len(sentences)} sentences.", file=sys.stderr)

    if not sentences:
        print("Error: No sentences found in input.", file=sys.stderr)
        sys.exit(1)

    # ── Language detection and voice resolution ────────────────────────
    lang_code = args.lang if args.lang else detect_language(text)
    voice = resolve_voice(args.voice, lang_code)

    # ── Generate audio ─────────────────────────────────────────────────
    output_stem = output_dir / output_stem_name
    wav_path, ts_path = generate_audio(sentences, voice, args.speed, output_stem, lang_code)

    # ── Generate per-book player and auto-open ─────────────────────────
    if not args.no_open:
        player_template = project_root / "player" / "player.html"
        if player_template.exists():
            generated = generate_player_html(wav_path, ts_path, player_template)
            print(f"Opening: {generated}", file=sys.stderr)
            webbrowser.open(generated.as_uri())
        else:
            print(f"Warning: Player template not found at {player_template}", file=sys.stderr)


if __name__ == "__main__":
    main()
