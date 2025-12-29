import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
try:
    gi.require_version('GtkSource', '5')
    gi.require_version('WebKit', '6.0')
except:
    pass

from gi.repository import Gtk, Adw, GObject, Gio, GLib
try:
    from gi.repository import GtkSource, WebKit
except ImportError:
    GtkSource = None
    WebKit = None

class ArtifactsPanel(Gtk.Box):
    def __init__(self, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, **kwargs)
        self.add_css_class("artifacts-panel")
        self.set_size_request(400, -1)

        # Header
        self.header = Adw.HeaderBar()
        self.header.set_show_end_title_buttons(False)
        
        # View Switcher in Header
        self.view_stack = Adw.ViewStack()
        
        self.view_switcher = Adw.ViewSwitcherTitle()
        self.view_switcher.set_stack(self.view_stack)
        self.header.set_title_widget(self.view_switcher)
        
        self.append(self.header)

        # Code View
        self.code_scroll = Gtk.ScrolledWindow()
        if GtkSource:
            self.code_view = GtkSource.View()
            self.code_view.set_editable(False)
            self.code_view.set_show_line_numbers(True)
            self.code_view.set_monospace(True)
            self.code_scroll.set_child(self.code_view)
        else:
            self.code_view = Gtk.TextView()
            self.code_view.set_editable(False)
            self.code_view.set_monospace(True)
            self.code_scroll.set_child(self.code_view)
        
        self.view_stack.add_titled_with_icon(
            self.code_scroll, "code", "Code", "code-context-menu-symbolic"
        )

        # Preview View
        self.preview_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        if WebKit:
            self.web_view = WebKit.WebView()
            self.preview_box.append(self.web_view)
        else:
            label = Gtk.Label(label="WebKit (Web Preview) not available")
            label.add_css_class("dim-label")
            self.preview_box.append(label)
        
        self.view_stack.add_titled_with_icon(
            self.preview_box, "preview", "Preview", "recenter-symbolic"
        )

        self.append(self.view_stack)

        # Placeholder
        self.placeholder = Adw.StatusPage()
        self.placeholder.set_title("No Artifacts")
        self.placeholder.set_description("Generated websites and code will appear here.")
        self.placeholder.set_icon_name("system-search-symbolic")
        self.view_stack.add_named(self.placeholder, "placeholder")
        self.view_stack.set_visible_child(self.placeholder)
        
    def load_artifact(self, artifact_data: dict):
        """Load an artifact into the panel."""
        self.view_stack.set_visible_child(self.code_scroll)
        
        filename = artifact_data.get("filename", "unknown")
        content = ""
        path = artifact_data.get("path")
        
        if path and os.path.exists(path):
            with open(path, "r") as f:
                content = f.read()
        
        # Update Code View
        buffer = self.code_view.get_buffer()
        buffer.set_text(content)
        
        if GtkSource:
            lang_manager = GtkSource.LanguageManager.get_default()
            lang = lang_manager.get_language(artifact_data.get("language", "text"))
            if lang:
                buffer.set_language(lang)

        # Update Web Preview if HTML
        if artifact_data.get("language") == "html" and WebKit:
            self.web_view.load_uri(f"file://{path}")
            self.view_stack.set_visible_child(self.preview_box)
        elif artifact_data.get("type") == "web" and WebKit:
            self.web_view.load_uri(f"file://{path}")
            self.view_stack.set_visible_child(self.preview_box)

import os
