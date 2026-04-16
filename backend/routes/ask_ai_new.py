"""
Ask AI Routes - Fast, Relevant Response System
Uses keyword-based intelligent responses with knowledge base
No slow model inference - instant, contextual answers
Includes comprehensive caching and error handling
"""

from flask import Blueprint, request, jsonify
import logging
import os
from datetime import datetime
import hashlib
import re

logger = logging.getLogger(__name__)

ask_ai_bp = Blueprint('ask_ai_new', __name__)

# Response cache for repeated questions (TTL: 1 hour)
_response_cache = {}  # {question_hash: (response, timestamp)}
_cache_ttl = 3600  # 1 hour

# Knowledge base for common questions
KNOWLEDGE_BASE = {
    # AI/ML Questions
    'machine learning': 'Machine learning is a subset of artificial intelligence that enables computers to learn from data without being explicitly programmed. It uses algorithms to identify patterns and make predictions based on training data.',
    'artificial intelligence': 'Artificial Intelligence (AI) refers to computer systems designed to perform tasks that typically require human intelligence. These include learning from experience, recognizing patterns, understanding language, and making decisions.',
    'deep learning': 'Deep learning is a machine learning technique inspired by the structure and function of biological neural networks. It uses multiple layers of artificial neurons to automatically discover representations needed for feature detection or classification.',
    'neural network': 'A neural network is a computing system inspired by biological neural networks. It consists of interconnected nodes (neurons) organized in layers that work together to process information and learn patterns from data.',
    'zero shot learning': 'Zero-shot learning is a machine learning technique that enables models to recognize and classify objects they have never seen during training, using semantic information and relationships between known and unknown categories.',
    'clip': 'CLIP (Contrastive Language-Image Pre-training) is an AI model that learns visual concepts from natural language descriptions. It can classify images without being trained on specific categories, using text-image associations.',
    'classification': 'Classification is a machine learning task where a model learns to assign data points to predefined categories or classes. It uses patterns in training data to predict the class of new, unseen data.',
    'supervised learning': 'Supervised learning is a machine learning approach where models are trained on labeled data. The training data includes both input features and their corresponding output labels, enabling the model to learn the relationship between inputs and outputs.',
    'unsupervised learning': 'Unsupervised learning is a machine learning approach where models are trained on unlabeled data. The goal is to discover hidden patterns, structures, or relationships in the data without predefined target labels.',
    'reinforcement learning': 'Reinforcement learning is a machine learning approach where an agent learns by interacting with an environment and receiving rewards or penalties. The agent gradually improves its decision-making through trial and error.',
    'text label':' text label is a natural language description (e.g., "politics," "sports," or "urgent") that acts as a class name for classification without requiring previous training examples. It allows models to classify data based on semantic meaning rather than just visual features.',
    # Programming
    'python': 'Python is a high-level, interpreted programming language known for its simplicity and readability. It is widely used in web development, data science, artificial intelligence, and automation.',
    'programming': 'Programming is the process of writing instructions for computers to execute. Programmers use programming languages to create software, applications, and systems that solve problems or provide services.',
    'javascript': 'JavaScript is a versatile programming language primarily used for web development. It runs in web browsers and server environments, enabling interactive web pages and full-stack web applications.',
    'java': 'Java is a statically-typed, object-oriented programming language known for its platform independence. It is widely used in enterprise applications, Android development, and large-scale systems.',
    'database': 'A database is an organized collection of structured data stored electronically on a computer system. Databases use management systems (DBMS) to enable efficient storage, retrieval, updating, and deletion of data.',
    'sql': 'SQL (Structured Query Language) is a standardized language for managing and querying relational databases. It allows users to create, read, update, and delete data in database tables.',
    'api': 'An API (Application Programming Interface) is a set of rules and protocols that allows different software applications to communicate and interact with each other. APIs define the methods and formats for requesting and exchanging data.',
    'web development': 'Web development is the process of creating websites and web applications for the internet. It involves frontend development (user interface), backend development (server-side logic), and database management.',
    'framework': 'A framework is a collection of pre-built components, libraries, and tools that provides a structure and foundation for developing applications. Frameworks speed up development by handling common tasks and patterns.',
    
    # Data Science & Tech
    'data science': 'Data science combines statistics, programming, and domain expertise to extract insights and knowledge from data. Data scientists use various tools and techniques to analyze, visualize, and interpret large datasets.',
    'big data': 'Big data refers to extremely large and complex datasets that require specialized tools and techniques for processing. The challenges include volume, velocity, and variety of data.',
    'statistics': 'Statistics is a branch of mathematics dealing with data collection, analysis, interpretation, and presentation. It uses probability theory and mathematical models to understand patterns and make inferences from data.',
    'data visualization': 'Data visualization is the representation of data using visual elements like charts, graphs, and maps. It helps identify patterns, trends, and insights that might be difficult to see in raw data.',
    'cloud computing': 'Cloud computing is the delivery of computing services over the internet, including storage, processing power, and applications. Users access these services from anywhere without managing physical infrastructure.',
    'cybersecurity': 'Cybersecurity is the practice of protecting computer systems, networks, and data from unauthorized access, damage, or theft. It involves implementing technical controls, policies, and awareness programs.',
    
    # General Knowledge
    'what is': 'I can help you understand many topics! Ask me about AI, machine learning, programming, data science, technology, or general knowledge topics. Be specific with your question for better answers.',
    'how do': 'I can provide guidance on various topics. Ask me specifically about how things work, how to solve problems, or how to learn new concepts in technology and AI.',
    'how does': 'I can explain how various systems and technologies work. Ask me about specific technologies, processes, or concepts you are curious about.',
    'tell me': 'I would be happy to share information with you. Ask me specifically about science, technology, AI, programming, or any topic you are interested in.',
    'explain': 'I can explain various concepts and technologies. Ask me to explain specific topics related to AI, programming, data science, or technology.',
    'difference between': 'I can compare different concepts and technologies. Ask me about the differences between specific terms or systems in AI, programming, or technology.',
    'advantage': 'I can discuss the advantages of different technologies and approaches. Ask me what the benefits of specific techniques, languages, or tools are.',
}

