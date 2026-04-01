from __future__ import annotations

import json
import logging
import os
import subprocess
import uuid
from pathlib import Path

import essentia
import essentia.standard as es
import numpy as np
import pandas as pd

from youtube_audio_pipeline import model_inference

logger = logging.getLogger(__name__)

# High-level parent genres from Discogs taxonomy
FLATTENED_GENRES = [
    "Blues", "Brass & Military", "Children's", "Classical", "Electronic", 
    "Folk, World, & Country", "Funk / Soul", "Hip Hop", "Jazz", "Latin", 
    "Non-Music", "Pop", "Reggae", "Rock", "Stage & Screen"
]

# Full 56 mood/theme tags from MTG-Jamendo
ALL_MOODS = [
    "action", "adventure", "advertising", "background", "ballad", "calm", "children", 
    "christmas", "commercial", "cool", "corporate", "dark", "deep", "documentary", 
    "drama", "dramatic", "dream", "emotional", "energetic", "epic", "fast", "film", 
    "fun", "funny", "game", "groovy", "happy", "heavy", "holiday", "hopeful", 
    "inspiring", "love", "meditative", "melancholic", "melodic", "motivational", 
    "movie", "nature", "party", "positive", "powerful", "relaxing", "retro", 
    "romantic", "sad", "sexy", "slow", "soft", "soundscape", "space", "sport", 
    "summer", "trailer", "travel", "upbeat", "uplifting"
]

