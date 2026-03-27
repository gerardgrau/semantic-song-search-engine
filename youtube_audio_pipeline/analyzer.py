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


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _compute_frame_statistics(audio, sample_rate: int = 44100) -> tuple[float, float]:
    windowing = es.Windowing(type="hann")
    spectrum = es.Spectrum()
    centroid_algo = es.Centroid(range=sample_rate / 2)
    zcr_algo = es.ZeroCrossingRate()

    centroid_values: list[float] = []
    zcr_values: list[float] = []

    for frame in es.FrameGenerator(audio, frameSize=2048, hopSize=1024, startFromZero=True):
        windowed = windowing(frame)
        spec = spectrum(windowed)
        centroid_values.append(float(centroid_algo(spec)))
        zcr_values.append(float(zcr_algo(frame)))

    if not centroid_values:
        return 0.0, 0.0

    spectral_centroid_hz = sum(centroid_values) / len(centroid_values)
    zero_crossing_rate = sum(zcr_values) / len(zcr_values)
    return spectral_centroid_hz, zero_crossing_rate


def analyze_and_discard(filepath: str | None, url: str, title: str | None) -> dict[str, object] | None:
    if not filepath or not os.path.exists(filepath):
        return None

    safe_title = title or "Unknown Title"
    analysis_filepath = filepath
    generated_temp = False

    try:
        analysis_filepath, generated_temp = _prepare_analysis_file(filepath)
        sample_rate = 44100
        audio = es.MonoLoader(filename=analysis_filepath, sampleRate=sample_rate)()
        duration_seconds = float(len(audio)) / sample_rate

        rhythm_extractor = es.RhythmExtractor2013(method="multifeature")
        bpm, _, confidence, _, _ = rhythm_extractor(audio)

        key_extractor = es.KeyExtractor()
        key, scale, _ = key_extractor(audio)

        loudness_algo = es.DynamicComplexity()
        _, overall_loudness = loudness_algo(audio)

        rms_algo = es.RMS()
        rms_energy = float(rms_algo(audio))

        spectral_centroid_hz, zero_crossing_rate = _compute_frame_statistics(audio, sample_rate=sample_rate)

        bpm_norm = _clamp((float(bpm) - 70.0) / 90.0)
        confidence_norm = _clamp(float(confidence))
        danceability_proxy = _clamp(0.55 * bpm_norm + 0.45 * confidence_norm)

        major_flag = 1.0 if str(scale).lower() == "major" else 0.35
        centroid_norm = _clamp(spectral_centroid_hz / 4000.0)
        loudness_norm = _clamp((float(overall_loudness) + 45.0) / 45.0)
        valence_proxy = _clamp(0.45 * major_flag + 0.35 * centroid_norm + 0.2 * loudness_norm)

        return {
            "URL": url,
            "Title": safe_title,
            "BPM": round(float(bpm), 1),
            "Key": f"{key} {scale}",
            "Loudness": round(float(overall_loudness), 2),
            "DurationSeconds": round(duration_seconds, 2),
            "RmsEnergy": round(rms_energy, 6),
            "Danceability": round(danceability_proxy, 4),
            "Valence": round(valence_proxy, 4),
            "SpectralCentroidHz": round(spectral_centroid_hz, 2),
            "ZeroCrossingRate": round(zero_crossing_rate, 6),
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
