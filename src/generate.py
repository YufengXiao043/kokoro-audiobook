"""generate.py — Convert clean text to audiobook (WAV + timestamps JSON).

Usage:
    uv run python src/generate.py input/mybook.txt
    uv run python src/generate.py input/mybook.txt --voice af_bella --speed 1.1
    uv run python src/generate.py input/mybook.txt --output-dir output/custom/

Output: output/<stem>.wav + output/<stem>_timestamps.json
Load both files in player/player.html to listen with synchronized highlighting.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from tqdm import tqdm

from utils import split_sentences, make_output_stem

SAMPLE_RATE = 24000  # Kokoro outputs at 24 kHz


def load_pipeline(voice: str, speed: float):
    """Load and return a Kokoro KPipeline instance."""
    try:
        from kokoro import KPipeline
    except ImportError:
        print("Error: kokoro not installed. Run: uv sync", file=sys.stderr)
        sys.exit(1)

    print(f"Loading Kokoro pipeline (voice={voice}, speed={speed})...", file=sys.stderr)
    pipeline = KPipeline(lang_code="a")  # 'a' = American English
    return pipeline


def generate_audio(
    sentences: list[str],
    voice: str,
    speed: float,
    output_stem: Path,
) -> tuple[Path, Path]:
    """Generate audio for each sentence, concatenate to WAV, write timestamps JSON.

    Returns (wav_path, timestamps_path).
    """
    wav_path = output_stem.with_suffix(".wav")
    timestamps_path = output_stem.parent / (output_stem.name + "_timestamps.json")

    # Resume support: load existing timestamps + WAV if both are present and consistent
    timestamps: list[dict] = []
    completed_count = 0
    audio_chunks: list[np.ndarray] = []

    if timestamps_path.exists() and wav_path.exists() and wav_path.stat().st_size > 0:
        try:
            existing = json.loads(timestamps_path.read_text(encoding="utf-8"))
            existing_array, _ = sf.read(str(wav_path), dtype="float32")
            if existing_array.ndim > 1:
                existing_array = existing_array.mean(axis=1)

            if isinstance(existing, list) and existing:
                # Sanity check: WAV duration should roughly match last timestamp end
                wav_duration = len(existing_array) / SAMPLE_RATE
                expected_duration = existing[-1]["end"]
                if abs(wav_duration - expected_duration) < 2.0:  # allow 2s drift
                    timestamps = existing
                    completed_count = len(timestamps)
                    audio_chunks.append(existing_array)
                    print(
                        f"Resuming: {completed_count}/{len(sentences)} sentences done "
                        f"({wav_duration:.1f}s of audio loaded).",
                        file=sys.stderr,
                    )
                else:
                    print(
                        f"Warning: WAV duration ({wav_duration:.1f}s) doesn't match "
                        f"timestamps ({expected_duration:.1f}s). Restarting.",
                        file=sys.stderr,
                    )
        except Exception as e:
            print(f"Warning: Could not load existing files for resume: {e}. Restarting.", file=sys.stderr)

    pipeline = load_pipeline(voice, speed)

    remaining = sentences[completed_count:]
    current_time = timestamps[-1]["end"] if timestamps else 0.0

    print(f"Generating audio for {len(remaining)} sentences...", file=sys.stderr)

    for sentence in tqdm(remaining, desc="Generating", unit="sentence", file=sys.stderr):
        sentence = sentence.strip()
        if not sentence:
            continue

        # KPipeline yields (graphemes, phonemes, audio_array) tuples per chunk.
        # A single sentence may produce multiple chunks; concatenate them.
        sentence_chunks: list[np.ndarray] = []
        try:
            for _, _, audio in pipeline(sentence, voice=voice, speed=speed):
                if audio is not None and len(audio) > 0:
                    sentence_chunks.append(audio)
        except Exception as e:
            print(f"\nWarning: TTS failed for sentence: {sentence!r}: {e}", file=sys.stderr)
            # Insert 0.3s silence as placeholder
            sentence_chunks.append(np.zeros(int(SAMPLE_RATE * 0.3), dtype=np.float32))

        if not sentence_chunks:
            sentence_chunks.append(np.zeros(int(SAMPLE_RATE * 0.3), dtype=np.float32))

        sentence_audio = np.concatenate(sentence_chunks)
        duration = len(sentence_audio) / SAMPLE_RATE

        timestamps.append({
            "text": sentence,
            "start": round(current_time, 3),
            "end": round(current_time + duration, 3),
        })
        current_time += duration
        audio_chunks.append(sentence_audio)

        # Periodically save timestamps for resume support
        if len(timestamps) % 10 == 0:
            timestamps_path.write_text(
                json.dumps(timestamps, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    # Concatenate all audio and write WAV
    print("Writing audio file...", file=sys.stderr)
    full_audio = np.concatenate(audio_chunks) if audio_chunks else np.zeros(SAMPLE_RATE, dtype=np.float32)

    output_stem.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(wav_path), full_audio, SAMPLE_RATE, subtype="PCM_16")

    # Final timestamps save
    timestamps_path.write_text(
        json.dumps(timestamps, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    total_duration = current_time
    minutes, seconds = divmod(int(total_duration), 60)
    print(
        f"Done! {len(timestamps)} sentences, {minutes}m{seconds}s of audio.",
        file=sys.stderr,
    )
    print(f"  Audio:      {wav_path}", file=sys.stderr)
    print(f"  Timestamps: {timestamps_path}", file=sys.stderr)

    return wav_path, timestamps_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate audiobook WAV + timestamps from a text file."
    )
    parser.add_argument("text_file", help="Path to the input .txt file.")
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
    args = parser.parse_args()

    text_path = Path(args.text_file)
    if not text_path.exists():
        print(f"Error: File not found: {text_path}", file=sys.stderr)
        sys.exit(1)

    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else Path(__file__).parent.parent / "output"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    output_stem = make_output_stem(text_path, output_dir)

    # Read and split text
    print(f"Reading: {text_path}", file=sys.stderr)
    text = text_path.read_text(encoding="utf-8")
    sentences = split_sentences(text)
    print(f"Found {len(sentences)} sentences.", file=sys.stderr)

    if not sentences:
        print("Error: No sentences found in input file.", file=sys.stderr)
        sys.exit(1)

    wav_path, ts_path = generate_audio(sentences, args.voice, args.speed, output_stem)
    # Print output paths to stdout for scripting
    print(str(wav_path))
    print(str(ts_path))


if __name__ == "__main__":
    main()
