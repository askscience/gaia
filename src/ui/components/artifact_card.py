import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk

class ArtifactCard(Gtk.Frame):
    """A card for a single generated file (e.g. style.css)."""
    def __init__(self, filename: str, path: str, language: str):
        super().__init__()
        self.add_css_class("card")
        
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.set_spacing(12)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(8)
        box.set_margin_end(8)
        
        self.filename = filename
        self.path = path
        self.language = language

        icon = Gtk.Image.new_from_icon_name("text-x-generic-symbolic")
        if language == "html": icon.set_from_icon_name("text-html-symbolic")
        elif language == "css": icon.set_from_icon_name("text-css-symbolic")
        elif language == "javascript": icon.set_from_icon_name("text-x-javascript-symbolic")
        
        icon.set_pixel_size(24)
        box.append(icon)

        label = Gtk.Label(label=filename)
        label.set_hexpand(True)
        label.set_halign(Gtk.Align.START)
        box.append(label)

        self.set_child(box)

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
