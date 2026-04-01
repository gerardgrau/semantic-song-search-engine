# YouTube Audio Pipeline Upgrade & Validation Summary

This document summarizes the enhancements made to the YouTube audio pipeline to support advanced ML-based feature extraction and database-optimized data structures.

## 🎯 Core Project Objectives
The pipeline is designed to fulfill two primary goals:
1.  **Database Searchability (MariaDB)**: Providing a structured, high-performance dataset where songs can be filtered and ranked using standard SQL queries across a wide range of musical metrics (BPM, Key, Danceability, Moods, Genres).
2.  **Semantic Search Foundation**: Preparing high-quality feature vectors (1280-dim embeddings) to serve as the training foundation for a downstream **Semantic Embedding Model**. This will enable users to search the song library using **natural language queries** (e.g., "fast electronic music for a summer party").

## 1. Model Integration (Enriched Version)
The pipeline utilizes an optimized suite of Essentia pretrained models:
- **Backbone**: `discogs-effnet-1.pb` (EfficientNet-B0 backbone for audio embeddings).
- **Genre Classifier**: `genre_discogs400-discogs-effnet-1.pb` (400 music styles).
- **Mood & Theme (Multi-task)**: `mtg_jamendo_moodtheme-discogs-effnet-1.pb` (56 moods/themes).
- **Instrumentation**: `mtg_jamendo_instrument-discogs-effnet-1.pb` (40 instrument types).
- **Voice Detection**: Binary Voice/Instrumental and Gender classification.
- **Timbre**: Bright/Dark classification.

## 2. Technical Enhancements (Production Edition)
To support these models and maximize hardware utilization (CPU & GPU), the following updates were made:

- **Dual-Consumer Architecture**: Implemented a producer-consumer model where downloading, CPU feature extraction, and ML inference run in parallel.
- **Vectorized Batch Inference**: ML models now process multiple tracks in a single large batch, significantly boosting GPU throughput.
- **Fully Flattened Data Structure**: Expanded nested data into **130 individual columns** (Genres, Moods, MFCCs, HPCPs) for direct database consumption.
- **Robust Spectral Averaging**: Features (BPM, Centroid, MFCC) are averaged across the entire track duration for representative accuracy.
- **Aggregated Metrics**: Implemented algorithmic **Valence** and **Aggregated Danceability** for high-quality emotional/rhythmic searching.
- **WAV Reliability**: Automatic conversion to WAV ensures 100% compatibility with Essentia algorithms.

## 3. Validation Results
The pipeline has been validated across Pop, Classical, and Metal tracks, producing a stable, non-zero dataset ready for SQL and ML training.

| Track | ViewCount | GenreTopParent | Mood_happy | Valence |
| :--- | :--- | :--- | :--- | :--- |
| Enter Sandman (Metal) | (Numerical) | Rock | 0.007 | (Low) |
| Never Gonna Give You Up | (Numerical) | Electronic | 0.052 | (High) |

## 4. Maintenance
- **Persistence**: Models and metadata are stored in `youtube_audio_pipeline/models/`.
- **Output**: The results are stored in `data/processed/youtube_song_characteristics.csv`.
- **Database Mapping**: Headers map directly to MariaDB `FLOAT`, `INT`, and `TEXT` types.
