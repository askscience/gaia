import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GObject, Gio, GLib
import os

# Import optional libraries separately
GtkSource = None
WebKit = None

try:
    gi.require_version('GtkSource', '5')
    from gi.repository import GtkSource
    print(f"[DEBUG views.py] GtkSource loaded: {GtkSource}")
except Exception as e:
    print(f"[DEBUG views.py] GtkSource not available: {e}")

try:
    gi.require_version('WebKit', '6.0')
    from gi.repository import WebKit
    print(f"[DEBUG views.py] WebKit loaded: {WebKit}")
except Exception as e:
    print(f"[DEBUG views.py] WebKit not available: {e}")

class CodeView(Gtk.ScrolledWindow):
    def __init__(self):
        super().__init__()
        self.set_vexpand(True)
        self.set_hexpand(True)
        if GtkSource:
            self.view = GtkSource.View()
            self.view.set_editable(False)
            self.view.set_show_line_numbers(True)
            self.view.set_monospace(True)
        else:
            self.view = Gtk.TextView()
            self.view.set_editable(False)
            self.view.set_monospace(True)
        self.set_child(self.view)

    def load_content(self, content: str, language: str = None):
        buffer = self.view.get_buffer()
        buffer.set_text(content)
        if GtkSource and language:
            lang_manager = GtkSource.LanguageManager.get_default()
            lang = lang_manager.get_language(language)
            if lang:
                buffer.set_language(lang)

class WebView(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.set_vexpand(True)
        self.set_hexpand(True)
        if WebKit:
            self.web_view = WebKit.WebView()
            self.web_view.set_vexpand(True)
            self.web_view.set_hexpand(True)
            # Disable same-origin restrictions for local preview if needed
            settings = self.web_view.get_settings()
            settings.set_allow_file_access_from_file_urls(True)
            settings.set_allow_universal_access_from_file_urls(True)
            self.append(self.web_view)
        else:
            label = Gtk.Label(label="WebKit (Web Preview) not available")
            label.add_css_class("dim-label")
            label.set_vexpand(True)
            self.append(label)

    def load_uri(self, uri: str):
        if WebKit:
            self.web_view.load_uri(uri)