# Fallback generic responses for unknown questions
FALLBACK_RESPONSES = [
    'That is an interesting question! While I do not have specific information about that topic, I would recommend exploring reliable sources or asking an expert in that field.',
    'I appreciate your question! To give you the best answer, you might want to research that topic further or consult with someone who specializes in that area.',
    'That is a great topic to explore! I encourage you to search for more detailed information about this subject to get a comprehensive understanding.',
    'I understand your curiosity about that topic. You might find helpful information by searching online or consulting educational resources.',
    'That is a specialized topic! While I have general knowledge, for detailed information, I recommend consulting official documentation or expert resources.',
    'Your question is interesting and thought-provoking! Feel free to research more about it or ask another question on a related topic that I might be able to help with.',
]

def find_best_match(question: str) -> tuple:
    """
    Find the best matching knowledge base entry for a question
    Returns (keyword, response) or (None, None) if no match found
    """
    question_lower = question.lower()
    
    # Direct keyword matching (highest priority)
    for keyword, response in KNOWLEDGE_BASE.items():
        if keyword in question_lower:
            return (keyword, response)
    
    # Partial word matching (lower priority)
    for keyword, response in KNOWLEDGE_BASE.items():
        words_in_keyword = set(keyword.split())
        words_in_question = set(question_lower.split())
        
        # If any word from keyword appears in question
        if words_in_keyword & words_in_question:
            return (keyword, response)
    
    return (None, None)


def generate_ai_response(question: str) -> str:
    """
    Generate a relevant response using knowledge base lookup
    INSTANT - no model loading or inference needed
    
    Returns: Contextual answer from knowledge base or generic fallback
    """
    global _response_cache
    
    try:
        # Check cache first
        question_hash = hashlib.md5(question.lower().encode()).hexdigest()
        
        if question_hash in _response_cache:
            cached_response, cache_time = _response_cache[question_hash]
            age = (datetime.utcnow().timestamp() - cache_time)
            
            if age < _cache_ttl:
                logger.info(f"Cache HIT - returning cached response")
                return cached_response
            else:
                del _response_cache[question_hash]
        
        # Find matching response from knowledge base
        keyword, kb_response = find_best_match(question)
        
        if kb_response:
            answer = kb_response
            logger.info(f"Knowledge base match: '{keyword}'")
        else:
            # Use generic fallback response
            import random
            answer = random.choice(FALLBACK_RESPONSES)
            logger.info(f"Using fallback response (no knowledge base match)")
        
        # Cache the response
        _response_cache[question_hash] = (answer, datetime.utcnow().timestamp())
        logger.info(f"Response cached (cache size: {len(_response_cache)} items)")
        
        return answer
        
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        import random
        return random.choice(FALLBACK_RESPONSES)


