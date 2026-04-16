"""
Ask-AI Routes - Real AI answers using backend API
"""

from flask import Blueprint, request, jsonify
import logging
import os

logger = logging.getLogger(__name__)

ask_ai_bp = Blueprint('ask_ai', __name__)


@ask_ai_bp.route('/api/ask-ai', methods=['POST'])
def ask_ai():
    """
    Process AI questions using Google Search or OpenAI
    
    Request: {"question": "What is zero-shot learning?"}
    Response: {"success": true, "answer": "..."}
    """
    try:
        data = request.get_json()
        
        if not data or 'question' not in data:
            return jsonify({
                "success": False,
                "message": "question field is required"
            }), 400
        
        question = data.get('question', '').strip()
        
        if not question:
            return jsonify({
                "success": False,
                "message": "question cannot be empty"
            }), 400
        
        # Try OpenAI first (if API key available)
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            try:
                answer = get_openai_answer(question, openai_key)
                return jsonify({
                    "success": True,
                    "answer": answer,
                    "source": "OpenAI GPT"
                }), 200
            except Exception as e:
                logger.warning(f"OpenAI failed: {e}. Trying Google Search...")
        
        # Fallback to Google Custom Search
        google_key = os.getenv("GOOGLE_SEARCH_API_KEY")
        google_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
        
        if google_key and google_engine_id:
            try:
                answer = get_google_answer(question, google_key, google_engine_id)
                return jsonify({
                    "success": True,
                    "answer": answer,
                    "source": "Google Search"
                }), 200
            except Exception as e:
                logger.warning(f"Google Search failed: {e}")
        
        # Fallback: return error
        return jsonify({
            "success": False,
            "message": "No AI service configured. Set OPENAI_API_KEY or GOOGLE_SEARCH_API_KEY in .env"
        }), 503
    
    except Exception as e:
        logger.error(f"Ask-AI error: {e}")
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500


def get_openai_answer(question: str, api_key: str) -> str:
    """Get answer from OpenAI GPT"""
    try:
        import openai
        openai.api_key = api_key
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant answering questions about image classification and machine learning."},
                {"role": "user", "content": question}
            ],
            max_tokens=500
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        raise


def get_google_answer(question: str, api_key: str, engine_id: str) -> str:
    """Get answer from Google Custom Search"""
    try:
        from googleapiclient.discovery import build
        
        service = build("customsearch", "v1", developerKey=api_key)
        result = service.cse().list(q=question, cx=engine_id).execute()
        
        if 'items' in result and len(result['items']) > 0:
            # Extract snippet from first result
            snippet = result['items'][0].get('snippet', '')
            title = result['items'][0].get('title', '')
            link = result['items'][0].get('link', '')
            
            answer = f"**{title}**\n\n{snippet}\n\n[Source]({link})"
            return answer
        else:
            return "No results found for your question."
    
    except Exception as e:
        logger.error(f"Google Search error: {e}")
        raise
