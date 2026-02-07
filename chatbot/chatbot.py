#!/usr/bin/env python3
"""
チャットボット - Gemini APIプロキシ（記憶・ログ機能付き）
"""

import json
import os
import uuid
from datetime import datetime

import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins="*")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
MEMORY_FILE = os.path.join(DATA_DIR, "chat_memory.json")
LOGS_FILE = os.path.join(DATA_DIR, "chat_logs.json")

SYSTEM_PROMPT = """あなたは「ふじのすけ」専用のAIアシスタントです。
親しみやすく、カジュアルな日本語で応答してください。
丁寧すぎる敬語は不要です。友人のように話してください。

以下はユーザーについて記憶している情報です。会話の中で自然に活用してください：
{memories}
"""


def load_json(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def build_system_prompt():
    memories = load_json(MEMORY_FILE)
    if memories:
        mem_text = "\n".join(f"- {m['text']}" for m in memories)
    else:
        mem_text = "（まだ記憶はありません）"
    return SYSTEM_PROMPT.format(memories=mem_text)


def append_log(role, text):
    logs = load_json(LOGS_FILE)
    logs.append({
        "timestamp": datetime.now().isoformat(),
        "role": role,
        "text": text,
    })
    save_json(LOGS_FILE, logs)


@app.route("/api/chat", methods=["POST"])
def chat():
    """ユーザーメッセージをGemini APIに送信し応答を返す"""
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "message is required"}), 400

    if not GEMINI_API_KEY:
        return jsonify({"error": "GEMINI_API_KEY not configured"}), 500

    user_message = data["message"]
    history = data.get("history", [])

    # Gemini API用のcontentsを構築
    contents = []
    for entry in history:
        role = "user" if entry.get("role") == "user" else "model"
        contents.append({
            "role": role,
            "parts": [{"text": entry["text"]}]
        })
    contents.append({
        "role": "user",
        "parts": [{"text": user_message}]
    })

    # システムプロンプトを構築
    system_instruction = {
        "parts": [{"text": build_system_prompt()}]
    }

    payload = {
        "system_instruction": system_instruction,
        "contents": contents,
    }

    try:
        resp = requests.post(
            GEMINI_URL,
            params={"key": GEMINI_API_KEY},
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()
        reply = result["candidates"][0]["content"]["parts"][0]["text"]

        # ログ保存
        append_log("user", user_message)
        append_log("model", reply)

        return jsonify({"reply": reply})
    except requests.exceptions.Timeout:
        return jsonify({"error": "Gemini API timeout"}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Gemini API error: {str(e)}"}), 502
    except (KeyError, IndexError):
        return jsonify({"error": "Unexpected response from Gemini API"}), 502


# --- 記憶 API ---

@app.route("/api/chat/memory", methods=["GET"])
def get_memory():
    memories = load_json(MEMORY_FILE)
    return jsonify(memories)


@app.route("/api/chat/memory", methods=["POST"])
def add_memory():
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "text is required"}), 400
    memories = load_json(MEMORY_FILE)
    entry = {
        "id": str(uuid.uuid4())[:8],
        "text": data["text"],
        "created_at": datetime.now().isoformat(),
    }
    memories.append(entry)
    save_json(MEMORY_FILE, memories)
    return jsonify(entry), 201


@app.route("/api/chat/memory/<memory_id>", methods=["DELETE"])
def delete_memory(memory_id):
    memories = load_json(MEMORY_FILE)
    memories = [m for m in memories if m["id"] != memory_id]
    save_json(MEMORY_FILE, memories)
    return jsonify({"ok": True})


# --- ログ API ---

@app.route("/api/chat/logs", methods=["GET"])
def get_logs():
    logs = load_json(LOGS_FILE)
    return jsonify(logs[-100:])


@app.route("/api/chat/logs", methods=["DELETE"])
def clear_logs():
    save_json(LOGS_FILE, [])
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8088, debug=False)
