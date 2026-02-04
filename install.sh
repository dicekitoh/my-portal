#!/bin/bash
# Portal Management System - Installation Script
# Mac mini Server - Top 5 Priority System

set -e

PORTAL_DIR="$HOME/projects/portal"
BIN_DIR="$HOME/.local/bin"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  Installing Portal Management System         ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# 1. ディレクトリ作成
mkdir -p "$BIN_DIR"
mkdir -p "$PORTAL_DIR/backups"
mkdir -p "$PORTAL_DIR/templates"
mkdir -p "$HOME/logs"

# 2. 実行権限付与
chmod +x "$PORTAL_DIR/portal_manager.py"
chmod +x "$PORTAL_DIR/portal"

# 3. コマンドをPATHに追加
ln -sf "$PORTAL_DIR/portal" "$BIN_DIR/portal"

# 4. PATHに追加（まだの場合）
if ! grep -q ".local/bin" "$HOME/.bashrc"; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
    echo "Added ~/.local/bin to PATH"
fi

# 5. システム優先度ファイル作成
cat > "$HOME/projects/SYSTEMS_PRIORITY.md" << 'EOF'
# Mac mini Server - System Priority List

## Top 5 Priority Systems

| Rank | System | Directory | Description |
|------|--------|-----------|-------------|
| 1 | - | - | (Reserved) |
| 2 | - | - | (Reserved) |
| 3 | - | - | (Reserved) |
| 4 | - | - | (Reserved) |
| 5 | Portal Site | ~/projects/portal | Web portal management system |

## Portal Site System

- **URL**: https://dicekitoh.github.io/my-portal/
- **Local**: http://localhost:8085
- **Command**: `portal` (CLI tool)
- **Config**: ~/projects/portal/config.json
- **Logs**: ~/logs/portal_manager.log

### Quick Commands
```bash
portal status   # Show status
portal deploy   # Deploy changes
portal create   # Create new page
portal backup   # Backup site
```

EOF

echo ""
echo "Installation complete!"
echo ""
echo "Usage:"
echo "  portal          - Show help"
echo "  portal status   - Show site status"
echo "  portal deploy   - Deploy to GitHub"
echo ""
echo "Restart your shell or run: source ~/.bashrc"
echo ""
