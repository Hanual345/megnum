import os
try:
    from dotenv import load_dotenv
    load_dotenv()  # loads .env file for local development
except ImportError:
    pass
import hashlib
import base64
import io
import datetime
import urllib.parse

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# ── Lazy imports so a missing package doesn't crash gunicorn at startup ─────
try:
    from pymongo import MongoClient
    _mongo_available = True
except ImportError:
    _mongo_available = False
    print("WARNING: pymongo not installed – database features disabled")

try:
    from pypdf import PdfReader
    _pypdf_available = True
except ImportError:
    _pypdf_available = False
    print("WARNING: pypdf not installed – PDF extraction disabled")

from ai_client import query_volcano_ai

app = Flask(__name__)
CORS(app)

# ── MongoDB – lazy connection (initialised on first use, not at import time) ─
_mongo_client = None
_db = None
_history_collection = None
_users_collection = None
_sessions_collection = None

def get_db():
    """Return (history_col, users_col, sessions_col) or (None, None, None)."""
    global _mongo_client, _db, _history_collection, _users_collection, _sessions_collection
    if _mongo_client is not None:
        return _history_collection, _users_collection, _sessions_collection
    if not _mongo_available:
        return None, None, None
    try:
        mongo_uri = os.environ.get("MONGODB_URI")
        if not mongo_uri:
            password = urllib.parse.quote_plus("Volcano@2026")
            mongo_uri = (
                f"mongodb+srv://adminvolcano_db_user:{password}"
                f"@volcano.fczkc5w.mongodb.net/?appName=Volcano"
            )
        _mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        _db = _mongo_client["volcano_db"]
        _history_collection  = _db["chat_history"]
        _users_collection    = _db["users"]
        _sessions_collection = _db["chat_sessions"]
        print("MongoDB connected successfully")
    except Exception as exc:
        print(f"MongoDB connection error: {exc}")
        _mongo_client = None
    return _history_collection, _users_collection, _sessions_collection


# ── Helpers ──────────────────────────────────────────────────────────────────
def hash_password(password, salt=None):
    if salt is None:
        salt = os.urandom(16).hex()
    h = hashlib.sha256((password + salt).encode("utf-8")).hexdigest()
    return h, salt

def verify_password(password, salt, stored_hash):
    h, _ = hash_password(password, salt)
    return h == stored_hash

def extract_text_from_pdf(base64_data):
    if not _pypdf_available:
        return None
    try:
        if "," in base64_data:
            base64_data = base64_data.split(",")[1]
        pdf_bytes = base64.b64decode(base64_data)
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        return text.strip() or None
    except Exception as exc:
        print("PDF extraction error:", exc)
        return None


# ── Static file serving ──────────────────────────────────────────────────────
@app.route("/")
def serve_index():
    return send_from_directory(".", "index.html")

# NOTE: this catch-all is defined LAST so that API routes take priority.
# The /api/ guard below is a safety net in case Flask somehow falls through.


# ── Auth endpoints ────────────────────────────────────────────────────────────
@app.route("/api/auth/signup", methods=["POST"])
def signup():
    _, users_col, _ = get_db()
    data     = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    email    = data.get("email", "").strip()
    password = data.get("password", "")

    if not username or not email or not password:
        return jsonify({"success": False, "error": "Username, email, and password are required"}), 400

    if users_col is None:
        return jsonify({"success": False, "error": "Database unavailable"}), 503

    try:
        if users_col.find_one({"email": email}):
            return jsonify({"success": False, "error": "Email is already registered"}), 400
        if users_col.find_one({"username": username}):
            return jsonify({"success": False, "error": "Username is already taken"}), 400

        pwd_hash, salt = hash_password(password)
        result = users_col.insert_one({
            "username": username, "email": email,
            "password_hash": pwd_hash, "salt": salt,
            "created_at": datetime.datetime.utcnow()
        })
        return jsonify({"success": True, "user": {
            "id": str(result.inserted_id), "username": username, "email": email
        }})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/auth/login", methods=["POST"])
def login():
    _, users_col, _ = get_db()
    data        = request.get_json(silent=True) or {}
    login_input = data.get("email", "").strip()
    password    = data.get("password", "")

    if not login_input or not password:
        return jsonify({"success": False, "error": "Email/Username and password are required"}), 400

    if users_col is None:
        return jsonify({"success": False, "error": "Database unavailable"}), 503

    try:
        user = users_col.find_one({"$or": [{"email": login_input}, {"username": login_input}]})
        if not user:
            return jsonify({"success": False, "error": "Account not found"}), 400
        if not verify_password(password, user["salt"], user["password_hash"]):
            return jsonify({"success": False, "error": "Incorrect password"}), 400
        return jsonify({"success": True, "user": {
            "id": str(user["_id"]), "username": user["username"], "email": user["email"]
        }})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


