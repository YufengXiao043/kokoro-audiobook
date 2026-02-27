"""extract.py — Convert PDF or web URL to clean text.

Usage:
    uv run python src/extract.py input/mybook.pdf
    uv run python src/extract.py "https://example.com/article"
    uv run python src/extract.py input/mybook.pdf --output input/mybook_clean.txt
"""

import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse

from utils import clean_text


def is_url(value: str) -> bool:
    """Return True if value looks like an HTTP/HTTPS URL."""
    try:
        result = urlparse(value)
        return result.scheme in ("http", "https")
    except ValueError:
        return False


def extract_pdf(pdf_path: Path) -> str:
    """Extract text from a PDF file using PyMuPDF (fitz)."""
    try:
        import fitz  # pymupdf
    except ImportError:
        print("Error: pymupdf not installed. Run: uv sync", file=sys.stderr)
        sys.exit(1)

    print(f"Extracting text from PDF: {pdf_path}", file=sys.stderr)
    doc = fitz.open(str(pdf_path))
    pages_text: list[str] = []
    for i, page in enumerate(doc):
        text = page.get_text("text")  # type: ignore[arg-type]
        pages_text.append(text)
        if (i + 1) % 10 == 0:
            print(f"  Processed {i + 1}/{len(doc)} pages...", file=sys.stderr)
    doc.close()
    raw = "\n\n".join(pages_text)
    return clean_text(raw)


def extract_url(url: str) -> tuple[str, str | None]:
    """Extract article body and title from a web URL using trafilatura.

    Returns (text, title) where title may be None if not found.
    """
    try:
        import trafilatura
    except ImportError:
        print("Error: trafilatura not installed. Run: uv sync", file=sys.stderr)
        sys.exit(1)

    print(f"Fetching and extracting: {url}", file=sys.stderr)
    downloaded = trafilatura.fetch_url(url)
    if downloaded is None:
        print(f"Error: Could not fetch URL: {url}", file=sys.stderr)
        sys.exit(1)

    result = trafilatura.bare_extraction(
        downloaded,
        include_comments=False,
        include_tables=False,
        no_fallback=False,
    )

    if result is None:
        print("Error: Could not extract readable text from the page.", file=sys.stderr)
        sys.exit(1)

    # bare_extraction() returns a Metadata dataclass (trafilatura >= 0.9) or dict (older)
    if isinstance(result, dict):
        raw_text: str = result.get("text") or ""
        title: str | None = result.get("title") or None
    else:
        raw_text = getattr(result, "text", None) or ""
        title = getattr(result, "title", None) or None

    if not raw_text:
        print("Error: Could not extract readable text from the page.", file=sys.stderr)
        sys.exit(1)

    return clean_text(raw_text), title


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract clean text from a PDF or web URL."
    )
    parser.add_argument(
        "source",
        help="Path to a PDF file or an HTTP/HTTPS URL.",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output .txt file path. Defaults to input/<stem>.txt for PDFs, "
             "or input/extracted.txt for URLs.",
    )
    args = parser.parse_args()

    source: str = args.source
    input_dir = Path(__file__).parent.parent / "input"
    input_dir.mkdir(exist_ok=True)

    # Extract text
    if is_url(source):
        text, _title = extract_url(source)  # title ignored in standalone CLI mode
        default_output = input_dir / "extracted.txt"
    else:
        pdf_path = Path(source)
        if not pdf_path.exists():
            print(f"Error: File not found: {pdf_path}", file=sys.stderr)
            sys.exit(1)
        text = extract_pdf(pdf_path)
        default_output = input_dir / (pdf_path.stem + ".txt")

    # Determine output path
    out_path = Path(args.output) if args.output else default_output

    # Write output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    print(f"Extracted {len(text.split())} words → {out_path}", file=sys.stderr)
    print(str(out_path))  # print path to stdout for scripting


if __name__ == "__main__":
    main()
