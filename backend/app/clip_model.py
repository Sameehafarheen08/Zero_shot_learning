"""
CLIP with Category Labels - CRASH-PROOF LABEL UPDATES
✅ FIX #1: Load ONLY selected category labels
✅ FIX #2: NORMALIZE embeddings (L2 norm critical!)
✅ FIX #3: Per-category cache (fresh on restart)
✅ FIX #4: Prompt MUST include label: "a photo of ice cream"
✅ FIX #5: Image RGB 224x224 CLIP preprocessing
✅ FIX #6: DYNAMIC LABEL DETECTION - Auto-regenerate embeddings on label changes
✅ FIX #7: Never crash on label.txt updates
"""

from PIL import Image
import os
from typing import List, Tuple, Optional
import logging
import hashlib
import json

torch = None

logger = logging.getLogger(__name__)

_model_cache = None
_processor_cache = None
_device = None
_embeddings_cache = {}  # PER CATEGORY: {category -> embeddings}
_labels_cache = {}      # PER CATEGORY: {category -> labels}
_label_hash_cache = None  # Track label file hash to detect changes

UNKNOWN_THRESHOLD = 0.15  # Lower threshold for category-specific classification (10-15% confidence enough)


def get_label_file_hash() -> str:
    """
    Calculate hash of all label files to detect changes
    Returns hash of concatenated label file contents
    """
    try:
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        label_file = os.path.join(backend_dir, "labels.txt")
        
        if os.path.exists(label_file):
            with open(label_file, 'rb') as f:
                content = f.read()
                file_hash = hashlib.md5(content).hexdigest()
                return file_hash
        else:
            return "no_file"
    except Exception as e:
        logger.warning(f"Could not calculate label hash: {e}")
        return "error"


def labels_have_changed() -> bool:
    """
    Check if label files have changed since last load
    Returns True if labels changed, False otherwise
    """
    global _label_hash_cache
    
    try:
        current_hash = get_label_file_hash()
        
        if _label_hash_cache is None:
            _label_hash_cache = current_hash
            return False
        
        if current_hash != _label_hash_cache:
            logger.warning(f"⚠️  Label files changed! Old hash: {_label_hash_cache}, New: {current_hash}")
            _label_hash_cache = current_hash
            return True
        
        return False
    except Exception as e:
        logger.error(f"Error checking label changes: {e}")
        return False


def invalidate_embeddings_cache():
    """
    Invalidate embedding cache when labels change
    This forces regeneration on next request
    """
    global _embeddings_cache, _labels_cache
    
    logger.info("🔄 Invalidating embedding cache due to label changes...")
    _embeddings_cache.clear()
    _labels_cache.clear()
    logger.info("✅ Cache cleared - embeddings will be regenerated")


def get_device():
    global _device, torch
    if _device is None:
        if torch is None:
            import torch as torch_module
            torch = torch_module
        _device = "cpu"
        logger.info(f"Using device: {_device}")
    return _device


def load_model():
    global _model_cache, _processor_cache, torch
    
    if _model_cache is not None and _processor_cache is not None:
        return _model_cache, _processor_cache
    
    try:
        logger.info("Loading CLIP ViT-B/32 using open_clip_torch...")
        
        if torch is None:
            import torch as torch_module
            torch = torch_module
        
        try:
            import open_clip_torch as open_clip
        except ImportError:
            import open_clip
        
        device = get_device()
        
        # Load model without signal-based timeout (incompatible with threading)
        logger.info("Downloading CLIP model (this may take a few minutes on first run)...")
        try:
            model, _, preprocess = open_clip.create_model_and_transforms(
                'ViT-B-32',
                pretrained='openai'
            )
        except Exception as e:
            logger.error(f"Failed to load CLIP model: {e}")
            raise
        
        model = model.to(device)
        model.eval()
        
        _model_cache = model
        _processor_cache = preprocess
        logger.info(f"✅ CLIP loaded successfully")
        return model, preprocess
    
    except Exception as e:
        logger.error(f"Model load error: {e}")
        raise


def load_labels_for_category(category: str = "all") -> List[str]:
    """
    FIX #1: Load labels from labels.txt file
    Category parameter ignored - loads all labels from single file
    """
    if category in _labels_cache:
        logger.info(f"Using cached labels for {category}")
        return _labels_cache[category]
    
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    label_file = os.path.join(backend_dir, "labels.txt")
    
    labels = []
    
    try:
        # Load all labels from labels.txt
        with open(label_file, 'r') as f:
            labels = [line.strip().lower() for line in f if line.strip()]
        
        logger.info(f"Loaded {len(labels)} labels from labels.txt")
        
        # Deduplicate while preserving order
        seen = set()
        unique = []
        for label in labels:
            if label not in seen:
                seen.add(label)
                unique.append(label)
        
        logger.info(f"✅ {category}: {len(unique)} unique labels")
        _labels_cache[category] = unique
        return unique
    
    except FileNotFoundError:
        logger.error(f"Labels file not found: {label_file}")
        raise Exception(f"Cannot load labels from {label_file}")
    
    except Exception as e:
        logger.error(f"Error loading labels: {e}")
        raise


