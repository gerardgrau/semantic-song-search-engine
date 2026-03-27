from __future__ import annotations

import json
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


def _safe_mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(sum(values)) / len(values)


def _safe_std(values: list[float], mean_value: float) -> float:
    if not values:
        return 0.0
    variance = sum((value - mean_value) ** 2 for value in values) / len(values)
    return float(variance ** 0.5)


def _vector_mean(vectors: list[list[float]], size: int) -> list[float]:
    if not vectors:
        return [0.0] * size

    totals = [0.0] * size
    for vector in vectors:
        for idx, value in enumerate(vector[:size]):
            totals[idx] += float(value)

    count = float(len(vectors))
    return [total / count for total in totals]


def _vector_std(vectors: list[list[float]], mean_vector: list[float], size: int) -> list[float]:
    if not vectors:
        return [0.0] * size

    totals = [0.0] * size
    for vector in vectors:
        for idx, value in enumerate(vector[:size]):
            delta = float(value) - mean_vector[idx]
            totals[idx] += delta * delta

    count = float(len(vectors))
    return [(total / count) ** 0.5 for total in totals]


def _round_vector(vector: list[float], decimals: int = 6) -> list[float]:
    return [round(float(value), decimals) for value in vector]


def _compute_frame_statistics(audio, sample_rate: int = 44100) -> dict[str, object]:
    windowing = es.Windowing(type="hann")
    spectrum = es.Spectrum()
    centroid_algo = es.Centroid(range=sample_rate / 2)
    zcr_algo = es.ZeroCrossingRate()
    rolloff_algo = es.RollOff()
    flatness_algo = es.FlatnessDB()
    mfcc_algo = es.MFCC(numberCoefficients=13)
    spectral_peaks_algo = es.SpectralPeaks()
    hpcp_algo = es.HPCP(size=12)
    pitch_algo = es.PitchYinFFT()

    centroid_values: list[float] = []
    zcr_values: list[float] = []
    rolloff_values: list[float] = []
    flatness_values: list[float] = []
    pitch_values: list[float] = []
    mfcc_vectors: list[list[float]] = []
    hpcp_vectors: list[list[float]] = []

    for frame in es.FrameGenerator(audio, frameSize=2048, hopSize=1024, startFromZero=True):
        windowed = windowing(frame)
        spec = spectrum(windowed)
        centroid_values.append(float(centroid_algo(spec)))
        zcr_values.append(float(zcr_algo(frame)))
        rolloff_values.append(float(rolloff_algo(spec)))
        flatness_values.append(float(flatness_algo(spec)))

        _, mfcc_coeffs = mfcc_algo(spec)
        mfcc_vectors.append([float(value) for value in mfcc_coeffs])

        peak_frequencies, peak_magnitudes = spectral_peaks_algo(spec)
        if len(peak_frequencies) > 0:
            hpcp_values = hpcp_algo(peak_frequencies, peak_magnitudes)
            hpcp_vectors.append([float(value) for value in hpcp_values])

        pitch_hz, pitch_confidence = pitch_algo(spec)
        if float(pitch_hz) > 0 and float(pitch_confidence) >= 0.1:
            pitch_values.append(float(pitch_hz))

    if not centroid_values:
        return {
            "spectral_centroid_hz": 0.0,
            "zero_crossing_rate": 0.0,
            "spectral_rolloff_hz": 0.0,
            "spectral_flatness": 0.0,
            "pitch_mean_hz": 0.0,
            "pitch_std_hz": 0.0,
            "mfcc_mean": [0.0] * 13,
            "mfcc_std": [0.0] * 13,
            "hpcp_mean": [0.0] * 12,
        }

    mfcc_mean = _vector_mean(mfcc_vectors, size=13)
    mfcc_std = _vector_std(mfcc_vectors, mean_vector=mfcc_mean, size=13)
    hpcp_mean = _vector_mean(hpcp_vectors, size=12)

    pitch_mean_hz = _safe_mean(pitch_values)
    pitch_std_hz = _safe_std(pitch_values, pitch_mean_hz)

    return {
        "spectral_centroid_hz": _safe_mean(centroid_values),
        "zero_crossing_rate": _safe_mean(zcr_values),
        "spectral_rolloff_hz": _safe_mean(rolloff_values),
        "spectral_flatness": _safe_mean(flatness_values),
        "pitch_mean_hz": pitch_mean_hz,
        "pitch_std_hz": pitch_std_hz,
        "mfcc_mean": _round_vector(mfcc_mean),
        "mfcc_std": _round_vector(mfcc_std),
        "hpcp_mean": _round_vector(hpcp_mean),
    }


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
        bpm, ticks, confidence, _, _ = rhythm_extractor(audio)

        key_extractor = es.KeyExtractor()
        key, scale, key_strength = key_extractor(audio)

        loudness_algo = es.DynamicComplexity()
        _, overall_loudness = loudness_algo(audio)

        rms_algo = es.RMS()
        rms_energy = float(rms_algo(audio))

        frame_stats = _compute_frame_statistics(audio, sample_rate=sample_rate)
        spectral_centroid_hz = float(frame_stats["spectral_centroid_hz"])
        zero_crossing_rate = float(frame_stats["zero_crossing_rate"])

        onset_rate_algo = es.OnsetRate()
        onset_times, onset_rate = onset_rate_algo(audio)
        beat_confidence = _clamp(float(confidence))

        bpm_norm = _clamp((float(bpm) - 70.0) / 90.0)
        confidence_norm = beat_confidence
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
            "KeyStrength": round(float(key_strength), 4),
            "Loudness": round(float(overall_loudness), 2),
            "DurationSeconds": round(duration_seconds, 2),
            "RmsEnergy": round(rms_energy, 6),
            "BeatConfidence": round(beat_confidence, 4),
            "BeatCount": int(len(ticks)),
            "OnsetRate": round(float(onset_rate), 6),
            "OnsetCount": int(len(onset_times)),
            "Danceability": round(danceability_proxy, 4),
            "Valence": round(valence_proxy, 4),
            "SpectralCentroidHz": round(spectral_centroid_hz, 2),
            "SpectralRolloffHz": round(float(frame_stats["spectral_rolloff_hz"]), 2),
            "SpectralFlatness": round(float(frame_stats["spectral_flatness"]), 6),
            "PitchMeanHz": round(float(frame_stats["pitch_mean_hz"]), 2),
            "PitchStdHz": round(float(frame_stats["pitch_std_hz"]), 2),
            "ZeroCrossingRate": round(zero_crossing_rate, 6),
            "MfccMeanJson": json.dumps(frame_stats["mfcc_mean"]),
            "MfccStdJson": json.dumps(frame_stats["mfcc_std"]),
            "HpcpMeanJson": json.dumps(frame_stats["hpcp_mean"]),
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