# ── Session endpoints ─────────────────────────────────────────────────────────
@app.route("/api/sessions", methods=["GET"])
def get_sessions():
    _, _, sessions_col = get_db()
    user_id = request.args.get("user_id", "")
    if not user_id:
        return jsonify({"success": False, "error": "User ID is required"}), 400
    if sessions_col is None:
        return jsonify({"success": True, "sessions": []})
    try:
        sessions = []
        for s in sessions_col.find({"user_id": user_id}).sort("created_at", -1):
            sessions.append({
                "session_id": s.get("session_id"),
                "title":      s.get("title"),
                "created_at": s.get("created_at").isoformat() if s.get("created_at") else None
            })
        return jsonify({"success": True, "sessions": sessions})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/sessions/clear", methods=["POST"])
def clear_sessions():
    history_col, _, sessions_col = get_db()
    data    = request.get_json(silent=True) or {}
    user_id = data.get("user_id", "")
    if not user_id:
        return jsonify({"success": False, "error": "User ID is required"}), 400
    if history_col is None or sessions_col is None:
        return jsonify({"success": False, "error": "Database unavailable"}), 503
    try:
        history_col.delete_many({"user_id": user_id})
        sessions_col.delete_many({"user_id": user_id})
        return jsonify({"success": True})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


# ── Chat endpoint ─────────────────────────────────────────────────────────────
@app.route("/api/chat", methods=["POST"])
def chat():
    data       = request.get_json(silent=True) or {}
    prompt     = data.get("prompt", "")
    session_id = data.get("session_id", "default_session")
    model      = data.get("model", "magma2")
    attachment = data.get("attachment", None)
    user_id    = data.get("user_id", "default_user")
    deep_think = data.get("deep_think", False)

    if not prompt and not attachment:
        return jsonify({"success": False, "error": "Prompt or attachment is required"}), 400

    # Extract PDF text if applicable
    if attachment and (
        attachment.get("type") == "application/pdf"
        or attachment.get("name", "").lower().endswith(".pdf")
    ):
        pdf_b64 = attachment.get("data", "")
        if pdf_b64:
            extracted = extract_text_from_pdf(pdf_b64)
            if extracted:
                attachment["content"] = extracted

    # Fetch conversation history from MongoDB (non-fatal)
    history = []
    history_col, _, sessions_col = get_db()
    if history_col is not None:
        try:
            past = list(history_col.find({"session_id": session_id}).sort("timestamp", 1))
            for msg in past[-10:]:
                history.append({"role": msg.get("role"), "content": msg.get("content")})
        except Exception as exc:
            print("History fetch error:", exc)

    # Call AI
    result = query_volcano_ai(
        prompt, history=history, model=model,
        attachment=attachment, deep_think=deep_think
    )

    # Persist to MongoDB (non-fatal)
    if result.get("success") and history_col is not None:
        try:
            now = datetime.datetime.utcnow()
            if sessions_col is not None and not sessions_col.find_one({"session_id": session_id}):
                title = (
                    (prompt[:50] + ("..." if len(prompt) > 50 else ""))
                    if prompt else
                    (attachment.get("name", "Document") if attachment else "New Chat")
                )
                sessions_col.insert_one({
                    "session_id": session_id, "user_id": user_id,
                    "title": title, "created_at": now
                })
            history_col.insert_many([
                {
                    "session_id": session_id, "user_id": user_id,
                    "role": "user", "content": prompt,
                    "attachment": attachment, "timestamp": now
                },
                {
                    "session_id": session_id, "user_id": user_id,
                    "role": "assistant", "content": result.get("content"),
                    "reasoning": result.get("reasoning"), "timestamp": now + datetime.timedelta(seconds=1)
                }
            ])
        except Exception as exc:
            print("MongoDB write error:", exc)

    return jsonify(result)


# ── History endpoint ──────────────────────────────────────────────────────────
@app.route("/api/history", methods=["GET"])
def get_history():
    history_col, _, _ = get_db()
    session_id = request.args.get("session_id", "default_session")
    if history_col is None:
        return jsonify({"success": True, "history": []})
    try:
        history = []
        for msg in history_col.find({"session_id": session_id}).sort("timestamp", 1):
            history.append({
                "role":       msg.get("role"),
                "content":    msg.get("content"),
                "reasoning":  msg.get("reasoning"),
                "attachment": msg.get("attachment")
            })
        return jsonify({"success": True, "history": history})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


# ── Health check ──────────────────────────────────────────────────────────────
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "Volcano AI"})


# ── Static catch-all (registered LAST so API routes always win) ───────────────
@app.route("/<path:path>")
def serve_static(path):
    if path.startswith("api/"):
        return jsonify({"success": False, "error": f"API endpoint '/{path}' not found"}), 404
    return send_from_directory(".", path)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=True)