def analyze_and_discard(
    filepath: Path,
    metadata: dict,
    skip_models: bool = False,
) -> dict | None:
    """
    Extracts audio characteristics and ML features from a local audio file,
    and returns them as a dictionary. The caller is responsible for cleanup.
    """
    url = metadata.get("url", "Unknown URL")
    title = metadata.get("title", "Unknown Title")
    
    try:
        # 1. Extract audio characteristics using Essentia
        sample_rate = 44100
        loader = es.MonoLoader(filename=str(filepath), sampleRate=sample_rate)
        audio = loader()

        # Rhythm
        rhythm_extractor = es.RhythmExtractor2013(method="multifeature")
        bpm, beats, beats_confidence, _, _ = rhythm_extractor(audio)

        # Key
        key_extractor = es.KeyExtractor()
        key, scale, strength = key_extractor(audio)

        # Loudness
        loudness_extractor = es.Loudness()
        loudness = loudness_extractor(audio)

        duration = len(audio) / sample_rate
        rms_energy = np.sqrt(np.mean(audio**2))

        # Proxy for onsets
        onset_count = len(beats)
        onset_rate = onset_count / duration if duration > 0 else 0

        # High-level features
        danceability_extractor = es.Danceability()
        danceability, _ = danceability_extractor(audio)
        valence = 0.0 

        # 2. Extract ML Model Features
        mood_theme_flat = {f"Mood_{m}": 0.0 for m in ALL_MOODS}
        genre_parent_flat = {f"Genre_{g.replace(' ', '').replace(',', '').replace('&', 'And').replace('/', 'Or')}": 0.0 for g in FLATTENED_GENRES}
        
        genre_top_label, genre_top_confidence = "Unknown", 0.0
        genre_top_parent = "Unknown"
        genre_probs_json = "{}"
        top_moods_str, top_inst_str = "", ""
        voice_inst_label, gender_label, timbre_label = "unknown", "unknown", "unknown"
        embedding_json = "[]"

        if not skip_models:
            full_res = model_inference.run_full_inference(audio)
            genre_probs = full_res["genre"]
            if genre_probs:
                genre_top_label, genre_top_confidence = max(genre_probs.items(), key=lambda x: x[1])
                parent_scores = {}
                for label, score in genre_probs.items():
                    parent = label.split("---")[0]
                    parent_scores[parent] = parent_scores.get(parent, 0.0) + score
                genre_top_parent = max(parent_scores.items(), key=lambda x: x[1])[0]
                for g in FLATTENED_GENRES:
                    col_name = f"Genre_{g.replace(' ', '').replace(',', '').replace('&', 'And').replace('/', 'Or')}"
                    if g in parent_scores: genre_parent_flat[col_name] = float(parent_scores[g])
                top_5_specific = dict(sorted(genre_probs.items(), key=lambda x: x[1], reverse=True)[:5])
                genre_probs_json = json.dumps(top_5_specific)
            
            mood_theme_probs = full_res["mood_theme"]
            top_moods = sorted(mood_theme_probs.items(), key=lambda x: x[1], reverse=True)[:5]
            top_moods_str = " | ".join([f"{m} ({s:.2f})" for m, s in top_moods])
            for m in ALL_MOODS:
                if m in mood_theme_probs: mood_theme_flat[f"Mood_{m}"] = float(mood_theme_probs[m])
            
            inst_probs = full_res["instrumentation"]
            top_inst = sorted(inst_probs.items(), key=lambda x: x[1], reverse=True)[:3]
            top_inst_str = " | ".join([f"{i} ({s:.2f})" for i, s in top_inst])
            
            voice_res = full_res["voice_instrumental"]
            voice_inst_label = max(voice_res.items(), key=lambda x: x[1])[0] if voice_res else "unknown"
            gender_res = full_res["voice_gender"]
            gender_label = max(gender_res.items(), key=lambda x: x[1])[0] if gender_res else "unknown"
            timbre_res = full_res["timbre"]
            timbre_label = max(timbre_res.items(), key=lambda x: x[1])[0] if timbre_res else "unknown"
            
            embedding = full_res["embedding"]
            embedding_json = json.dumps(embedding.tolist()) if embedding is not None else "[]"

        # 3. Spectral Features (Robust Extraction)
        mfcc_flat = {f"MFCC_{i+1}": 0.0 for i in range(13)}
        hpcp_flat = {f"HPCP_{i+1}": 0.0 for i in range(12)}
        centroids, rolloffs, flatness = [], [], []
        mfccs = []
        pitches = []

        try:
            w = es.Windowing(type="hann")
            fft = es.FFT()
            centroid_alg = es.Centroid()
            rolloff_alg = es.RollOff()
            flatness_alg = es.Flatness()
            mfcc_alg = es.MFCC(numberCoefficients=13)
            pitch_alg = es.PitchYinFFT()
            
            # Frame generator loop
            for frame in es.FrameGenerator(audio, frameSize=2048, hopSize=sample_rate):
                spec = fft(w(frame))
                mag = np.abs(spec).astype(np.float32)
                
                # Granular extraction to avoid whole-block failure
                try: centroids.append(centroid_alg(mag))
                except: pass
                
                try: rolloffs.append(rolloff_alg(mag))
                except: pass
                
                try: flatness.append(flatness_alg(mag))
                except: pass
                
                try:
                    _, m_coeffs = mfcc_alg(mag)
                    mfccs.append(m_coeffs)
                except: pass
                
                try:
                    p, c = pitch_alg(spec)
                    if c > 0.5: pitches.append(p)
                except: pass

            # Averages
            spec_centroid = float(np.mean(centroids)) if centroids else 0.0
            spec_rolloff = float(np.mean(rolloffs)) if rolloffs else 0.0
            spec_flatness = float(np.mean(flatness)) if flatness else 0.0
            pitch_mean = float(np.mean(pitches)) if pitches else 0.0
            pitch_std = float(np.std(pitches)) if pitches else 0.0
            
            if mfccs:
                avg_mfcc = np.mean(mfccs, axis=0)
                for i, val in enumerate(avg_mfcc): mfcc_flat[f"MFCC_{i+1}"] = float(val)
                
        except Exception as e:
            logger.debug(f"Averaged spectral extraction failed: {e}")
            spec_centroid, spec_rolloff, spec_flatness = 0.0, 0.0, 0.0
            pitch_mean, pitch_std = 0.0, 0.0

        zcr = float(es.ZeroCrossingRate()(audio))

        # 4. Result
        result = {
            "URL": url,
            "Title": title,
            "YouTubeID": metadata.get("id", "Unknown"),
            "Uploader": metadata.get("uploader", "Unknown"),
            "Channel": metadata.get("channel", "Unknown"),
            "UploadDate": metadata.get("upload_date", "Unknown"),
            "ViewCount": int(metadata.get("view_count", 0)),
            "LikeCount": int(metadata.get("like_count", 0)),
            "BPM": float(bpm),
            "Key": f"{key} {scale}",
            "KeyStrength": float(strength),
            "Loudness": float(loudness),
            "DurationSeconds": float(duration),
            "RmsEnergy": float(rms_energy),
            "BeatConfidence": float(beats_confidence),
            "BeatCount": int(len(beats)),
            "OnsetRate": float(onset_rate),
            "OnsetCount": int(onset_count),
            "Danceability": float(danceability),
            "Valence": float(valence),
            "SpectralCentroidHz": spec_centroid,
            "SpectralRolloffHz": spec_rolloff,
            "SpectralFlatness": spec_flatness,
            "PitchMeanHz": pitch_mean,
            "PitchStdHz": pitch_std,
            "ZeroCrossingRate": zcr,
            "GenreTopLabel": genre_top_label,
            "GenreTopParent": genre_top_parent,
            "GenreTopConfidence": genre_top_confidence,
            "MoodThemeSummary": top_moods_str,
            "InstrumentationSummary": top_inst_str,
            "VoiceInstrumental": voice_inst_label,
            "VoiceGender": gender_label,
            "Timbre": timbre_label,
        }
        
        result.update(mood_theme_flat)
        result.update(genre_parent_flat)
        result.update(mfcc_flat)
        result.update(hpcp_flat)
        
        result["GenreProbsJson"] = genre_probs_json
        result["DiscogsEmbeddingJson"] = embedding_json

        return result

    except Exception as e:
        logger.error(f"Analysis failed for {url}: {e}")
        return None


def save_to_dataframe(results_list: list[dict], output_csv: str) -> None:
    if not results_list: return
    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(results_list)
    if output_path.exists():
        df.to_csv(output_path, mode="a", header=False, index=False)
    else:
        df.to_csv(output_path, index=False)
