# Kokoro Audiobook Pipeline

Convert PDFs and web articles into audio files with a synchronized text-highlighting player.
Supports Bilibili articles, general web pages, and PDFs.
Runs entirely on Windows — no internet required after setup, no GPU needed, no Docker.

---

## Requirements

Only one thing needs manual installation before running setup:

**espeak-ng** — the phoneme engine Kokoro TTS depends on.

1. Download the Windows installer from:
   `https://github.com/espeak-ng/espeak-ng/releases`
   Pick the file named `espeak-ng-XXXXXXXXX-x64.msi`.
2. Run it. It adds `espeak-ng` to your PATH automatically.
3. Open a **new** terminal after installation.

Everything else (Python, all packages, model weights) is handled by `setup.bat`.

---

## First-Time Setup

Run once after installing espeak-ng:

```bat
setup.bat
```

This will:
- Install `uv` (Python toolchain manager) if not already present
- Install Python 3.11 and all dependencies into a local `.venv/` (~1.5 GB)
- Pre-download the Kokoro-82M model weights (~330 MB, cached for offline use)

After setup completes you do not need internet access again.

---

## Usage

### GUI launcher — no terminal needed (recommended)

**Double-click `launch.bat`** to open the launcher window.

- Paste a URL, or click **Browse…** to pick a PDF or text file
- If your clipboard already contains a URL, it is pre-filled automatically
- Choose voice and speed, then click **Generate Audiobook**
- The browser opens with audio playing as soon as generation finishes

No terminal, no commands, no file-picking in the player.

---

### Command-line pipeline

`run.py` handles extraction + generation + opening the player in one step:

```bat
:: From a web URL (general)
uv run python src\run.py "https://en.wikipedia.org/wiki/Audiobook"

:: From a Bilibili article or short link
uv run python src\run.py "https://www.bilibili.com/read/cv12345678"
uv run python src\run.py "https://b23.tv/xxxxx"

:: From a PDF
uv run python src\run.py input\mybook.pdf

:: From an already-extracted text file
uv run python src\run.py input\mybook.txt
```

