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

## 2. Technical Enhancements (v1.2.0)
To support these models and prepare for database ingestion and ML training, the following updates were made:

- **Fully Flattened Data Structure**: Optimized for MariaDB and ML consumption by expanding nested data into **133 individual columns**:
    - **15 Parent Genre Columns** (e.g., `Genre_Rock`, `Genre_Electronic`).
    - **56 Mood/Theme Columns** (e.g., `Mood_happy`, `Mood_energetic`, `Mood_industrial`).
    - **13 MFCC Columns** (`MFCC_1` to `MFCC_13`).
    - **12 HPCP Columns** (`HPCP_1` to `HPCP_12`).
- **Robust Spectral Averaging**: Refactored `analyzer.py` to calculate spectral features (BPM, Centroid, MFCC) by **averaging across the entire song** (sampling every ~1s) instead of just the first frame. This ensures representative data and eliminates issues with silence at the start of tracks.
- **Multi-task Inference**: Transitioned to a multi-task architecture for improved prediction efficiency.
- **WAV Conversion**: Automatic conversion to WAV ensuring 100% Essentia compatibility and avoiding "Unsupported Codec" crashes.
- **Enriched Metadata**: Captured rich metrics including `ViewCount`, `LikeCount`, `Uploader`, and `UploadDate`.
- **Simplified JSON**: `GenreProbsJson` truncated to top 5 subgenres to reduce bloat; others fully flattened.

## 3. Validation Results
The pipeline has been validated across a diversified set of genres (Pop, Classical, Metal), producing a "wide" structure optimized for both SQL filtering and downstream semantic model training.

### Genre-Specific Metric Samples (Verified):
| Track | GenreTopParent | BPM | SpectralCentroid | Mood_relaxing |
| :--- | :--- | :--- | :--- | :--- |
| Enter Sandman (Metal) | Rock | 123.6 | 0.171 | 0.007 |
| Never Gonna Give You Up | Electronic | 113.2 | 0.158 | 0.012 |
| Clair de lune (Classical) | Classical | 103.3 | 0.034 | 0.145 |

## 4. Maintenance & Versioning
- **Persistence**: Models and metadata are stored in `youtube_audio_pipeline/models/`.
- **Versioning**: Output files are versioned (e.g., `youtube_song_characteristics_v1.2.0.csv`) to track architectural iterations.
- **Database Mapping**: Headers map directly to MariaDB `FLOAT`, `INT`, and `TEXT` types.
