# Kokoro Audiobook Pipeline

Convert PDFs and web articles into audio files with a synchronized HTML player.
Runs locally on Windows — no internet required after setup, no GPU needed.

## Quick Start

1. **Install espeak-ng** (required for TTS):
   - Download the Windows `.msi` installer from
     https://github.com/espeak-ng/espeak-ng/releases
   - Run it. It adds `espeak-ng` to your PATH automatically.

2. **Run setup:**
   ```bat
   setup.bat
   ```
   This installs `uv`, Python 3.11, all Python dependencies, and pre-downloads
   the Kokoro model weights (~330 MB). Only needed once.

3. **Extract text from a PDF:**
   ```bat
   uv run python src/extract.py input/mybook.pdf
   ```
   Output: `input/mybook.txt`

4. **Or extract from a web URL:**
   ```bat
   uv run python src/extract.py "https://example.com/article"
   ```
   Output: `input/extracted.txt`

5. **Generate the audiobook:**
   ```bat
   uv run python src/generate.py input/mybook.txt
   ```
   Output: `output/mybook.mp3` + `output/mybook_timestamps.json`

6. **Open the player:**
   Double-click `player/player.html` in your browser.
   Click the audio card → select `output/mybook.mp3`
   Click the JSON card → select `output/mybook_timestamps.json`
   Press **Start Playing**.

## Player Controls

| Action | How |
|---|---|
| Play / Pause | `Space` or the ▶ button |
| Previous sentence | `←` or `◀◀` button |
| Next sentence | `→` or `▶▶` button |
| Seek anywhere | Click the progress bar |
| Jump to sentence | Click on any text |
| Change speed | Speed dropdown (0.5× – 2×) |
| Dark/light mode | Theme button |

## Advanced Usage

```bat
:: Use a different voice
uv run python src/generate.py input/mybook.txt --voice af_bella

:: Set speech speed
uv run python src/generate.py input/mybook.txt --speed 1.2

:: Custom output directory
uv run python src/generate.py input/mybook.txt --output-dir D:\audiobooks\

:: Combine options
uv run python src/generate.py input/mybook.txt --voice af_bella --speed 1.1 --output-dir output\bella\
```

Available voices include: `af_heart` (default), `af_bella`, `af_nicole`, `am_adam`,
`am_michael`, `bf_emma`, `bm_george`, and others. See the
[Kokoro model card](https://huggingface.co/hexgrad/Kokoro-82M) for the full list.

## Requirements

- Windows 10/11 (x64)
- `espeak-ng` installed (see Step 1)
- `ffmpeg` in PATH — needed for MP3 output
  - Download from https://www.gyan.dev/ffmpeg/builds/
  - Add the `bin/` folder to your system PATH
- Internet connection for first-time setup only

## Project Structure

```
kokoro-audiobook/
├── setup.bat           ← First-time setup
├── src/
│   ├── extract.py      ← PDF/URL → clean text
│   ├── generate.py     ← text → audio + timestamps
│   └── utils.py        ← shared helpers
├── player/
│   └── player.html     ← Self-contained audiobook player
├── input/              ← Drop PDFs and text files here
└── output/             ← Generated MP3 and JSON land here
```

## Portability

The entire folder is self-contained. To move it to another machine:
1. Copy the whole folder (including `.venv/` if you want offline transfer)
2. Install `espeak-ng` and `ffmpeg` on the new machine
3. Run `setup.bat` (or just `uv sync` if uv is already installed)

## Troubleshooting

**"espeak-ng not found"** — Install it from the link above and restart your terminal.

**"ffmpeg not found" / MP3 conversion fails** — Install ffmpeg and add its `bin/`
to your PATH. Alternatively, if you only need WAV output, modify `generate.py` to
skip the pydub conversion and save WAV directly with soundfile.

**Audio quality / speed issues** — Try adjusting `--speed`. Kokoro works best in
the 0.8–1.3× range for natural-sounding speech.

**Long books are slow** — CPU inference is ~10–30× real-time depending on your CPU.
A 300-page book may take 30–90 minutes to generate. The pipeline saves progress
every 10 sentences, so you can interrupt and resume.