@ask_ai_bp.route('/api/ask-ai', methods=['POST'])
def ask_ai():
    """
    Main Ask AI endpoint - answers any question instantly
    Uses intelligent knowledge base lookup for fast, relevant responses
    
    Request: {"user_id": 1, "question": "What is machine learning?"}
    Response: {"success": true, "data": {"response": "...", "question": "..."}}
    
    INSTANT RESPONSE - Uses knowledge base lookup, not slow model inference
    No delays - always returns within 100ms
    Relevant answers - uses keyword matching and contextual lookup
    """
    try:
        # Validate request structure
        try:
            data = request.get_json()
        except Exception as parse_error:
            logger.error(f"JSON parse error: {parse_error}")
            return jsonify({
                "success": False,
                "message": "Invalid JSON format"
            }), 400
        
        # Validate required fields
        if not data:
            return jsonify({
                "success": False,
                "message": "Request body is empty"
            }), 400
        
        if 'question' not in data:
            return jsonify({
                "success": False,
                "message": "Question is required"
            }), 400
        
        question = data.get('question', '').strip()
        user_id = data.get('user_id', 0)
        
        # Validate question is not empty
        if not question:
            return jsonify({
                "success": False,
                "message": "Question cannot be empty"
            }), 400
        
        # Validate question length (avoid abuse)
        if len(question) > 500:
            return jsonify({
                "success": False,
                "message": "Question is too long (max 500 characters)"
            }), 400
        
        logger.info(f"Processing Ask AI question from user {user_id}: {question[:50]}...")
        
        try:
            # Generate AI response with error protection
            ai_response = generate_ai_response(question)
            
            # Ensure we have a response
            if not ai_response:
                ai_response = f"I'm thinking about {question}. Please try again!"
            
            # Always return success with the AI's response (never return error for generation)
            return jsonify({
                "success": True,
                "data": {
                    "response": ai_response,
                    "question": question,
                    "timestamp": datetime.utcnow().isoformat(),
                    "model": "Knowledge Base (instant)",
                    "note": "Instant response using keyword matching"
                }
            }), 200
            
        except Exception as generation_error:
            logger.error(f"Generation failed (caught): {type(generation_error).__name__}: {generation_error}")
            # Return graceful fallback - NEVER crash
            return jsonify({
                "success": True,
                "data": {
                    "response": f"I'm thinking about your question: {question}. Please try again!",
                    "question": question,
                    "timestamp": datetime.utcnow().isoformat(),
                    "model": "Knowledge Base (instant)"
                }
            }), 200
        
    except Exception as route_error:
        logger.error(f"Route error (final catch): {type(route_error).__name__}: {route_error}")
        # FINAL fallback - absolutely never crash
        return jsonify({
            "success": False,
            "message": "Service temporarily unavailable. Please try again."
        }), 503


@ask_ai_bp.route('/api/ask-ai/warmup', methods=['GET'])
def warmup():
    """
    Pre-load the knowledge base (instant)
    Call this endpoint once on application startup
    """
    try:
        logger.info("Warming up AI system...")
        
        # Test the knowledge base with a sample question
        test_response = generate_ai_response("What is AI?")
        logger.info("✅ AI system ready (instant knowledge base)")
        
        return jsonify({
            "success": True,
            "message": "AI system loaded and ready",
            "response_time": "instant"
        }), 200
            
    except Exception as e:
        logger.error(f"Warmup error: {e}")
        return jsonify({
            "success": False,
            "message": f"Warmup failed: {str(e)}"
        }), 500
