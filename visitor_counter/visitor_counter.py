#!/usr/bin/env python3
"""
訪問者カウンター - OS/デバイス別トラッキング
"""

import json
import fcntl
import re
import uuid
from datetime import datetime
from pathlib import Path

from flask import Flask, request, jsonify, render_template, make_response

# パス設定
BASE_DIR = Path(__file__).parent.parent
DATA_FILE = BASE_DIR / "data" / "visitors.json"

# Flask設定
app = Flask(__name__)

# OS判別パターン（順序が重要）
OS_PATTERNS = [
    ("ChromeOS", re.compile(r"CrOS")),
    ("iOS", re.compile(r"iPhone|iPad|iPod")),
    ("Android", re.compile(r"Android")),
    ("Windows", re.compile(r"Windows")),
    ("macOS", re.compile(r"Macintosh|Mac OS X")),
    ("Linux", re.compile(r"Linux")),
]


def detect_os(user_agent):
    """User-Agent文字列からOS名を判別"""
    if not user_agent:
        return "Other"
    for os_name, pattern in OS_PATTERNS:
        if pattern.search(user_agent):
            return os_name
    return "Other"


def load_data():
    """JSONからカウントデータを読み込む"""
    if not DATA_FILE.exists():
        return {"total": 0, "by_os": {}, "daily": {}}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_SH)
        data = json.load(f)
        fcntl.flock(f, fcntl.LOCK_UN)
    return data


def save_data(data):
    """カウントデータをJSONに保存"""
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        json.dump(data, f, ensure_ascii=False, indent=2)
        fcntl.flock(f, fcntl.LOCK_UN)


@app.route("/api/visit", methods=["POST"])
def record_visit():
    """訪問を記録（Cookie で1日1回のみ）"""
    today = datetime.now().strftime("%Y-%m-%d")
    visitor_id = request.cookies.get("visitor_id")
    last_visit = request.cookies.get("last_visit")

    # 今日すでにカウント済みならスキップ
    if visitor_id and last_visit == today:
        data = load_data()
        resp = make_response(jsonify({
            "counted": False,
            "total": data.get("total", 0),
            "by_os": data.get("by_os", {})
        }))
        return resp

    # 新規またはその日初回 → カウント
    if not visitor_id:
        visitor_id = str(uuid.uuid4())

    user_agent = request.headers.get("User-Agent", "")
    os_name = detect_os(user_agent)

    data = load_data()
    data["total"] = data.get("total", 0) + 1
    by_os = data.setdefault("by_os", {})
    by_os[os_name] = by_os.get(os_name, 0) + 1

    daily = data.setdefault("daily", {})
    day_data = daily.setdefault(today, {"total": 0, "by_os": {}})
    day_data["total"] = day_data.get("total", 0) + 1
    day_by_os = day_data.setdefault("by_os", {})
    day_by_os[os_name] = day_by_os.get(os_name, 0) + 1

    save_data(data)

    resp = make_response(jsonify({
        "counted": True,
        "total": data["total"],
        "by_os": data["by_os"]
    }))
    resp.set_cookie("visitor_id", visitor_id, max_age=365 * 24 * 3600, httponly=True)
    resp.set_cookie("last_visit", today, max_age=24 * 3600, httponly=True)
    return resp


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """OS別カウントを返す"""
    data = load_data()
    return jsonify({
        "total": data.get("total", 0),
        "by_os": data.get("by_os", {}),
        "daily": data.get("daily", {})
    })


@app.route("/dashboard")
def dashboard():
    """管理者ダッシュボード"""
    data = load_data()
    return render_template("dashboard.html", data=data)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8087, debug=False)
