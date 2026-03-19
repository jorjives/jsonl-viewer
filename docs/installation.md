---
layout: default
title: Installation
nav_order: 2
---

# Installation

## Requirements

- Python 3
- GTK 4, libadwaita, GtkSourceView 5
- Linux (GNOME or any GTK 4-compatible desktop)

## Install from .deb

Download the latest `.deb` from [GitHub Releases](https://github.com/jorjives/jsonl-viewer/releases/latest):

```bash
sudo apt install ./jsonl-viewer_*_all.deb
```

## Install from source

```bash
git clone https://github.com/jorjives/jsonl-viewer.git
cd jsonl-viewer
./install.sh
```

The install script creates a symlink in `~/.local/bin`, registers the desktop entry, and sets up MIME types for `.jsonl` and `.ndjson` files.

Make sure `~/.local/bin` is in your `PATH`.

## Uninstall

### Installed via .deb

```bash
sudo apt remove jsonl-viewer
```

### Installed via install.sh

```bash
rm ~/.local/bin/jsonl-viewer
rm ~/.local/share/applications/dev.jorj.jsonl-viewer.desktop
rm ~/.local/share/mime/packages/jsonl-viewer.xml
rm ~/.local/share/icons/hicolor/scalable/apps/dev.jorj.jsonl-viewer.svg
rm ~/.local/share/icons/hicolor/scalable/apps/dev.jorj.jsonl-viewer-symbolic.svg
update-mime-database ~/.local/share/mime
update-desktop-database ~/.local/share/applications
gtk-update-icon-cache ~/.local/share/icons/hicolor
```
