from flask import Flask, request, jsonify
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
password = urllib.parse.quote_plus("Volcano@2026")
mongo_uri = f"mongodb+srv://adminvolcano_db_user:{password}@volcano.fczkc5w.mongodb.net/?appName=Volcano"
mongo_client = MongoClient(mongo_uri)
db = mongo_client["volcano_db"]
history_collection = db["chat_history"]

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

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json or {}
    prompt = data.get('prompt', '')
    session_id = data.get('session_id', 'default_session')
    model = data.get('model', 'magma2')
    attachment = data.get('attachment', None)
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
            history_collection.insert_many([
                {
                    "session_id": session_id,
                    "role": "user",
                    "content": prompt,
                    "attachment": attachment,
                    "timestamp": now
                },
                {
                    "session_id": session_id,
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
    # Start the server on port 5001 to avoid conflicts with http-server
    app.run(host='0.0.0.0', port=5001, debug=True)
