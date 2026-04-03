#!/bin/bash

# Navigate to project root (one level up from this script)
cd "$(dirname "$0")/.."

# 1. Export GPU library paths
export LD_LIBRARY_PATH=$(pwd)/.venv/nvidia_fix:$(.venv/bin/python3 -c 'import os, sys; from glob import glob; print(":".join(set(os.path.dirname(p) for p in glob(sys.prefix + "/lib/python*/site-packages/nvidia/*/lib/*.so*"))))'):/usr/lib/x86_64-linux-gnu:/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# 2. FORCE GPU Behavior (Fix for "No DNN" error)
export TF_FORCE_GPU_ALLOW_GROWTH=true
export TF_CPP_MIN_LOG_LEVEL=2
export XLA_FLAGS="--xla_gpu_cuda_data_dir=/usr/lib/cuda"

# 3. Run the Stealth Engine
echo "🚀 Starting YouTube Audio Pipeline v2.0 (GPU Guard Active)..."
.venv/bin/python3 -m youtube_audio_pipeline.main "$@"
