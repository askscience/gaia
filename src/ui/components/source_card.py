import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, GLib
import threading
import requests
from urllib.parse import urlparse

class SourceCard(Gtk.Box):
    """A compact, native GTK4 list row to display a web source link."""
    
    def __init__(self, title: str, url: str, snippet: str = "", image_url: str = None, favicon_url: str = None):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self.add_css_class("source-row")
        self.url = url
        self.set_spacing(12)
        self.set_margin_top(6)
        self.set_margin_bottom(6)
        self.set_margin_start(12)
        self.set_margin_end(12)
        
        # Favicon (small icon on the left)
        self.favicon_image = Gtk.Image()
        self.favicon_image.set_pixel_size(20)
        self.favicon_image.add_css_class("source-favicon")
        self.favicon_image.set_from_icon_name("text-html-symbolic")
        self.favicon_image.set_valign(Gtk.Align.CENTER)
        self.append(self.favicon_image)
        
        # Text content box (title and domain)
        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        text_box.set_spacing(2)
        text_box.set_hexpand(True)
        text_box.set_valign(Gtk.Align.CENTER)
        
        # Title
        title_label = Gtk.Label(label=title)
        title_label.add_css_class("source-title")
        title_label.set_halign(Gtk.Align.START)
        title_label.set_ellipsize(gi.repository.Pango.EllipsizeMode.END)
        title_label.set_xalign(0)
        text_box.append(title_label)
        
        # Domain/URL
        try:
            domain = urlparse(url).netloc
        except:
            domain = url
            
        domain_label = Gtk.Label(label=domain)
        domain_label.add_css_class("source-domain")
        domain_label.set_halign(Gtk.Align.START)
        domain_label.set_xalign(0)
        text_box.append(domain_label)
        
        self.append(text_box)
        
        # Thumbnail image (right side) - only if image_url is available
        self.thumbnail = Gtk.Picture()
        self.thumbnail.set_content_fit(Gtk.ContentFit.COVER)
        self.thumbnail.set_size_request(64, 64)
        self.thumbnail.add_css_class("source-thumbnail")
        self.thumbnail.set_visible(False)
        self.thumbnail.set_valign(Gtk.Align.CENTER)
        self.append(self.thumbnail)
        
        # Click gesture
        gesture = Gtk.GestureClick()
        gesture.connect("released", self.on_clicked)
        self.add_controller(gesture)
        self.set_cursor(Gdk.Cursor.new_from_name("pointer", None))
        
        # Async loading
        self._load_images(domain, favicon_url, image_url)

    def _load_images(self, domain, favicon_url, image_url):
        def fetch():
            # 1. Favicon
            try:
                f_url = favicon_url or f"https://www.google.com/s2/favicons?sz=64&domain={domain}"
                response = requests.get(f_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
                if response.status_code == 200:
                    GLib.idle_add(self._set_image, self.favicon_image, response.content, False)
            except Exception as e:
                print(f"Error fetching favicon for {domain}: {e}")
            
            # 2. Thumbnail Image
            if image_url:
                try:
                    response = requests.get(image_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
                    if response.status_code == 200:
                        GLib.idle_add(self._set_image, self.thumbnail, response.content, True)
                except Exception as e:
                    print(f"Error fetching thumbnail for {domain}: {e}")

        thread = threading.Thread(target=fetch)
        thread.daemon = True
        thread.start()

    def _set_image(self, image_widget, data, is_picture=False):
        try:
            from gi.repository import GdkPixbuf
            loader = GdkPixbuf.PixbufLoader()
            loader.write(data)
            loader.close()
            pixbuf = loader.get_pixbuf()
            if pixbuf:
                texture = Gdk.Texture.new_for_pixbuf(pixbuf)
                if isinstance(image_widget, Gtk.Picture):
                    image_widget.set_paintable(texture)
                else:
                    image_widget.set_from_paintable(texture)
                
                if is_picture:
                    image_widget.set_visible(True)
        except Exception as e:
            print(f"Error setting image: {e}")
        return False

    def on_clicked(self, gesture, n_press, x, y):
        Gtk.show_uri(None, self.url, Gdk.CURRENT_TIME)
