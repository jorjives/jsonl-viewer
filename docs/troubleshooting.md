---
layout: default
title: Tips & Troubleshooting
nav_order: 4
---

# Tips & Troubleshooting

## App does not appear in the file manager's "Open with" menu

The MIME database may need updating. Run:

```bash
update-mime-database ~/.local/share/mime
update-desktop-database ~/.local/share/applications
```

## `jsonl-viewer: command not found`

Ensure `~/.local/bin` is in your `PATH`. Add this to your shell profile (e.g., `~/.bashrc` or `~/.zshrc`):

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Then restart your terminal or run `source ~/.bashrc`.

## Parse errors shown in the header bar

Lines that are not valid JSON are skipped. The header subtitle shows the count:

- Before selecting an entry: `"5 entries (2 parse errors)"`
- After selecting an entry: `"1/5 viewed (2 parse errors)"`

This is normal for files with comments or malformed lines.

## Reset all saved label preferences

Delete the preferences file:

```bash
rm ~/.config/jsonl-viewer/key-prefs.json
```

This removes all per-file key overrides. The app will revert to automatic label detection for every file.
