import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gdk, Gio, GLib


class SourceCard(Gtk.Box):
    """A native GTK4 widget to display a web source link with images."""
    
    def __init__(self, title: str, url: str, snippet: str = "", image_url: str = None, favicon_url: str = None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.add_css_class("source-card")
        self.url = url
        # self.set_size_request(250, -1) # Removed to allow better responsiveness
        
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
            from urllib.parse import urlparse
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
        import threading
        import requests
        
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


class ProjectCard(Gtk.Box):
    """A card for a website project with Preview and Export buttons."""
    def __init__(self, title: str, folder_path: str, index_path: str):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.add_css_class("project-card")
        self.add_css_class("source-card")
        self.set_margin_top(8)
        self.set_margin_bottom(8)
        
        self.folder_path = folder_path
        self.index_path = index_path

        # Content
        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        content.set_spacing(12)
        content.set_margin_start(12)
        content.set_margin_end(12)
        content.set_margin_top(12)
        
        icon = Gtk.Image.new_from_icon_name("folder-remote-symbolic")
        icon.set_pixel_size(32)
        content.append(icon)

        text_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        text_vbox.set_hexpand(True)
        
        title_label = Gtk.Label(label=title)
        title_label.add_css_class("source-title")
        title_label.set_halign(Gtk.Align.START)
        text_vbox.append(title_label)
        
        desc_label = Gtk.Label(label="Website Project")
        desc_label.add_css_class("dim-label")
        desc_label.set_halign(Gtk.Align.START)
        text_vbox.append(desc_label)
        
        content.append(text_vbox)
        self.append(content)

        # Buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        button_box.set_spacing(8)
        button_box.set_margin_start(12)
        button_box.set_margin_end(12)
        button_box.set_margin_bottom(12)
        button_box.set_margin_top(8)

        preview_btn = Gtk.Button(label="View Preview")
        preview_btn.add_css_class("suggested-action")
        preview_btn.connect("clicked", self.on_preview_clicked)
        button_box.append(preview_btn)

        export_btn = Gtk.Button(label="Export ZIP")
        export_btn.connect("clicked", self.on_export_clicked)
        button_box.append(export_btn)

        self.append(button_box)

    def on_preview_clicked(self, button):
        root = self.get_native()
        if hasattr(root, "artifacts_panel"):
            root.artifacts_panel.load_project(self.index_path)
            root.show_artifacts()

    def on_export_clicked(self, button):
        import zipfile
        dialog = Gtk.FileDialog()
        dialog.set_title("Save Website ZIP")
        dialog.set_initial_name("website_export.zip")
        
        def on_save_response(dialog, result):
            try:
                file = dialog.save_finish(result)
                if not file: return
                zip_path = file.get_path()
                with zipfile.ZipFile(zip_path, 'w') as zipf:
                    for root_dir, dirs, files in os.walk(self.folder_path):
                        for file in files:
                            full_path = os.path.join(root_dir, file)
                            rel_path = os.path.relpath(full_path, self.folder_path)
                            zipf.write(full_path, rel_path)
                print(f"Exported to {zip_path}")
            except Exception as e:
                print(f"Export failed: {e}")

        dialog.save(self.get_native(), None, on_save_response)

import os
