"""launcher.py — No-CLI GUI launcher for the Kokoro audiobook pipeline.

Open via launch.bat (double-click) — no terminal needed.
Paste a URL or browse for a PDF/TXT, choose voice and speed, click Generate.
The browser opens with audio playing as soon as generation finishes.
"""

import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk
from urllib.parse import urlparse

# Ensure sibling modules in src/ are importable
sys.path.insert(0, str(Path(__file__).parent))

VOICES = [
    "af_heart", "af_bella", "af_nicole", "af_sky",
    "am_adam", "am_michael",
    "bf_emma", "bf_isabella", "bm_george", "bm_lewis",
]
SPEEDS = ["0.75", "0.9", "1.0", "1.1", "1.2", "1.5", "2.0"]
PROJECT_ROOT = Path(__file__).parent.parent


class _QueueStream:
    """Forwards sys.stderr writes to a queue so the GUI can display them."""

    def __init__(self, q: "queue.Queue[str | None]") -> None:
        self._q = q

    def write(self, text: str) -> None:
        # Strip carriage returns used by tqdm to overwrite lines
        text = text.replace("\r", "").strip()
        if text:
            self._q.put(text)

    def flush(self) -> None:
        pass


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Kokoro Audiobook")
        self.root.resizable(False, False)
        self._build_ui()
        self._prefill_clipboard()

    # ── UI construction ───────────────────────────────────────────────

    def _build_ui(self) -> None:
        f = tk.Frame(self.root, padx=16, pady=12)
        f.pack(fill="both", expand=True)

        # Title
        tk.Label(f, text="Kokoro Audiobook", font=("Segoe UI", 13, "bold")).grid(
            row=0, column=0, columnspan=3, pady=(0, 10), sticky="w"
        )

        # Input row
        tk.Label(f, text="URL or file:").grid(row=1, column=0, sticky="w", pady=(0, 2))
        self.input_var = tk.StringVar()
        self._input = tk.Entry(f, textvariable=self.input_var, width=46)
        self._input.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        self._browse_btn = tk.Button(f, text="Browse…", command=self._browse)
        self._browse_btn.grid(row=2, column=2, padx=(6, 0), pady=(0, 8))

        # Voice + Speed row
        opt = tk.Frame(f)
        opt.grid(row=3, column=0, columnspan=3, sticky="w", pady=(0, 10))
        tk.Label(opt, text="Voice:").pack(side="left")
        self.voice_var = tk.StringVar(value="af_heart")
        self._voice_cb = ttk.Combobox(
            opt, textvariable=self.voice_var, values=VOICES, width=13, state="readonly"
        )
        self._voice_cb.pack(side="left", padx=(4, 14))
        tk.Label(opt, text="Speed:").pack(side="left")
        self.speed_var = tk.StringVar(value="1.0")
        self._speed_cb = ttk.Combobox(
            opt, textvariable=self.speed_var, values=SPEEDS, width=5
        )
        self._speed_cb.pack(side="left", padx=(4, 0))

        # Generate button
        self._gen_btn = tk.Button(
            f, text="Generate Audiobook", command=self._start,
            bg="#4a6fa5", fg="white", activebackground="#3a5f95",
            font=("Segoe UI", 10, "bold"), padx=16, pady=7, relief="flat",
        )
        self._gen_btn.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(0, 8))

        # Progress bar (indeterminate spinner while generating)
        self._pb = ttk.Progressbar(f, mode="indeterminate", length=1)
        self._pb.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(0, 6))

        # Status label
        self.status_var = tk.StringVar(value="Ready.")
        tk.Label(
            f, textvariable=self.status_var, anchor="w",
            wraplength=390, fg="#555", font=("Segoe UI", 9),
        ).grid(row=6, column=0, columnspan=3, sticky="w")

        f.columnconfigure(0, weight=1)

    # ── Helpers ───────────────────────────────────────────────────────

    def _prefill_clipboard(self) -> None:
        """Pre-fill the input field if the clipboard contains a URL."""
        try:
            clip = self.root.clipboard_get().strip()
            if clip.startswith(("http://", "https://")):
                self.input_var.set(clip)
        except tk.TclError:
            pass

    def _browse(self) -> None:
        path = filedialog.askopenfilename(
            title="Select a PDF or text file",
            filetypes=[
                ("Supported files", "*.pdf *.txt"),
                ("PDF files", "*.pdf"),
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.input_var.set(path)

    def _set_busy(self, busy: bool) -> None:
        """Disable/enable all interactive controls and toggle the progress bar."""
        self._gen_btn.config(state="disabled" if busy else "normal")
        self._input.config(state="disabled" if busy else "normal")
        self._browse_btn.config(state="disabled" if busy else "normal")
        self._voice_cb.config(state="disabled" if busy else "readonly")
        self._speed_cb.config(state="disabled" if busy else "normal")
        if busy:
            self._pb.start(10)
        else:
            self._pb.stop()

    # ── Generation ────────────────────────────────────────────────────

    def _start(self) -> None:
        source = self.input_var.get().strip()
        if not source:
            self.status_var.set("Enter a URL or browse for a PDF / .txt file.")
            return
        try:
            speed = float(self.speed_var.get())
        except ValueError:
            self.status_var.set("Speed must be a number (e.g. 1.0).")
            return

        self._set_busy(True)
        self.status_var.set("Starting…")
        q: "queue.Queue[str | None]" = queue.Queue()
        threading.Thread(
            target=self._run, args=(source, self.voice_var.get(), speed, q), daemon=True
        ).start()
        self.root.after(100, self._poll, q)

    def _run(
        self, source: str, voice: str, speed: float, q: "queue.Queue[str | None]"
    ) -> None:
        """Pipeline — runs in a background thread. Never touches tkinter directly."""
        # Late imports: keeps GUI startup fast; packages only load when Generate is clicked
        from extract import extract_pdf, extract_url, is_url
        from generate import generate_audio
        from run import generate_player_html
        from utils import slugify, split_sentences
        import webbrowser

        old_stderr = sys.stderr
        sys.stderr = _QueueStream(q)
        try:
            output_dir = PROJECT_ROOT / "output"
            output_dir.mkdir(exist_ok=True)
            input_dir = PROJECT_ROOT / "input"
            input_dir.mkdir(exist_ok=True)

            # Dispatch: URL / PDF / TXT
            if is_url(source):
                text, title = extract_url(source)
                stem = (
                    slugify(title)
                    if title
                    else "extracted_" + urlparse(source).netloc.replace(".", "-")
                )
                (input_dir / f"{stem}.txt").write_text(text, encoding="utf-8")
            elif source.lower().endswith(".pdf"):
                text = extract_pdf(Path(source))
                stem = Path(source).stem
                (input_dir / f"{stem}.txt").write_text(text, encoding="utf-8")
            elif source.lower().endswith(".txt"):
                text = Path(source).read_text(encoding="utf-8")
                stem = Path(source).stem
            else:
                q.put("ERROR: Use a URL, a .pdf file, or a .txt file.")
                return

            sentences = split_sentences(text)
            if not sentences:
                q.put("ERROR: No readable sentences found in the input.")
                return

            wav_path, ts_path = generate_audio(sentences, voice, speed, output_dir / stem)

            generated = generate_player_html(
                wav_path, ts_path, PROJECT_ROOT / "player" / "player.html"
            )
            webbrowser.open(generated.as_uri())
            q.put("DONE")

        except SystemExit:
            pass  # sys.exit() inside the pipeline means the error was already queued
        except Exception as exc:
            q.put(f"ERROR: {exc}")
        finally:
            sys.stderr = old_stderr
            q.put(None)  # sentinel: signals _poll that the thread has finished

    def _poll(self, q: "queue.Queue[str | None]") -> None:
        """Drain status messages from the queue and update the label (main thread)."""
        done = False
        try:
            while True:
                msg = q.get_nowait()
                if msg is None:          # sentinel — thread finished normally
                    done = True
                    break
                elif msg == "DONE":
                    self.status_var.set("Done!  Player opened in browser.")
                elif msg.startswith("ERROR:"):
                    self.status_var.set(msg)
                    done = True
                    break
                else:
                    self.status_var.set(msg)   # show latest pipeline status line
        except queue.Empty:
            pass

        if done:
            self._set_busy(False)
            if "DONE" in self.status_var.get():
                self.status_var.set("Done!  Player opened in browser.")
        else:
            self.root.after(100, self._poll, q)


def main() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
