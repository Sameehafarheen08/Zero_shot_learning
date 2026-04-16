"""
CLIP with Category Labels - COMPLETE REWRITE
✅ FIX #1: Load ONLY selected category labels
✅ FIX #2: NORMALIZE embeddings (L2 norm critical!)
✅ FIX #3: Per-category cache (fresh on restart)
✅ FIX #4: Prompt MUST include label: "a photo of ice cream"
✅ FIX #5: Image RGB 224x224 CLIP preprocessing
"""

from PIL import Image
import os
from typing import List, Tuple, Optional
import logging

torch = None
CLIPModel = None
CLIPProcessor = None

logger = logging.getLogger(__name__)

_model_cache = None
_processor_cache = None
_device = None
_embeddings_cache = {}  # PER CATEGORY: {category -> embeddings}
_labels_cache = {}      # PER CATEGORY: {category -> labels}

UNKNOWN_THRESHOLD = 0.25


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
    global _model_cache, _processor_cache, torch, CLIPModel, CLIPProcessor
    
    if _model_cache is not None and _processor_cache is not None:
        return _model_cache, _processor_cache
    
    try:
        logger.info("Loading CLIP ViT-B/32...")
        
        if torch is None:
            import torch as torch_module
            torch = torch_module
        
        if CLIPModel is None:
            from transformers import CLIPModel as CM, CLIPProcessor as CP
            CLIPModel = CM
            CLIPProcessor = CP
        
        device = get_device()
        model_id = "openai/clip-vit-base-patch32"
        
        os.environ['HF_HUB_DOWNLOAD_TIMEOUT'] = '600'
        
        processor = CLIPProcessor.from_pretrained(model_id)
        model = CLIPModel.from_pretrained(model_id).to(device)
        model.eval()
        
        _model_cache = model
        _processor_cache = processor
        logger.info(f"✅ CLIP loaded")
        return model, processor
    
    except Exception as e:
        logger.error(f"Model load error: {e}")
        raise


def load_labels_for_category(category: str = "all") -> List[str]:
    """
    FIX #1: Load ONLY the selected category
    If category="all", load all files and merge
    If category="food", load ONLY food.txt
    """
    if category in _labels_cache:
        logger.info(f"Using cached labels for {category}")
        return _labels_cache[category]
    
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    labels_dir = os.path.join(backend_dir, "labels")
    
    labels = []
    
    try:
        if category == "all":
            # Load all .txt files
            for filename in sorted(os.listdir(labels_dir)):
                if filename.endswith(".txt"):
                    filepath = os.path.join(labels_dir, filename)
                    with open(filepath, 'r') as f:
                        cat_labels = [line.strip().lower() for line in f if line.strip()]
                        labels.extend(cat_labels)
                        logger.info(f"Loaded {filename}: {len(cat_labels)} labels")
        else:
            # Load ONLY specific category
            filepath = os.path.join(labels_dir, f"{category}.txt")
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    labels = [line.strip().lower() for line in f if line.strip()]
                logger.info(f"Loaded {category}.txt: {len(labels)} labels")
            else:
                logger.warning(f"Category file {filepath} not found!")
        
        # Deduplicate
        seen = set()
        unique = []
        for label in labels:
            if label not in seen:
                seen.add(label)
                unique.append(label)
        
        logger.info(f"✅ {category}: {len(unique)} unique labels")
        _labels_cache[category] = unique
        return unique
    
    except Exception as e:
        logger.error(f"Error loading labels: {e}")
        raise


class CLIPClassifier:
    def __init__(self, category: str = "all"):
        """Load classifier for specific category"""
        self.model, self.processor = load_model()
        self.device = get_device()
        self.category = category
        self.labels = load_labels_for_category(category)
        logger.info(f"✅ Classifier ready for '{category}' ({len(self.labels)} labels)")
    
    def classify(self, image_path: str) -> Tuple[str, float]:
        """
        Classify image with PROPER normalization and preprocessing
        """
        global torch
        
        try:
            if torch is None:
                import torch as torch_module
                torch = torch_module
            
            # FIX #5: Load and preprocess image (RGB, 224x224, CLIP normalization)
            image = Image.open(image_path).convert("RGB")
            image_inputs = self.processor(images=image, return_tensors="pt").to(self.device)
            
            # FIX #4: Prompts MUST include label
            prompts = [f"a photo of {label}" for label in self.labels]
            cache_key = f"{self.category}_{len(self.labels)}"
            
            # FIX #3: Cache per category
            if cache_key in _embeddings_cache:
                text_embeddings = _embeddings_cache[cache_key]
            else:
                # Generate text embeddings
                text_inputs = self.processor(text=prompts, return_tensors="pt", padding=True).to(self.device)
                with torch.no_grad():
                    outputs = self.model(**text_inputs)
                    text_embeddings = outputs.text_embeds
                
                # FIX #2: NORMALIZE embeddings (L2 norm)
                text_embeddings = text_embeddings / text_embeddings.norm(dim=-1, keepdim=True)
                _embeddings_cache[cache_key] = text_embeddings
            
            # Get image embedding and normalize
            with torch.no_grad():
                image_emb = self.model.get_image_features(**image_inputs)
                # FIX #2: NORMALIZE image embedding too!
                image_emb = image_emb / image_emb.norm(dim=-1, keepdim=True)
                
                # Cosine similarity
                logits = image_emb @ text_embeddings.T
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
        """Get top-k predictions"""
        global torch
        
        try:
            if torch is None:
                import torch as torch_module
                torch = torch_module
            
            image = Image.open(image_path).convert("RGB")
            image_inputs = self.processor(images=image, return_tensors="pt").to(self.device)
            
            prompts = [f"a photo of {label}" for label in self.labels]
            cache_key = f"{self.category}_{len(self.labels)}"
            
            if cache_key in _embeddings_cache:
                text_embeddings = _embeddings_cache[cache_key]
            else:
                text_inputs = self.processor(text=prompts, return_tensors="pt", padding=True).to(self.device)
                with torch.no_grad():
                    outputs = self.model(**text_inputs)
                    text_embeddings = outputs.text_embeds
                text_embeddings = text_embeddings / text_embeddings.norm(dim=-1, keepdim=True)
                _embeddings_cache[cache_key] = text_embeddings
            
            with torch.no_grad():
                image_emb = self.model.get_image_features(**image_inputs)
                image_emb = image_emb / image_emb.norm(dim=-1, keepdim=True)
                logits = image_emb @ text_embeddings.T
                probs = logits.softmax(dim=-1).squeeze(0)
            
            top_k_probs, top_k_indices = torch.topk(probs, min(k, len(self.labels)))
            
            results = [(self.labels[idx.item()], float(prob.item())) 
                      for prob, idx in zip(top_k_probs, top_k_indices)]
            
            return results
        
        except Exception as e:
            logger.error(f"Top-k error: {e}")
            raise
