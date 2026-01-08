import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, GLib

class CodeBlock(Gtk.Box):
    """A widget for displaying code blocks with a copy button."""
    
    def __init__(self, content: str, language: str = "text", *args, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, *args, **kwargs)
        self.add_css_class("code-block")
        
        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        header.add_css_class("code-header")
        
        lang_label = Gtk.Label(label=language.upper())
        lang_label.add_css_class("code-lang-label")
        lang_label.set_hexpand(True)
        lang_label.set_halign(Gtk.Align.START)
        header.append(lang_label)
        
        copy_btn = Gtk.Button()
        copy_btn.set_icon_name("edit-copy-symbolic")
        copy_btn.add_css_class("flat")
        copy_btn.add_css_class("copy-button")
        copy_btn.set_tooltip_text("Copy")
        copy_btn.connect("clicked", self._on_copy_clicked)
        header.append(copy_btn)
        
        self.append(header)
        
        # Content
        self.content = content
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER) # Horizontal scroll only
        scrolled.set_max_content_height(400) # Prevents huge blocks from taking over
        
        # Using TextView for better code display (selection, etc)
        text_view = Gtk.TextView()
        text_view.set_editable(False)
        text_view.set_monospace(True)
        text_view.set_wrap_mode(Gtk.WrapMode.NONE) # Code usually better without wrapping
        text_view.add_css_class("code-content")
        
        buffer = text_view.get_buffer()
        buffer.set_text(self.content, -1)
        
        scrolled.set_child(text_view)
        self.append(scrolled)
        
    def _on_copy_clicked(self, button):
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.set(self.content)
        
        # Visual feedback
        icon = button.get_child() 
        # (Usually an Adw.ButtonContent or Image, but simpler for standard icon button)
        
        # Change icon temporarily
        button.set_icon_name("object-select-symbolic")
        
        def restore():
            button.set_icon_name("edit-copy-symbolic")
            return False
            
        GLib.timeout_add(1000, restore)
