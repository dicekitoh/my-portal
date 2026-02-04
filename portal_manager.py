#!/usr/bin/env python3
"""
Portal Site Management System
Mac mini Server - Top 5 Priority System

機能:
- ページの追加・編集・削除
- 自動デプロイ（GitHub Pages）
- バックアップ管理
- サイト状態監視
- メール通知
"""

import os
import sys
import json
import subprocess
import shutil
from datetime import datetime
from pathlib import Path

# プロジェクトディレクトリ
PROJECT_DIR = Path(__file__).parent
CONFIG_FILE = PROJECT_DIR / "config.json"
BACKUP_DIR = PROJECT_DIR / "backups"
TEMPLATES_DIR = PROJECT_DIR / "templates"
LOG_FILE = Path.home() / "logs" / "portal_manager.log"


class PortalManager:
    def __init__(self):
        self.load_config()
        self.ensure_directories()

    def load_config(self):
        """設定ファイルを読み込む"""
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

    def save_config(self):
        """設定ファイルを保存する"""
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=4)

    def ensure_directories(self):
        """必要なディレクトリを作成"""
        BACKUP_DIR.mkdir(exist_ok=True)
        TEMPLATES_DIR.mkdir(exist_ok=True)
        LOG_FILE.parent.mkdir(exist_ok=True)

    def log(self, message):
        """ログを記録"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_entry + "\n")

    def status(self):
        """サイトの状態を表示"""
        print("\n" + "="*50)
        print(f"  {self.config['site']['name']} - Status")
        print("="*50)
        print(f"\n  URL: {self.config['site']['url']}")
        print(f"  Local: {self.config['site']['local_url']}")
        print(f"\n  Pages:")
        for page in self.config['pages']:
            protected = " [Protected]" if page.get('protected') else ""
            file_path = PROJECT_DIR / page['file']
            exists = "OK" if file_path.exists() else "MISSING"
            print(f"    - {page['title']}: {exists}{protected}")
        print("\n" + "="*50 + "\n")

    def list_pages(self):
        """ページ一覧を表示"""
        print("\nPages:")
        for i, page in enumerate(self.config['pages'], 1):
            protected = " [Protected]" if page.get('protected') else ""
            print(f"  {i}. {page['title']} ({page['file']}){protected}")
        print()

    def create_page(self, page_id, title, protected=False):
        """新しいページを作成"""
        filename = f"{page_id}.html"
        file_path = PROJECT_DIR / filename

        if file_path.exists():
            self.log(f"Error: {filename} already exists")
            return False

        # テンプレートからページを生成
        template = self._get_template(protected)
        content = template.replace("{{TITLE}}", title)
        content = content.replace("{{SITE_NAME}}", self.config['site']['name'])

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        # 設定に追加
        self.config['pages'].append({
            "id": page_id,
            "title": title,
            "file": filename,
            "protected": protected
        })
        self.save_config()

        # index.htmlにリンクを追加
        self._add_link_to_index(title, filename)

        self.log(f"Created new page: {title} ({filename})")
        return True

    def _get_template(self, protected=False):
        """ページテンプレートを取得"""
        return '''<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{TITLE}} - {{SITE_NAME}}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Hiragino Sans', sans-serif;
            background-color: #ffffff;
            color: #333;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }
        header { padding: 2rem; text-align: center; border-bottom: 1px solid #eee; }
        header h1 { font-size: 1.8rem; font-weight: 300; }
        main { flex: 1; padding: 2rem; max-width: 800px; margin: 0 auto; width: 100%; }
        .content { background: #f9f9f9; padding: 1.5rem; border-radius: 8px; margin-bottom: 1.5rem; }
        .back-link { display: block; text-align: center; margin-top: 2rem; color: #666; text-decoration: none; }
        .back-link:hover { color: #333; }
        footer { padding: 1rem; text-align: center; border-top: 1px solid #eee; font-size: 0.8rem; color: #999; }
    </style>
</head>
<body>
    <header>
        <h1>{{TITLE}}</h1>
    </header>
    <main>
        <div class="content">
            <p>ここにコンテンツを追加してください。</p>
        </div>
        <a href="index.html" class="back-link">← トップに戻る</a>
    </main>
    <footer>
        <p>&copy; 2025 {{SITE_NAME}}</p>
    </footer>
</body>
</html>'''

    def _add_link_to_index(self, title, filename):
        """index.htmlにリンクを追加"""
        index_path = PROJECT_DIR / "index.html"
        with open(index_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # リンクセクションを見つけて追加
        link_html = f'            <a href="{filename}">{title}</a>\n'
        insert_pos = content.find('</nav>')
        if insert_pos != -1:
            content = content[:insert_pos] + link_html + content[insert_pos:]
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write(content)

    def backup(self):
        """現在のサイトをバックアップ"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"backup_{timestamp}"

        # HTMLファイルをコピー
        backup_path.mkdir(exist_ok=True)
        for f in PROJECT_DIR.glob("*.html"):
            shutil.copy(f, backup_path)
        shutil.copy(CONFIG_FILE, backup_path)

        self.log(f"Backup created: {backup_path}")
        return backup_path

    def deploy(self, message=None):
        """GitHubにデプロイ"""
        if self.config['settings'].get('backup_before_deploy'):
            self.backup()

        if not message:
            message = f"Update portal - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        try:
            os.chdir(PROJECT_DIR)
            subprocess.run(["git", "add", "-A"], check=True)
            subprocess.run(["git", "commit", "-m", message], check=True)
            subprocess.run(["git", "push"], check=True)
            self.log(f"Deployed: {message}")

            # 通知送信
            if self.config['settings'].get('notification_email'):
                self._send_notification(f"Portal deployed: {message}")

            return True
        except subprocess.CalledProcessError as e:
            self.log(f"Deploy failed: {e}")
            return False

    def _send_notification(self, message):
        """メール通知を送信"""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            sender_email = 'itoh@thinksblog.com'
            sender_password = '***REMOVED***'
            to_email = self.config['settings']['notification_email']

            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = to_email
            msg['Subject'] = f'[Mac mini] Portal Update'

            body = f"""
Portal Site Update Notification
================================
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Message: {message}
URL: {self.config['site']['url']}
"""
            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            server.quit()
            self.log("Notification sent")
        except Exception as e:
            self.log(f"Notification failed: {e}")

    def check_online(self):
        """オンライン状態を確認"""
        import urllib.request
        try:
            url = self.config['site']['url']
            response = urllib.request.urlopen(url, timeout=10)
            if response.status == 200:
                self.log(f"Site is online: {url}")
                return True
        except Exception as e:
            self.log(f"Site check failed: {e}")
        return False


def main():
    manager = PortalManager()

    if len(sys.argv) < 2:
        print("""
Portal Manager - Usage:
  python portal_manager.py status      - Show site status
  python portal_manager.py list        - List all pages
  python portal_manager.py create ID TITLE - Create new page
  python portal_manager.py backup      - Create backup
  python portal_manager.py deploy [MSG] - Deploy to GitHub
  python portal_manager.py check       - Check online status
""")
        return

    command = sys.argv[1]

    if command == "status":
        manager.status()
    elif command == "list":
        manager.list_pages()
    elif command == "create":
        if len(sys.argv) < 4:
            print("Usage: create ID TITLE")
            return
        page_id = sys.argv[2]
        title = " ".join(sys.argv[3:])
        manager.create_page(page_id, title)
    elif command == "backup":
        manager.backup()
    elif command == "deploy":
        message = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else None
        manager.deploy(message)
    elif command == "check":
        manager.check_online()
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
