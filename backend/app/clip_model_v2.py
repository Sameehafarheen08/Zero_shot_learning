"""
REDESIGNED CLIP Classifier - Final Solution
Loads labels ONCE at startup, generates text embeddings once, optimizes for accuracy
WITH CACHING for fast startup on subsequent runs
"""

from PIL import Image
import os
import torch
import logging
from typing import List, Tuple
import numpy as np
import pickle

logger = logging.getLogger(__name__)

# Global state - loaded once at startup
_model = None
_processor = None
_text_features = None
_labels = None
_device = None

TEMPERATURE = 0.3  # Lower = sharper predictions


def get_device():
    global _device
    if _device is None:
        _device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {_device}")
    return _device


def load_labels():
    """Load labels from single labels.txt file"""
    global _labels
    
    if _labels is not None:
        return _labels
    
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    labels_file = os.path.join(backend_dir, "labels.txt")
    
    try:
        with open(labels_file, 'r') as f:
            labels = [line.strip().lower() for line in f if line.strip()]
        
        # Remove duplicates while preserving order
        seen = set()
        unique_labels = []
        for label in labels:
            if label not in seen:
                seen.add(label)
                unique_labels.append(label)
        
        _labels = unique_labels
        logger.info(f"✅ Loaded {len(unique_labels)} unique labels from labels.txt")
        return unique_labels
    
    except Exception as e:
        logger.error(f"Error loading labels: {e}")
        raise


def load_model():
    """Load CLIP model and processor"""
    global _model, _processor
    
    if _model is not None and _processor is not None:
        return _model, _processor
    
    try:
        logger.info("Loading CLIP ViT-B/32...")
        import clip
        
        device = get_device()
        model, preprocess = clip.load("ViT-B/32", device=device)
        model.eval()
        
        _model = model
        _processor = preprocess
        logger.info("✅ CLIP model loaded successfully")
        return model, preprocess
    
    except Exception as e:
        logger.error(f"Error loading CLIP: {e}")
        raise


def load_text_features():
    """Tokenize all labels and compute text embeddings once at startup
    Uses caching to speed up subsequent startups (~1 second instead of 20 seconds)"""
    global _text_features, _model, _processor, _labels
    
    if _text_features is not None:
        logger.info("Text features already in memory, returning cached version")
        return _text_features
    
    try:
        # Try to load from cache file first
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cache_file = os.path.join(backend_dir, ".embeddings_cache.pkl")
        
        if os.path.exists(cache_file):
            logger.info("Loading text embeddings from cache file...")
            try:
                with open(cache_file, 'rb') as f:
                    cached_data = pickle.load(f)
                    _text_features = cached_data['embeddings'].to(get_device())
                    logger.info(f"✅ Text embeddings loaded from cache: shape {_text_features.shape} (took ~1 second)")
                    return _text_features
            except Exception as e:
                logger.warning(f"Cache load failed: {e}, regenerating...")
        
        # Generate fresh embeddings
        logger.info("Generating text embeddings (ONE TIME)...")
        
        model, _ = load_model()
        labels = load_labels()
        device = get_device()
        
        logger.info(f"Preparing {len(labels)} prompts...")
        prompts = []
        for label in labels:
            if label in ['cat', 'dog', 'cow', 'horse', 'bird', 'fish']:
                prompt = f"a photo of a {label}, animal"
            elif label in ['mobile phone', 'laptop', 'laptop computer', 'keyboard', 'mouse', 'tablet', 'camera', 'headphones', 'television', 'printer', 'remote']:
                prompt = f"a photo of a {label}, electronic device"
            elif any(food in label for food in ['ice cream', 'hamburger', 'pizza', 'rice', 'bread', 'cake', 'chicken', 'fish', 'pasta', 'salad', 'samosa', 'dosa', 'naan', 'chapati', 'paneer', 'dal', 'mutton', 'vegetables', 'steak', 'shrimp', 'tikka', 'tandoori']):
                prompt = f"a photo of {label}, food"
            else:
                prompt = f"a photo of a {label}, object"
            prompts.append(prompt)
        
        logger.info(f"Tokenizing {len(prompts)} prompts...")
        import clip
        text_tokens = clip.tokenize(prompts).to(device)
        
        logger.info("Computing text embeddings...")
        with torch.no_grad():
            text_features = model.encode_text(text_tokens)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)
        
        _text_features = text_features
        
        # Save to cache for next time
        try:
            logger.info("Saving embeddings to cache...")
            with open(cache_file, 'wb') as f:
                pickle.dump({'embeddings': _text_features.cpu()}, f)
            logger.info("✅ Cache saved")
        except Exception as e:
            logger.warning(f"Could not save cache: {e} (non-critical)")
        
        logger.info(f"✅ Text embeddings generated: shape {text_features.shape}")
        return text_features
    
    except Exception as e:
        logger.error(f"Error generating text features: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


def preprocess_image(image_path: str) -> torch.Tensor:
    """
    Strict CLIP preprocessing:
    - Convert to RGB
    - Resize to 224×224
    - Center crop
    - Normalize with CLIP mean/std
    """
    try:
        _, preprocess = load_model()
        
        # Load image
        image = Image.open(image_path).convert("RGB")
        
        # Use CLIP's built-in preprocess
        image_tensor = preprocess(image)
        
        return image_tensor
    
    except Exception as e:
        logger.error(f"Error preprocessing image: {e}")
        raise


def classify(image_path: str, top_k: int = 3) -> List[Tuple[str, float]]:
    """
    Classify image using CACHED text embeddings - FAST!
    Returns top-k predictions
    Automatically initializes if not already done
    """
    try:
        global _text_features, _model, _processor, _labels
        
        device = get_device()
        logger.info(f"Classifying image with top-k={top_k}...")
        
        # Auto-initialize if needed
        if _text_features is None:
            logger.info("Auto-initializing CLIP model...")
            initialize_at_startup()
        
        # Check again after initialization
        if _text_features is None or _model is None:
            logger.error("Failed to initialize CLIP model")
            raise RuntimeError("CLIP model initialization failed")
        
        # Load image
        image = Image.open(image_path).convert('RGB')
        image_input = _processor(image).unsqueeze(0).to(device)
        
        # Encode image (only this part runs at prediction time)
        with torch.no_grad():
            image_features = _model.encode_image(image_input)
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            
            # Use cached text embeddings - SUPER FAST!
            logits = image_features @ _text_features.T
            probs = logits.softmax(dim=-1)[0]
        
        # Get top-k
        top_probs, top_indices = torch.topk(probs, min(top_k, len(_labels)))
        
        results = [
            (_labels[idx.item()], float(prob.item()))
            for prob, idx in zip(top_probs, top_indices)
        ]
        
        top_label, top_conf = results[0]
        logger.info(f"✅ Predicted: {top_label} ({top_conf*100:.1f}%)")
        
        return results
    
    except Exception as e:
        logger.error(f"Classification error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


def initialize_at_startup():
    """Call this at Flask startup to preload everything"""
    try:
        logger.info("=== STARTUP INITIALIZATION ===")
        logger.info("[1] Loading CLIP model...")
        load_model()
        logger.info("[1] ✓ CLIP model loaded")
        
        logger.info("[2] Loading labels...")
        load_labels()
        logger.info("[2] ✓ Labels loaded")
        
        logger.info("[3] Pre-generating text embeddings...")
        result = load_text_features()
        logger.info(f"[3] ✓ Text embeddings loaded: {result.shape if result is not None else 'None'}")
        
        logger.info("=== INITIALIZATION COMPLETE ===")
        return True
    except Exception as e:
        logger.error(f"Startup initialization failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
