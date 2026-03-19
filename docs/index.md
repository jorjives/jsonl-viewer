---
layout: default
title: Home
nav_order: 1
---

# JSONL Viewer

A GNOME desktop app for browsing and inspecting JSONL/NDJSON files.

![JSONL Viewer showing a file with syntax-highlighted JSON](screenshots/nested-json.png)

## Features

- Syntax-highlighted JSON detail view (GtkSourceView)
- Smart sidebar labels extracted from common keys (`name`, `title`, `id`, etc.)
- Right-click any key in the JSON to use it as the sidebar label — persisted per file
- Live file watching with incremental append for streaming logs
- Manual reload via Ctrl+R
- Follows your system light/dark theme

## Quick install

Download the latest `.deb` from [GitHub Releases](https://github.com/jorjives/jsonl-viewer/releases/latest), or see [Installation](installation.md) for other methods.

```bash
sudo apt install ./jsonl-viewer_*_all.deb
```

## Get started

Read the [User Guide](user-guide.md) to learn how to browse, inspect, and customise your JSONL files.
