# YouTube Audio Pipeline Production Upgrade Summary

This document provides a technical overview of the production-grade enhancements implemented in the YouTube audio pipeline.

---

## 🚀 Turbo Hybrid Architecture (v1.3.0)

We have achieved a **3.7x speedup** end-to-end (from 3m 55s down to 1m 03s for 16 tracks) by transitioning to a decoupled, high-overlap execution model.

### 1. Parallel Metadata Pre-Fetching
We identified that sequential metadata requests to YouTube added significant latency.
*   **The Fix**: The pipeline now bursts metadata requests for all URLs in parallel at startup.
*   **Result**: Downloaders can start their file transfers immediately without waiting for info-roundtrips.

### 2. Adaptive GPU Heartbeat
Previous versions suffered from "Batch Starvation," where the GPU sat idle while waiting for a full batch of 16 tracks.
*   **The Fix**: The Inference Manager now uses a **2-second heartbeat**. If any data is waiting and the timeout is reached, the GPU processes the partial batch immediately.
*   **Result**: Results start appearing on the console within seconds, rather than at the very end of the run.

### 3. Unified Decoupled Pool
We moved away from rigid thread counts for specific tasks.
*   **The Fix**: A unified `ThreadPoolExecutor` handles both downloads and analysis. Analyzers are triggered the microsecond a download finishes.
*   **Result**: Maximum utilization of network bandwidth and CPU cores simultaneously.

### 4. "16kHz Uniform" & Filter-Bank Optimization
*   **Early Resampling**: Resampling to 16kHz happens inside `ffmpeg` during the download.
*   **Fixed Math**: MFCC algorithms are pre-configured for the 513-bin spectrum produced by our 1024-frame window. This eliminates thousands of redundant filter-bank recomputations per song.

---

## 🛠️ Final Production Usage

### Recommended Command:
```bash
# 1. Set GPU library path
export LD_LIBRARY_PATH=$(pwd)/.venv/nvidia_fix:$(.venv/bin/python3 -c 'import os, sys; from glob import glob; print(":".join(set(os.path.dirname(p) for p in glob(sys.prefix + "/lib/python*/site-packages/nvidia/*/lib/*.so*"))))'):/usr/lib/x86_64-linux-gnu:/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# 2. Run with optimized flags
.venv/bin/python3 -m youtube_audio_pipeline.main \
  --downloaders 4 \
  --workers 6 \
  --batch-size 16 \
  --skip-pitch
```

### Key Columns in Output (131 total):
*   **YouTubeID / Title / URL / Uploader**: Identity metadata.
*   **ViewCount / LikeCount**: Popularity metrics.
*   **BPM / Key / Scale / KeyStrength**: Rhythmic and harmonic base.
*   **Danceability / Valence**: High-level emotional proxies.
*   **GenreTopParent / GenreTopLabel**: Discogs-based classification.
*   **Mood_* (56 columns)**: MTG-Jamendo mood and theme probabilities.
*   **DiscogsEmbeddingJson**: 1280-dimensional vector for semantic search training.