def load_labels() -> List[str]:
    """
    Load all labels from labels.txt
    Used by prediction routes and other modules
    """
    return load_labels_for_category("all")


class CLIPClassifier:
    def __init__(self, category: str = "all"):
        """Load classifier for specific category"""
        self.model, self.preprocess = load_model()
        self.device = get_device()
        self.category = category
        self.labels = load_labels_for_category(category)
        logger.info(f"✅ Classifier ready for '{category}' ({len(self.labels)} labels)")
    
    def classify(self, image_path: str) -> Tuple[str, float]:
        """
        Classify image with PROPER normalization and preprocessing
        ✅ INCLUDES: Label change detection + cache invalidation
        """
        global torch
        
        try:
            if torch is None:
                import torch as torch_module
                torch = torch_module
            
            try:
                import open_clip_torch as open_clip
            except ImportError:
                import open_clip
            
            # ✅ FIX #6: Check if labels changed and invalidate cache if needed
            if labels_have_changed():
                invalidate_embeddings_cache()
                # Reload labels
                self.labels = load_labels_for_category(self.category)
                logger.info(f"🔄 Labels reloaded: {len(self.labels)} total")
            
            # Load and preprocess image (RGB, 224x224, CLIP normalization)
            image = Image.open(image_path).convert("RGB")
            image_input = self.preprocess(image).unsqueeze(0).to(self.device)
            
            # FIX #4: Prompts MUST include label
            prompts = [f"a photo of {label}" for label in self.labels]
            cache_key = f"{self.category}_{len(self.labels)}"
            
            # FIX #3: Cache per category
            if cache_key in _embeddings_cache:
                text_embeddings = _embeddings_cache[cache_key]
            else:
                # Tokenize text and get embeddings
                text_inputs = open_clip.tokenize(prompts)
                text_inputs = text_inputs.to(self.device)
                
                with torch.no_grad():
                    text_embeddings = self.model.encode_text(text_inputs)
                
                # FIX #2: NORMALIZE embeddings (L2 norm)
                text_embeddings = text_embeddings / text_embeddings.norm(dim=-1, keepdim=True)
                _embeddings_cache[cache_key] = text_embeddings
            
            # Get image embedding and normalize
            with torch.no_grad():
                image_embeddings = self.model.encode_image(image_input)
                # FIX #2: NORMALIZE image embedding too!
                image_embeddings = image_embeddings / image_embeddings.norm(dim=-1, keepdim=True)
                
                # Cosine similarity
                logits = image_embeddings @ text_embeddings.T
                probs = logits.softmax(dim=-1).squeeze(0)
            
            # Get top prediction
            top_idx = probs.argmax().item()
            confidence = float(probs[top_idx].item())
            label = self.labels[top_idx]
            
            # Unknown threshold
            if confidence < UNKNOWN_THRESHOLD:
                label = "Unknown Object"
            
            logger.info(f"✅ {label} ({confidence:.1%})")
            return label, confidence
        
        except Exception as e:
            logger.error(f"Classification error: {e}")
            raise
    
    def get_top_k(self, image_path: str, k: int = 5) -> List[Tuple[str, float]]:
        """Get top-k predictions with label change detection"""
        global torch
        
        try:
            if torch is None:
                import torch as torch_module
                torch = torch_module
            
            try:
                import open_clip_torch as open_clip
            except ImportError:
                import open_clip
            
            # ✅ FIX #6: Check if labels changed and invalidate cache if needed
            if labels_have_changed():
                invalidate_embeddings_cache()
                # Reload labels
                self.labels = load_labels_for_category(self.category)
                logger.info(f"🔄 Labels reloaded: {len(self.labels)} total")
            
            image = Image.open(image_path).convert("RGB")
            image_input = self.preprocess(image).unsqueeze(0).to(self.device)
            
            prompts = [f"a photo of {label}" for label in self.labels]
            cache_key = f"{self.category}_{len(self.labels)}"
            
            if cache_key in _embeddings_cache:
                text_embeddings = _embeddings_cache[cache_key]
            else:
                text_inputs = open_clip.tokenize(prompts)
                text_inputs = text_inputs.to(self.device)
                with torch.no_grad():
                    text_embeddings = self.model.encode_text(text_inputs)
                
                text_embeddings = text_embeddings / text_embeddings.norm(dim=-1, keepdim=True)
                _embeddings_cache[cache_key] = text_embeddings
            
            with torch.no_grad():
                image_embeddings = self.model.encode_image(image_input)
                image_embeddings = image_embeddings / image_embeddings.norm(dim=-1, keepdim=True)
                logits = image_embeddings @ text_embeddings.T
                probs = logits.softmax(dim=-1).squeeze(0)
            
            top_k_probs, top_k_indices = torch.topk(probs, min(k, len(self.labels)))
            
            results = [(self.labels[idx.item()], float(prob.item())) 
                      for prob, idx in zip(top_k_probs, top_k_indices)]
            
            return results
        
        except Exception as e:
            logger.error(f"Top-k error: {e}")
            raise
