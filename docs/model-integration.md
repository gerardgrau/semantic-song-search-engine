# Model Integration Guide

Technical reference for Essentia pretrained model loading, inference, and caching in the YouTube audio pipeline.

## Overview

The pipeline integrates three categories of Essentia pretrained TensorFlow models:

1. **Genre Classification** (`genre_dortmund-discogs-effnet-1`): Multi-label genre prediction
2. **Mood Classification** (7 dimensions): Acoustic, Aggressive, Electronic, Happy, Party, Relaxed, Sad
3. **Audio Embedding** (`discogs-effnet-1`): 2048-dimensional feature extractor

Models are trained on **200M+ Discogs tracks** and use **EfficientNet** backbone (fast inference, high accuracy).

## Architecture

### Model Loading Strategy

**Thread Safety:** Models are initialized globally at application startup (in `main.py:main()`) before `ThreadPoolExecutor` begins. This approach:
- Eliminates per-thread model loading overhead (expensive initialization ~1–2s per model)
- Shares model state across threads (TensorFlow GIL-protected during inference)
- Reduces total memory footprint (one model instance per process, not per worker)

**Lazy Initialization:** Within `model_inference.py`, models use double-checked locking (`_models_lock`) to ensure thread-safe first-access initialization if called before `initialize_models_globally()`.

### Code Flow

```
main.py:main()
   ├─ load_urls()
   ├─ initialize_models_globally()  ← Warm up all models
   │   └─ model_inference.py
   │       └─ _ensure_models_loaded()  ← Double-checked lock
   │           ├─ Load genre_dortmund.pb → _GENRE_MODEL
   │           ├─ Load mood_*.pb → _MOOD_MODELS dict
   │           └─ Load discogs-effnet.pb → _EMBEDDING_MODEL
   └─ run_pipeline()
       └─ ThreadPoolExecutor(workers=22)
           └─ process_single_url() [per worker]
               └─ analyze_and_discard()
                   ├─ Extract 23 Essentia audio features
                   ├─ run_genre_inference(audio)
                   ├─ run_mood_inference(audio)
                   ├─ run_embedding_inference(audio)
                   └─ Return combined dict → CSV
```

## Model Files

### File Structure

```
youtube_audio_pipeline/
├── models/
│   ├── .gitkeep
│   ├── genre_dortmund-discogs-effnet-1.pb (~200MB)
│   ├── genre_dortmund-discogs-effnet-1_metadata.json
│   ├── mood_acoustic-discogs-effnet-1.pb (~200MB)
│   ├── mood_acoustic-discogs-effnet-1_metadata.json
│   ├── mood_aggressive-discogs-effnet-1.pb (~200MB)
│   ├── mood_aggressive-discogs-effnet-1_metadata.json
│   ├── mood_electronic-discogs-effnet-1.pb (~200MB)
│   ├── mood_electronic-discogs-effnet-1_metadata.json
│   ├── mood_happy-discogs-effnet-1.pb (~200MB)
│   ├── mood_happy-discogs-effnet-1_metadata.json
│   ├── mood_party-discogs-effnet-1.pb (~200MB)
│   ├── mood_party-discogs-effnet-1_metadata.json
│   ├── mood_relaxed-discogs-effnet-1.pb (~200MB)
│   ├── mood_relaxed-discogs-effnet-1_metadata.json
│   ├── mood_sad-discogs-effnet-1.pb (~200MB)
│   ├── mood_sad-discogs-effnet-1_metadata.json
│   ├── discogs-effnet-1.pb (~200MB)
│   └── discogs-effnet-1_metadata.json
└── .gitignore  ← Excludes *.pb and metadata files
```

### Download

All models are public and available from Essentia model zoo:

```bash
mkdir -p youtube_audio_pipeline/models && cd youtube_audio_pipeline/models

# Genre
wget http://essentia.upf.edu/models/classifiers/genre/discogs-effnet/genre_dortmund-discogs-effnet-1.pb
wget http://essentia.upf.edu/models/classifiers/genre/discogs-effnet/genre_dortmund-discogs-effnet-1_metadata.json

# Mood (7 models)
for mood in acoustic aggressive electronic happy party relaxed sad; do
  wget "http://essentia.upf.edu/models/classifiers/mood/discogs-effnet/mood_${mood}-discogs-effnet-1.pb"
  wget "http://essentia.upf.edu/models/classifiers/mood/discogs-effnet/mood_${mood}-discogs-effnet-1_metadata.json"
done

# Embedding
wget http://essentia.upf.edu/models/feature-extractors/discogs-effnet/discogs-effnet-1.pb
wget http://essentia.upf.edu/models/feature-extractors/discogs-effnet/discogs-effnet-1_metadata.json
```

