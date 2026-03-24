from __future__ import annotations

import os
import subprocess
import uuid
from pathlib import Path

import essentia.standard as es
import pandas as pd


def _prepare_analysis_file(filepath: str) -> tuple[str, bool]:
    source = Path(filepath)
    if source.suffix.lower() == ".wav":
        return str(source), False

    converted = source.with_name(f"{source.stem}.{uuid.uuid4().hex}.analysis.wav")
    cmd = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-i",
        str(source),
        "-ac",
        "1",
        "-ar",
        "44100",
        str(converted),
    ]
    subprocess.run(cmd, check=True)
    return str(converted), True


def analyze_and_discard(filepath: str | None, url: str, title: str | None) -> dict[str, object] | None:
    if not filepath or not os.path.exists(filepath):
        return None

    safe_title = title or "Unknown Title"
    analysis_filepath = filepath
    generated_temp = False

    try:
        analysis_filepath, generated_temp = _prepare_analysis_file(filepath)
        audio = es.MonoLoader(filename=analysis_filepath, sampleRate=44100)()

        rhythm_extractor = es.RhythmExtractor2013(method="multifeature")
        bpm, _, _, _, _ = rhythm_extractor(audio)

        key_extractor = es.KeyExtractor()
        key, scale, _ = key_extractor(audio)

        loudness_algo = es.DynamicComplexity()
        _, overall_loudness = loudness_algo(audio)

        return {
            "URL": url,
            "Title": safe_title,
            "BPM": round(float(bpm), 1),
            "Key": f"{key} {scale}",
            "Loudness": round(float(overall_loudness), 2),
        }
    except Exception as exc:
        print(f"❌ Analysis failed for {safe_title} | Error: {exc}")
        return None
    finally:
        try:
            if generated_temp and analysis_filepath and os.path.exists(analysis_filepath):
                os.remove(analysis_filepath)
            if os.path.exists(filepath):
                os.remove(filepath)
        except OSError:
            pass


def save_to_dataframe(results_list: list[dict[str, object]], output_csv: str = "data/processed/youtube_song_characteristics.csv") -> None:
    if not results_list:
        return

    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(results_list)
    if output_path.exists():
        df.to_csv(output_path, mode="a", header=False, index=False)
    else:
        df.to_csv(output_path, index=False)
