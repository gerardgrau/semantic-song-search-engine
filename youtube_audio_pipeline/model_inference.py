"""
Essentia TensorFlow Model Inference (High-Performance with Batching)

Optimized for high-throughput with Singleton Session Management and 
multi-track vectorized batching support.
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any

import numpy as np
import tensorflow as tf
import essentia.standard as es

logger = logging.getLogger(__name__)

# --- FIX: Enable Dynamic GPU Memory Growth at Import Time ---
try:
    gpus = tf.config.experimental.list_physical_devices('GPU')
    if gpus:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
except Exception as e:
    pass # Already set or not available
# ------------------------------------------------------------

# Global model instances
_models_lock = threading.Lock()
_PREPROCESSOR: Any = None
_BACKBONE_SESS: tf.compat.v1.Session = None
_HEAD_SESSIONS: dict[str, tuple[tf.compat.v1.Session, str, str, list[str]]] = {}
_METADATA: dict[str, Any] = {}
_models_initialized = False

MODELS_DIR = Path(__file__).parent / "models"

MODEL_REGISTRY = {
    "backbone": "discogs-effnet-1.pb",
    "genre": "genre_discogs400-discogs-effnet-1.pb",
    "mood_theme": "mtg_jamendo_moodtheme-discogs-effnet-1.pb",
    "instrumentation": "mtg_jamendo_instrument-discogs-effnet-1.pb",
    "voice_instrumental": "voice_instrumental-discogs-effnet-1.pb",
    "voice_gender": "voice_gender-discogs-effnet-1.pb",
    "timbre": "timbre-discogs-effnet-1.pb",
}

def _load_frozen_graph(pb_path: Path) -> tf.GraphDef:
    with tf.io.gfile.GFile(str(pb_path), "rb") as f:
        graph_def = tf.compat.v1.GraphDef()
        graph_def.ParseFromString(f.read())
    return graph_def

def _find_tensors(graph: tf.Graph):
    placeholders = [t.name for op in graph.get_operations() if op.type == "Placeholder" for t in op.outputs]
    primary_input = ""
    for p in placeholders:
        if "mel" in p.lower() or "input" in p.lower() or "placeholder" in p.lower():
            primary_input = p
            break
    if not primary_input and placeholders:
        primary_input = placeholders[0]
        
    outputs = []
    for op in graph.get_operations():
        for t in op.outputs:
            if t.dtype in [tf.float32, tf.float64]:
                if any(x in t.name for x in ["PartitionedCall", "Softmax", "Sigmoid"]):
                    outputs.append(t.name)
    
    primary_output = ""
    if outputs:
        pcalls_1 = [o for o in outputs if "PartitionedCall" in o and o.endswith(":1")]
        primary_output = pcalls_1[-1] if pcalls_1 else outputs[-1]
    
    return primary_input, primary_output, placeholders

def _ensure_models_loaded() -> None:
    global _PREPROCESSOR, _BACKBONE_SESS, _HEAD_SESSIONS, _METADATA, _models_initialized

    if _models_initialized: return

    with _models_lock:
        if _models_initialized: return

        # --- FIX: Enable Dynamic GPU Memory Growth ---
        # This prevents cuDNN initialization errors on virtualized GPUs (L4)
        gpus = tf.config.experimental.list_physical_devices('GPU')
        if gpus:
            try:
                for gpu in gpus:
                    tf.config.experimental.set_memory_growth(gpu, True)
            except RuntimeError as e:
                logger.warning(f"GPU Memory Growth config failed: {e}")
        # ----------------------------------------------

        logger.info(f"Initializing High-Performance Inference Engine from {MODELS_DIR}")
        _PREPROCESSOR = es.TensorflowInputMusiCNN()
        
        for key, filename in MODEL_REGISTRY.items():
            path = MODELS_DIR / filename
            if path.exists():
                graph_def = _load_frozen_graph(path)
                graph = tf.Graph()
                with graph.as_default():
                    tf.import_graph_def(graph_def, name="model")
                    inp, out, phelds = _find_tensors(graph)
                    sess = tf.compat.v1.Session(graph=graph)
                    
                    if key == "backbone":
                        _BACKBONE_SESS = sess
                    else:
                        _HEAD_SESSIONS[key] = (sess, inp, out, phelds)
                
                meta_path = path.with_name(filename.replace(".pb", "_metadata.json"))
                if meta_path.exists():
                    with open(meta_path, "r") as f:
                        _METADATA[key] = json.load(f)
                logger.info(f"✓ {key} model initialized")

        _models_initialized = True

def initialize_models_globally() -> None:
    _ensure_models_loaded()

def _run_sess(sess: tf.compat.v1.Session, inp_name: str, out_name: str, phelds: list[str], val: np.ndarray) -> np.ndarray:
    graph = sess.graph
    feed_dict = {inp_name: val}
    for p in phelds:
        if p != inp_name:
            tensor = graph.get_tensor_by_name(p)
            if tensor.dtype == tf.string: feed_dict[p] = b""
            elif tensor.dtype in [tf.float32, tf.float64]: feed_dict[p] = 0.0
            else: feed_dict[p] = 0
    return sess.run(out_name, feed_dict=feed_dict)

def preprocess_audio(audio_16k: np.ndarray) -> np.ndarray:
    """Converts 16kHz audio to mel patches [n, 128, 96]."""
    _ensure_models_loaded()
    mel_frames = [_PREPROCESSOR(f).flatten() for f in es.FrameGenerator(audio_16k, frameSize=512, hopSize=256, startFromZero=True)]
    if not mel_frames: return np.array([])
    mel_data = np.array(mel_frames)
    
    patch_size, hop_size = 128, 64
    patches = [mel_data[i:i+patch_size] for i in range(0, len(mel_data) - patch_size + 1, hop_size)]
    if not patches:
        patches = [np.pad(mel_data, ((0, patch_size - len(mel_data)), (0, 0)), mode='constant')]
    return np.array(patches)

def run_full_inference(audio_16k: np.ndarray) -> dict[str, Any]:
    """Single-track high-performance inference."""
    patches = preprocess_audio(audio_16k)
    if patches.size == 0: return {k: {} for k in MODEL_REGISTRY if k != "backbone"}
    
    # Wrap patches into a list format for batch runner
    batch_results = run_batch_inference([patches])
    return batch_results[0]

def run_batch_inference(list_of_patches: list[np.ndarray]) -> list[dict[str, Any]]:
    """
    Vectorized batch inference across multiple tracks.
    Efficiently packs patches from all tracks into batches of 64.
    """
    _ensure_models_loaded()
    if not list_of_patches: return []
    if _BACKBONE_SESS is None: return [{k: {} for k in MODEL_REGISTRY if k != "backbone"} for _ in list_of_patches]

    # 1. Flatten all patches into one big list and keep track of indices
    all_patches = []
    track_patch_ranges = []
    current_idx = 0
    for patches in list_of_patches:
        count = len(patches)
        all_patches.extend(patches)
        track_patch_ranges.append((current_idx, current_idx + count))
        current_idx += count

    # 2. Backbone Inference (Batch Size 64)
    batch_size = 64
    all_embs = []
    inp_b, out_b, phelds_b = _find_tensors(_BACKBONE_SESS.graph)
    
    for i in range(0, len(all_patches), batch_size):
        batch = all_patches[i:i+batch_size]
        actual_len = len(batch)
        if actual_len < batch_size:
            # Pad batch with copies of the last patch
            batch = list(batch) # ensure list
            for _ in range(batch_size - actual_len): batch.append(batch[-1])
        
        embs = _run_sess(_BACKBONE_SESS, inp_b, out_b, phelds_b, np.array(batch))
        all_embs.append(embs[:actual_len])
    
    combined_embs = np.concatenate(all_embs, axis=0)

    # 3. Aggregate Embeddings per Track and Run Heads
    final_results = []
    for start, end in track_patch_ranges:
        track_patches_embs = combined_embs[start:end]
        track_embedding = np.mean(track_patches_embs, axis=0, keepdims=True)
        
        res: dict[str, Any] = {"embedding": track_embedding.flatten()}
        
        # Heads Inference (one track at a time for now, as heads are extremely fast)
        for key, (sess, inp, out, phelds) in _HEAD_SESSIONS.items():
            logits = _run_sess(sess, inp, out, phelds, track_embedding)
            probs = logits.flatten()
            labels = _METADATA.get(key, {}).get("classes", [])
            if labels:
                res[key] = {labels[i]: float(probs[i]) for i in range(min(len(labels), len(probs)))}
            else:
                res[key] = {"score": float(probs[0])}
        
        final_results.append(res)

    return final_results
