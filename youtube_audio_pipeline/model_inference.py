"""
Essentia TensorFlow Model Inference

Provides thread-safe loading and inference for Essentia pretrained models:
- Genre classification (Dortmund) - multi-label genre prediction
- Mood classification (happy/sad/relaxed) - multi-class mood prediction
- Discogs EfficientNet embeddings - 2048-dim audio embeddings

Models are initialized globally at application startup to avoid per-thread overhead.
All inference functions are thread-safe (TensorFlow GIL-protected).
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# Global model instances (lazy-loaded, thread-protected)
_models_lock = threading.Lock()
_GENRE_MODEL: Any = None
_MOOD_MODELS: dict[str, Any] = {}
_EMBEDDING_MODEL: Any = None
_models_initialized = False

# Model paths (relative to this module's directory)
MODELS_DIR = Path(__file__).parent / "models"

# Model registry (files expected in MODELS_DIR)
MODEL_REGISTRY = {
    "genre_dortmund": {
        "pb_file": "genre_dortmund-discogs-effnet-1.pb",
        "metadata_file": "genre_dortmund-discogs-effnet-1_metadata.json",
        "description": "Multi-label genre classification trained on Discogs",
    },
    "mood_acoustic": {
        "pb_file": "mood_acoustic-discogs-effnet-1.pb",
        "metadata_file": "mood_acoustic-discogs-effnet-1_metadata.json",
        "description": "Acoustic/organic vs electronic timbre",
    },
    "mood_aggressive": {
        "pb_file": "mood_aggressive-discogs-effnet-1.pb",
        "metadata_file": "mood_aggressive-discogs-effnet-1_metadata.json",
        "description": "Aggressive/intense mood classification",
    },
    "mood_electronic": {
        "pb_file": "mood_electronic-discogs-effnet-1.pb",
        "metadata_file": "mood_electronic-discogs-effnet-1_metadata.json",
        "description": "Electronic/synthetic sound character",
    },
    "mood_happy": {
        "pb_file": "mood_happy-discogs-effnet-1.pb",
        "metadata_file": "mood_happy-discogs-effnet-1_metadata.json",
        "description": "Happy/positive mood classification",
    },
    "mood_party": {
        "pb_file": "mood_party-discogs-effnet-1.pb",
        "metadata_file": "mood_party-discogs-effnet-1_metadata.json",
        "description": "Party/energetic mood classification",
    },
    "mood_relaxed": {
        "pb_file": "mood_relaxed-discogs-effnet-1.pb",
        "metadata_file": "mood_relaxed-discogs-effnet-1_metadata.json",
        "description": "Relaxed/calm mood classification",
    },
    "mood_sad": {
        "pb_file": "mood_sad-discogs-effnet-1.pb",
        "metadata_file": "mood_sad-discogs-effnet-1_metadata.json",
        "description": "Sad/melancholic mood classification",
    },
    "discogs_effnet": {
        "pb_file": "discogs-effnet-1.pb",
        "metadata_file": "discogs-effnet-1_metadata.json",
        "description": "2048-dim audio embedding feature extractor",
    },
}


def _load_pb_model(pb_path: Path) -> Any:
    """Load a TensorFlow SavedModel from .pb file."""
    try:
        import tensorflow as tf
        model = tf.saved_model.load(str(pb_path))
        return model
    except Exception as e:
        logger.warning(f"Failed to load model {pb_path.name}: {e}")
        return None


def _parse_metadata_json(json_path: Path) -> dict[str, Any]:
    """Parse Essentia model metadata JSON."""
    try:
        with open(json_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load metadata {json_path.name}: {e}")
        return {}


def _ensure_models_loaded() -> None:
    """Lazy-load all models on first inference call (thread-safe)."""
    global _GENRE_MODEL, _MOOD_MODELS, _EMBEDDING_MODEL, _models_initialized

    if _models_initialized:
        return

    with _models_lock:
        if _models_initialized:  # Double-check locking
            return

        logger.info(f"Loading Essentia models from {MODELS_DIR}")

        # Load genre model
        genre_pb = MODELS_DIR / MODEL_REGISTRY["genre_dortmund"]["pb_file"]
        if genre_pb.exists():
            _GENRE_MODEL = _load_pb_model(genre_pb)
            if _GENRE_MODEL:
                logger.info("✓ Genre model loaded")
        else:
            logger.warning(f"Genre model not found at {genre_pb}")

        # Load mood models (7 total)
        for mood in ["acoustic", "aggressive", "electronic", "happy", "party", "relaxed", "sad"]:
            key = f"mood_{mood}"
            pb_file = MODELS_DIR / MODEL_REGISTRY[key]["pb_file"]
            if pb_file.exists():
                model = _load_pb_model(pb_file)
                if model:
                    _MOOD_MODELS[mood] = model
                    logger.info(f"✓ Mood ({mood}) model loaded")
            else:
                logger.warning(f"Mood ({mood}) model not found at {pb_file}")

        # Load embedding model
        embed_pb = MODELS_DIR / MODEL_REGISTRY["discogs_effnet"]["pb_file"]
        if embed_pb.exists():
            _EMBEDDING_MODEL = _load_pb_model(embed_pb)
            if _EMBEDDING_MODEL:
                logger.info("✓ Embedding model loaded")
        else:
            logger.warning(f"Embedding model not found at {embed_pb}")

        _models_initialized = True


def initialize_models_globally() -> None:
    """
    Initialize all models at application startup (called once by main.py).
    This is separate from _ensure_models_loaded() to allow explicit
    early initialization with user feedback.
    """
    logger.info("Pre-loading Essentia models...")
    _ensure_models_loaded()
    if _GENRE_MODEL and len(_MOOD_MODELS) == 3 and _EMBEDDING_MODEL:
        logger.info("✓ All models loaded successfully")
    else:
        logger.warning("⚠ Some models failed to load; pipeline will skip those features")


def run_genre_inference(audio: np.ndarray, sr: int = 44100) -> dict[str, float]:
    """
    Run genre classification inference.

    Args:
        audio: Mono audio waveform (numpy array, float32)
        sr: Sample rate (default 44100)

    Returns:
        Dict mapping genre labels to confidence scores [0-1].
        Empty dict if inference fails or model unavailable.
    """
    _ensure_models_loaded()

    if _GENRE_MODEL is None:
        logger.debug("Genre model not available, skipping genre inference")
        return {}

    try:
        # Prepare audio for inference (model expects specific shape/format)
        # Essentia TensorFlow models typically expect [1, num_samples] or [1, time_steps, features]
        audio_input = np.expand_dims(audio, axis=0).astype(np.float32)

        # Run inference through the model's signature (saved_model)
        # Typically: model.signatures['serving_default'](tensor) → dict with output keys
        infer = _GENRE_MODEL.signatures["serving_default"]
        output = infer(tf.constant(audio_input))

        # Extract probabilities (key depends on model; typically 'predictions' or 'output')
        # For Essentia models: output keys are model-specific; need metadata to map
        predictions = {}
        for key, value in output.items():
            if "predictions" in key.lower() or "scores" in key.lower():
                probs = value.numpy().flatten()
                # Map to class labels (load from metadata)
                metadata = _parse_metadata_json(
                    MODELS_DIR / MODEL_REGISTRY["genre_dortmund"]["metadata_file"]
                )
                labels = metadata.get("classes", [f"Genre_{i}" for i in range(len(probs))])
                predictions = {label: float(prob) for label, prob in zip(labels, probs)}
                break

        return predictions

    except Exception as e:
        logger.debug(f"Genre inference failed: {e}")
        return {}


def run_mood_inference(audio: np.ndarray, sr: int = 44100) -> dict[str, float]:
    """
    Run multi-class mood inference (happy, sad, relaxed).

    Args:
        audio: Mono audio waveform (numpy array, float32)
        sr: Sample rate (default 44100)

    Returns:
        Dict with keys 'happy', 'sad', 'relaxed' mapped to confidence scores [0-1].
        Empty dict if inference fails or models unavailable.
    """
    _ensure_models_loaded()

    if len(_MOOD_MODELS) == 0:
        logger.debug("Mood models not available, skipping mood inference")
        return {}

    mood_scores = {}

    for mood, model in _MOOD_MODELS.items():
        try:
            if model is None:
                continue

            audio_input = np.expand_dims(audio, axis=0).astype(np.float32)
            import tensorflow as tf

            infer = model.signatures["serving_default"]
            output = infer(tf.constant(audio_input))

            # Extract confidence (typically binary classifier output)
            for key, value in output.items():
                if "predictions" in key.lower() or "scores" in key.lower():
                    prob = float(value.numpy().flatten()[0])
                    mood_scores[mood] = prob
                    break

        except Exception as e:
            logger.debug(f"Mood ({mood}) inference failed: {e}")

    return mood_scores


def run_embedding_inference(audio: np.ndarray, sr: int = 44100) -> np.ndarray | None:
    """
    Extract 2048-dim audio embedding using Discogs EfficientNet model.

    Args:
        audio: Mono audio waveform (numpy array, float32)
        sr: Sample rate (default 44100)

    Returns:
        2048-dimensional numpy array (float32) or None if inference fails.
    """
    _ensure_models_loaded()

    if _EMBEDDING_MODEL is None:
        logger.debug("Embedding model not available, skipping embedding inference")
        return None

    try:
        audio_input = np.expand_dims(audio, axis=0).astype(np.float32)
        import tensorflow as tf

        infer = _EMBEDDING_MODEL.signatures["serving_default"]
        output = infer(tf.constant(audio_input))

        # Extract embedding (typically 2048-dim vector)
        for key, value in output.items():
            if "embedding" in key.lower() or "features" in key.lower():
                embedding = value.numpy().flatten()
                return embedding

        # Fallback: if no explicit embedding key, grab first output
        first_output = next(iter(output.values()))
        embedding = first_output.numpy().flatten()
        return embedding

    except Exception as e:
        logger.debug(f"Embedding inference failed: {e}")
        return None


# Lazy import TensorFlow at module level to avoid errors when models aren't loaded
import tensorflow as tf
