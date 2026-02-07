#!/usr/bin/env python3
"""
チャットボット - Gemini APIプロキシ（訪問者向け）
"""

import os

import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins="*")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

SYSTEM_PROMPT = """あなたは個人ポータルサイト「My Portal」のAIアシスタントです。

以下のルールに従って応答してください：
- 丁寧で親しみやすい日本語でお話しします
- 訪問者の質問や相談に、誠実にお答えします
- わからないことは正直に「わかりかねます」とお伝えします
- 簡潔でわかりやすい回答を心がけます
"""


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

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
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
        return jsonify({"reply": reply})
    except requests.exceptions.Timeout:
        return jsonify({"error": "Gemini API timeout"}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Gemini API error: {str(e)}"}), 502
    except (KeyError, IndexError):
        return jsonify({"error": "Unexpected response from Gemini API"}), 502


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8088, debug=False)
