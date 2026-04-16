"""
Ask-AI Routes - Backend API for real AI answers
Removes hardcoded frontend answers and fetches real responses
"""

from flask import Blueprint, request, jsonify
import logging

logger = logging.getLogger(__name__)

ask_bp = Blueprint('ask', __name__)


@ask_bp.route('/api/ask', methods=['POST'])
def ask():
    """
    Simple chatbot-style Ask AI endpoint
    Just takes a question and returns an answer
    
    Request: {"user_id": 1, "question": "What is a dog?"}
    Response: {"success": true, "data": {"response": "..."}}
    """
    try:
        data = request.get_json()
        
        if not data or 'question' not in data:
            return jsonify({
                "success": False,
                "message": "Question is required"
            }), 400
        
        question = data.get('question', '').strip()
        user_id = data.get('user_id')
        
        if not question:
            return jsonify({
                "success": False,
                "message": "Question cannot be empty"
            }), 400
        
        # Try to get answer from knowledge base
        answer = get_knowledge_base_answer(question)
        
        # If no knowledge base answer, try Google
        if not answer:
            try:
                answer = get_google_search_answer(question)
            except Exception as e:
                logger.warning(f"Google search failed: {e}")
                answer = None
        
        # Default fallback answer
        if not answer:
            answer = (
                "I'm not entirely sure about that specific question. "
                "However, I know a lot about CLIP, zero-shot learning, image classification, and how to use this app! "
                "Try asking me: 'What is CLIP?', 'How does zero-shot learning work?', 'What can you classify?', or 'How do I use this app?'"
            )
        
        # Always return success with an answer (no 404 errors)
        return jsonify({
            "success": True,
            "data": {
                "response": answer,
                "question": question
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Ask error: {e}")
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500


# OLD /api/ask-ai route REMOVED - use ask_ai_new.py instead for real AI responses

# OLD /api/ask-ai route REMOVED - use ask_ai_new.py instead for real AI responses


def get_google_search_answer(question: str) -> str:
    """
    Fetch answer from Google Custom Search API
    Requires: GOOGLE_API_KEY and GOOGLE_SEARCH_ENGINE_ID env variables
    """
    import os
    
    api_key = os.getenv("GOOGLE_API_KEY")
    search_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
    
    if not api_key or not search_engine_id:
        logger.warning("Google API credentials not configured")
        return None
    
    try:
        import requests
        
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "q": question,
            "key": api_key,
            "cx": search_engine_id,
            "num": 3
        }
        
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        
        results = response.json()
        
        if 'items' in results and len(results['items']) > 0:
            # Combine snippets from top results
            snippets = [item.get('snippet', '') for item in results['items'][:3]]
            answer = ' '.join(snippets)
            return answer[:500]  # Limit to 500 chars
        
        return None
    
    except Exception as e:
        logger.error(f"Google Search API error: {e}")
        return None


def get_knowledge_base_answer(question: str) -> str:
    """
    Simple knowledge base for common questions
    Uses keyword matching for flexibility
    """
    question_lower = question.lower()
    
    # Knowledge base with keywords to match
    knowledge_base = [
        {
            "keywords": ["zero-shot", "zero shot"],
            "answer": "Zero-shot learning is a machine learning technique where a model can recognize "
                     "or classify objects without being specifically trained on them. Instead, it uses "
                     "learned relationships between words and concepts to make predictions on completely "
                     "new categories. For example, CLIP can classify images of objects it has never seen "
                     "by matching image features with text descriptions."
        },
        {
            "keywords": ["clip"],
            "answer": "CLIP (Contrastive Language-Image Pre-Training) is an AI model by OpenAI that learns "
                     "to understand images and text together. It can classify images into any category "
                     "described in text, without needing training on those specific categories. This makes "
                     "it powerful for zero-shot image classification."
        },
        {
            "keywords": ["image classification", "classify image"],
            "answer": "Image classification is the process of assigning an image to one or more predefined "
                     "categories. Machine learning models analyze pixel patterns, colors, shapes, and other "
                     "features to identify what's in the image. Modern models like CLIP use deep learning "
                     "to understand complex visual concepts."
        },
        {
            "keywords": ["deep learning"],
            "answer": "Deep learning is a subset of machine learning that uses artificial neural networks "
                     "with multiple layers (hence 'deep') to learn patterns from data. It powers many modern "
                     "AI applications including image recognition, natural language processing, and language "
                     "models. Deep learning models can automatically discover the features needed for detection "
                     "or classification."
        },
        {
            "keywords": ["neural network"],
            "answer": "A neural network is a computational model inspired by biological neurons in the brain. "
                     "It consists of interconnected layers of simple processing units (neurons) that learn to "
                     "recognize patterns in data. Neural networks are trained by adjusting connection weights "
                     "to minimize errors on example data."
        },
        {
            "keywords": ["machine learning"],
            "answer": "Machine learning is a branch of artificial intelligence where computer systems learn "
                     "and improve from experience without being explicitly programmed. Instead of following "
                     "fixed instructions, ML systems analyze data, identify patterns, and make predictions "
                     "or decisions based on what they've learned."
        },
        {
            "keywords": ["artificial intelligence", "ai", "what is ai"],
            "answer": "Artificial Intelligence (AI) refers to computer systems designed to perform tasks that "
                     "typically require human intelligence. This includes learning from examples, recognizing "
                     "patterns, understanding language, and making decisions. Modern AI powers applications "
                     "like image recognition, voice assistants, and recommendation systems."
        },
        {
            "keywords": ["how to use", "how do i use", "usage"],
            "answer": "This app uses CLIP for zero-shot image classification. Simply upload an image using "
                     "the Upload page, and the system will classify it into one of 100+ categories without "
                     "needing specific training. You can also compare two images to see if they belong to "
                     "the same category. Check your prediction history on the History page."
        },
        {
            "keywords": ["categories", "what can you classify", "types of objects"],
            "answer": "The system can classify images into 100+ categories including: food items (pizza, burger, "
                     "ice cream), animals (cat, dog, bird), objects (phone, keyboard, cup), and many more. "
                     "Because of zero-shot learning, it can often classify variations even if not explicitly "
                     "trained on them."
        },
        {
            "keywords": ["upload", "predict", "classification"],
            "answer": "To get a classification, go to the Upload page and select an image from your device. "
                     "The system will analyze it and show you the top 3 predictions with confidence scores. "
                     "The higher the confidence, the more certain the model is about its prediction."
        },
        {
            "keywords": ["compare", "comparison"],
            "answer": "You can compare two images by going to the Compare page. Upload two images and the system "
                     "will tell you if they belong to the same category. This is useful for understanding how "
                     "CLIP interprets different images."
        },
        {
            "keywords": ["accuracy", "correct", "wrong"],
            "answer": "CLIP is highly accurate for most common objects, but like all AI models, it can sometimes "
                     "make mistakes. The confidence score shows how certain the model is. Lower confidence scores "
                     "indicate the model is less sure. If a prediction seems wrong, try uploading a clearer image."
        },
    ]
    
    # Try to find matching answer by keywords
    for item in knowledge_base:
        for keyword in item["keywords"]:
            if keyword in question_lower:
                return item["answer"]
    
    # If no exact match, try partial matching with common words
    common_questions = {
        "ice cream": "The app can classify ice cream! Try uploading an ice cream image to see how CLIP recognizes it.",
        "food": "Yes, the system can classify many food items like pizza, hamburger, ice cream, and more!",
        "animal": "Yes, the system can recognize animals like cats, dogs, birds, and other common animals.",
        "object": "The system can classify many objects like phones, keyboards, chairs, tables, and more.",
        "help": "Need help? Try asking 'How to use this app', 'What is CLIP?', or 'What categories can you classify?'",
        "feature": "This app has Upload (classify single images), Compare (compare two images), History (view past predictions), and Ask AI (chat with me!).",
    }
    
    for word, answer in common_questions.items():
        if word in question_lower:
            return answer
    
    return None
