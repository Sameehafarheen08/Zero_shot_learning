from flask import Blueprint, request, jsonify
from app.db import get_db, execute_mutation, execute_query

user_bp = Blueprint('user', __name__)

# ========================
# Route: Get User Profile
# ========================
@user_bp.route("/api/user/<int:user_id>", methods=["GET"])
def get_user_profile(user_id):
    import os
    try:
        db_type = os.getenv("DB_TYPE", "sqlite").lower()
        
        if db_type == "sqlite":
            query = "SELECT id, email, created_at FROM users WHERE id = ?"
        else:
            query = "SELECT id, email, created_at FROM users WHERE id = %s"
        
        user = execute_query(query, (user_id,), fetch_one=True)
        
        if user:
            return jsonify({"success": True, "user": user})
        else:
            return jsonify({"success": False, "message": "User not found"}), 404
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error fetching user profile: {e}")
        return jsonify({"success": False, "message": "Server error"}), 500


# ================================
# Route: Get User Prediction History
# ================================
@user_bp.route("/api/user/<int:user_id>/predictions", methods=["GET"])
def get_user_predictions(user_id):
    import os
    try:
        db_type = os.getenv("DB_TYPE", "sqlite").lower()
        
        if db_type == "sqlite":
            query = "SELECT * FROM predictions WHERE user_id = ? ORDER BY timestamp DESC"
        else:
            query = "SELECT * FROM predictions WHERE user_id = %s ORDER BY timestamp DESC"
        
        predictions = execute_query(query, (user_id,))
        
        # Convert sqlite3.Row objects to dictionaries if needed
        if predictions and hasattr(predictions[0], 'keys'):
            predictions = [dict(p) for p in predictions]
        
        return jsonify({"success": True, "predictions": predictions})
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error fetching predictions: {e}")
        return jsonify({"success": False, "message": "Server error"}), 500


# ======================
# Route: Submit Feedback
# ======================
@user_bp.route("/api/feedback", methods=["POST"])
def submit_feedback():
    import os
    data = request.get_json()
    user_id = data.get("user_id")
    message = data.get("message")

    if not user_id or not message:
        return jsonify({"success": False, "message": "All fields required"}), 400

    try:
        # Use database-agnostic execute_mutation function
        db_type = os.getenv("DB_TYPE", "sqlite").lower()
        
        if db_type == "sqlite":
            query = "INSERT INTO feedback (user_id, message, timestamp) VALUES (?, ?, CURRENT_TIMESTAMP)"
        else:
            query = "INSERT INTO feedback (user_id, message, timestamp) VALUES (%s, %s, NOW())"
        
        execute_mutation(query, (user_id, message))
        return jsonify({"success": True, "message": "Feedback submitted successfully"}), 201
    except Exception as e:
        logger = __import__('logging').getLogger(__name__)
        logger.error(f"Error submitting feedback: {e}")
        return jsonify({"success": False, "message": "Error submitting feedback"}), 500


# =======================
# Route: Fetch All Feedback (For Admin)
# =======================
@user_bp.route("/api/feedbacks", methods=["GET"])
def get_all_feedbacks():
    try:
        query = """SELECT f.id, f.user_id, f.message, f.timestamp, u.email 
                      FROM feedback f 
                      JOIN users u ON f.user_id = u.id 
                      ORDER BY f.timestamp DESC"""
        feedbacks = execute_query(query)
        
        # Convert sqlite3.Row objects to dictionaries if needed
        if feedbacks and hasattr(feedbacks[0], 'keys'):
            feedbacks = [dict(fb) for fb in feedbacks]
        
        return jsonify({"success": True, "feedbacks": feedbacks, "data": {"feedbacks": feedbacks}})
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error fetching feedbacks: {e}")
        return jsonify({"success": False, "message": "Error fetching feedbacks"}), 500


# Route: Delete Feedback (Admin)
# =======================
@user_bp.route("/api/feedbacks/<int:feedback_id>", methods=["DELETE"])
def delete_feedback(feedback_id):
    from app.utils import verify_jwt_token
    import os
    import logging
    logger = logging.getLogger(__name__)
    
    # Verify token
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        return jsonify({"success": False, "message": "No token provided"}), 401
    
    payload = verify_jwt_token(token)
    if not payload:
        return jsonify({"success": False, "message": "Invalid token"}), 401
    
    try:
        # Check database type for proper syntax
        db_type = os.getenv("DB_TYPE", "sqlite").lower()
        
        # Check if feedback exists
        if db_type == "sqlite":
            check_query = "SELECT id FROM feedback WHERE id = ?"
        else:
            check_query = "SELECT id FROM feedback WHERE id = %s"
        
        feedback = execute_query(check_query, (feedback_id,), fetch_one=True)
        
        if not feedback:
            return jsonify({"success": False, "message": "Feedback not found"}), 404
        
        # Delete feedback with proper syntax
        if db_type == "sqlite":
            delete_query = "DELETE FROM feedback WHERE id = ?"
        else:
            delete_query = "DELETE FROM feedback WHERE id = %s"
        
        execute_mutation(delete_query, (feedback_id,))
        
        return jsonify({"success": True, "message": "Feedback deleted successfully"}), 200
    
    except Exception as e:
        logger.error(f"Error deleting feedback: {e}")
        return jsonify({"success": False, "message": "Server error"}), 500


