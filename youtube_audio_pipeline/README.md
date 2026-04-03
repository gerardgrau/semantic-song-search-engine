# YouTube Audio Pipeline: Stealth & Accuracy (v2.0)

A resilient, high-fidelity audio processing engine designed to extract 131 musical features and 1280-dim embeddings from YouTube URLs while respecting platform rate limits.

## 🕵️ v2.0 Stealth Architecture

Following YouTube's implementation of stricter rate limits (~300 videos/hour for guest sessions), this module has been refactored from a high-speed "Turbo" engine into a **Precision Stealth Engine**.

### Core Principles:
- **Resiliency Over Speed**: Processes songs linearly (one-by-one) to mimic human behavior and avoid IP bans.
- **Bot Bypass**: Cycles through mobile player identities (`ios`, `android`) to leverage higher guest limits and maximize format availability.
- **Self-Healing**: Automatically detects bot challenges and enters **Hibernate Mode** (5-minute pause) to let rate-limit buckets reset.
- **Persistence**: Tracks progress in `pipeline_state.json` allowing for seamless resumes after interruptions.

## 💎 High-Fidelity Extraction

Because the pipeline is network-throttled, we utilize the "idle" time to perform exhaustive musical analysis:

- **PredominantPitchMelodia**: Full lead-pitch tracking for accurate melodic contours.
- **High-Res Spectral Mapping**: 6x higher temporal resolution than v1.0 (captures features every 0.15s).
- **Precision Resampling**: High-quality source audio is resampled in-memory by Essentia's C++ core for maximum classification accuracy.

## 📦 Extracted Features

The pipeline produces a wide CSV with 131 columns, including:

- **Rhythmic**: BPM, BeatCount, BeatConfidence, OnsetRate.
- **Harmonic**: Key, Scale, PitchMeanHz, PitchStdHz, 12-bin HPCPs.
- **Timbral**: Spectral Centroid, Flatness, Rolloff, 13 MFCCs.
- **Classifications**: 56 Mood/Theme tags, 15 Parent Genres, Voice/Instrumental detection.
- **Embeddings**: 1280-dimensional Discogs-EFFNet vector (stored as JSON).

## 🚀 Usage

### Recommended Execution (via tmux)
```bash
# 1. Set paths
export LD_LIBRARY_PATH=$(pwd)/.venv/nvidia_fix:...:$LD_LIBRARY_PATH

# 2. Run
.venv/bin/python3 -m youtube_audio_pipeline.main
```

## 🛠️ Concurrency & Stealth Note
We have explicitly disabled `aria2c` and multi-threaded downloads. The pipeline now uses a **Single Connection** per song. This is a deliberate design choice to ensure your server IP remains healthy during 10,000+ song runs.
