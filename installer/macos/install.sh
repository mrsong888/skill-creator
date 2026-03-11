#!/bin/bash
# Agent Skill Extension - macOS Installer
# Installs the Chrome extension via External Extensions JSON

set -e

EXTENSION_ID="agent-skill-extension"
EXTENSION_DIR="$HOME/Library/Application Support/AgentSkillExtension"
EXTERNAL_EXTENSIONS_DIR="/Library/Google/Chrome/External Extensions"
BACKEND_URL="${1:-http://localhost:8001}"

echo "=== Agent Skill Extension Installer (macOS) ==="
echo ""

# Copy extension files
echo "[1/3] Copying extension files..."
mkdir -p "$EXTENSION_DIR"
cp -R "$(dirname "$0")/../../frontend/dist/"* "$EXTENSION_DIR/"
echo "  -> Installed to: $EXTENSION_DIR"

# Write managed config
echo "[2/3] Writing configuration..."
CONFIG_DIR="$HOME/.config/agent-skill-extension"
mkdir -p "$CONFIG_DIR"
cat > "$CONFIG_DIR/config.json" << EOF
{
  "backend_url": "$BACKEND_URL"
}
EOF
echo "  -> Backend URL: $BACKEND_URL"

# Write External Extensions JSON (requires admin for system-wide)
echo "[3/3] Registering Chrome extension..."
PREFS_FILE="$HOME/Library/Application Support/Google/Chrome/External Extensions/$EXTENSION_ID.json"
mkdir -p "$(dirname "$PREFS_FILE")"
cat > "$PREFS_FILE" << EOF
{
  "external_crx": "$EXTENSION_DIR",
  "external_version": "0.1.0"
}
EOF

echo ""
echo "=== Installation complete ==="
echo "Please restart Chrome to load the extension."
echo "Or load manually: chrome://extensions -> Load unpacked -> $EXTENSION_DIR"
