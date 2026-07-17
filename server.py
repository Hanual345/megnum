import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from ai_client import query_volcano_ai
from pymongo import MongoClient
import urllib.parse
import datetime
import base64
import io
from pypdf import PdfReader

app = Flask(__name__)
CORS(app) # Enable Cross-Origin requests for the frontend

# MongoDB Configuration
mongo_uri = os.environ.get("MONGODB_URI")
if not mongo_uri:
    password = urllib.parse.quote_plus("Volcano@2026")
    mongo_uri = f"mongodb+srv://adminvolcano_db_user:{password}@volcano.fczkc5w.mongodb.net/?appName=Volcano"

mongo_client = MongoClient(mongo_uri)
db = mongo_client["volcano_db"]
history_collection = db["chat_history"]
users_collection = db["users"]
sessions_collection = db["chat_sessions"]

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    # Do NOT serve static files for API routes — return a proper JSON 404 instead
    if path.startswith('api/'):
        return jsonify({"success": False, "error": f"API endpoint '/{path}' not found"}), 404
    return send_from_directory('.', path)

import hashlib

def hash_password(password, salt=None):
    if salt is None:
        salt = os.urandom(16).hex()
    hash_obj = hashlib.sha256((password + salt).encode('utf-8'))
    return hash_obj.hexdigest(), salt

def verify_password(password, salt, stored_hash):
    hash_val, _ = hash_password(password, salt)
    return hash_val == stored_hash

def extract_text_from_pdf(base64_data):
    try:
        if "," in base64_data:
            base64_data = base64_data.split(",")[1]
        pdf_bytes = base64.b64decode(base64_data)
        pdf_file = io.BytesIO(pdf_bytes)
        reader = PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        return text.strip()
    except Exception as e:
        print("Error parsing PDF:", e)
        return None

# Auth Endpoints
@app.route('/api/auth/signup', methods=['POST'])
def signup():
    data = request.json or {}
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')

    if not username or not email or not password:
        return jsonify({"success": False, "error": "Username, email, and password are required"}), 400

    try:
        # Check if email or username already exists
        if users_collection.find_one({"email": email}):
            return jsonify({"success": False, "error": "Email is already registered"}), 400
        if users_collection.find_one({"username": username}):
            return jsonify({"success": False, "error": "Username is already taken"}), 400

        pwd_hash, salt = hash_password(password)
        user_doc = {
            "username": username,
            "email": email,
            "password_hash": pwd_hash,
            "salt": salt,
            "created_at": datetime.datetime.utcnow()
        }
        result = users_collection.insert_one(user_doc)
        return jsonify({
            "success": True,
            "user": {
                "id": str(result.inserted_id),
                "username": username,
                "email": email
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json or {}
    login_input = data.get('email', '').strip() # Can be username or email
    password = data.get('password', '')

    if not login_input or not password:
        return jsonify({"success": False, "error": "Email/Username and password are required"}), 400

    try:
        # Find user by email or username
        user = users_collection.find_one({"$or": [{"email": login_input}, {"username": login_input}]})
        if not user:
            return jsonify({"success": False, "error": "Account not found"}), 400

        # Verify password
        if not verify_password(password, user["salt"], user["password_hash"]):
            return jsonify({"success": False, "error": "Incorrect password"}), 400

        return jsonify({
            "success": True,
            "user": {
                "id": str(user["_id"]),
                "username": user["username"],
                "email": user["email"]
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Recent Sessions Endpoints
@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    user_id = request.args.get('user_id', '')
    if not user_id:
        return jsonify({"success": False, "error": "User ID is required"}), 400
    try:
        cursor = sessions_collection.find({"user_id": user_id}).sort("created_at", -1)
        sessions = []
        for s in cursor:
            sessions.append({
                "session_id": s.get("session_id"),
                "title": s.get("title"),
                "created_at": s.get("created_at").isoformat() if s.get("created_at") else None
            })
        return jsonify({"success": True, "sessions": sessions})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/sessions/clear', methods=['POST'])
def clear_sessions():
    data = request.json or {}
    user_id = data.get('user_id', '')
    if not user_id:
        return jsonify({"success": False, "error": "User ID is required"}), 400
    try:
        # Delete all chat messages for this user
        history_collection.delete_many({"user_id": user_id})
        # Delete all session cards
        sessions_collection.delete_many({"user_id": user_id})
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json or {}
    prompt = data.get('prompt', '')
    session_id = data.get('session_id', 'default_session')
    model = data.get('model', 'magma2')
    attachment = data.get('attachment', None)
    user_id = data.get('user_id', 'default_user')
    deep_think = data.get('deep_think', False)
    
    if not prompt and not attachment:
        return jsonify({"success": False, "error": "Prompt or attachment is required"}), 400

    # If attachment is a PDF, extract its text content
    if attachment and (attachment.get("type") == "application/pdf" or attachment.get("name", "").lower().endswith(".pdf")):
        pdf_base64 = attachment.get("data", "")
        if pdf_base64:
            extracted_text = extract_text_from_pdf(pdf_base64)
            if extracted_text:
                attachment["content"] = extracted_text

    # Fetch last 10 messages from MongoDB for this session
    history = []
    try:
        cursor = history_collection.find({"session_id": session_id}).sort("timestamp", 1)
        past_msgs = list(cursor)
        for msg in past_msgs[-10:]:
            history.append({
                "role": msg.get("role"),
                "content": msg.get("content")
            })
    except Exception as e:
        print("Error fetching history from MongoDB:", e)

    # Call AI Client
    result = query_volcano_ai(prompt, history=history, model=model, attachment=attachment, deep_think=deep_think)
    
    # If successful, store both user prompt and bot response in MongoDB
    if result.get("success"):
        try:
            now = datetime.datetime.utcnow()
            
            # Save session descriptor in recent sessions if it's the first message
            if not sessions_collection.find_one({"session_id": session_id}):
                title = prompt[:50] + ("..." if len(prompt) > 50 else "") if prompt else (attachment.get("name", "Document") if attachment else "New Chat")
                sessions_collection.insert_one({
                    "session_id": session_id,
                    "user_id": user_id,
                    "title": title,
                    "created_at": now
                })

            history_collection.insert_many([
                {
                    "session_id": session_id,
                    "user_id": user_id,
                    "role": "user",
                    "content": prompt,
                    "attachment": attachment,
                    "timestamp": now
                },
                {
                    "session_id": session_id,
                    "user_id": user_id,
                    "role": "assistant",
                    "content": result.get("content"),
                    "reasoning": result.get("reasoning", None),
                    "timestamp": now + datetime.timedelta(seconds=1)
                }
            ])
        except Exception as e:
            print("Error writing to MongoDB:", e)
            
    return jsonify(result)

@app.route('/api/history', methods=['GET'])
def get_history():
    session_id = request.args.get('session_id', 'default_session')
    try:
        cursor = history_collection.find({"session_id": session_id}).sort("timestamp", 1)
        history = []
        for msg in cursor:
            history.append({
                "role": msg.get("role"),
                "content": msg.get("content"),
                "reasoning": msg.get("reasoning", None),
                "attachment": msg.get("attachment", None)
            })
        return jsonify({"success": True, "history": history})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    # Use $PORT from environment (required by Render.com), fallback to 5001 locally
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)
