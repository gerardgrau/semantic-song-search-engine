# YouTube Audio Pipeline

High-throughput module to download YouTube audio URLs directly into RAM and extract:

### Audio Features (Essentia-based)

- BPM
- Key
- Loudness
- DurationSeconds
- RmsEnergy
- KeyStrength
- BeatConfidence
- BeatCount
- OnsetRate
- OnsetCount
- Danceability (proxy)
- Valence (proxy)
- SpectralCentroidHz
- SpectralRolloffHz
- SpectralFlatness
- PitchMeanHz
- PitchStdHz
- ZeroCrossingRate

### High-Level Model Features (TensorFlow Pretrained)

- **Genre Classification**: `GenreTopLabel`, `GenreTopConfidence`, `GenreProbsJson` (multi-label via Dortmund/Discogs)
- **Mood Classification** (7 dimensions): `MoodAcoustic`, `MoodAggressive`, `MoodElectronic`, `MoodHappy`, `MoodParty`, `MoodRelaxed`, `MoodSad`, `MoodProbsJson`
- **Audio Embedding**: `DiscogsEmbeddingJson` (2048-dim Discogs EfficientNet embedding)

### Vector Features (JSON-serialized)

- `MfccMeanJson`, `MfccStdJson` (13-dim MFCC coefficients)
- `HpcpMeanJson` (12-dim chroma features)

Additional metadata:

- `YouTubeID` (stable join key for DB updates)
- `SourceInput` (original user-provided URL/ID)

The output is stored in CSV format for downstream processing (database ingestion, embeddings indexing, etc.).

## Why this module is fast

- Downloads native audio stream (`bestaudio/best`), no MP3 conversion.
- Uses `/dev/shm` as RAM-disk to avoid SSD I/O bottlenecks.
- Integrates `yt-dlp` with `aria2c` (`-x 16 -s 16 -k 1M`) for accelerated transfer.
- Uses C++-backed `essentia.standard` for high-performance feature extraction.
- Enforces analyze-and-delete so temporary files are removed immediately.

## Concurrency model

The pipeline uses two layers of parallelism:

1. **Song-level parallelism (Python threads):**
  - `main.py` uses a `ThreadPoolExecutor`.
  - Each worker processes a different song URL (`download -> analyze -> discard`).

2. **Per-song download parallelism (`aria2c`):**
  - Inside each song download, `yt-dlp` calls `aria2c` with multiple connections (`-x 16 -s 16`).
  - This can split the same song download into multiple chunks/connections.

Practical note:

- Total network pressure is roughly song-level workers × per-song connections.
- Tune `--workers` according to your target server capacity.

Compatibility note:

- If the downloaded codec is not directly readable by Essentia in your environment, the analyzer performs a temporary in-RAM conversion to mono 44.1kHz WAV using `ffmpeg`, analyzes it, and deletes both files immediately.

## Model Initialization

The pipeline uses Essentia pretrained TensorFlow models for genre, 7-dimensional mood, and embedding inference. Models are initialized globally at startup (before ThreadPoolExecutor begins) to amortize overhead across all workers.

### Model Files Location

Models are stored in `youtube_audio_pipeline/models/` and are **not committed to Git** (see `.gitignore`). You need to download them manually:

```bash
mkdir -p youtube_audio_pipeline/models/
cd youtube_audio_pipeline/models/

# Download genre model
wget http://essentia.upf.edu/models/classifiers/genre/discogs-effnet/genre_dortmund-discogs-effnet-1.pb
wget http://essentia.upf.edu/models/classifiers/genre/discogs-effnet/genre_dortmund-discogs-effnet-1_metadata.json

# Download mood models (7 dimensions)
for mood in acoustic aggressive electronic happy party relaxed sad; do
  wget "http://essentia.upf.edu/models/classifiers/mood/discogs-effnet/mood_${mood}-discogs-effnet-1.pb"
  wget "http://essentia.upf.edu/models/classifiers/mood/discogs-effnet/mood_${mood}-discogs-effnet-1_metadata.json"
done

# Download embedding extractor
wget http://essentia.upf.edu/models/feature-extractors/discogs-effnet/discogs-effnet-1.pb
wget http://essentia.upf.edu/models/feature-extractors/discogs-effnet/discogs-effnet-1_metadata.json
```

### Disabling Models

If models are unavailable or you want to test the audio-only pipeline, use `--skip-models`:

```bash
python -m youtube_audio_pipeline --urls-file urls.txt --skip-models
```

This will skip genre/mood/embedding inference and only output the 23 audio features.

## Performance Notes

- **Audio feature extraction**: ~0.5–1s per song (Essentia C++ backend)
- **Model inference** (genre + 7 moods + embedding): ~2.7–4.5s per song (TensorFlow)
- **Total end-to-end**: ~3–5s per song with 22 workers

Model initialization adds ~5–8 seconds to the startup sequence (one-time cost for 9 models).

## Files

- [downloader.py](downloader.py): download to RAM-disk
- [analyzer.py](analyzer.py): feature extraction and guaranteed cleanup
- [main.py](main.py): CLI runner with parallel processing and batch CSV flushes
- [benchmark.py](benchmark.py): server-side throughput benchmark to tune worker count
- [urls.example.txt](urls.example.txt): sample URL input file
- [urls.benchmark.example.txt](urls.benchmark.example.txt): benchmark URL sample

