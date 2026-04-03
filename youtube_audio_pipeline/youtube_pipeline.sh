#!/bin/bash

# Navigate to project root (one level up from this script)
cd "$(dirname "$0")/.."

# 1. Export GPU library paths
export LD_LIBRARY_PATH=$(pwd)/.venv/nvidia_fix:$(.venv/bin/python3 -c 'import os, sys; from glob import glob; print(":".join(set(os.path.dirname(p) for p in glob(sys.prefix + "/lib/python*/site-packages/nvidia/*/lib/*.so*"))))'):/usr/lib/x86_64-linux-gnu:/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# 2. Run the Stealth Engine (Restored to stable defaults)
echo "🚀 Starting YouTube Audio Pipeline v2.0 (STABLE BASELINE)..."
.venv/bin/python3 -m youtube_audio_pipeline.main "$@"
