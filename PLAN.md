# PLAN.md — Architecture Decisions & Project Log

> Internal reference for Claude Code. Tracks decisions, known issues, and completed phases.

---

## Current State (Phase 6 complete)

All phases complete. The pipeline is fully functional end-to-end:
- `run.py` — unified entry point (extract + generate + auto-open player)
- `extract.py` — PDF (pymupdf) + URL (trafilatura) → clean text
- `generate.py` — Kokoro KPipeline → WAV + timestamps JSON
- `utils.py` — `clean_text`, `split_sentences`, `make_output_stem`, `slugify`
- `player.html` — self-contained player with drag-and-drop, dark mode, keyboard shortcuts

---

## Completed Phases

### Phase 1: Project skeleton
- uv project initialized, Python 3.11 pinned
- CPU-only torch via `[[tool.uv.index]]` pytorch-cpu source override
- Directory structure: `src/`, `player/`, `input/`, `output/`
- `setup.bat` created

### Phase 2: Text extraction (`src/extract.py`)
- PDF: `pymupdf` (import as `fitz`) — fast, pure Python
- URL: `trafilatura` — extracts article body, strips boilerplate
- `clean_text()` utility: fixes hyphenated line breaks, normalizes whitespace

### Phase 3: Audio generation (`src/generate.py`)
- `KPipeline(lang_code='a')` — American English, CPU-only
- Sentence-by-sentence generation → numpy arrays → `soundfile` writes WAV (PCM_16, 24kHz)
- Timestamps JSON: `[{text, start, end}]` in seconds (float, 3dp)
- Resume: validates WAV duration vs timestamp end before trusting existing files (±2s)
- Progress saved every 10 sentences via tqdm

### Phase 4: HTML player (`player/player.html`)
- Fully self-contained (inline CSS + JS, no external deps, works on `file://`)
- Dual file-card UI + drag-and-drop loading
- Binary search sentence sync on `timeupdate`
- Click-to-seek, Space/←/→ keyboard shortcuts
- Dark mode (respects `prefers-color-scheme`)
- In-memory position tracking (no `localStorage` — blocked on `file://`)

### Phase 5: Polish
- `setup.bat`: uv install + espeak-ng check + model pre-download
- End-to-end test: `input/kokoro.txt` → `output/kokoro.wav` (9.3 MB, 3m21s, 32 sentences)

### Phase 6: Ease-of-use
- `src/run.py`: unified pipeline (Feature A) — URL/PDF/TXT in one command
- Smart URL output naming via `slugify(title)` from `bare_extraction()` (Feature B)
- Auto-opens `player.html` in browser after generation via `webbrowser.open()` (Feature C)
- Drag-and-drop in player: drop both files → auto-start; drop one → populates card (Feature D)

---

## Key Decisions

| Decision | Rationale |
|---|---|
| WAV output (not MP3) | Browsers support WAV natively — no ffmpeg needed |
| `soundfile` for audio write | Pure Python, no system dependency, supports PCM_16 |
| `pymupdf` for PDF | Fast, pure Python wheel, good text layout handling |
| `trafilatura` for URL | Best-in-class article extraction, minimal noise |
| CPU-only torch | `[[tool.uv.index]]` pytorch-cpu override — avoids ~3 GB CUDA wheels |
| `pip` as a dependency | `kokoro` calls `pip` at first run to download `en_core_web_sm` via spacy |
| Regex sentence splitter | Paragraph-aware, handles smart quotes, no NLTK/spacy dependency |
| In-memory position | `localStorage` is blocked on `file://` protocol in all browsers |
| `bare_extraction()` for URLs | Returns `Metadata` object with `.title` + `.text` in one fetch |

---

## Known Warnings (harmless)

- **torch FutureWarning** about `weight_norm` — upstream kokoro/torch issue, no impact
- **HuggingFace symlinks** — Windows needs Developer Mode; cache works anyway (uses copies)
- **"Defaulting repo_id to hexgrad/Kokoro-82M"** — suppress with explicit `repo_id` arg in KPipeline

---

## Bugs Fixed

- **pydub/ffmpeg removed**: original plan used pydub for MP3 output. Switched to WAV
  via soundfile — simpler, zero system deps, browsers play WAV natively.
- **Resume bug**: stale timestamps + missing WAV caused silent mismatch. Fixed by
  comparing WAV duration vs `timestamps[-1]["end"]` before trusting resume state.
- **pip missing from venv**: kokoro downloads `en_core_web_sm` via pip at first run.
  Added `pip>=24.0` to pyproject.toml dependencies.
