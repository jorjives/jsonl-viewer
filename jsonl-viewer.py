#!/usr/bin/env python3
"""GNOME JSONL Viewer - Browse and inspect JSONL documents."""

import json
import os
import re
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GtkSource", "5")
from gi.repository import Adw, Gio, GLib, GObject, Gtk, GtkSource, Pango  # noqa: E402


class JsonlViewer(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="dev.jorj.jsonl-viewer",
            flags=Gio.ApplicationFlags.HANDLES_OPEN,
        )
        self.entries = []
        self.viewed = set()
        self.last_dir = None
        self.current_path = None
        self.file_monitor = None
        self.file_offset = 0
        self.next_lineno = 1
        self.debounce_id = 0
        self.errors = 0
        self.summary_key = None

    def do_activate(self):
        self._build_window()
        self.win.present()

    def do_open(self, files, n_files, hint):
        self._build_window()
        self.win.present()
        if n_files > 0:
            path = files[0].get_path()
            self.last_dir = str(GLib.path_get_dirname(path))
            self._load_file(path)

    def _build_window(self):
        if hasattr(self, "win") and self.win is not None:
            return

        self.win = Adw.ApplicationWindow(application=self, title="JSONL Viewer")
        self.win.set_default_size(1000, 650)

        # Header bar with open button
        header = Adw.HeaderBar()
        self.reload_btn = Gtk.Button(
            icon_name="view-refresh-symbolic",
            tooltip_text="Reload (Ctrl+R)",
            sensitive=False,
        )
        self.reload_btn.connect("clicked", lambda _btn: self._reload_file())
        header.pack_start(self.reload_btn)

        self.watch_btn = Gtk.ToggleButton(
            icon_name="view-reveal-symbolic",
            tooltip_text="Watch for changes",
            sensitive=False,
        )
        self.watch_btn.connect("toggled", self._on_watch_toggled)
        header.pack_start(self.watch_btn)

        open_btn = Gtk.Button(label="Open")
        open_btn.connect("clicked", self._on_open_clicked)
        header.pack_start(open_btn)

        self.title_label = Adw.WindowTitle(title="JSONL Viewer", subtitle="")
        header.set_title_widget(self.title_label)

        # --- Left side: entry list ---
        self.list_store = Gio.ListStore(item_type=EntryItem)
        self.selection = Gtk.SingleSelection(model=self.list_store)
        self.selection.set_autoselect(False)
        self.selection.connect("notify::selected", self._on_selection_changed)

        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_factory_setup)
        factory.connect("bind", self._on_factory_bind)

        list_view = Gtk.ListView(model=self.selection, factory=factory)
        list_view.add_css_class("navigation-sidebar")

        list_scroll = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        list_scroll.set_child(list_view)
        list_scroll.set_size_request(280, -1)

        # --- Right side: JSON detail view with syntax highlighting ---
        lang_mgr = GtkSource.LanguageManager.get_default()
        self.source_buffer = GtkSource.Buffer()
        self.source_buffer.set_language(lang_mgr.get_language("json"))

        scheme_mgr = GtkSource.StyleSchemeManager.get_default()
        style_mgr = Adw.StyleManager.get_default()
        scheme_id = "Adwaita-dark" if style_mgr.get_dark() else "Adwaita"
        self.source_buffer.set_style_scheme(scheme_mgr.get_scheme(scheme_id))
        style_mgr.connect("notify::dark", self._on_theme_changed)

        self.detail_view = GtkSource.View(
            buffer=self.source_buffer,
            editable=False,
            monospace=True,
            wrap_mode=Gtk.WrapMode.WORD_CHAR,
            left_margin=12,
            right_margin=12,
            top_margin=12,
            bottom_margin=12,
        )
        click_gesture = Gtk.GestureClick(button=3)
        click_gesture.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        click_gesture.connect("pressed", self._on_detail_right_click)
        self.detail_view.add_controller(click_gesture)
        detail_scroll = Gtk.ScrolledWindow()
        detail_scroll.set_child(self.detail_view)
        detail_scroll.set_vexpand(True)
        detail_scroll.set_hexpand(True)

        # Placeholder when nothing selected
        self.detail_stack = Gtk.Stack()
        placeholder = Adw.StatusPage(
            icon_name="document-open-symbolic",
            title="No Entry Selected",
            description="Open a JSONL file and select an entry to view",
        )
        self.detail_stack.add_named(placeholder, "placeholder")
        self.detail_stack.add_named(detail_scroll, "detail")
        self.detail_stack.set_visible_child_name("placeholder")

        # Paned layout
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_start_child(list_scroll)
        paned.set_end_child(self.detail_stack)
        paned.set_resize_start_child(False)
        paned.set_shrink_start_child(False)
        paned.set_position(280)

        # Main layout
        self.toast_overlay = Adw.ToastOverlay()
        self.toast_overlay.set_child(paned)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.append(header)
        box.append(self.toast_overlay)
        self.win.set_content(box)

        reload_action = Gio.SimpleAction(name="reload")
        reload_action.connect("activate", lambda _a, _p: self._reload_file())
        self.add_action(reload_action)
        self.set_accels_for_action("app.reload", ["<Ctrl>r"])

        set_key_action = Gio.SimpleAction(
            name="set-summary-key",
            parameter_type=GLib.VariantType.new("s"),
        )
        set_key_action.connect("activate", self._on_set_summary_key)
        self.add_action(set_key_action)

        reset_key_action = Gio.SimpleAction(name="reset-summary-key")
        reset_key_action.connect("activate", self._on_reset_summary_key)
        self.add_action(reset_key_action)

    def _on_factory_setup(self, factory, list_item):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_start(8)
        box.set_margin_end(8)
        box.set_margin_top(4)
        box.set_margin_bottom(4)

        icon = Gtk.Image(icon_name="emblem-ok-symbolic", visible=False)
        icon.add_css_class("success")
        box.append(icon)

        label = Gtk.Label(xalign=0, ellipsize=Pango.EllipsizeMode.END)
        box.append(label)

        list_item.set_child(box)

    def _on_factory_bind(self, factory, list_item):
        item = list_item.get_item()
        box = list_item.get_child()
        icon = box.get_first_child()
        label = icon.get_next_sibling()

        label.set_text(item.summary)
        icon.set_visible(item.index in self.viewed)

    def _on_selection_changed(self, selection, _pspec):
        if getattr(self, "_rebuilding", False):
            return
        pos = selection.get_selected()
        if pos == Gtk.INVALID_LIST_POSITION or pos >= len(self.entries):
            return

        self.viewed.add(pos)
        # Refresh the list to update the viewed icon
        # Emit items-changed for the single changed item to rebind it
        self.list_store.items_changed(pos, 1, 1)

        entry = self.entries[pos]
        formatted = json.dumps(entry, indent=2, ensure_ascii=False)
        self.source_buffer.set_text(formatted, -1)
        self.detail_stack.set_visible_child_name("detail")

        viewed_count = len(self.viewed)
        total = len(self.entries)
        subtitle = f"{viewed_count}/{total} viewed"
        if self.errors:
            subtitle += f" ({self.errors} parse errors)"
        self.title_label.set_subtitle(subtitle)

    def _on_theme_changed(self, style_mgr, _pspec):
        scheme_mgr = GtkSource.StyleSchemeManager.get_default()
        scheme_id = "Adwaita-dark" if style_mgr.get_dark() else "Adwaita"
        self.source_buffer.set_style_scheme(scheme_mgr.get_scheme(scheme_id))

    def _on_detail_right_click(self, gesture, _n_press, x, y):
        """Update extra-menu with key selection items before the context menu opens."""
        buf_x, buf_y = self.detail_view.window_to_buffer_coords(
            Gtk.TextWindowType.WIDGET, int(x), int(y)
        )
        ok, text_iter = self.detail_view.get_iter_at_location(buf_x, buf_y)
        if not ok:
            self.detail_view.set_extra_menu(None)
            return

        # Get the full line text
        line_start = text_iter.copy()
        line_start.set_line_offset(0)
        line_end = text_iter.copy()
        if not line_end.ends_line():
            line_end.forward_to_line_end()
        line_text = self.source_buffer.get_text(line_start, line_end, False)

        # Match top-level key: exactly 2 spaces indent, then "key":
        match = re.match(r'^  "((?:[^"\\]|\\.)*)"\s*:', line_text)
        if not match:
            self.detail_view.set_extra_menu(None)
            return

        key_name = match.group(1)

        # Build context menu items — GTK appends these to the built-in menu
        menu = Gio.Menu()
        menu.append(f'Use "{key_name}" as list key', f"app.set-summary-key::{key_name}")
        if self.summary_key is not None:
            menu.append("Reset to automatic", "app.reset-summary-key")
        self.detail_view.set_extra_menu(menu)

    def _on_set_summary_key(self, _action, param):
        if self.current_path is None:
            return
        key_name = param.get_string()
        self.summary_key = key_name
        self._rebuild_summaries()
        # Persist
        prefs = _load_key_prefs()
        prefs[self.current_path] = key_name
        _save_key_prefs(prefs)
        self.toast_overlay.add_toast(
            Adw.Toast(title=f'List key set to "{key_name}"')
        )

    def _on_reset_summary_key(self, _action, _param):
        self.summary_key = None
        self._rebuild_summaries()
        # Persist
        prefs = _load_key_prefs()
        prefs.pop(self.current_path, None)
        _save_key_prefs(prefs)
        self.toast_overlay.add_toast(Adw.Toast(title="List key reset to automatic"))

    def _rebuild_summaries(self):
        """Regenerate all sidebar summaries using the current key override."""
        n = self.list_store.get_n_items()
        if n == 0:
            return
        new_items = []
        for i, entry in enumerate(self.entries):
            old = self.list_store.get_item(i)
            summary = _make_summary(entry, old.lineno, self.summary_key)
            new_items.append(EntryItem(index=old.index, summary=summary, lineno=old.lineno))
        self._rebuilding = True
        self.list_store.splice(0, n, new_items)
        self._rebuilding = False

    def _on_open_clicked(self, _btn):
        dialog = Gtk.FileDialog()
        json_filter = Gtk.FileFilter()
        json_filter.set_name("JSONL files")
        json_filter.add_pattern("*.jsonl")
        json_filter.add_pattern("*.ndjson")
        all_filter = Gtk.FileFilter()
        all_filter.set_name("All files")
        all_filter.add_pattern("*")
        filters = Gio.ListStore(item_type=Gtk.FileFilter)
        filters.append(json_filter)
        filters.append(all_filter)
        dialog.set_filters(filters)
        if self.last_dir:
            dialog.set_initial_folder(Gio.File.new_for_path(self.last_dir))
        dialog.open(self.win, None, self._on_file_chosen)

    def _on_file_chosen(self, dialog, result):
        try:
            f = dialog.open_finish(result)
            path = f.get_path()
            self.last_dir = str(GLib.path_get_dirname(path))
            self._load_file(path)
        except GLib.Error:
            pass  # user cancelled

    def _load_file(self, path):
        self._stop_watching()
        self.current_path = path
        prefs = _load_key_prefs()
        self.summary_key = prefs.get(path)
        self.entries.clear()
        self.viewed.clear()
        self.list_store.remove_all()
        self.source_buffer.set_text("", -1)
        self.detail_stack.set_visible_child_name("placeholder")

        self.errors = 0
        with open(path, "rb") as fh:
            lineno = 0
            for raw_line in fh:
                lineno += 1
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    self.errors += 1
                    continue
                self.entries.append(obj)
                summary = _make_summary(obj, lineno, self.summary_key)
                item = EntryItem(index=len(self.entries) - 1, summary=summary, lineno=lineno)
                self.list_store.append(item)
            self.file_offset = fh.tell()
            self.next_lineno = lineno + 1

        self._update_subtitle()
        self.title_label.set_title(GLib.path_get_basename(path))
        self.reload_btn.set_sensitive(True)
        self.watch_btn.set_sensitive(True)
        if self.watch_btn.get_active():
            self._start_watching()
        else:
            self.watch_btn.set_active(True)

    def _update_subtitle(self):
        total = len(self.entries)
        subtitle = f"{total} entries"
        if self.errors:
            subtitle += f" ({self.errors} parse errors)"
        self.title_label.set_subtitle(subtitle)

    def _reload_file(self):
        if self.current_path is None:
            return
        self._load_file(self.current_path)

    def _stop_watching(self):
        if self.debounce_id:
            GLib.source_remove(self.debounce_id)
            self.debounce_id = 0
        if self.file_monitor is not None:
            self.file_monitor.cancel()
            self.file_monitor = None

    def _start_watching(self):
        if self.current_path is None:
            return
        self._stop_watching()
        gfile = Gio.File.new_for_path(self.current_path)
        self.file_monitor = gfile.monitor_file(Gio.FileMonitorFlags.NONE, None)
        self.file_monitor.connect("changed", self._on_file_changed)

    def _on_watch_toggled(self, btn):
        if btn.get_active():
            self._start_watching()
            self._check_for_new_content()
        else:
            self._stop_watching()

    def _on_file_changed(self, monitor, file, other_file, event_type):
        if event_type == Gio.FileMonitorEvent.DELETED:
            self._stop_watching()
            self.watch_btn.set_active(False)
            self.toast_overlay.add_toast(Adw.Toast(title="File was deleted"))
            return
        if event_type in (
            Gio.FileMonitorEvent.CHANGED,
            Gio.FileMonitorEvent.CHANGES_DONE_HINT,
        ):
            if self.debounce_id:
                GLib.source_remove(self.debounce_id)
            self.debounce_id = GLib.timeout_add(200, self._check_for_new_content)

    def _check_for_new_content(self):
        self.debounce_id = 0
        if self.current_path is None:
            return GLib.SOURCE_REMOVE
        try:
            size = os.path.getsize(self.current_path)
        except OSError:
            return GLib.SOURCE_REMOVE
        if size < self.file_offset:
            self._reload_file()
            return GLib.SOURCE_REMOVE
        if size == self.file_offset:
            return GLib.SOURCE_REMOVE
        with open(self.current_path, "rb") as fh:
            fh.seek(self.file_offset)
            new_data = fh.read()
            self.file_offset = fh.tell()
        lineno = self.next_lineno
        for raw_line in new_data.decode("utf-8", errors="replace").splitlines():
            line = raw_line.strip()
            if not line:
                lineno += 1
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                self.errors += 1
                lineno += 1
                continue
            self.entries.append(obj)
            summary = _make_summary(obj, lineno, self.summary_key)
            item = EntryItem(index=len(self.entries) - 1, summary=summary, lineno=lineno)
            self.list_store.append(item)
            lineno += 1
        self.next_lineno = lineno
        self._update_subtitle()
        return GLib.SOURCE_REMOVE


