import gi
import re
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Gdk, Adw
from src.ui.utils import markdown_to_pango

class PlanConfirmationCard(Gtk.Frame):
    """
    A specific card for reviewing implementation plans properly.
    Uses Adwaita widgets for a native system look.
    """
    def __init__(self, plan_data: dict, on_proceed_callback):
        super().__init__()
        self.add_css_class("card")
        self.on_proceed = on_proceed_callback
        
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main_box.set_spacing(16)
        main_box.set_margin_top(16)
        main_box.set_margin_bottom(16)
        main_box.set_margin_start(16)
        main_box.set_margin_end(16)
        
        # 1. Header & Description
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        header_box.set_spacing(12)
        
        title = Gtk.Label()
        title.set_markup(f"<span size='large' weight='bold'>Proposed Plan</span>")
        title.set_halign(Gtk.Align.START)
        header_box.append(title)
        
        if "description" in plan_data and plan_data["description"]:
            desc_text = plan_data["description"]
            # cleanup clean logs prefix if present
            desc_text = re.sub(r'^---.*?---\s*', '', desc_text, flags=re.DOTALL)
            
            parsed_desc = markdown_to_pango(desc_text)
            desc = Gtk.Label()
            desc.set_markup(parsed_desc)
            desc.set_wrap(True)
            desc.set_max_width_chars(60)
            desc.set_halign(Gtk.Align.START)
            desc.add_css_class("dim-label")
            header_box.append(desc)
            
        main_box.append(header_box)
        
        # 2. File List (Adw.PreferencesGroup with ActionRows)
        files = plan_data.get("files", [])
        if files:
            # Wrap in ScrolledWindow to prevent massive height
            scrolled = Gtk.ScrolledWindow()
            scrolled.set_min_content_height(min(len(files) * 60, 350))
            scrolled.set_propagate_natural_height(True)
            
            pref_group = Adw.PreferencesGroup()
            pref_group.set_title("Files to Create")
            
            for f in files:
                row = Adw.ActionRow()
                row.set_title(f.get('filename', 'Unknown File'))
                
                # Subtitle for dependencies
                deps = f.get('dependencies', [])
                if deps:
                    display_deps = ", ".join(deps)
                    if len(display_deps) > 50: display_deps = display_deps[:47] + "..."
                    row.set_subtitle(f"Imports: {display_deps}")
                
                # Icon
                fn = f.get('filename', '').lower()
                icon_name = "text-x-generic-symbolic"
                if fn.endswith('.html'): icon_name = "text-html-symbolic"
                elif fn.endswith('.css'): icon_name = "text-css-symbolic"
                elif fn.endswith('.js'): icon_name = "text-x-javascript-symbolic"
                elif fn.endswith('.py'): icon_name = "text-x-python-symbolic"
                elif fn.endswith('.md'): icon_name = "text-markdown-symbolic"
                
                icon = Gtk.Image.new_from_icon_name(icon_name)
                row.add_prefix(icon)
                
                pref_group.add(row)
                
            scrolled.set_child(pref_group)
            main_box.append(scrolled)
        
        # 3. Footer / Action
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        btn_box.set_halign(Gtk.Align.END)
        btn_box.set_margin_top(8)
        
        self.proceed_btn = Gtk.Button(label="Proceed with Plan")
        self.proceed_btn.add_css_class("suggested-action")
        self.proceed_btn.add_css_class("pill")
        self.proceed_btn.connect("clicked", self._on_click)
        btn_box.append(self.proceed_btn)
        
        main_box.append(btn_box)
        self.set_child(main_box)
        
    def _on_click(self, btn):
        btn.set_sensitive(False)
        btn.set_label("Build Queued...")
        if self.on_proceed:
            self.on_proceed()
