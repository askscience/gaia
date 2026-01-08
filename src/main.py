import sys
import os

# Fix for blank WebView in packaged apps (Debian/Flatpak)
# WebKitGTK sandbox can block access to local files (~/.gaia/artifacts)
os.environ["WEBKIT_DISABLE_SANDBOX"] = "1"

import gi

# Ensure project root is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Gdk
from src.ui.window import MainWindow
from src.core.chat_storage import ChatStorage

class GaiaApplication(Adw.Application):
    def __init__(self):
        super().__init__(application_id='io.github.askscience.gaia',
                         flags=0)
        self.storage = ChatStorage()

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = MainWindow(storage=self.storage, application=self)
            self.load_css()
        win.present()

    def load_css(self):
        # Add project root to icon theme search path
        icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        icon_theme.add_search_path(project_root)

        css_provider = Gtk.CssProvider()
        
        if getattr(sys, 'frozen', False):
            # PyInstaller one-file bundle
            base_path = sys._MEIPASS
            # We bundled 'src' folder to 'src'
            css_path = os.path.join(base_path, "src", "ui", "css", "style.css")
        else:
            # Development mode
            css_path = os.path.join(current_dir, "ui", "css", "style.css")
            
        try:
            css_provider.load_from_path(css_path)
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(),
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        except Exception as e:
            print(f"Failed to load CSS: {e}")

def main():
    app = GaiaApplication()
    return app.run(sys.argv)

if __name__ == '__main__':
    sys.exit(main())
