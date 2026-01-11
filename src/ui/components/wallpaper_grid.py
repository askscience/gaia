import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, GLib, Gio
import threading
import requests
import os

class WallpaperGrid(Gtk.Box):
    def __init__(self, images, on_click_callback=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.set_spacing(10)
        self.set_margin_top(10)
        self.set_margin_bottom(10)
        self.images = images
        self.on_click_callback = on_click_callback
        
        # Grid/FlowBox
        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_valign(Gtk.Align.START)
        self.flowbox.set_max_children_per_line(2)
        self.flowbox.set_min_children_per_line(2) # Force 2 columns
        self.flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flowbox.set_column_spacing(10)
        self.flowbox.set_row_spacing(10)
        self.append(self.flowbox)
        
        for i, img_data in enumerate(images):
            child = self._create_card(i + 1, img_data)
            self.flowbox.append(child)

    def _create_card(self, index, img_data):
        # Frame for the card visual
        frame = Gtk.Frame()
        frame.add_css_class("card")
        
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        # card.add_css_class("wallpaper-card") # Frame handles the border/bg
        card.set_size_request(160, 150) # Reduced width to ensure 2x2 fit
        
        # Image Area
        # Use Overlay for the index badge
        overlay = Gtk.Overlay()
        
        picture = Gtk.Picture()
        picture.set_content_fit(Gtk.ContentFit.COVER)
        picture.set_can_shrink(True)
        # Force aspect ratio logic via size request if needed, but COVER handles it nicely if container is fixed
        picture.set_size_request(-1, 140) 
        
        self._load_image_async(img_data['url'], picture)
        overlay.set_child(picture)
        
        # Badge
        badge_label = Gtk.Label(label=str(index))
        badge_label.add_css_class("caption-xsmall")
        # Creating a small pill for the badge
        badge_box = Gtk.Box()
        badge_box.add_css_class("badge-pill") # Assuming theme has this or simple styling
        badge_box.append(badge_label)
        badge_box.set_halign(Gtk.Align.END)
        badge_box.set_valign(Gtk.Align.START)
        badge_box.set_margin_top(8)
        badge_box.set_margin_end(8)
        
        # Manually styling the badge if no generic class
        context = badge_box.get_style_context()
        provider = Gtk.CssProvider()
        css = b".badge-pill { background-color: rgba(0,0,0,0.6); color: white; border-radius: 12px; padding: 2px 8px; }"
        provider.load_from_data(css)
        context.add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        
        overlay.add_overlay(badge_box)
        
        card.append(overlay)
        
        # Caption
        desc = img_data.get('description', 'Wallpaper')
        label = Gtk.Label(label=desc)
        label.set_ellipsize(3) # END
        label.set_wrap(False)
        label.set_max_width_chars(25)
        label.add_css_class("caption")
        label.set_margin_top(6)
        label.set_margin_bottom(6)
        label.set_margin_start(6)
        label.set_margin_end(6)
        card.append(label)
        
        frame.set_child(card)
        
        btn = Gtk.Button()
        btn.set_child(frame)
        btn.add_css_class("flat") # Remove button background
        btn.connect("clicked", lambda b: self._on_card_clicked(index))
        
        return btn

    def _on_card_clicked(self, index):
        if self.on_click_callback:
            self.on_click_callback(index)

    def _load_image_async(self, url, picture):
        def load():
            try:
                session = requests.Session()
                session.headers.update({'User-Agent': 'Mozilla/5.0 GaiaBot/1.0'})
                resp = session.get(url, timeout=10, stream=True)
                if resp.status_code == 200:
                    import tempfile
                    fd, path = tempfile.mkstemp(suffix=".jpg")
                    with os.fdopen(fd, 'wb') as tmp:
                        for chunk in resp.iter_content(chunk_size=1024):
                            tmp.write(chunk)
                    f = Gio.File.new_for_path(path)
                    GLib.idle_add(picture.set_file, f)
            except Exception as e:
                print(f"Error loading grid image: {e}")
        
        threading.Thread(target=load, daemon=True).start()
