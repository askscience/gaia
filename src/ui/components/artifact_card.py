import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk

class ArtifactCard(Gtk.Box):
    """A card for a single generated file (e.g. style.css)."""
    def __init__(self, filename: str, path: str, language: str):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self.add_css_class("artifact-card")
        self.add_css_class("source-card") # Reuse base styling
        self.set_spacing(12)
        self.set_margin_top(4)
        self.set_margin_bottom(4)
        
        self.filename = filename
        self.path = path
        self.language = language

        icon = Gtk.Image.new_from_icon_name("text-x-generic-symbolic")
        if language == "html": icon.set_from_icon_name("text-html-symbolic")
        elif language == "css": icon.set_from_icon_name("text-css-symbolic")
        elif language == "javascript": icon.set_from_icon_name("text-x-javascript-symbolic")
        
        icon.set_pixel_size(24)
        icon.set_margin_start(12)
        self.append(icon)

        label = Gtk.Label(label=filename)
        label.set_hexpand(True)
        label.set_halign(Gtk.Align.START)
        label.set_margin_top(12)
        label.set_margin_bottom(12)
        self.append(label)

        # Click gesture to open code viewer
        gesture = Gtk.GestureClick()
        gesture.connect("released", self.on_clicked)
        self.add_controller(gesture)
        self.set_cursor(Gdk.Cursor.new_from_name("pointer", None))

    def on_clicked(self, *args):
        root = self.get_native()
        if hasattr(root, "artifacts_panel"):
            root.artifacts_panel.load_artifact(self.path, self.language)
            root.show_artifacts()