The output files land in `output\`. A per-book player (`output\mybook_player.html`) is
also generated and opens automatically — audio and text are pre-loaded, playback starts
immediately with no file-picking.

Pass `--no-open` to suppress the browser auto-open.

### Supported URL sources

| Source | How it works |
|---|---|
| **Bilibili articles** (`bilibili.com/read/cv*`, `b23.tv/*`) | Uses the Bilibili API directly — bypasses CAPTCHA |
| **General web pages** | Uses trafilatura for article body extraction |

Bilibili short links (`b23.tv/xxxxx`) are automatically resolved to their
destination. Currently only Bilibili *article* pages (`/read/cv*`) are
supported — video pages are not.

### Options

```bat
:: Choose a different voice
uv run python src\run.py input\mybook.txt --voice af_bella

:: Chinese voice (auto-detected from text, or force with --lang)
uv run python src\run.py input\chinese.txt --voice zf_xiaoni
uv run python src\run.py input\chinese.txt --lang z

:: Adjust speech speed (0.5–2.0, default 1.0)
uv run python src\run.py input\mybook.txt --speed 1.2

:: Custom output directory
uv run python src\run.py input\mybook.txt --output-dir D:\audiobooks

:: Combined
uv run python src\run.py input\mybook.txt --voice af_bella --speed 1.1 --no-open
```

**Available voices:**

| Language | Female | Male |
|---|---|---|
| American English | `af_heart` (default), `af_bella`, `af_nicole`, `af_sky` | `am_adam`, `am_michael` |
| British English | `bf_emma`, `bf_isabella` | `bm_george`, `bm_lewis` |
| Mandarin Chinese | `zf_xiaobei`, `zf_xiaoni`, `zf_xiaoxiao`, `zf_xiaoyi` | `zm_yunjian`, `zm_yunxi`, `zm_yunxia`, `zm_yunyang` |

See the [Kokoro model card](https://huggingface.co/hexgrad/Kokoro-82M) for the full list.

**Language auto-detection:** The pipeline detects whether the input text is Chinese
or English and picks the matching voice automatically. If you select an English voice
but the text is Chinese, the pipeline switches to `zf_xiaoni` and prints a notice.
You can also force a language with `--lang z` (Chinese) or `--lang a` (English).

---

## Using the Player

After `run.py` finishes, a per-book player (`output\mybook_player.html`) opens in your
browser with audio and text already loaded — no clicking required.

You can also reopen it any time by double-clicking `output\mybook_player.html`.

**If using the generic `player\player.html` directly:**

- **Drag and drop** both `output\yourbook.wav` and `output\yourbook_timestamps.json`
  onto the player window at once — playback starts automatically.
- Or click the **Audio File** card to pick the `.wav`, then the **Timestamps JSON**
  card to pick the `_timestamps.json`, then press **Start Playing**.

**Controls:**

| Action | How |
|---|---|
| Play / Pause | `Space` or the ▶ button |
| Previous sentence | `←` arrow key or `◀◀` button |
| Next sentence | `→` arrow key or `▶▶` button |
| Jump to any sentence | Click on the sentence text |
| Seek anywhere | Click the progress bar |
| Change speed | Speed dropdown (0.5× – 2×) |
| Dark / light mode | Theme button (top right) |
| Load new files | Load button (top right) |

The player works as a local file — no web server, no internet needed.

---

## Standalone Commands

`extract.py` and `generate.py` can be used independently if needed:

```bat
:: Extract text from a PDF → input\mybook.txt
uv run python src\extract.py input\mybook.pdf

:: Extract text from a URL → input\extracted.txt
uv run python src\extract.py "https://example.com/article"

:: Generate audio from text → output\mybook.wav + output\mybook_timestamps.json
uv run python src\generate.py input\mybook.txt

:: Generate with options
uv run python src\generate.py input\mybook.txt --voice af_bella --speed 1.1
uv run python src\generate.py input\mybook.txt --output-dir D:\audiobooks
```

---

## Project Structure

```
kokoro-audiobook\
├── launch.bat              ← Double-click to open the GUI launcher
├── setup.bat               ← Run once on a new machine
├── README.md               ← This file
├── pyproject.toml          ← Python dependencies (managed by uv)
├── uv.lock                 ← Pinned dependency versions (do not edit)
├── src\
│   ├── launcher.py         ← GUI launcher (opened by launch.bat)
│   ├── run.py              ← Command-line pipeline entry point
│   ├── extract.py          ← PDF / URL → clean text (dispatches to site extractors)
│   ├── bilibili.py         ← Bilibili article extractor (API-based)
│   ├── generate.py         ← Text → audio + timestamps JSON
│   └── utils.py            ← Shared helpers
├── player\
│   └── player.html         ← Generic player (drag-and-drop loading)
├── input\                  ← Drop PDFs or text files here
└── output\                 ← Generated files land here
    ├── mybook.wav              ← Audio
    ├── mybook_timestamps.json  ← Sync data
    └── mybook_player.html      ← Auto-generated per-book player
```

---

## Portability — Moving to Another Machine

The `.venv\` folder contains compiled binaries tied to the current machine and
**cannot** be copied. On the new machine:

1. Copy the entire project folder (excluding `.venv\` to save space).
2. Install **espeak-ng** (see Requirements above).
3. Run `setup.bat` — it reinstalls the environment from `uv.lock` in a few minutes.

`uv.lock` pins every dependency to the exact version used on the original machine,
so the rebuild is fully reproducible.

If you want a fully offline transfer (no internet on the new machine):
- Copy including `.venv\` (adds ~1.5 GB)
- Copy the HuggingFace model cache: `%USERPROFILE%\.cache\huggingface\hub\`
- On the new machine, run `uv sync` (fast, skips downloads) and set
  `TRANSFORMERS_OFFLINE=1` if needed.

---

## Troubleshooting

**"espeak-ng not found" or audio generation fails immediately**
Install espeak-ng from the link in Requirements, then open a **new** terminal.
The current terminal won't see the PATH change until restarted.

**setup.bat fails at "uv sync"**
Common causes: no internet, disk space under 2 GB, or antivirus blocking `.venv\`
creation. Check the error text for details.

**Model download fails during setup**
Make sure espeak-ng is installed first (Kokoro tries to call it during initialization).
Re-run `setup.bat` after installing espeak-ng.

**HuggingFace symlink warning on Windows**
Harmless. Windows requires Developer Mode for symlinks; the model cache still works,
it just uses copies instead. Enable Developer Mode in Windows Settings → For Developers
to suppress it.

**"Unsupported Bilibili URL format" or "Could not extract readable text"**
Currently only Bilibili article pages (`/read/cv*`) are supported via the API.
Video pages, dynamic posts, and other Bilibili content types are not yet handled.
For non-Bilibili sites that fail, the page may use JavaScript rendering or
anti-bot protection that trafilatura cannot bypass.

**Generation is slow**
CPU inference is ~10–30× real-time. A 300-page book may take 30–90 minutes.
The pipeline saves progress every 10 sentences — you can Ctrl+C and resume later
by re-running the same command.

**Resuming a generation**
Run the exact same command again. If `output\yourbook.wav` and
`output\yourbook_timestamps.json` both exist and their durations match, generation
picks up where it left off.

**Audio quality issues**
Kokoro sounds best at `--speed 0.9` to `1.2`. Very low or high speeds can
introduce artifacts.