**Total size:** ~2.0 GB (9 × 200MB models + metadata)

### Metadata JSON

Each model's `.json` metadata file contains:

- `classes`: List of output class labels (genre names, mood names, etc.)
- `model_type`: Model architecture (e.g., "EfficientNet")
- `date`: Training date
- `version`: Model version
- Additional training hyperparameters

Example `genre_dortmund-discogs-effnet-1_metadata.json`:
```json
{
  "classes": ["electronic", "hip-hop", "pop", "rock", ...],
  "model_type": "EfficientNet-B3",
  "version": "1.0",
  "date": "2022-11-15"
}
```

## API Reference

### module_inference.py

#### `initialize_models_globally() → None`

Called once at application startup. Loads all models into global state and logs success/failure.

**Usage:**
```python
from youtube_audio_pipeline import model_inference
model_inference.initialize_models_globally()
```

**Side Effects:**
- Populates `_GENRE_MODEL`, `_MOOD_MODELS`, `_EMBEDDING_MODEL` globals
- Logs "✓ Genre model loaded" etc. to logger (INFO level)
- Logs warnings if model files are missing

#### `run_genre_inference(audio: np.ndarray, sr: int = 44100) → dict[str, float]`

Runs genre classification.

**Args:**
- `audio`: Mono float32 numpy array (e.g., output of `essentia.standard.MonoLoader()`)
- `sr`: Sample rate (default 44100 Hz)

**Returns:**
- Dict mapping genre labels (str) to confidence scores (float, range [0, 1])
- Empty dict `{}` if model unavailable or inference fails
- Example: `{"electronic": 0.89, "pop": 0.07, "hip-hop": 0.04}`

**Thread Safety:** ✓ Safe to call from multiple threads simultaneously

#### `run_mood_inference(audio: np.ndarray, sr: int = 44100) → dict[str, float]`

Runs multi-dimensional mood inference (7 moods).

**Args:**
- `audio`: Mono float32 numpy array
- `sr`: Sample rate (default 44100 Hz)

**Returns:**
- Dict with keys `"acoustic"`, `"aggressive"`, `"electronic"`, `"happy"`, `"party"`, `"relaxed"`, `"sad"` mapped to confidence scores [0, 1]
- Empty dict if any model unavailable or inference fails
- Example: `{"acoustic": 0.8, "aggressive": 0.1, "electronic": 0.2, "happy": 0.1, "party": 0.05, "relaxed": 0.75, "sad": 0.0}`

**Mood Dimensions:**
- **Acoustic/Electronic**: Whether the sound is organic/live (acoustic) or synthesized/digital (electronic)
- **Happy**: Positive, uplifting emotional content
- **Sad**: Melancholic, sorrowful emotional character
- **Aggressive**: Intense, forceful, confrontational tone
- **Party**: Energetic, social, upbeat, dance-oriented
- **Relaxed**: Calm, soothing, mellow atmosphere

**Thread Safety:** ✓ Safe to call from multiple threads simultaneously

#### `run_embedding_inference(audio: np.ndarray, sr: int = 44100) → np.ndarray | None`

Extracts audio embedding (2048-dim feature vector).

**Args:**
- `audio`: Mono float32 numpy array
- `sr`: Sample rate (default 44100 Hz)

**Returns:**
- Numpy array shape `(2048,)` dtype float32
- `None` if model unavailable or inference fails

**Thread Safety:** ✓ Safe to call from multiple threads simultaneously

**Usage in analyzer.py:**
```python
import json
embedding = model_inference.run_embedding_inference(audio, sr=44100)
if embedding is not None:
    embedding_json = json.dumps(embedding.tolist())
else:
    embedding_json = "[]"
```

## Error Handling

### Graceful Degradation

If any model file is missing or fails to load:

1. **At startup:** `initialize_models_globally()` logs a warning but continues
2. **During inference:** Return empty dict or None (not an exception)
3. **In analyzer:** New model-based columns are populated with defaults:
   - `GenreTopLabel` → `"Unknown"`
   - `GenreTopConfidence` → `0.0`
   - `GenreProbsJson` → `"{}"`
   - `MoodAcoustic/Aggressive/Electronic/Happy/Party/Relaxed/Sad` → `0.0`
   - `MoodProbsJson` → `"{}"`
   - `DiscogsEmbeddingJson` → `"[]"`

