#!/usr/bin/env python3
"""
お知らせカード管理システム
Google Keep風カードUIでポータルのお知らせを管理
"""

import os
import sys
import json
import hashlib
import fcntl
import subprocess
import secrets
from datetime import datetime
from pathlib import Path
from functools import wraps

from flask import (
    Flask, request, jsonify, render_template,
    session, redirect, url_for
)

# パス設定
BASE_DIR = Path(__file__).parent.parent
DATA_FILE = BASE_DIR / "data" / "news.json"
NEWS_HTML = BASE_DIR / "news.html"

# Flask設定
app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# 認証用ハッシュ（既存ポータルと同一）
ADMIN_HASH = "5fac9782738bc55eeb2688891075f9e37fb6779d5f31786acc0d259ec5b3a2e7"


# --- データ操作 ---

def load_cards():
    """JSONからカードデータを読み込む"""
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_SH)
        data = json.load(f)
        fcntl.flock(f, fcntl.LOCK_UN)
    return data


def save_cards(data):
    """カードデータをJSONに保存"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        json.dump(data, f, ensure_ascii=False, indent=4)
        fcntl.flock(f, fcntl.LOCK_UN)


# --- 認証 ---

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("authenticated"):
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"error": "認証が必要です"}), 401
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    password = request.form.get("password", "")
    pw_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()

    if pw_hash == ADMIN_HASH:
        session["authenticated"] = True
        return redirect(url_for("manager"))

    return render_template("login.html", error="パスワードが違います")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# --- UI ---

@app.route("/")
def index():
    return redirect(url_for("login"))


@app.route("/manager")
@login_required
def manager():
    return render_template("manager.html")


# --- API ---

@app.route("/api/cards", methods=["GET"])
@login_required
def get_cards():
    data = load_cards()
    return jsonify(data["cards"])


@app.route("/api/cards", methods=["POST"])
@login_required
def create_card():
    body = request.get_json()
    if not body or not body.get("title") or not body.get("content"):
        return jsonify({"error": "title と content は必須です"}), 400

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    # IDにタイトルの一部を使用
    slug = body.get("slug", "item")
    card_id = f"news-{date_str.replace('-', '')}-{slug}"

    card = {
        "id": card_id,
        "title": body["title"],
        "content": body["content"],
        "date": date_str,
        "date_display": f"{now.year}年{now.month}月{now.day}日",
        "visible": True,
        "created_at": now.isoformat(timespec="seconds"),
    }

    data = load_cards()

    # ID重複チェック - 重複する場合はサフィックス追加
    existing_ids = {c["id"] for c in data["cards"]}
    if card_id in existing_ids:
        i = 2
        while f"{card_id}-{i}" in existing_ids:
            i += 1
        card["id"] = f"{card_id}-{i}"

    data["cards"].insert(0, card)
    save_cards(data)

    return jsonify(card), 201


@app.route("/api/cards/<card_id>", methods=["PUT"])
@login_required
def update_card(card_id):
    body = request.get_json()
    if not body:
        return jsonify({"error": "リクエストボディが必要です"}), 400

    data = load_cards()
    for card in data["cards"]:
        if card["id"] == card_id:
            if "title" in body:
                card["title"] = body["title"]
            if "content" in body:
                card["content"] = body["content"]
            save_cards(data)
            return jsonify(card)

    return jsonify({"error": "カードが見つかりません"}), 404


@app.route("/api/cards/<card_id>", methods=["DELETE"])
@login_required
def delete_card(card_id):
    data = load_cards()
    original_len = len(data["cards"])
    data["cards"] = [c for c in data["cards"] if c["id"] != card_id]

    if len(data["cards"]) == original_len:
        return jsonify({"error": "カードが見つかりません"}), 404

    save_cards(data)
    return jsonify({"ok": True})


@app.route("/api/cards/<card_id>/toggle", methods=["PATCH"])
@login_required
def toggle_card(card_id):
    data = load_cards()
    for card in data["cards"]:
        if card["id"] == card_id:
            card["visible"] = not card["visible"]
            save_cards(data)
            return jsonify(card)

    return jsonify({"error": "カードが見つかりません"}), 404


# --- デプロイ ---

def generate_news_html(cards):
    """news.json から静的 news.html を生成"""
    visible_cards = [c for c in cards if c.get("visible", True)]

    articles = ""
    for card in visible_cards:
        title = card["title"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        content = card["content"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        date_display = card.get("date_display", card["date"])
        card_id = card["id"]

        articles += f'''        <article class="news-item" data-news-id="{card_id}">
            <button class="visibility-btn" onclick="toggleVisibility(this)"></button>
            <h3>{title}</h3>
            <div class="date">{date_display}</div>
            <p>{content}</p>
        </article>
'''

    html = f'''<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>お知らせ - My Portal</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Hiragino Sans", sans-serif;
            background-color: #ffffff;
            color: #333;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }}
        header {{ padding: 2rem; text-align: center; border-bottom: 1px solid #eee; }}
        header h1 {{ font-size: 1.8rem; font-weight: 300; }}
        main {{ flex: 1; padding: 2rem; max-width: 800px; margin: 0 auto; width: 100%; }}
        .news-item {{ background: #f9f9f9; padding: 1.5rem; border-radius: 8px; margin-bottom: 1.5rem; position: relative; }}
        .news-item h3 {{ font-size: 1.1rem; margin-bottom: 0.5rem; }}
        .news-item .date {{ font-size: 0.85rem; color: #888; margin-bottom: 0.8rem; }}
        .news-item p {{ line-height: 1.6; }}
        .back-link {{ display: block; text-align: center; margin-top: 2rem; color: #666; text-decoration: none; }}
        .back-link:hover {{ color: #333; }}
        footer {{ padding: 1rem; text-align: center; border-top: 1px solid #eee; font-size: 0.8rem; color: #999; }}

        /* 管理者モード */
        .admin-toggle {{
            cursor: pointer;
            user-select: none;
            color: #ccc;
            font-size: 0.75rem;
            transition: color 0.2s;
        }}
        .admin-toggle:hover {{ color: #999; }}
        .admin-toggle.active {{ color: #e74c3c; }}

        .visibility-btn {{
            display: none;
            position: absolute;
            top: 1rem;
            right: 1rem;
            border: none;
            border-radius: 6px;
            padding: 0.4rem 0.8rem;
            font-size: 0.8rem;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .visibility-btn.showing {{ background: #27ae60; color: #fff; }}
        .visibility-btn.hidden {{ background: #e74c3c; color: #fff; }}
        .visibility-btn:hover {{ opacity: 0.85; }}

        body.admin-mode .visibility-btn {{ display: block; }}
        body.admin-mode .news-item.is-hidden {{
            opacity: 0.4;
            border: 2px dashed #e74c3c;
        }}

        .admin-bar {{
            display: none;
            background: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 8px;
            padding: 0.8rem 1.2rem;
            margin-bottom: 1.5rem;
            font-size: 0.9rem;
            color: #856404;
            text-align: center;
        }}
        .admin-bar .logout-btn {{
            background: #dc3545;
            color: #fff;
            border: none;
            border-radius: 4px;
            padding: 0.3rem 0.8rem;
            margin-left: 1rem;
            font-size: 0.8rem;
            cursor: pointer;
        }}
        .admin-bar .logout-btn:hover {{ opacity: 0.85; }}
        body.admin-mode .admin-bar {{ display: block; }}

        /* パスワードダイアログ */
        .pw-overlay {{
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.4);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }}
        .pw-overlay.show {{ display: flex; }}
        .pw-dialog {{
            background: #fff;
            border-radius: 12px;
            padding: 2rem;
            width: 320px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.2);
            text-align: center;
        }}
        .pw-dialog h3 {{ font-size: 1rem; margin-bottom: 1rem; font-weight: 500; }}
        .pw-dialog input {{
            width: 100%;
            padding: 0.6rem 0.8rem;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 0.95rem;
            outline: none;
        }}
        .pw-dialog input:focus {{ border-color: #666; }}
        .pw-dialog .pw-actions {{
            margin-top: 1rem;
            display: flex;
            gap: 0.5rem;
        }}
        .pw-dialog .pw-actions button {{
            flex: 1;
            padding: 0.5rem;
            border: none;
            border-radius: 6px;
            font-size: 0.9rem;
            cursor: pointer;
        }}
        .pw-dialog .btn-login {{ background: #333; color: #fff; }}
        .pw-dialog .btn-login:hover {{ background: #555; }}
        .pw-dialog .btn-cancel {{ background: #eee; color: #333; }}
        .pw-dialog .btn-cancel:hover {{ background: #ddd; }}
        .pw-error {{ color: #e74c3c; font-size: 0.8rem; margin-top: 0.5rem; min-height: 1.2em; }}
    </style>
</head>
<body>
    <header>
        <h1>お知らせ</h1>
    </header>
    <main>
        <div class="admin-bar">
            管理者モード — 各お知らせの表示/非表示を切り替えできます
            <button class="logout-btn" onclick="logoutAdmin()">ログアウト</button>
        </div>

{articles}        <a href="index.html" class="back-link">← トップに戻る</a>
    </main>
    <footer>
        <p>&copy; 2026 My Portal <span class="admin-toggle" id="adminToggle" onclick="toggleAdmin()">&#9881;</span></p>
    </footer>

    <!-- パスワードダイアログ -->
    <div class="pw-overlay" id="pwOverlay">
        <div class="pw-dialog">
            <h3>管理者パスワード</h3>
            <input type="password" id="pwInput" placeholder="パスワードを入力">
            <div class="pw-error" id="pwError"></div>
            <div class="pw-actions">
                <button class="btn-cancel" onclick="closePwDialog()">キャンセル</button>
                <button class="btn-login" onclick="submitPassword()">ログイン</button>
            </div>
        </div>
    </div>

    <script>
        var STORAGE_KEY = 'portal_news_hidden';
        var AUTH_KEY = 'portal_news_admin';
        var ADMIN_HASH = '5fac9782738bc55eeb2688891075f9e37fb6779d5f31786acc0d259ec5b3a2e7';
        var adminMode = false;

        // SHA-256
        async function sha256(text) {{
            var data = new TextEncoder().encode(text);
            var buf = await crypto.subtle.digest('SHA-256', data);
            return Array.from(new Uint8Array(buf)).map(function(b) {{
                return b.toString(16).padStart(2, '0');
            }}).join('');
        }}

        // --- 表示/非表示管理 ---
        function getHiddenIds() {{
            try {{ return JSON.parse(localStorage.getItem(STORAGE_KEY)) || []; }}
            catch(e) {{ return []; }}
        }}

        function saveHiddenIds(ids) {{
            localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
        }}

        function applyVisibility() {{
            var hiddenIds = getHiddenIds();
            document.querySelectorAll('.news-item').forEach(function(item) {{
                var id = item.getAttribute('data-news-id');
                var isHidden = hiddenIds.indexOf(id) !== -1;
                var btn = item.querySelector('.visibility-btn');

                if (isHidden) {{
                    item.classList.add('is-hidden');
                    item.style.display = adminMode ? '' : 'none';
                    btn.textContent = '非表示中';
                    btn.className = 'visibility-btn hidden';
                }} else {{
                    item.classList.remove('is-hidden');
                    item.style.display = '';
                    btn.textContent = '表示中';
                    btn.className = 'visibility-btn showing';
                }}
            }});
        }}

        function toggleVisibility(btn) {{
            var item = btn.closest('.news-item');
            var id = item.getAttribute('data-news-id');
            var hiddenIds = getHiddenIds();
            var idx = hiddenIds.indexOf(id);
            if (idx !== -1) hiddenIds.splice(idx, 1);
            else hiddenIds.push(id);
            saveHiddenIds(hiddenIds);
            applyVisibility();
        }}

        // --- 管理者認証 ---
        function enterAdmin() {{
            adminMode = true;
            document.body.classList.add('admin-mode');
            document.getElementById('adminToggle').classList.add('active');
            sessionStorage.setItem(AUTH_KEY, '1');
            applyVisibility();
        }}

        function logoutAdmin() {{
            adminMode = false;
            document.body.classList.remove('admin-mode');
            document.getElementById('adminToggle').classList.remove('active');
            sessionStorage.removeItem(AUTH_KEY);
            applyVisibility();
        }}

        function toggleAdmin() {{
            if (adminMode) {{
                logoutAdmin();
                return;
            }}
            if (sessionStorage.getItem(AUTH_KEY) === '1') {{
                enterAdmin();
                return;
            }}
            openPwDialog();
        }}

        // --- パスワードダイアログ ---
        function openPwDialog() {{
            document.getElementById('pwOverlay').classList.add('show');
            document.getElementById('pwInput').value = '';
            document.getElementById('pwError').textContent = '';
            document.getElementById('pwInput').focus();
        }}

        function closePwDialog() {{
            document.getElementById('pwOverlay').classList.remove('show');
        }}

        async function submitPassword() {{
            var input = document.getElementById('pwInput').value;
            if (!input) return;
            var hash = await sha256(input);
            if (hash === ADMIN_HASH) {{
                closePwDialog();
                enterAdmin();
            }} else {{
                document.getElementById('pwError').textContent = 'パスワードが違います';
                document.getElementById('pwInput').value = '';
                document.getElementById('pwInput').focus();
            }}
        }}

        document.getElementById('pwInput').addEventListener('keypress', function(e) {{
            if (e.key === 'Enter') submitPassword();
        }});

        document.getElementById('pwOverlay').addEventListener('click', function(e) {{
            if (e.target === this) closePwDialog();
        }});

        // ページ読み込み時
        applyVisibility();
    </script>
</body>
</html>'''

    return html


@app.route("/api/deploy", methods=["POST"])
@login_required
def deploy():
    try:
        data = load_cards()

        # 1. news.html を生成
        html = generate_news_html(data["cards"])
        with open(NEWS_HTML, "w", encoding="utf-8") as f:
            f.write(html)

        # 2. git add, commit, push
        os.chdir(BASE_DIR)
        subprocess.run(["git", "add", "news.html", "data/news.json"], check=True)

        msg = f"Update news - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        result = subprocess.run(
            ["git", "commit", "-m", msg],
            capture_output=True, text=True
        )

        if result.returncode != 0 and "nothing to commit" in result.stdout:
            return jsonify({"ok": True, "message": "変更はありません"})

        if result.returncode != 0:
            return jsonify({"error": f"git commit 失敗: {result.stderr}"}), 500

        push_result = subprocess.run(
            ["git", "push"],
            capture_output=True, text=True
        )

        if push_result.returncode != 0:
            return jsonify({"error": f"git push 失敗: {push_result.stderr}"}), 500

        return jsonify({
            "ok": True,
            "message": f"デプロイ完了: {msg}"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8086, debug=False)
