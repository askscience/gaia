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

from .views import CodeView, WebView

class ArtifactsPanel(Gtk.Box):
    def __init__(self, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, **kwargs)
        self.add_css_class("artifacts-panel")
        self.set_vexpand(True)
        self.set_hexpand(True)
        
        # Header with View Switcher
        self.header = Adw.HeaderBar()
        self.header.set_show_end_title_buttons(False)
        
        self.view_stack = Adw.ViewStack()
        self.view_stack.set_vexpand(True)
        self.view_stack.set_hexpand(True)
        
        self.view_switcher = Adw.ViewSwitcherTitle()
        self.view_switcher.set_stack(self.view_stack)
        self.header.set_title_widget(self.view_switcher)
        
        # Fullscreen Button
        self.fullscreen_btn = Gtk.Button()
        self.fullscreen_btn.set_icon_name("view-fullscreen-symbolic")
        self.fullscreen_btn.set_tooltip_text("Toggle Fullscreen")
        self.fullscreen_btn.connect("clicked", self.on_fullscreen_toggled)
        self.header.pack_end(self.fullscreen_btn)
        
        self.append(self.header)

        # Content Views
        self.code_view = CodeView()
        self.web_view = WebView()
        
        self.view_stack.add_titled_with_icon(
            self.web_view, "preview", "Preview", "web-browser-symbolic"
        )
        self.view_stack.add_titled_with_icon(
            self.code_view, "code", "Code", "text-x-generic-symbolic"
        )
        
        # Placeholder
        self.placeholder = Adw.StatusPage()
        self.placeholder.set_title("No Artifact Selected")
        self.placeholder.set_description("Click a card in the chat to view it here.")
        self.placeholder.set_icon_name("system-search-symbolic")
        self.placeholder.set_vexpand(True)
        self.view_stack.add_named(self.placeholder, "placeholder")
        
        self.append(self.view_stack)
        self.clear()

    def load_project(self, index_path: str):
        """Load the project index file into the web view and show Preview."""
        import os
        print(f"[DEBUG ArtifactsPanel] load_project called with: {index_path}")
        
        if os.path.exists(index_path):
            abs_path = os.path.abspath(index_path)
            uri = Gio.File.new_for_path(abs_path).get_uri()
            print(f"[DEBUG ArtifactsPanel] Loading URI: {uri}")
            self.web_view.load_uri(uri)
            
            # Also load code for index.html if possible
            try:
                with open(index_path, "r") as f:
                    self.code_view.load_content(f.read(), "html")
            except Exception as e:
                print(f"[DEBUG ArtifactsPanel] Error loading code: {e}")
                
            self.view_stack.set_visible_child(self.web_view)
        else:
            print(f"[DEBUG ArtifactsPanel] Path does not exist: {index_path}")

    def load_artifact(self, path: str, language: str):
        """Load a single file into the code view and show Code."""
        import os
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    content = f.read()
                    self.code_view.load_content(content, language)
                
                # If it's HTML, also load it in web_view
                if language == "html":
                    abs_path = os.path.abspath(path)
                    uri = Gio.File.new_for_path(abs_path).get_uri()
                    self.web_view.load_uri(uri)
                    self.view_stack.set_visible_child(self.web_view)
                else:
                    self.view_stack.set_visible_child(self.code_view)
            except Exception as e:
                print(f"Error loading artifact: {e}")

    def on_fullscreen_toggled(self, button):
        """Toggle fullscreen mode by requesting the main window to hide the chat."""
        root = self.get_native()
        if hasattr(root, "toggle_artifact_fullscreen"):
            root.toggle_artifact_fullscreen()
        
    def clear(self):
        self.view_stack.set_visible_child(self.placeholder)
        if WebKit:
            self.web_view.load_uri("about:blank")
