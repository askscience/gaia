import gi
import os
import shutil
gi.require_version('Gtk', '4.0')
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, Gio
from src.core.language_manager import LanguageManager

class ResearchCard(Gtk.Frame):
    """A specialized card for Deep Research reports with PDF export."""
    def __init__(self, title: str, path: str):
        super().__init__()
        self.add_css_class("card")
        self.lang_manager = LanguageManager()
        
        self.path = path
        self.title = title
        
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main_box.set_spacing(8)
        main_box.set_margin_top(12)
        main_box.set_margin_bottom(12)
        main_box.set_margin_start(12)
        main_box.set_margin_end(12)
        
        # Header (Icon + Title)
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        header.set_spacing(12)
        
        icon = Gtk.Image.new_from_icon_name("system-search-symbolic")
        icon.set_pixel_size(32)
        header.append(icon)
        
        text_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        title_label = Gtk.Label(label=title)
        title_label.add_css_class("source-title")
        title_label.set_halign(Gtk.Align.START)
        text_vbox.append(title_label)
        
        title_label.set_halign(Gtk.Align.START)
        text_vbox.append(title_label)
        
        type_label = Gtk.Label(label=self.lang_manager.get("components.research_card.type_label"))
        type_label.add_css_class("dim-label")
        type_label.set_halign(Gtk.Align.START)
        text_vbox.append(type_label)
        
        header.append(text_vbox)
        main_box.append(header)
        
        # Action Buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        button_box.set_spacing(8)
        button_box.set_margin_top(8)
        
        button_box.set_margin_top(8)
        
        view_btn = Gtk.Button(label=self.lang_manager.get("components.research_card.view_button"))
        view_btn.add_css_class("suggested-action")
        view_btn.connect("clicked", self.on_view_clicked)
        button_box.append(view_btn)
        
        button_box.append(view_btn)
        
        pdf_btn = Gtk.Button(label=self.lang_manager.get("components.research_card.pdf_button"))
        pdf_btn.connect("clicked", self.on_pdf_clicked)
        button_box.append(pdf_btn)
        
        main_box.append(button_box)
        self.set_child(main_box)

    def on_view_clicked(self, button):
        root = self.get_native()
        if hasattr(root, "artifacts_panel"):
            root.artifacts_panel.load_artifact({"path": self.path, "language": "html", "type": "web"})
            root.show_artifacts()

    def on_pdf_clicked(self, button):
        """Triggers the PDF export."""
        dialog = Gtk.FileDialog()
        dialog.set_title(self.lang_manager.get("components.research_card.pdf_dialog_title"))
        dialog.set_initial_name(f"{self.title.replace(' ', '_').lower()}.pdf")
        
        def on_save_response(dialog, result):
            try:
                file = dialog.save_finish(result)
                if not file: return
                pdf_path = file.get_path()
                self._export_to_pdf(pdf_path)
            except Exception as e:
                print(f"PDF Save error: {e}")

        dialog.save(self.get_native(), None, on_save_response)

    def _export_to_pdf(self, pdf_path):
        """Uses pre-generated PDF or WebKit to print the report."""
        # 1. Try to use pre-generated PDF
        try:
            source_dir = os.path.dirname(self.path)
            pre_gen_pdf = os.path.join(source_dir, "report.pdf")
            if os.path.exists(pre_gen_pdf):
                shutil.copy2(pre_gen_pdf, pdf_path)
                return
        except Exception as e:
            print(f"Failed to copy pre-generated PDF: {e}")

        # 2. Fallback to WebKit Print
        try:
            from gi.repository import WebKit
            
            webview = WebKit.WebView()
            settings = webview.get_settings()
            settings.set_allow_file_access_from_file_urls(True)
            
            def on_load_changed(web_view, load_event):
                if load_event == WebKit.LoadEvent.FINISHED:
                    # Print to PDF
                    print_operation = WebKit.PrintOperation.new(web_view)
                    file = Gio.File.new_for_path(pdf_path)
                    print_operation.print_to_file(file)
            
            webview.connect("load-changed", on_load_changed)
            webview.load_uri(f"file://{self.path}")
            
            # Note: The webview doesn't need to be visible to print
        except ImportError:
            print("WebKit not available for PDF export.")
        except Exception as e:
            print(f"Failed to export PDF: {e}")