class EntryItem(GObject.Object):
    """A GObject wrapper for a single JSONL entry reference."""

    def __init__(self, index: int, summary: str, lineno: int):
        super().__init__()
        self.index = index
        self.summary = summary
        self.lineno = lineno


def _make_summary(obj, lineno: int, key_override: str | None = None) -> str:
    """Create a short summary string for the sidebar."""
    if isinstance(obj, dict):
        # Use override key if set and present in this entry
        if key_override and key_override in obj:
            val = obj[key_override]
            if isinstance(val, str) and len(val) > 60:
                val = val[:57] + "..."
            return f"#{lineno}: {val}"
        # Try common identifying keys
        for key in ("name", "title", "id", "type", "message", "event", "key", "label"):
            if key in obj:
                val = obj[key]
                if isinstance(val, str) and len(val) > 60:
                    val = val[:57] + "..."
                return f"#{lineno}: {val}"
        # Fall back to first key
        first_key = next(iter(obj), None)
        if first_key:
            val = obj[first_key]
            if isinstance(val, str) and len(val) > 50:
                val = val[:47] + "..."
            return f"#{lineno}: {first_key}={val}"
    return f"#{lineno}"


def _prefs_path() -> str:
    """Return the path to the key preferences file."""
    return os.path.join(GLib.get_user_config_dir(), "jsonl-viewer", "key-prefs.json")


def _load_key_prefs() -> dict:
    """Load per-file key preferences. Returns empty dict on any error."""
    try:
        with open(_prefs_path()) as f:
            prefs = json.load(f)
            return prefs if isinstance(prefs, dict) else {}
    except (OSError, json.JSONDecodeError, ValueError):
        return {}


def _save_key_prefs(prefs: dict) -> None:
    """Save per-file key preferences."""
    path = _prefs_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(prefs, f, indent=2)


def main():
    app = JsonlViewer()
    app.run(sys.argv)


if __name__ == "__main__":
    main()
