#!/bin/bash

# 1. Export GPU library paths
export LD_LIBRARY_PATH=$(pwd)/.venv/nvidia_fix:$(.venv/bin/python3 -c 'import os, sys; from glob import glob; print(":".join(set(os.path.dirname(p) for p in glob(sys.prefix + "/lib/python*/site-packages/nvidia/*/lib/*.so*"))))'):/usr/lib/x86_64-linux-gnu:/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# 2. Run the Stealth Engine
echo "🚀 Starting Stealth Engine v2.0..."
.venv/bin/python3 -m youtube_audio_pipeline.main "$@"