4. **Pipeline continues:** All 23 original audio features are still extracted and saved to CSV

### Logging

Enable debug logging to see inference activity:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Expected debug messages:
```
Loading Essentia models from .../youtube_audio_pipeline/models
✓ Genre model loaded
✓ Mood (happy) model loaded
✓ Mood (sad) model loaded
✓ Mood (relaxed) model loaded
✓ Embedding model loaded
```

## Performance

### Initialization Cost

First call to `initialize_models_globally()`:
- **Load genre model:** ~0.5–1.0s
- **Load mood models (3×):** ~1.5–3.0s
- **Load embedding model:** ~0.5–1.0s
- **Total:** ~2.5–5.0s (one-time)

### Per-Song Inference

For a 3-minute song (≈ 132K samples at 44100 Hz):
- **Genre inference:** ~0.3–0.5s
- **Mood inference (7× binary):** ~2.1–3.5s
- **Embedding inference:** ~0.3–0.5s
- **Total:** ~2.7–4.5s per song

With 22 workers: **~3–5 seconds total per song** (end-to-end including audio features).

### Memory

Approximate resident model memory:
- **Genre model:** ~400 MB
- **Mood models (7×):** ~2.8 GB
- **Embedding model:** ~400 MB
- **Total:** ~3.6 GB (shared across all workers)

Per-worker audio buffer (during analysis):
- **Average song (~3 min):** ~500 MB–1 GB (depends on bitrate)

Total machine requirement:
- **32 GB RAM** (default): Comfortable for 22 workers
- **16 GB RAM**: May need to reduce workers to 4–8

## Integration with analyzer.py

### Current Integration

In [youtube_audio_pipeline/analyzer.py](../analyzer.py), the `analyze_and_discard()` function:

1. **Loads and analyzes audio** (Essentia, 0.5–1s)
2. **Calls model inference** (3 functions, 1.5–2.5s)
3. **Serializes results to dict** (JSON encoding of vectors)
4. **Returns combined feature dict** (32 total columns: 23 audio + 9 model-based)

### Key Code Snippet

```python
# Inside analyze_and_discard(), after audio feature extraction:

genre_probs = model_inference.run_genre_inference(audio, sr=sample_rate)
mood_probs = model_inference.run_mood_inference(audio, sr=sample_rate)
embedding = model_inference.run_embedding_inference(audio, sr=sample_rate)

# Parse and serialize results
genre_top_label, genre_top_confidence = max(genre_probs.items(), key=lambda x: x[1]) if genre_probs else ("Unknown", 0.0)
mood_acoustic = float(mood_probs.get("acoustic", 0.0))
mood_aggressive = float(mood_probs.get("aggressive", 0.0))
mood_electronic = float(mood_probs.get("electronic", 0.0))
mood_happy = float(mood_probs.get("happy", 0.0))
mood_party = float(mood_probs.get("party", 0.0))
mood_relaxed = float(mood_probs.get("relaxed", 0.0))
mood_sad = float(mood_probs.get("sad", 0.0))
# ... etc

return {
    # ... 23 existing audio features ...
    "GenreTopLabel": genre_top_label,
    "GenreTopConfidence": genre_top_confidence,
    "GenreProbsJson": json.dumps(genre_probs),
    "MoodAcoustic": mood_acoustic,
    "MoodAggressive": mood_aggressive,
    "MoodElectronic": mood_electronic,
    "MoodHappy": mood_happy,
    "MoodParty": mood_party,
    "MoodRelaxed": mood_relaxed,
    "MoodSad": mood_sad,
    "MoodProbsJson": json.dumps(mood_probs),
    # ... etc
}
```

## Future Enhancements

Possible extensions (not yet implemented):

1. **Model versioning:** Track all model versions used for a CSV output
2. **Model caching:** Use `tools.model_manager` for automatic download + checksum verification
3. **Batch inference:** Queue multiple audio files and run inference in batches for higher throughput
4. **GPU acceleration:** Offload TensorFlow inference to GPU if available (`--cuda` flag)
5. **Additional models:** Instrument (drum/guitar/voice detection), artist/label classification, energy/arousal
6. **E5 embeddings:** Integrate multilingual text embeddings for lyric-based semantic search

## References

- **Essentia Documentation:** http://essentia.upf.edu/documentation/
- **Essentia Model Zoo:** http://essentia.upf.edu/models/
- **Discogs Dataset:** https://www.discogs.com
- **EfficientNet Paper:** https://arxiv.org/abs/1905.11946
- **TensorFlow SavedModel Format:** https://www.tensorflow.org/guide/saved_model
