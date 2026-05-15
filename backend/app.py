from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import os
import uuid
import fitz

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CHAT_FILE = os.path.join(
    BASE_DIR,
    "chats.json"
)

UPLOAD_FOLDER = os.path.join(
    BASE_DIR,
    "uploads"
)

# ================= CREATE FOLDERS =================

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

if not os.path.exists(CHAT_FILE):
    with open(CHAT_FILE, "w") as f:
        json.dump({}, f)

# ================= LOAD CHATS =================

def load_chats():

    with open(CHAT_FILE, "r") as f:
        return json.load(f)

# ================= SAVE CHATS =================

def save_chats(data):

    with open(CHAT_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ================= DELETE CHAT =================

@app.route("/delete_chat/<chat_id>", methods=["DELETE"])
def delete_chat(chat_id):

    chats = load_chats()

    if chat_id in chats:

        del chats[chat_id]

        save_chats(chats)

        return jsonify({
            "status": "deleted"
        })

    return jsonify({
        "status": "not found"
    })

# ================= ASK =================

@app.route("/ask", methods=["POST"])
def ask():

    data = request.get_json()

    message = str(
        data.get("message", "")
    ).strip()

    chat_id = data.get("chat_id")

    if chat_id in ["", "null", "undefined"]:
        chat_id = None

    chats = load_chats()

    # ================= CREATE CHAT =================

    if chat_id is None or chat_id not in chats:

        chat_id = str(uuid.uuid4())

        chats[chat_id] = {
            "title": message[:30],
            "messages": []
        }

    # ================= SAVE USER =================

    chats[chat_id]["messages"].append({
        "role": "user",
        "content": message
    })

    # ================= PROMPT =================

    prompt = f"""
You are EduGem AI,
a helpful educational AI assistant.

Answer shortly,
clearly,
and in simple words.

Question:
{message}

Answer:
"""

    try:

        print("Sending normal chat to Gemma...")

        response = requests.post(
            "http://127.0.0.1:11434/api/generate",
            json={
                # 🔥 FASTER MODEL
                "model": "gemma:2b",

                "prompt": prompt,

                "stream": False
            },

            # 🔥 LOWER TIMEOUT
            timeout=90
        )

        result = response.json()

        answer = result.get(
            "response",
            ""
        ).strip()

        if not answer:
            answer = "⚠️ No response"

    except Exception as e:

        print("CHAT ERROR:", e)

        answer = "❌ Backend error"

    # ================= SAVE AI =================

    chats[chat_id]["messages"].append({
        "role": "assistant",
        "content": answer
    })

    save_chats(chats)

    return jsonify({
        "answer": answer,
        "chat_id": chat_id
    })

# ================= PDF =================

@app.route("/upload_pdf", methods=["POST"])
def upload_pdf():

    print("PDF upload started")

    if "pdf" not in request.files:

        return jsonify({
            "answer": "❌ No PDF uploaded"
        })

    file = request.files["pdf"]

    filepath = os.path.join(
        UPLOAD_FOLDER,
        file.filename
    )

    file.save(filepath)

    text = ""

    try:

        # ================= READ PDF =================

        doc = fitz.open(filepath)

        for page in doc:
            text += page.get_text()

        doc.close()

        print("PDF extracted successfully")

        # 🔥 VERY IMPORTANT
        # Reduce CPU usage
        text = text[:1500]

        if len(text.strip()) == 0:

            return jsonify({
                "answer":
                "⚠️ Could not read PDF text"
            })

        # ================= PROMPT =================

        prompt = f"""
You are EduGem AI,
a smart educational AI assistant.

Read the PDF content below
and explain it clearly
in simple easy words.

PDF CONTENT:
{text}

EXPLANATION:
"""

        print("Sending PDF to Gemma...")

        # ================= GEMMA =================

        response = requests.post(
            "http://127.0.0.1:11434/api/generate",
            json={

                # 🔥 MUCH FASTER
                "model": "gemma:2b",

                "prompt": prompt,

                "stream": False
            },

            # 🔥 LOWER TIMEOUT
            timeout=120
        )

        result = response.json()

        print("Gemma response received")

        answer = result.get(
            "response",
            ""
        ).strip()

        if not answer:

            answer = (
                "⚠️ AI could not explain PDF"
            )

    except Exception as e:

        print("PDF ERROR:", e)

        answer = (
            "❌ PDF processing failed"
        )

    return jsonify({
        "answer": answer
    })

# ================= GET CHATS =================

@app.route("/chats", methods=["GET"])
def get_chats():

    return jsonify(load_chats())

# ================= SINGLE CHAT =================

@app.route("/chat/<chat_id>", methods=["GET"])
def get_chat(chat_id):

    chats = load_chats()

    return jsonify(
        chats.get(chat_id, {
            "messages": []
        })
    )

# ================= RUN =================

if __name__ == "__main__":

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )