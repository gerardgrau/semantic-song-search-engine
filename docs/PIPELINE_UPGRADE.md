# YouTube Audio Pipeline: Stealth & Accuracy (v2.0)

This document provides a technical overview of the v2.0 "Stealth" architecture, designed for reliable, high-fidelity processing of large datasets (10,000+ songs) under strict rate limits.

---

## 🕵️ The Stealth Strategy

YouTube limits guest sessions to approximately 300 videos per hour. v2.0 is designed to "sip" data at this rate indefinitely without triggering permanent IP bans.

### 1. Resiliency & Hibernate Mode
The engine now detects bot-challenges (`Sign in to confirm you're not a bot`). 
*   **Action**: On detection, the system enters **Hibernate Mode** for 5 minutes.
*   **Result**: Prevents IP blacklisting and allows the rate-limit bucket to reset.

### 2. Client Rotation
The downloader now cycles through multiple player identities (`ios`, `android`, `web`).
*   **Result**: Maximizes format availability and leverages the more generous rate limits of mobile clients.

### 3. Persistent State Saver
Progress is tracked in `data/processed/pipeline_state.json`.
*   **Action**: Every successful track is logged by its YouTube ID.
*   **Result**: Automatic resume support. If the process is interrupted, it skips finished tracks instantly upon restart.

---

## 💎 High-Fidelity Analysis

Since the pipeline is network-throttled, we utilize the "idle" time to perform much more intensive analysis:
*   **Full Pitch Tracking**: Re-enabled `PredominantPitchMelodia`.
*   **High-Res Spectral Mapping**: 6x higher temporal resolution for spectral features.
*   **In-Memory Resampling**: Precision resampling for higher classification accuracy.

---

## 🚀 Usage Guide

### Recommended Execution:
We recommend running the engine inside a **`tmux`** session to prevent interruption if your SSH connection drops.

```bash
# 1. Set GPU library path
export LD_LIBRARY_PATH=$(pwd)/.venv/nvidia_fix:$(.venv/bin/python3 -c 'import os, sys; from glob import glob; print(":".join(set(os.path.dirname(p) for p in glob(sys.prefix + "/lib/python*/site-packages/nvidia/*/lib/*.so*"))))'):/usr/lib/x86_64-linux-gnu:/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# 2. Start the Stealth Engine
.venv/bin/python3 -m youtube_audio_pipeline.main
```

### Capacity:
*   **Throughput**: ~270-300 songs per hour.
*   **Total Time for 10k**: ~35-40 Hours.
*   **Maintenance**: None. The engine is self-healing.