# =====================
# Route: Ask AI (DEPRECATED - moved to ask_routes.py)
# This endpoint is no longer used - see ask_routes.py for new /api/ask
# =====================
@user_bp.route("/api/ask-deprecated", methods=["POST"])
def ask_ai_deprecated():
    """
    DEPRECATED: Generate AI response for user questions about their predictions.
    This endpoint has been replaced by /api/ask in ask_routes.py
    
    Request JSON:
    {
        "user_id": 1,
        "label": "dog",
        "question": "What is a dog?"
    }
    """
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        label = data.get("label")
        question = data.get("question")
        
        if not all([user_id, label, question]):
            return jsonify({
                "success": False, 
                "message": "This endpoint is deprecated. Use /api/ask instead"
            }), 400
        
        # Verify user exists
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404
        
        # Generate AI response using integrated APIs
        ai_response = generate_ai_response(label, question)
        
        # Log the question for analytics (optional)
        # You can store this in a new "ai_queries" table if needed
        
        return jsonify({
            "success": True,
            "data": {
                "label": label,
                "question": question,
                "response": ai_response,
                "source": "CLIP AI Assistant"
            },
            "message": "Answer generated successfully"
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error generating response: {str(e)}"
        }), 500


def generate_ai_response(label, question):
    """
    Generate intelligent response for the question about the label.
    
    This is a demo implementation. In production, integrate with:
    - OpenAI ChatGPT API (gpt-3.5-turbo or gpt-4)
    - Google Generative AI (Gemini)
    - Other LLM services
    
    Example integration with OpenAI:
    ```
    import openai
    openai.api_key = os.getenv("OPENAI_API_KEY")
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content
    ```
    
    Example integration with Google:
    ```
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content(prompt)
    return response.text
    ```
    """
    
    # Build context-aware prompt
    prompt = f"""You are an AI assistant helping users understand image classification results from CLIP (Contrastive Language-Image Pre-training).

A user's image was classified as: "{label}"

The user is asking: "{question}"

Please provide a helpful, accurate answer about the "{label}" classification and their specific question. Keep the response concise and informative."""
    
    # Demo responses based on question keywords
    responses = {
        "what is": f'{label.capitalize()} is a classification category. Objects in this category typically share visual characteristics that the CLIP model learned from its training data. The model identified these characteristics in your uploaded image.',
        
        "how does": f"The CLIP model works by comparing your image against thousands of category descriptions. It found that your image best matches the '{label}' category based on visual features like color, shape, texture, and spatial relationships.",
        
        "characteristics": f"Objects classified as '{label}' typically have specific visual characteristics such as distinctive color patterns, shapes, textures, and spatial features that the CLIP model learned to recognize.",
        
        "difference": f"The classification '{label}' was chosen because your image has visual features most similar to the '{label}' category compared to other possible categories in the model's knowledge base.",
        
        "accuracy": f"The confidence score indicates how certain the model is about the '{label}' classification. Higher confidence means the image has strong visual similarity to typical '{label}' objects.",
        
        "improve": f"To improve '{label}' classification, you could upload clearer images, ensure good lighting, and make sure the main subject fills most of the frame.",
        
        "similar": f"Objects similar to '{label}' might include related categories. The model chose '{label}' specifically because it best matched your image's visual features.",
        
        "default": f"Your image was classified as '{label}' by the CLIP zero-shot learning model. This is a visual classification based on learned patterns in image embeddings. Regarding your question: \"{question}\" - this demonstrates the model's ability to make intelligent visual categorizations without task-specific retraining."
    }
    
    # Find matching response
    question_lower = question.lower()
    for keyword, response in responses.items():
        if keyword in question_lower:
            return response
    
    return responses["default"]


# =====================
# Route: Forgot Password (Dummy Logic)
# =====================
@user_bp.route("/api/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json()
    email = data.get("email")

    if not email:
        return jsonify({"success": False, "message": "Email is required"}), 400

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()
    conn.close()

    if user:
        return jsonify({"success": True, "message": "Reset link sent to email (not implemented)!"})
    else:
        return jsonify({"success": False, "message": "Email not found"}), 404