## Requirements

### System packages

- `aria2`
- `ffmpeg`

Ubuntu install command:

```bash
sudo apt update && sudo apt install -y aria2 ffmpeg
```


### Python packages

Install from repository root:

```bash
pip install -r requirements.txt
```

Note: this module is optimized for Linux (`/dev/shm`). On non-Linux systems it automatically falls back to the OS temp directory.

## Basic usage

From repository root:

```bash
python -m youtube_audio_pipeline.main --urls-file youtube_audio_pipeline/urls.example.txt
```

Shorthand (equivalent):

```bash
python -m youtube_audio_pipeline --urls-file youtube_audio_pipeline/urls.example.txt
```

Important:

- Prefer `python -m ...` execution from the repository root.
- Avoid `python main.py` from inside [youtube_audio_pipeline](youtube_audio_pipeline), because package imports are not reliably resolvable in that mode.

Input flexibility:

- The URL list can contain full watch URLs, short URLs, embed URLs, iframe embed snippets, or plain 11-char YouTube video IDs.
- Inputs are normalized to canonical watch URLs and deduplicated by `YouTubeID`.

CSV output default:

- `data/processed/youtube_song_characteristics.csv`

CSV columns include:

**Metadata:**
- `YouTubeID`
- `URL` (canonical where available)
- `SourceInput` (original raw value from your file/CLI)
- `Title`

**Rhythm & Timing:**
- `BPM`, `BeatCount`, `BeatConfidence`
- `OnsetRate`, `OnsetCount`
- `DurationSeconds`

**Harmonic & Key:**
- `Key`, `KeyStrength`

**Energy & Loudness:**
- `Loudness`, `RmsEnergy`

**Spectral Descriptors:**
- `SpectralCentroidHz`, `SpectralRolloffHz`, `SpectralFlatness`, `ZeroCrossingRate`

**Pitch:**
- `PitchMeanHz`, `PitchStdHz`

**High-Level Proxies:**
- `Danceability`, `Valence`

**Genre & Mood (Model-based):**
- `GenreTopLabel` (top-1 genre label)
- `GenreTopConfidence` (confidence of top-1 [0-1])
- `GenreProbsJson` (full multi-label genre probabilities)
- `MoodAcoustic`, `MoodAggressive`, `MoodElectronic`, `MoodHappy`, `MoodParty`, `MoodRelaxed`, `MoodSad` (7 mood dimensions)
- `MoodProbsJson` (full mood distribution)

**Vectors (JSON-serialized):**
- `MfccMeanJson` (mean of 13 MFCC coefficients per frame)
- `MfccStdJson` (std of 13 MFCC coefficients per frame)
- `HpcpMeanJson` (mean of 12-dim chroma vector)
- `DiscogsEmbeddingJson` (2048-dim audio embedding)

Storage design:

- High-value scalar descriptors are stored as regular CSV columns (queryable, indexable).
- High-dimensional vectors are stored as JSON strings for flexible DB ingestion.

## Common options

```bash
python -m youtube_audio_pipeline.main \
  --urls-file path/to/urls.txt \
  --output-csv data/processed/my_features.csv \
  --ram-disk-path /dev/shm/yt_audio \
  --workers 22 \
  --flush-every 250 \
  --skip-models  # Optional: disable model inference (audio features only)
```

Add ad-hoc URLs without editing a file:

```bash
python -m youtube_audio_pipeline.main \
  --url "https://www.youtube.com/watch?v=..." \
  --url "https://www.youtube.com/watch?v=..."
```

## Notes

- If `/dev/shm` is unavailable, the downloader falls back to the OS temp directory.
- This module assumes URL access rights and legal usage are handled by the operator.
- For very large runs, monitor RAM usage and tune `--workers`.

## Benchmark on the target server

Because performance is machine-dependent, benchmark on the same server where production runs will execute.

Example benchmark run (10 URLs, 1 repeat):

```bash
python -m youtube_audio_pipeline.benchmark \
  --urls-file youtube_audio_pipeline/urls.benchmark.example.txt \
  --max-urls 10 \
  --workers-list 1,2,4,8,12,16,22 \
  --repeats 1 \
  --flush-every 200
```

Benchmark summary output:

- `data/processed/youtube_pipeline_benchmark.csv`

How to choose workers:

- Prefer the highest `urls_per_second`.
- Require `success_rate` close to `1.0`.
- If success rate drops at high workers, choose the best stable lower value.

Keep per-run feature CSVs for inspection:

```bash
python -m youtube_audio_pipeline.benchmark \
  --urls-file youtube_audio_pipeline/urls.benchmark.example.txt \
  --keep-run-csv
```

## Credits

This project is made possible by:

- **Essentia Library** (Audio feature extraction + Pretrained Models)
  - http://essentia.upf.edu
  - Models trained on Discogs dataset (200M+ tracks)
  - Reference: Bogdanov, D., Nicolas, N., et al. "ESSENTIA: An Open-Source Library for the Audio Description"
  
- **yt-dlp** (YouTube audio download)
  - https://github.com/yt-dlp/yt-dlp

- **aria2** (Download acceleration)
  - https://aria2.github.io
