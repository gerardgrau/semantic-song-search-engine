from __future__ import annotations

import argparse
import logging
import os
import time
import queue
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from youtube_audio_pipeline.analyzer import extract_base_features, finalize_song_data, save_to_dataframe
from youtube_audio_pipeline.downloader import download_to_ram
from youtube_audio_pipeline.youtube_utils import normalize_youtube_input
from youtube_audio_pipeline import model_inference

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

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

def run_turbo_pipeline(
    urls: list[dict[str, str | None]],
    output_csv: str,
    ram_disk_path: str = "/dev/shm/yt_audio",
    num_downloaders: int = 4,
    num_analyzers: int = 6,
    ml_batch_size: int = 16,
    skip_models: bool = False,
    skip_pitch: bool = False,
) -> tuple[int, int]:
    if not urls: return 0, 0
    total_count = len(urls)
    start_time = time.time()
    
    # 1. Parallel Metadata Pre-Fetching (Hides network latency)
    print(f"📡 Pre-fetching metadata for {total_count} songs...")
    metadata_results = []
    with ThreadPoolExecutor(max_workers=10) as meta_pool:
        def fetch_meta(u_entry):
            import yt_dlp
            try:
                with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
                    info = ydl.extract_info(u_entry['url'], download=False)
                    return info, u_entry['source_input']
            except:
                return None, u_entry['source_input']
        metadata_results = list(meta_pool.map(fetch_meta, urls))
    
    print(f"✅ Metadata complete. Starting Turbo Run...")
    
    # Queues
    inference_queue = queue.Queue(maxsize=ml_batch_size * 2)
    processed_count = 0
    
    # 2. Adaptive Inference Manager (Heartbeat-based batching)
    def inference_manager(total_to_process):
        nonlocal processed_count
        pending_batch = []
        received = 0
        last_inference_time = time.time()
        
        while received < total_to_process:
            try:
                item = inference_queue.get(timeout=1.0)
                received += 1
                if item is not None:
                    pending_batch.append(item)
            except queue.Empty:
                if pending_batch:
                    _run_batch(pending_batch)
                    processed_count += len(pending_batch)
                    pending_batch = []
                    last_inference_time = time.time()
                continue

            # Batch logic: Either the bucket is full, or the heartbeat timeout (2s) reached
            if len(pending_batch) >= ml_batch_size or (time.time() - last_inference_time > 2.0):
                if pending_batch:
                    _run_batch(pending_batch)
                    processed_count += len(pending_batch)
                    pending_batch = []
                    last_inference_time = time.time()
        
        if pending_batch:
            _run_batch(pending_batch)
            processed_count += len(pending_batch)

    def _run_batch(batch):
        list_of_patches = [item[1] for item in batch]
        if not skip_models:
            ml_batch_results = model_inference.run_batch_inference(list_of_patches)
        else:
            ml_batch_results = [{"embedding": None} for _ in batch]
        
        completed_rows = []
        for i, (base_data, _) in enumerate(batch):
            final_row = finalize_song_data(base_data, ml_batch_results[i])
            completed_rows.append(final_row)
            
            idx = processed_count + i + 1
            elapsed = time.time() - start_time
            avg = elapsed / idx
            eta = avg * (total_count - idx)
            print(f"[{idx}/{total_count}] ✅ Processed: {final_row['Title']} | ETA: {format_duration(eta)}")
        
        save_to_dataframe(completed_rows, output_csv)

    # 3. Unified Execution Pool (Decoupled Download/Analysis)
    inf_thread = threading.Thread(target=inference_manager, args=(total_count,))
    inf_thread.start()

    with ThreadPoolExecutor(max_workers=num_downloaders + num_analyzers) as pool:
        # Step A: Downloaders (Submitting all tasks to the pool)
        download_futures = []
        for meta_res in metadata_results:
            info, source_input = meta_res
            if not info:
                inference_queue.put(None)
                continue
            
            def d_task(u, s):
                return download_to_ram(u, ram_disk_path), s
            
            f = pool.submit(d_task, info['webpage_url'], source_input)
            download_futures.append(f)
            
        # Step B: Analyzers (Triggered as downloads complete)
        for df in as_completed(download_futures):
            download_res, source_input = df.result()
            success, filepath, metadata = download_res
            
            if not success or not filepath:
                inference_queue.put(None)
                continue
            
            def a_task(fp, meta, src):
                res = extract_base_features(Path(fp), meta, skip_models, skip_pitch)
                if Path(fp).exists(): Path(fp).unlink()
                if res:
                    base_data, patches = res
                    base_data["SourceInput"] = src
                    return (base_data, patches)
                return None
            
            # Submit analysis task
            af = pool.submit(a_task, filepath, metadata, source_input)
            
            # Callback to feed the inference manager
            def push_to_inf(fut):
                try:
                    inference_queue.put(fut.result())
                except:
                    inference_queue.put(None)
            
            af.add_done_callback(push_to_inf)

    inf_thread.join()
    total_time = time.time() - start_time
    print(f"\nTurbo Pipeline finished in {format_duration(total_time)}.")
    return processed_count, processed_count

def main() -> None:
    parser = argparse.ArgumentParser(description="YouTube Audio Pipeline Production v1.2.0")
    parser.add_argument("--urls-file", type=str, default="youtube_audio_pipeline/urls.example.txt")
    parser.add_argument("--url", action="append")
    parser.add_argument("--output-csv", type=str, default="data/processed/youtube_song_characteristics.csv")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--downloaders", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--skip-models", action="store_true")
    parser.add_argument("--skip-pitch", action="store_true")
    args = parser.parse_args()

    urls = []
    if args.url:
        for u in args.url:
            u_norm, vid_id = normalize_youtube_input(u)
            urls.append({"url": u_norm, "youtube_id": vid_id, "source_input": u})
    if args.urls_file and os.path.exists(args.urls_file):
        urls.extend(load_urls(args.urls_file))

    if not urls: return
    if not args.skip_models: model_inference.initialize_models_globally()

    run_turbo_pipeline(
        urls, 
        args.output_csv, 
        num_downloaders=args.downloaders,
        num_analyzers=args.workers, 
        ml_batch_size=args.batch_size, 
        skip_models=args.skip_models,
        skip_pitch=args.skip_pitch
    )

if __name__ == "__main__":
    main()
