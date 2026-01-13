import gi
import os
import shutil
import zipfile
import random
import time
import cairo
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
# Optional dependencies
GtkSource = None
WebKit = None

try:
    gi.require_version('GtkSource', '5')
    from gi.repository import GtkSource
    print(f"[DEBUG ArtifactsPanel] GtkSource loaded: {GtkSource}")
except (ValueError, ImportError) as e:
    print(f"[DEBUG ArtifactsPanel] Failed to load GtkSource: {e}")

try:
    gi.require_version('WebKit', '6.0')
    from gi.repository import WebKit
    print(f"[DEBUG ArtifactsPanel] WebKit loaded: {WebKit}")
except (ValueError, ImportError) as e:
    print(f"[DEBUG ArtifactsPanel] Failed to load WebKit: {e}")

from gi.repository import Gtk, Adw, GObject, Gio, GLib, Gdk

class ArtifactsPanel(Gtk.Box):
    def __init__(self, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, **kwargs)
        self.add_css_class("artifacts-panel")
        self.set_size_request(400, -1)
        
        self.current_project_path = None
        self.project_files = [] # List of strings (filenames)
        self._internal_change = False
        self._last_load_time = 0  # Debounce for WebView reloads

        # Header
        self.header = Adw.HeaderBar()
        self.header.set_show_end_title_buttons(False)
        self.header.add_css_class("flat")
        
        # Custom Title Widget (Toolbar)
        self.title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.title_box.add_css_class("linked")
        
        # 1. Preview Toggle
        if WebKit:
            self.preview_btn = Gtk.ToggleButton()
            self.preview_btn.set_icon_name("globe-symbolic") # Icon for "Preview" state
            self.preview_btn.set_tooltip_text("Show Web Preview")
            self.preview_btn.connect("toggled", self.on_preview_toggled)
            self.title_box.append(self.preview_btn)
        
        # 2. File Dropdown (The "Code" replacement)
        self.file_model = Gtk.StringList()
        self.file_dropdown = Gtk.DropDown(model=self.file_model)
        self.file_dropdown.set_sensitive(False)
        self.file_dropdown.connect("notify::selected-item", self.on_file_selected)
        self.file_dropdown.set_hexpand(False)
        self.file_dropdown.set_size_request(160, -1) 
        self.title_box.append(self.file_dropdown)
        
        # 3. Export & Create
        self.export_btn = Gtk.Button()
        self.export_btn.set_icon_name("document-save-symbolic")
        self.export_btn.set_tooltip_text("Export ZIP")
        self.export_btn.connect("clicked", self.on_export_clicked)
        self.export_btn.set_sensitive(False)
        self.title_box.append(self.export_btn)
        
        self.create_app_btn = Gtk.Button()
        self.create_app_btn.set_icon_name("view-app-grid-symbolic")
        self.create_app_btn.set_tooltip_text("Create GNOME App")
        self.create_app_btn.connect("clicked", self.on_create_app_clicked)
        self.create_app_btn.set_sensitive(False)
        self.title_box.append(self.create_app_btn)
        
        self.fullscreen_btn = Gtk.ToggleButton()
        self.fullscreen_btn.set_icon_name("view-fullscreen-symbolic")
        self.fullscreen_btn.set_tooltip_text("Toggle Fullscreen")
        self.fullscreen_btn.connect("toggled", self.on_fullscreen_clicked)
        self.title_box.append(self.fullscreen_btn)

        self.header.set_title_widget(self.title_box)

        self.append(self.header)

        # Main content stack
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_vexpand(True)
        self.stack.set_hexpand(True)
        self.append(self.stack)

        # Code View
        self.code_scroll = Gtk.ScrolledWindow()
        self.code_scroll.set_vexpand(True)
        if GtkSource:
            self.code_view = GtkSource.View()
            self.code_view.set_editable(False)
            self.code_view.set_show_line_numbers(True)
            self.code_view.set_monospace(True)
            self.code_scroll.set_child(self.code_view)
            
            # Setup theme and react to system theme changes
            self._setup_code_view_theme()
            style_manager = Adw.StyleManager.get_default()
            style_manager.connect("notify::dark", self._on_style_changed)
        else:
            self.code_view = Gtk.TextView()
            self.code_view.set_editable(False)
            self.code_view.set_monospace(True)
            self.code_scroll.set_child(self.code_view)
        
        self.stack.add_named(self.code_scroll, "code")

        # Preview View
        self.preview_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.preview_box.set_vexpand(True)
        self.preview_box.set_hexpand(True)
        if WebKit:
            self.web_view = WebKit.WebView()
            self.web_view.set_vexpand(True)
            self.web_view.set_hexpand(True)
            
            # Enable local file access (Critical for relative imports)
            settings = self.web_view.get_settings()
            settings.set_allow_file_access_from_file_urls(True)
            settings.set_allow_universal_access_from_file_urls(True)
            settings.set_enable_write_console_messages_to_stdout(True)
            
            self.preview_box.append(self.web_view)
            
            # Setup Bridge
            from src.ui.preview.manager import PreviewManager
            self.preview_manager = PreviewManager()
            self.preview_manager.setup_bridge(self.web_view)
            
            print("[DEBUG ArtifactsPanel] WebView created and Bridge successfully hooked.")
        else:
            label = Gtk.Label(label="WebKit (Web Preview) not available")
            label.add_css_class("dim-label")
            self.preview_box.append(label)
        
        self.stack.add_named(self.preview_box, "preview")

        # Placeholder (Initial State)
        self.placeholder = Adw.StatusPage()
        self.placeholder.set_title("No Project")
        self.placeholder.set_description("No web project loaded.")
        self.placeholder.set_icon_name("folder-symbolic")
        self.stack.add_named(self.placeholder, "placeholder")
        
        self.stack.set_visible_child_name("placeholder")
        
        # Reload WebView when panel becomes visible
        self.connect("map", self._on_map)

    def load_project(self, folder_path: str, is_research: bool = False, force: bool = False, quick_load: bool = False):
        """
        Load a web project from a folder path.
        :param quick_load: If True, minimizes the loading delay (use when checking existing files).
        """
        if not os.path.exists(folder_path):
            return
        
        # Debounce: skip if same project was loaded very recently (unless forced)
        if (not force and 
            self.current_project_path == folder_path and 
            time.time() - self._last_load_time < 0.5):
            return

        # Start logging for this project
        if hasattr(self, 'preview_manager'):
            self.preview_manager.start_logging(folder_path)

        # Auto-detect research mode from path if not explicitly set
        if not is_research and "deepresearch" in folder_path:
            is_research = True

        self.current_project_path = folder_path
        self.is_research_mode = is_research
        self._internal_change = True  # Block all signal handlers
        
        # 1. Scan files (FLAT ONLY)
        files = []
        if os.path.exists(folder_path):
            with os.scandir(folder_path) as entries:
                for entry in entries:
                    if entry.is_file():
                        f = entry.name
                        # Filter out internal files
                        if f == "console.json":
                            continue
                        # Filter useful files
                        if f.endswith(('.html', '.css', '.js', '.py', '.md', '.json', '.txt')):
                            files.append(f)
        
        files.sort()
        # Ensure index.html is first if exists
        if "index.html" in files:
            files.remove("index.html")
            files.insert(0, "index.html")
            
        self.project_files = files
        
        # 2. Update Dropdown
        self.file_model = Gtk.StringList.new(files)
        self.file_dropdown.set_model(self.file_model)
        self.file_dropdown.set_sensitive(True)
        
        # 3. Enable Actions
        self.export_btn.set_sensitive(True)
        if self.is_research_mode:
            self.export_btn.set_icon_name("document-print-symbolic")
            self.export_btn.set_tooltip_text("Download Report (PDF)")
            self.create_app_btn.set_sensitive(False)
        else:
            self.export_btn.set_icon_name("document-save-symbolic")
            self.export_btn.set_tooltip_text("Export ZIP")
            self.create_app_btn.set_sensitive(True)
        if hasattr(self, 'preview_btn'):
            self.preview_btn.set_sensitive(True)
        
        # 4. Select first file
        if files:
            self.file_dropdown.set_selected(0)
            self._load_file_content(files[0])
        
        # 5. Find entry point for preview
        entry_point = None
        if "index.html" in files:
            entry_point = "index.html"
        else:
            for f in files:
                if f.endswith(".html"):
                    entry_point = f
                    break
        
        # 6. Load WebView and force preview mode via delayed callback
        if entry_point:
            if WebKit:
                full_path = os.path.join(self.current_project_path, entry_point)
                target_uri = f"file://{full_path}"
                
                # Delay loading to ensure files are fully flushed to disk
                def delayed_load():
                    # If loaded recently (e.g. by _on_map race), skip
                    if time.time() - self._last_load_time < 0.2:
                        return False

                    if os.path.exists(full_path):
                        # Always load, even if hidden. WebKit can handle background loading.
                        current_uri = self.web_view.get_uri()
                        if current_uri == target_uri:
                            self.web_view.reload_bypass_cache()
                        else:
                            self.web_view.load_uri(target_uri)
                        self._last_load_time = time.time()
                    return False
                
                delay_ms = 10 if quick_load else 300
                GLib.timeout_add(delay_ms, delayed_load)
            
            # Use GLib.timeout_add to guarantee this runs AFTER all signal handlers and UI updates
            def force_preview_mode():
                print(f"[DEBUG] Forcing preview mode for {entry_point}")
                
                # Check if we need to update the dropdown selection to match the preview
                if hasattr(self, 'project_files') and entry_point in self.project_files:
                    try:
                        idx = self.project_files.index(entry_point)
                        self._internal_change = True # Block signals
                        self.file_dropdown.set_selected(idx)
                        self._load_file_content(entry_point) 
                        self._internal_change = False
                    except Exception as e:
                        print(f"[DEBUG] Failed to sync dropdown: {e}")

                if hasattr(self, 'preview_btn'):
                    self.preview_btn.set_active(True)
                self.stack.set_visible_child_name("preview")
                self._internal_change = False
                return False  # Don't repeat
            
            GLib.timeout_add(100, force_preview_mode)
        else:
            # No HTML, show code
            if hasattr(self, 'preview_btn'):
                self.preview_btn.set_active(False)
            if files:
                self.stack.set_visible_child_name("code")
            else:
                self.stack.set_visible_child_name("placeholder")
            self._internal_change = False
            self._last_load_time = time.time()

    def on_file_selected(self, dropdown, param):
        """Handle file selection from dropdown."""
        selected_item = dropdown.get_selected_item()
        if not selected_item: return
        filename = selected_item.get_string()
        self._load_file_content(filename)
        
        if self._internal_change:
            return
        
        # If user selects a file, switch to code view and untoggle preview
        if hasattr(self, 'preview_btn'):
            self.preview_btn.set_active(False) 

        self.stack.set_visible_child_name("code")

    def _load_file_content(self, rel_path):
        if not self.current_project_path: return
        
        full_path = os.path.join(self.current_project_path, rel_path)
        
        if os.path.isdir(full_path):
            return

        content = ""
        try:
            with open(full_path, "r") as f:
                content = f.read()
        except Exception as e:
            content = f"(Unable to read file: {e})"
            
        buffer = self.code_view.get_buffer()
        buffer.set_text(content, -1)
        
        if GtkSource:
            lang_manager = GtkSource.LanguageManager.get_default()
            # Simple extension matching
            ext = os.path.splitext(rel_path)[1][1:]
            if ext == "js": ext = "javascript"
            lang = lang_manager.get_language(ext)
            if lang:
                buffer.set_language(lang)

    def on_fullscreen_clicked(self, btn):
        """Toggle fullscreen mode for artifacts."""
        root = self.get_native()
        if hasattr(root, "toggle_artifact_fullscreen"):
            root.toggle_artifact_fullscreen()
            
        if btn.get_active():
             btn.set_icon_name("view-restore-symbolic")
        else:
             btn.set_icon_name("view-fullscreen-symbolic")

    def on_preview_toggled(self, btn):
        if self._internal_change:
            return
            
        if btn.get_active():
            self.stack.set_visible_child_name("preview")
        else:
            self.stack.set_visible_child_name("code")
            
    def clear(self):
        """Reset the panel to its initial state."""
        self._internal_change = True
        self.current_project_path = None
        self.project_files = []
        
        # Clear dropdown
        self.file_model = Gtk.StringList()
        self.file_dropdown.set_model(self.file_model)
        self.file_dropdown.set_sensitive(False)
        
        # Disable Actions
        self.export_btn.set_sensitive(False)
        self.create_app_btn.set_sensitive(False)
        
        if hasattr(self, 'preview_btn'):
            self.preview_btn.set_active(False)
            self.preview_btn.set_sensitive(False)
            
        # Clear WebView
        if WebKit and hasattr(self, 'web_view'):
            self.web_view.load_uri("about:blank")
            
        # Clear Code View
        self.code_view.get_buffer().set_text("", -1)
        
        # Show Placeholder
        self.stack.set_visible_child_name("placeholder")
        self._internal_change = False

    def _setup_code_view_theme(self):
        """Apply style scheme based on system dark/light preference."""
        if not GtkSource:
            return
        
        style_manager = Adw.StyleManager.get_default()
        is_dark = style_manager.get_dark()
        
        scheme_manager = GtkSource.StyleSchemeManager.get_default()
        
        # Choose scheme based on dark mode
        scheme_name = "Adwaita-dark" if is_dark else "Adwaita"
        scheme = scheme_manager.get_scheme(scheme_name)
        
        # Fallbacks
        if not scheme:
            scheme = scheme_manager.get_scheme("oblivion" if is_dark else "classic")
        
        if scheme:
            buffer = self.code_view.get_buffer()
            buffer.set_style_scheme(scheme)

    def _on_style_changed(self, style_manager, param):
        """React to system theme changes."""
        self._setup_code_view_theme()

    def _on_map(self, widget):
        """Reload content when panel becomes visible."""
        # Debounce: don't reload if we just loaded recently
        if time.time() - self._last_load_time < 1.0:
            return
            
        if self.current_project_path and WebKit and hasattr(self, 'web_view'):
            # Find entry point
            entry_point = None
            if "index.html" in self.project_files:
                entry_point = "index.html"
            else:
                for f in self.project_files:
                    if f.endswith(".html"):
                        entry_point = f
                        break
            if entry_point:
                full_path = os.path.join(self.current_project_path, entry_point)
                if os.path.exists(full_path):
                    self.web_view.load_uri(f"file://{full_path}")
                    self._last_load_time = time.time()

    def load_artifact(self, path, language="text"):
        """Legacy compatibility or single file loading."""
        # For now, if we get a single file, treat parent as project?
        if os.path.exists(path):
            if os.path.isdir(path):
                self.load_project(path, force=True)
            else:
                parent = os.path.dirname(path)
                self.load_project(parent, force=True)
                # Try to select the specific file
                fname = os.path.basename(path)
                if fname in self.project_files:
                    idx = self.project_files.index(fname)
                    self.file_dropdown.set_selected(idx)

    # --- Actions Ported from ProjectCard ---

    def on_export_clicked(self, button):
        if not self.current_project_path: return
        
        if getattr(self, "is_research_mode", False):
            self._print_to_pdf()
            return
        
        dialog = Gtk.FileDialog()
        dialog.set_title("Save Website ZIP")
        dialog.set_initial_name("website_export.zip")
        
        def on_save_response(dialog, result):
            try:
                file = dialog.save_finish(result)
                if not file: return
                zip_path = file.get_path()
                with zipfile.ZipFile(zip_path, 'w') as zipf:
                    for root_dir, dirs, files in os.walk(self.current_project_path):
                        for file in files:
                            full_path = os.path.join(root_dir, file)
                            rel_path = os.path.relpath(full_path, self.current_project_path)
                            zipf.write(full_path, rel_path)
                print(f"Exported to {zip_path}")
                # Optional: Toast
                self._show_toast(f"Exported to {os.path.basename(zip_path)}")
            except Exception as e:
                print(f"Export failed: {e}")
                self._show_toast(f"Export failed: {e}")

        dialog.save(self.get_native(), None, on_save_response)

    def on_create_app_clicked(self, button):
        """Ask for app name and create the GNOME app."""
        if not self.current_project_path: return

        # Simple dialog to get App Name
        dialog = Gtk.Dialog(title="Create App")
        dialog.set_transient_for(self.get_native())
        dialog.set_modal(True)
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Create", Gtk.ResponseType.OK)
        
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
            shutil.copytree(self.current_project_path, www_dir)
            
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
            print(f"App '{app_name}' created successfully at {app_dir}")
            self._show_toast(f"App '{app_name}' created!")
            
            # Update database
            cmd = f"update-desktop-database {desktop_dir}"
            os.system(cmd)
            
        except Exception as e:
            print(f"Error creating app: {e}")
            self._show_toast(f"Error: {e}")

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

    def _print_to_pdf(self):
        """Export current view to PDF using WebKit printing."""
        if not WebKit or not hasattr(self, 'web_view'):
            self._show_toast("PDF Export requires WebKit")
            return

        print_op = WebKit.PrintOperation.new(self.web_view)
        # Configure for PDF output
        # In WebKitGTK 6.0, we can basically just run the print dialog 
        # or try to set export settings.
        # For simplicity, let's open the standard print dialog which includes "Print to File (PDF)"
        print_op.run_dialog(self.get_native())

    def _show_toast(self, message):
        root = self.get_native()
        if hasattr(root, "overlay"): 
            # Assuming root window has an 'overlay' property which is Adw.ToastOverlay
            root.overlay.add_toast(Adw.Toast.new(message))
        elif hasattr(root, "add_toast"):
             root.add_toast(Adw.Toast.new(message))
