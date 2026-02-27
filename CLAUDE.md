# Kokoro Audiobook Pipeline — Project Instructions

## What This Project Is

A local, offline-capable TTS audiobook pipeline for Windows. It converts text from
PDFs and web pages into audio files with a synchronized HTML player that supports
pause, text highlighting, and click-to-seek.

## Architecture Overview

```
[PDF / Web URL] → [extract.py] → [clean .txt]
                                      ↓
                              [generate.py] (Kokoro TTS, CPU)
                                      ↓
                        [audio.mp3 + timestamps.json]
                                      ↓
                          [player.html] (open in browser)
```

## Tech Stack & Constraints

- **OS**: Windows (no WSL required). Must also work on other Windows machines.
- **Python**: Managed by `uv` (not system Python, not conda)
- **TTS Model**: Kokoro-82M via the `kokoro` PyPipeline (Apache 2.0)
- **GPU**: Not required. Target CPU-only inference. Do NOT add torch CUDA/ROCm deps.
- **System dependency**: `espeak-ng` (Windows .msi installer)
- **Player**: Single self-contained HTML file, no build tools, no npm, no server

## Project Structure (Target)

```
kokoro-audiobook/
├── CLAUDE.md                ← you are here
├── PLAN.md                  ← scratchpad: roadmap, decisions, open questions
├── pyproject.toml           ← uv project definition
├── uv.lock                  ← pinned dependencies (auto-generated)
├── setup.bat                ← one-click first-time setup for Windows
├── src/
│   ├── extract.py           ← PDF/URL → clean text
│   ├── generate.py          ← text → audio + timestamp JSON
│   └── utils.py             ← shared helpers (text chunking, cleaning)
├── player/
│   └── player.html          ← single-file audiobook player
├── input/                   ← user drops PDFs/text files here
├── output/                  ← generated audio + JSON land here
└── README.md                ← end-user documentation
```

## Key Design Decisions

### Text Extraction (`extract.py`)
- PDF: use `pymupdf` (aka `fitz`) — fast, pure Python, good text extraction
- Web URL: use `trafilatura` — excellent article/body extraction, strips boilerplate
- Output: clean .txt file in `input/` with one sentence per line or natural paragraphs
- Handle encoding, weird whitespace, hyphenated line breaks from PDFs

### Audio Generation (`generate.py`)
- Use `kokoro.KPipeline` directly (not Kokoro-FastAPI, not Docker)
- Iterate sentence by sentence, collecting (text, audio_array, start_time, end_time)
- Concatenate all audio chunks → single .mp3 file via soundfile + pydub or similar
- Write timestamps.json alongside: `[{text, start, end}, ...]`
- Show progress bar during generation (use `tqdm`)
- Support resuming: if output already partially exists, skip completed segments
- Default voice: `af_heart` (top-ranked), allow override via CLI arg

### HTML Player (`player.html`)
- Fully self-contained: inline CSS, inline JS, no external dependencies
- User opens it in browser, uses file picker to load audio.mp3 + timestamps.json
- Features:
  - Play / Pause button + keyboard shortcut (Space)
  - Speed control (0.5x to 2.0x)
  - Current sentence highlighted in the text panel
  - Click any sentence to seek there
  - Auto-scroll to keep current sentence visible
  - Progress bar showing position in the full text
  - Dark/light mode toggle
  - Remember last position (in-memory, NOT localStorage)

### setup.bat
- Check if `uv` is available, if not download it (standalone installer)
- Run `uv sync` to install Python + all packages
- Check if `espeak-ng` is in PATH, if not print clear instructions
- Download Kokoro model weights into a local cache dir

### Portability
- No global Python install assumed
- No system PATH modifications beyond espeak-ng
- `uv.lock` pins every dependency exactly
- Model weights can be pre-cached in the project folder for offline transfer
- The entire folder is xcopy-deployable to another Windows machine

## CLI Interface

```bash
# Extract text from a PDF
uv run python src/extract.py input/mybook.pdf

# Extract text from a URL
uv run python src/extract.py "https://example.com/article"

# Generate audiobook from extracted text
uv run python src/generate.py input/mybook.txt

# Generate with options
uv run python src/generate.py input/mybook.txt --voice af_bella --speed 1.1

# Output goes to output/mybook.mp3 + output/mybook_timestamps.json
# Then open player/player.html in browser and load those files
```

## Code Style

- Python 3.11+, type hints on all function signatures
- Use `argparse` for CLI, not click/typer (fewer deps)
- Keep it simple: no classes where functions suffice
- Docstrings on public functions
- Print human-friendly progress messages to stderr
- Errors should be caught and reported clearly, not stack traces for user errors

## Testing

- Not a priority for v1. Focus on getting a working pipeline.
- But do verify: run extract on a sample PDF, generate a short clip, confirm player loads it.

## What NOT To Do

- Do NOT use Docker or WSL
- Do NOT add GPU/CUDA/ROCm dependencies
- Do NOT use a web server for the player — it must work as a local file
- Do NOT use localStorage in the player (sandboxed file:// doesn't support it)
- Do NOT over-engineer: this is a personal tool, not a product
- Do NOT add npm, webpack, or any JS build tools
