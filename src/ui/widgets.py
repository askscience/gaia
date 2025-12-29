import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gdk, Gio, GLib
import os
import shutil
import random
import string
import cairo
import re



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
    def __init__(self, title: str, folder_path: str, index_path: str, artifacts: list = None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.add_css_class("project-card")
        self.add_css_class("source-card")
        self.set_margin_top(8)
        self.set_margin_bottom(8)
        
        self.folder_path = folder_path
        self.index_path = index_path
        self.artifacts = artifacts or []

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
        
        create_app_btn = Gtk.Button(label="Create App")
        create_app_btn.add_css_class("suggested-action")
        create_app_btn.connect("clicked", self.on_create_app_clicked)
        button_box.append(create_app_btn)

        self.append(button_box)
        
        # Files List (Integrated)
        if self.artifacts:
            # Separator
            sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
            sep.set_margin_start(12)
            sep.set_margin_end(12)
            sep.set_opacity(0.1) # Subtle separator
            self.append(sep)
            
            files_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            files_box.set_spacing(2) # Tight spacing
            files_box.set_margin_top(8)
            files_box.set_margin_bottom(8)
            files_box.set_margin_start(8)
            files_box.set_margin_end(8)
            
            for art in self.artifacts:
                filename = art.get('filename', 'Unknown')
                path = art.get('path', '')
                language = art.get('language', '')
                
                # Flat Button for file
                btn = Gtk.Button()
                btn.add_css_class("flat") # No border/bg by default
                btn.set_has_frame(False)
                btn.set_halign(Gtk.Align.FILL) # Stretch to width
                
                # Custom content for button (Icon + Text)
                btn_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
                btn_content.set_spacing(10)
                
                # Icon
                icon_name = "text-x-generic-symbolic"
                if language == "html": icon_name = "text-html-symbolic"
                elif language == "css": icon_name = "text-css-symbolic"
                elif language == "javascript": icon_name = "text-x-javascript-symbolic"
                
                f_icon = Gtk.Image.new_from_icon_name(icon_name)
                f_icon.set_pixel_size(16) # Compact icon
                f_icon.set_opacity(0.7)
                btn_content.append(f_icon)
                
                f_label = Gtk.Label(label=filename)
                f_label.set_halign(Gtk.Align.START)
                btn_content.append(f_label)
                
                btn.set_child(btn_content)
                
                # Connect click
                # Capture path/language in closure
                def on_file_click(b, p=path, l=language):
                    root = self.get_native()
                    if hasattr(root, "artifacts_panel"):
                        root.artifacts_panel.load_artifact(p, l)
                        root.show_artifacts()
                        
                btn.connect("clicked", on_file_click)
                files_box.append(btn)
                
            self.append(files_box)

    def on_create_app_clicked(self, button):
        """Ask for app name and create the GNOME app."""
        
        # Simple dialog to get App Name
        dialog = Gtk.Dialog(title="Create App")
        dialog.set_transient_for(self.get_native())
        dialog.set_modal(True)
        dialog.add_buttons("Cancel", Gtk.ResponseType.CANCEL, "Create", Gtk.ResponseType.OK)
        
        content_area = dialog.get_content_area()
        content_area.set_spacing(12)
        content_area.set_margin_top(12)
        content_area.set_margin_bottom(12)
        content_area.set_margin_start(12)
        content_area.set_margin_end(12)
        
        label = Gtk.Label(label="Enter a name for your application:")
        content_area.append(label)
        
        entry = Gtk.Entry()
        entry.set_placeholder_text("App Name")
        entry.set_text("My Gaia App")
        content_area.append(entry)
        
        def on_response(dialog, response):
            if response == Gtk.ResponseType.OK:
                app_name = entry.get_text().strip()
                if app_name:
                    self._create_gnome_app(app_name)
            dialog.destroy()
            
        dialog.connect("response", on_response)
        dialog.show()

    def _create_gnome_app(self, app_name):
        try:
            # 1. Prepare Paths
            slug = "".join(x for x in app_name if x.isalnum() or x in "._- ").strip().replace(" ", "_").lower()
            if not slug: slug = "gaia_app"
            
            base_dir = os.path.expanduser("~/.local/share/gaia_apps")
            app_dir = os.path.join(base_dir, slug)
            os.makedirs(app_dir, exist_ok=True)
            
            www_dir = os.path.join(app_dir, "www")
            if os.path.exists(www_dir):
                shutil.rmtree(www_dir)
            shutil.copytree(self.folder_path, www_dir)
            
            # 2. Generate Icon
            icon_path = os.path.join(app_dir, "icon.png")
            self._generate_app_icon(app_name, icon_path)
            
            # 3. Create wrapper script
            script_path = os.path.join(app_dir, "main.py")
            with open(script_path, "w") as f:
                f.write(self._get_app_wrapper_code(app_name, slug))
                
            # 4. Create .desktop file
            desktop_dir = os.path.expanduser("~/.local/share/applications")
            os.makedirs(desktop_dir, exist_ok=True)
            desktop_file = os.path.join(desktop_dir, f"com.gaia.{slug}.desktop")
            
            with open(desktop_file, "w") as f:
                f.write(f"""[Desktop Entry]
Name={app_name}
Comment=Created with Gaia
Exec=python3 "{script_path}"
Icon={icon_path}
Terminal=false
Type=Application
Categories=Utility;
StartupNotify=true
StartupWMClass=com.gaia.{slug}
keywords=Gaia;Web;
""")
                
            # 5. Notify user
            # We can't easily show a toast from here without passing context, 
            # so we'll just print for now or try to find a parent overlay
            print(f"App '{app_name}' created successfully at {app_dir}")
            
            # Try to trigger a toast if possible
            root = self.get_native()
            if hasattr(root, "overlay"): # Assuming standard Adw.ToastOverlay usage
                root.add_toast(Adw.Toast.new(f"App '{app_name}' created!"))
            
            # Update database
            cmd = f"update-desktop-database {desktop_dir}"
            os.system(cmd)
            
        except Exception as e:
            print(f"Error creating app: {e}")

    def _generate_app_icon(self, app_name, output_path):
        size = 128
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
        ctx = cairo.Context(surface)
        
        # Random Gradient Background
        r1, g1, b1 = random.random(), random.random(), random.random()
        r2, g2, b2 = random.random(), random.random(), random.random()
        
        pat = cairo.LinearGradient(0.0, 0.0, size, size)
        pat.add_color_stop_rgb(0, r1, g1, b1)
        pat.add_color_stop_rgb(1, r2, g2, b2)
        
        ctx.rectangle(0, 0, size, size)
        ctx.set_source(pat)
        ctx.fill()
        
        # Initials
        initials = "".join([w[0] for w in app_name.split()[:2]]).upper()
        if not initials: initials = "??"
        
        ctx.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(size * 0.5)
        
        # Center text
        (x, y, width, height, dx, dy) = ctx.text_extents(initials)
        ctx.move_to(size/2 - width/2 - x, size/2 + height/2)
        ctx.set_source_rgb(1, 1, 1) # White text
        ctx.show_text(initials)
        
        surface.write_to_png(output_path)

    def _get_app_wrapper_code(self, app_name, app_id):
        return f'''import sys
import os
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('WebKit', '6.0')
from gi.repository import Gtk, Adw, WebKit

class MyApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.gaia.{app_id}", flags=0)

    def do_activate(self):
        win = Adw.ApplicationWindow(application=self)
        win.set_default_size(800, 600)
        win.set_title("{app_name}")
        
        # Main Layout
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        # Header Bar (Window Buttons)
        header = Adw.HeaderBar()
        box.append(header)
        
        # WebView
        webview = WebKit.WebView()
        webview.set_vexpand(True)
        webview.set_hexpand(True)
        
        settings = webview.get_settings()
        settings.set_allow_file_access_from_file_urls(True)
        settings.set_allow_universal_access_from_file_urls(True)
        
        # Calculate path to index.html
        base_dir = os.path.dirname(os.path.abspath(__file__))
        index_path = os.path.join(base_dir, "www", "index.html")
        
        webview.load_uri(f"file://{{index_path}}")
        
        box.append(webview)
        win.set_content(box)
        win.present()

if __name__ == "__main__":
    app = MyApp()
    app.run(sys.argv)
'''

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


