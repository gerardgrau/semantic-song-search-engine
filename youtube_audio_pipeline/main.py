from __future__ import annotations

import argparse
import logging
import os
import time
import json
import random
import csv
from pathlib import Path

from youtube_audio_pipeline.analyzer import extract_base_features, finalize_song_data
from youtube_audio_pipeline.downloader import download_to_ram
from youtube_audio_pipeline.youtube_utils import normalize_youtube_input
from youtube_audio_pipeline import model_inference

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

STATE_FILE = "data/processed/pipeline_state.json"

def load_processed_ids() -> set[str]:
    if not os.path.exists(STATE_FILE): return set()
    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
            return set(data.get("processed_ids", []))
    except: return set()

def save_processed_id(video_id: str):
    processed = list(load_processed_ids())
    if video_id not in processed:
        processed.append(video_id)
        with open(STATE_FILE, "w") as f:
            json.dump({"processed_ids": processed}, f)

def load_urls(urls_file: str) -> list[dict[str, str | None]]:
    urls = []
    urls_path = Path(urls_file)
    if not urls_path.exists(): return []
    with open(urls_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"): continue
            url, video_id = normalize_youtube_input(line)
            urls.append({"url": url, "youtube_id": video_id, "source_input": line})
    return urls

def format_duration(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0: return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0: return f"{minutes}m {secs}s"
    else: return f"{secs}s"

def save_row_to_csv(row: dict, output_csv: str):
    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = output_path.exists()
    with open(output_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists: writer.writeheader()
        writer.writerow(row)

def run_stealth_pipeline(
    urls: list[dict[str, str | None]],
    output_csv: str,
    ram_disk_path: str = "/dev/shm/yt_audio",
    ml_batch_size: int = 8,
    cookies_path: str | None = None
):
    if not urls: return
    
    processed_ids = load_processed_ids()
    to_process = [u for u in urls if u['youtube_id'] not in processed_ids]
    
    total_count = len(urls)
    already_done = total_count - len(to_process)
    start_time = time.time()
    
    print(f"🕵️ Entering Stealth Mode (v2.0)")
    print(f"📊 Progress: {already_done}/{total_count} already processed.")
    print(f"🚀 Starting work on {len(to_process)} remaining songs...")

    pending_batch = []
    
    for i, url_entry in enumerate(to_process):
        current_idx = already_done + i + 1
        
        # 1. DOWNLOAD (Stealth One-by-One)
        status, filepath, metadata = download_to_ram(url_entry['url'], ram_disk_path, cookies_path)
        
        if status == "BOT_CHALLENGE":
            print(f"\n⚠️ BOT CHALLENGE DETECTED. Entering Hibernate Mode for 5 minutes...")
            time.sleep(300)
            # Retry once after sleep
            status, filepath, metadata = download_to_ram(url_entry['url'], ram_disk_path, cookies_path)
            if status == "BOT_CHALLENGE":
                print("❌ Still blocked. Skipping this song for now.")
                continue

        if status != "SUCCESS" or not filepath:
            print(f"[{current_idx}/{total_count}] ❌ Failed: {url_entry['source_input']}")
            continue

        # 2. ANALYZE (High Fidelity)
        res = extract_base_features(Path(filepath), metadata)
        if os.path.exists(filepath): os.remove(filepath)
        
        if res:
            base_data, patches = res
            base_data["SourceInput"] = url_entry['source_input']
            pending_batch.append((base_data, patches))
        
        # 3. BATCH INFERENCE (GPU Efficiency)
        if len(pending_batch) >= ml_batch_size:
            _process_gpu_batch(pending_batch, output_csv, start_time, current_idx, total_count)
            pending_batch = []
            
        # 4. JITTER: Random human-like pause (2-5 seconds)
        # This keeps us under the 300/hour limit
        time.sleep(random.uniform(2.0, 5.0))

    # Final sweep
    if pending_batch:
        _process_gpu_batch(pending_batch, output_csv, start_time, total_count, total_count)

    print(f"\nStealth Pipeline finished in {format_duration(time.time() - start_time)}.")

def _process_gpu_batch(batch, output_csv, start_time, current_idx, total_count):
    list_of_patches = [item[1] for item in batch]
    ml_results = model_inference.run_batch_inference(list_of_patches)
    
    for j, (base_data, _) in enumerate(batch):
        final_row = finalize_song_data(base_data, ml_results[j])
        save_row_to_csv(final_row, output_csv)
        save_processed_id(base_data['YouTubeID'])
        
        # We estimate ETA based on the current song in the batch
        # current_idx is where the batch started, we add j
        actual_idx = (current_idx - len(batch)) + j + 1
        elapsed = time.time() - start_time
        avg = elapsed / (actual_idx - (total_count - len(batch) if actual_idx > total_count else 0)) # simplified
        eta = avg * (total_count - actual_idx)
        print(f"[{actual_idx}/{total_count}] [{time.strftime('%H:%M:%S')}] ✅ Processed: {final_row['Title']} | ETA: {format_duration(eta)}")

def main() -> None:
    parser = argparse.ArgumentParser(description="YouTube Audio Pipeline Stealth v2.0")
    parser.add_argument("--urls-file", type=str, default="youtube_audio_pipeline/urls.example.txt")
    parser.add_argument("--url", action="append")
    parser.add_argument("--output-csv", type=str, default="data/processed/youtube_song_characteristics.csv")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--cookies", type=str, default=None, help="Path to cookies.txt (optional).")
    args = parser.parse_args()

    urls = []
    if args.url:
        for u in args.url:
            u_norm, vid_id = normalize_youtube_input(u)
            urls.append({"url": u_norm, "youtube_id": vid_id, "source_input": u})
    if args.urls_file and os.path.exists(args.urls_file):
        urls.extend(load_urls(args.urls_file))

    if not urls: 
        print("❌ Error: No URLs provided.")
        return

    model_inference.initialize_models_globally()
    run_stealth_pipeline(urls, args.output_csv, ml_batch_size=args.batch_size, cookies_path=args.cookies)

if __name__ == "__main__":
    main()
