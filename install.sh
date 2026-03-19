#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN_DIR="$HOME/.local/bin"
APP_DIR="$HOME/.local/share/applications"
MIME_DIR="$HOME/.local/share/mime/packages"

ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"

mkdir -p "$BIN_DIR" "$APP_DIR" "$MIME_DIR" "$ICON_DIR"

# Install the binary
ln -sf "$SCRIPT_DIR/jsonl-viewer.py" "$BIN_DIR/jsonl-viewer"

# Install icon and desktop entry
cp "$SCRIPT_DIR/data/icons/hicolor/scalable/apps/dev.jorj.jsonl-viewer-symbolic.svg" "$ICON_DIR/"
cp "$SCRIPT_DIR/dev.jorj.jsonl-viewer.desktop" "$APP_DIR/"

# Register MIME types for .jsonl and .ndjson files
cat > "$MIME_DIR/jsonl-viewer.xml" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
  <mime-type type="application/x-ndjson">
    <comment>Newline-delimited JSON</comment>
    <glob pattern="*.jsonl"/>
    <glob pattern="*.ndjson"/>
  </mime-type>
</mime-info>
EOF

# Update MIME, desktop, and icon databases
update-mime-database "$HOME/.local/share/mime" 2>/dev/null || true
update-desktop-database "$APP_DIR" 2>/dev/null || true
gtk-update-icon-cache "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

echo "Installed successfully."
echo "  Binary:  $BIN_DIR/jsonl-viewer"
echo "  Desktop: $APP_DIR/dev.jorj.jsonl-viewer.desktop"
echo "  MIME:    $MIME_DIR/jsonl-viewer.xml"
echo ""
echo "Make sure $BIN_DIR is in your PATH."
