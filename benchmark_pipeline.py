import time
import subprocess
import os
from pathlib import Path

# Use 6 URLs for a quick but clear comparison
URLS = [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://www.youtube.com/watch?v=97_VJve7UVc",
    "https://www.youtube.com/watch?v=CD-E-LDc384",
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://www.youtube.com/watch?v=97_VJve7UVc",
    "https://www.youtube.com/watch?v=CD-E-LDc384"
]

TEMP_CSV = "data/processed/benchmark_results.csv"

def run_test(name, flags):
    print(f"\n🚀 Running Benchmark: {name}")
    # Use 1 worker to clearly see the overlapping benefit of P-C
    cmd = [".venv/bin/python3", "-m", "youtube_audio_pipeline.main", "--workers", "1", "--output-csv", TEMP_CSV] + flags
    for url in URLS:
        cmd.extend(["--url", url])
    
    start = time.time()
    subprocess.run(cmd)
    duration = time.time() - start
    
    if os.path.exists(TEMP_CSV): os.remove(TEMP_CSV)
    return duration

results = {}

# 1. Baseline
results["Base (Serial DP+A)"] = run_test("Baseline", [])

# 2. Producer-Consumer
results["Producer-Consumer (Parallel D/A)"] = run_test("Producer-Consumer", ["--optimize"])

print("\n" + "="*40)
print("📈 BENCHMARK RESULTS (6 Tracks)")
print("="*40)
for name, duration in results.items():
    print(f"{name:35} | {duration:.2f}s")
print("="*40)
