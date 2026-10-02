"""
NeuroSeek AI — Flask Backend API
REST API for chat, conversations, settings, feedback
"""

import os
import sys
import json
import uuid
import hashlib
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import Database
from domain_engine.domains import get_domain, get_all_domains, get_domains_by_category, search_domains, CATEGORIES
from services.ai_engine import LocalAIEngine
from web_search.search import WebSearch

app = Flask(__name__, static_folder="../../frontend", static_url_path="")
CORS(app)

db = Database()
web_search = WebSearch()
ai_engine = LocalAIEngine(db, web_search)


@app.route("/")
def index():
    return send_from_directory("../../frontend", "index.html")


@app.route("/api/health")
def health():
    return jsonify({
        "status": "healthy",
        "web_search_available": web_search.is_available(),
        "domains_count": len(get_all_domains())
    })


@app.route("/api/domains")
def domains():
    domain_list = get_all_domains()
    return jsonify({
        "domains": domain_list,
        "categories": CATEGORIES
    })


@app.route("/api/domains/search")
def search_domains_api():
    query = request.args.get("q", "")
    if not query:
        return jsonify({"results": []})
    results = search_domains(query)
    return jsonify({"results": results})


@app.route("/api/conversations", methods=["GET"])
def get_conversations():
    conversations = db.get_conversations()
    return jsonify({"conversations": conversations})


@app.route("/api/conversations", methods=["POST"])
def create_conversation():
    data = request.get_json()
    title = data.get("title", "New Chat")
    domain_id = data.get("domain_id", "universal")
    conv_id = str(uuid.uuid4())[:12]
    db.create_conversation(conv_id, title, domain_id)
    return jsonify({"id": conv_id, "title": title, "domain_id": domain_id})


@app.route("/api/conversations/<conv_id>", methods=["GET"])
def get_conversation(conv_id):
    conversation = db.get_conversation(conv_id)
    if not conversation:
        return jsonify({"error": "Not found"}), 404
    messages = db.get_messages(conv_id)
    return jsonify({"conversation": conversation, "messages": messages})


@app.route("/api/conversations/<conv_id>", methods=["DELETE"])
def delete_conversation(conv_id):
    db.delete_conversation(conv_id)
    return jsonify({"status": "deleted"})


@app.route("/api/conversations/<conv_id>/title", methods=["PUT"])
def update_conversation_title(conv_id):
    data = request.get_json()
    title = data.get("title", "")
    if title:
        db.update_conversation_title(conv_id, title)
    return jsonify({"status": "updated"})


@app.route("/api/conversations/search", methods=["GET"])
def search_conversations():
    query = request.args.get("q", "")
    results = db.search_conversations(query)
    return jsonify({"results": results})


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_input = data.get("message", "")
    domain_id = data.get("domain_id", "universal")
    conv_id = data.get("conversation_id")

    if not user_input:
        return jsonify({"error": "Message required"}), 400

    # Create conversation if not exists
    if not conv_id:
        conv_id = str(uuid.uuid4())[:12]
        db.create_conversation(conv_id, user_input[:30], domain_id)

    # Save user message
    msg_id = str(uuid.uuid4())[:12]
    db.add_message(msg_id, conv_id, "user", user_input)

    # Get conversation history
    messages = db.get_messages(conv_id)
    history = [{"role": m["role"], "content": m["content"]} for m in messages[-10:]]

    # Generate response
    result = ai_engine.generate_response(user_input, domain_id, history)

    # Save AI response
    ai_msg_id = str(uuid.uuid4())[:12]
    db.add_message(ai_msg_id, conv_id, "assistant", result["response"], {
        "confidence": result["confidence"],
        "sources": result["sources"],
        "domain_used": result["domain_used"]
    })

    return jsonify({
        "response": result["response"],
        "confidence": result["confidence"],
        "sources": result["sources"],
        "domain_used": result["domain_used"],
        "conversation_id": conv_id
    })


@app.route("/api/feedback", methods=["POST"])
def feedback():
    data = request.get_json()
    fb_id = str(uuid.uuid4())[:12]
    db.add_feedback(
        fb_id=fb_id,
        message_id=data.get("message_id"),
        domain_id=data.get("domain_id", "universal"),
        fb_type=data.get("type", "general"),
        correction=data.get("correction"),
        context=data.get("context")
    )
    return jsonify({"status": "recorded"})


@app.route("/api/memory", methods=["GET"])
def get_memory():
    domain_id = request.args.get("domain_id")
    memories = db.get_learning_memory(domain_id)
    return jsonify({"memories": memories})


@app.route("/api/memory", methods=["DELETE"])
def clear_memory():
    db.clear_learning_memory()
    return jsonify({"status": "cleared"})


@app.route("/api/settings", methods=["GET"])
def get_settings():
    settings = {}
    for key in ["theme", "language", "response_style", "streaming", "auto_scroll", "enter_to_send", "show_citations", "web_verification", "voice_input"]:
        value = db.get_setting(key)
        if value:
            settings[key] = value
    return jsonify({"settings": settings})


@app.route("/api/settings", methods=["POST"])
def save_settings():
    data = request.get_json()
    for key, value in data.items():
        db.set_setting(key, str(value))
    return jsonify({"status": "saved"})


if __name__ == "__main__":
    print("🧠 NeuroSeek AI Backend starting...")
    print("📱 API: http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
