# PLAN.md — Development Scratchpad

> Claude Code: Use this file as your working scratchpad. Update it as you go.
> Check off completed items, note decisions and blockers here.

## Phase 1: Project Skeleton & Dependencies
- [x] Initialize uv project (`uv init`)
- [x] Add dependencies to pyproject.toml: kokoro, soundfile, pymupdf, trafilatura, tqdm, pydub
- [x] Pin CPU-only torch (via [[tool.uv.index]] pytorch-cpu source override)
- [x] Run `uv lock` — 108 packages resolved (CPython 3.11.14)
- [x] Create directory structure: src/, player/, input/, output/
- [x] Create setup.bat
- [x] Run `uv sync` — 106 packages installed, torch 2.10.0+cpu, CUDA=False ✓

## Phase 2: Text Extraction (`src/extract.py`)
- [x] PDF extraction with pymupdf: read pages, clean text, handle line breaks
- [x] URL extraction with trafilatura: fetch and extract body text
- [x] Auto-detect input type (file vs URL)
- [x] Output cleaned text to input/ directory
- [ ] Test with a sample PDF and a sample URL

## Phase 3: Audio Generation (`src/generate.py`)
- [x] Load Kokoro KPipeline
- [x] Read input text, split into sentences
- [x] Generate audio sentence by sentence with progress bar (tqdm)
- [x] Track timestamps per sentence
- [x] Concatenate audio → .mp3 output (soundfile → WAV → pydub → MP3)
- [x] Write timestamps.json alongside
- [x] Resume support (skip completed segments)
- [x] CLI args: --voice, --speed, --output-dir
- [ ] Test with a short text passage

## Phase 4: HTML Player (`player/player.html`)
- [x] Basic layout: text panel + audio controls
- [x] File picker for audio + timestamps JSON (dual card UI)
- [x] Play/pause, speed control (0.5×–2×)
- [x] Sentence highlighting synced via timeupdate + binary search
- [x] Click-to-seek on any sentence
- [x] Auto-scroll to keep active sentence visible
- [x] Keyboard shortcuts (Space = toggle, ← → = skip sentence)
- [x] Dark/light mode toggle (respects system preference)
- [x] Progress bar with click-to-seek
- [ ] Test end-to-end

## Phase 5: Polish & Documentation
- [x] setup.bat: uv install, espeak-ng check, model pre-download
- [x] README.md with clear usage instructions
- [x] End-to-end test: input/kokoro.txt → output/kokoro.wav (9.3MB, 3m21s, 32 sentences)
- [ ] Test portability: does the folder work from a clean state?

## Bugs Fixed
- Removed pydub/ffmpeg dependency: generate.py now writes WAV directly via soundfile (browsers support WAV natively)
- Fixed resume logic: previously would silently produce mismatched audio if WAV was missing but timestamps existed; now sanity-checks WAV duration against timestamps before trusting resume state
- Added pip to dependencies: kokoro downloads en_core_web_sm via pip at first run

## Known Issues / Warnings (harmless)
- torch FutureWarning about weight_norm — upstream issue in kokoro/torch, no impact
- HuggingFace symlinks warning — Windows needs Developer Mode for symlinks; cache still works, just uses more disk
- "Defaulting repo_id to hexgrad/Kokoro-82M" — suppress with `repo_id='hexgrad/Kokoro-82M'` in KPipeline call (minor)

---

## Decisions Log

### Phase 1 (2026-02-26)
- Using `uv` installed to `~/.local/bin` (no global Python needed)
- Python 3.11 pinned in pyproject.toml
- torch CPU-only: using `--index-url https://download.pytorch.org/whl/cpu` via tool override
- kokoro package: `kokoro` on PyPI requires torch + espeak-ng system dep
- soundfile for reading WAV arrays; pydub + ffmpeg for MP3 output
  - Alternative: use scipy.io.wavfile (no extra dep) but pydub gives MP3 easily
  - Decision: use pydub with ffmpeg for MP3 concatenation; soundfile for reading
- tqdm for progress bars
- pymupdf (PyMuPDF) for PDF — package name is `pymupdf`, import as `fitz`
- trafilatura for URL extraction

## Open Questions

- Does `kokoro` PyPipeline output numpy arrays directly? Yes — KPipeline yields (gs, ps, audio) tuples where audio is numpy float32.
- ffmpeg: must be installed separately or bundled. Will note in setup.bat and README.
  - Alternative: use `pydub` with ffmpeg, or use `soundfile` + `numpy` to write WAV then convert via ffmpeg subprocess
  - Decision: write WAV with soundfile/scipy, then use pydub to convert to MP3 (pydub needs ffmpeg in PATH)

## Known Issues
<!-- Track bugs or limitations discovered during development -->
