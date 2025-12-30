import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, GLib
import threading
import requests
from urllib.parse import urlparse

class SourceCard(Gtk.Box):
    """A native GTK4 widget to display a web source link with images."""
    
    def __init__(self, title: str, url: str, snippet: str = "", image_url: str = None, favicon_url: str = None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.add_css_class("source-card")
        self.url = url
        
        # Main content box
        content_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        content_hbox.set_spacing(10)
        content_hbox.set_margin_top(8)
        content_hbox.set_margin_bottom(8)
        content_hbox.set_margin_start(10)
        content_hbox.set_margin_end(10)
        
        # Text side (Left)
        text_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        text_vbox.set_spacing(2)
        text_vbox.set_hexpand(True)
        
        # Site header (Favicon | Domain)
        header_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        header_hbox.set_spacing(8)
        
        self.favicon_image = Gtk.Image()
        self.favicon_image.set_pixel_size(18) # Smaller favicon
        self.favicon_image.add_css_class("source-favicon")
        self.favicon_image.set_from_icon_name("text-html-symbolic")
        header_hbox.append(self.favicon_image)
        
        try:
            domain = urlparse(url).netloc
        except:
            domain = url
            
        domain_label = Gtk.Label(label=domain)
        domain_label.add_css_class("source-domain")
        domain_label.set_halign(Gtk.Align.START)
        header_hbox.append(domain_label)
        
        text_vbox.append(header_hbox)
        
        # Title
        title_label = Gtk.Label(label=title)
        title_label.add_css_class("source-title")
        title_label.set_halign(Gtk.Align.START)
        title_label.set_ellipsize(gi.repository.Pango.EllipsizeMode.END)
        title_label.set_wrap(True)
        title_label.set_lines(2)
        title_label.set_xalign(0)
        text_vbox.append(title_label)
        
        # Snippet
        if snippet:
            snippet_label = Gtk.Label(label=snippet)
            snippet_label.add_css_class("source-snippet")
            snippet_label.set_halign(Gtk.Align.START)
            snippet_label.set_wrap(True)
            snippet_label.set_max_width_chars(60)
            snippet_label.set_lines(3)
            snippet_label.set_ellipsize(gi.repository.Pango.EllipsizeMode.END)
            snippet_label.set_xalign(0)
            text_vbox.append(snippet_label)
            
        content_hbox.append(text_vbox)
        
        # Featured Image (Right)
        self.featured_image = Gtk.Picture()
        self.featured_image.set_content_fit(Gtk.ContentFit.COVER)
        self.featured_image.set_size_request(80, 80)
        self.featured_image.add_css_class("source-featured-image")
        self.featured_image.set_visible(False)
        self.featured_image.set_valign(Gtk.Align.CENTER)
        content_hbox.append(self.featured_image)
        
        self.append(content_hbox)
        
        # Async loading
        self._load_images(domain, favicon_url, image_url)
        
        # Click gesture
        gesture = Gtk.GestureClick()
        gesture.connect("released", self.on_clicked)
        self.add_controller(gesture)
        self.set_cursor(Gdk.Cursor.new_from_name("pointer", None))

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
            
            # 2. Featured Image
            if image_url:
                try:
                    response = requests.get(image_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
                    if response.status_code == 200:
                        GLib.idle_add(self._set_image, self.featured_image, response.content, True)
                except Exception as e:
                    print(f"Error fetching featured image for {domain}: {e}")

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
