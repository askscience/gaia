use std::cell::RefCell;
use std::fs;
use std::path::Path;
use std::rc::Rc;

use gtk4::glib;
use gtk4::prelude::*;
use gtk4::{self, Box as GtkBox, Button, DropDown, Label, Orientation, Stack, ToggleButton};
use libadwaita::prelude::*;
use libadwaita::{HeaderBar, StatusPage, Toast};

struct PanelData {
    current_project_path: Option<String>,
    project_files: Vec<String>,
    is_research_mode: bool,
    internal_change: bool,
}

pub struct ArtifactsPanel {
    pub widget: GtkBox,
    data: Rc<RefCell<PanelData>>,
    file_dropdown: DropDown,
    stack: Stack,
    code_view: gtk4::TextView,
    webview: gtk4::Label,
    export_btn: Button,
    create_app_btn: Button,
    preview_btn: ToggleButton,
    fullscreen_btn: ToggleButton,
    placeholder: StatusPage,
}

impl ArtifactsPanel {
    pub fn new() -> Self {
        let data = Rc::new(RefCell::new(PanelData {
            current_project_path: None,
            project_files: Vec::new(),
            is_research_mode: false,
            internal_change: false,
        }));

        let widget = GtkBox::new(Orientation::Vertical, 0);
        widget.add_css_class("artifacts-panel");
        widget.set_size_request(400, -1);

        let header = HeaderBar::new();
        header.set_show_end_title_buttons(false);
        header.add_css_class("flat");

        let title_box = GtkBox::new(Orientation::Horizontal, 0);
        title_box.add_css_class("linked");

        let preview_btn = ToggleButton::new();
        preview_btn.set_icon_name("globe-symbolic");
        preview_btn.set_tooltip_text(Some("Show Web Preview"));
        title_box.append(&preview_btn);

        let file_dropdown = DropDown::from_strings(&[]);
        file_dropdown.set_sensitive(false);
        file_dropdown.set_size_request(160, -1);
        title_box.append(&file_dropdown);

        let export_btn = Button::new();
        export_btn.set_icon_name("document-save-symbolic");
        export_btn.set_tooltip_text(Some("Export ZIP"));
        export_btn.set_sensitive(false);
        title_box.append(&export_btn);

        let create_app_btn = Button::new();
        create_app_btn.set_icon_name("view-app-grid-symbolic");
        create_app_btn.set_tooltip_text(Some("Create GNOME App"));
        create_app_btn.set_sensitive(false);
        title_box.append(&create_app_btn);

        let fullscreen_btn = ToggleButton::new();
        fullscreen_btn.set_icon_name("view-fullscreen-symbolic");
        fullscreen_btn.set_tooltip_text(Some("Toggle Fullscreen"));
        title_box.append(&fullscreen_btn);

        header.set_title_widget(Some(&title_box));
        widget.append(&header);

        let stack = Stack::new();
        stack.set_transition_type(gtk4::StackTransitionType::Crossfade);
        stack.set_vexpand(true);
        stack.set_hexpand(true);
        widget.append(&stack);

        let code_scroll = gtk4::ScrolledWindow::new();
        code_scroll.set_vexpand(true);

        let code_view = gtk4::TextView::new();
        code_view.set_editable(false);
        code_view.set_monospace(true);
        code_scroll.set_child(Some(&code_view));
        stack.add_named(&code_scroll, Some("code"));

        let webview = Label::new(Some("Web preview requires webkitgtk system library"));
        webview.set_vexpand(true);
        webview.set_hexpand(true);
        stack.add_named(&webview, Some("preview"));

        let placeholder = StatusPage::new();
        placeholder.set_title("No Project");
        placeholder.set_description(Some("No web project loaded."));
        placeholder.set_icon_name(Some("folder-symbolic"));
        stack.add_named(&placeholder, Some("placeholder"));
        stack.set_visible_child_name("placeholder");

        let status_label = Label::new(Some(""));
        status_label.add_css_class("dim-label");
        widget.append(&status_label);

        {
            let data = data.clone();
            let stack = stack.clone();
            preview_btn.connect_toggled(move |btn| {
                let d = data.borrow();
                if d.internal_change {
                    return;
                }
                drop(d);
                if btn.is_active() {
                    stack.set_visible_child_name("preview");
                } else {
                    stack.set_visible_child_name("code");
                }
            });
        }

        {
            let data = data.clone();
            let stack = stack.clone();
            let preview_btn = preview_btn.clone();
            let code_view_for_dd = code_view.clone();
            file_dropdown.connect_selected_item_notify(move |dd| {
                let d = data.borrow();
                if d.internal_change {
                    return;
                }
                let current_path = d.current_project_path.clone();
                drop(d);

                if let Some(item) = dd.selected_item() {
                    if let Some(so) = item.downcast_ref::<gtk4::StringObject>() {
                        let filename = so.string().to_string();
                        if let Some(ref proj_path) = current_path {
                            let full_path = Path::new(proj_path).join(&filename);
                            if let Ok(content) = fs::read_to_string(&full_path) {
                                code_view_for_dd.buffer().set_text(&content);
                            }
                        }
                        stack.set_visible_child_name("code");
                        preview_btn.set_active(false);
                    }
                }
            });
        }

        {
            let data = data.clone();
            let export_btn = export_btn.clone();
            let widget = widget.clone();
            export_btn.connect_clicked(move |_btn| {
                let d = data.borrow();
                let path = d.current_project_path.clone();
                let is_research = d.is_research_mode;
                drop(d);
                if let Some(ref proj_path) = path {
                    if is_research {
                        let pdf_path = Path::new(proj_path).join("report.pdf");
                        if pdf_path.exists() {
                            save_existing_pdf(widget.upcast_ref(), &pdf_path);
                    }
                } else {
                    export_zip_internal(widget.upcast_ref(), proj_path);
                    }
                }
            });
        }

        {
            let widget = widget.clone();
            let data = data.clone();
            create_app_btn.connect_clicked(move |_btn| {
                let d = data.borrow();
                let path = d.current_project_path.clone();
                drop(d);
                if let Some(ref proj_path) = path {
                    create_gnome_app_dialog(widget.upcast_ref(), proj_path);
                }
            });
        }

        {
            let widget = widget.clone();
            fullscreen_btn.connect_toggled(move |btn| {
                if let Some(root) = widget.root() {
                    if let Some(window) = root.downcast_ref::<gtk4::Window>() {
                        if btn.is_active() {
                            window.fullscreen();
                        } else {
                            window.unfullscreen();
                        }
                    }
                }
            });
        }

        ArtifactsPanel {
            widget,
            data,
            file_dropdown,
            stack,
            code_view,
            webview,
            export_btn,
            create_app_btn,
            preview_btn,
            fullscreen_btn,
            placeholder,
        }
    }

    pub fn load_project(&self, project_path: &str, _force: bool, _quick_load: bool) {
        if !Path::new(project_path).exists() {
            return;
        }

        let mut d = self.data.borrow_mut();
        let is_research = project_path.contains("deepresearch");
        d.current_project_path = Some(project_path.to_string());
        d.is_research_mode = is_research;
        d.internal_change = true;

        let mut files: Vec<String> = Vec::new();
        if let Ok(entries) = fs::read_dir(project_path) {
            for entry in entries.flatten() {
                if !entry.file_type().map(|t| t.is_file()).unwrap_or(false) {
                    continue;
                }
                let name = entry.file_name().to_string_lossy().to_string();
                if name == "console.json" {
                    continue;
                }
                if name.ends_with(".html")
                    || name.ends_with(".css")
                    || name.ends_with(".js")
                    || name.ends_with(".py")
                    || name.ends_with(".md")
                    || name.ends_with(".json")
                    || name.ends_with(".txt")
                {
                    files.push(name);
                }
            }
        }

        files.sort();
        if let Some(idx) = files.iter().position(|f| f == "index.html") {
            files.remove(idx);
            files.insert(0, "index.html".to_string());
        }

        d.project_files = files.clone();
        drop(d);

        let strings: Vec<&str> = files.iter().map(|s| s.as_str()).collect();
        let model = gtk4::StringList::new(&strings);
        self.file_dropdown.set_model(Some(&model));
        self.file_dropdown.set_sensitive(true);
        self.export_btn.set_sensitive(true);

        if is_research {
            self.export_btn.set_icon_name("folder-download-symbolic");
            self.export_btn
                .set_tooltip_text(Some("Download Report (PDF)"));
            self.create_app_btn.set_sensitive(false);
        } else {
            self.export_btn.set_icon_name("document-save-symbolic");
            self.export_btn.set_tooltip_text(Some("Export ZIP"));
            self.create_app_btn.set_sensitive(true);
        }
        self.preview_btn.set_sensitive(true);

        if !files.is_empty() {
            self.file_dropdown.set_selected(0);
            let full_path = Path::new(project_path).join(&files[0]);
            if let Ok(content) = fs::read_to_string(&full_path) {
                self.code_view.buffer().set_text(&content);
            }
        }

        self.data.borrow_mut().internal_change = false;
    }

    pub fn clear(&self) {
        let mut d = self.data.borrow_mut();
        d.internal_change = true;
        d.current_project_path = None;
        d.project_files.clear();
        d.is_research_mode = false;
        drop(d);

        self.file_dropdown.set_model(None::<&gtk4::StringList>);
        self.file_dropdown.set_sensitive(false);
        self.export_btn.set_sensitive(false);
        self.create_app_btn.set_sensitive(false);
        self.preview_btn.set_active(false);
        self.preview_btn.set_sensitive(false);
        self.code_view.buffer().set_text("");
        self.stack.set_visible_child_name("placeholder");
        self.data.borrow_mut().internal_change = false;
    }

    pub fn set_visible(&self, visible: bool) {
        self.widget.set_visible(visible);
    }

    pub fn load_file(&self, filepath: &str) {
        if let Ok(content) = fs::read_to_string(filepath) {
            self.code_view.buffer().set_text(&content);
        }
    }

    pub fn load_web_preview(&self, _html_content: &str) {
        self.webview.set_label("Web preview requires webkitgtk system library");
    }

    pub fn export_zip(&self) {
        let d = self.data.borrow();
        if let Some(ref path) = d.current_project_path {
            export_zip_internal(self.widget.upcast_ref(), path);
        }
    }

    pub fn download_pdf(&self) {
        let d = self.data.borrow();
        if let Some(ref proj_path) = d.current_project_path {
            let pdf_path = Path::new(proj_path).join("report.pdf");
            if pdf_path.exists() {
                save_existing_pdf(self.widget.upcast_ref(), &pdf_path);
            }
        }
    }

    pub fn load_artifact(&self, path: &str, _language: &str) {
        if Path::new(path).is_dir() {
            self.load_project(path, true, false);
        } else if let Some(parent) = Path::new(path).parent() {
            let parent_str = parent.to_string_lossy().to_string();
            self.load_project(&parent_str, true, false);
        }
    }
}

fn show_toast(widget: &gtk4::Widget, message: &str) {
    if let Some(root) = widget.root() {
        if let Some(window) = root.downcast_ref::<libadwaita::ApplicationWindow>() {
            if let Some(content) = window.content() {
                if let Some(toast_overlay) = content.downcast_ref::<libadwaita::ToastOverlay>() {
                    toast_overlay.add_toast(Toast::new(message));
                }
            }
        }
    }
}

fn export_zip_internal(widget: &gtk4::Widget, project_path: &str) {
    let dialog = gtk4::FileDialog::new();
    dialog.set_title("Save Website ZIP");
    dialog.set_initial_name(Some("website_export.zip"));

    let project_path = project_path.to_string();
    let widget_weak = widget.downgrade();

    dialog.save(
        widget
            .root()
            .as_ref()
            .and_then(|r| r.downcast_ref::<gtk4::Window>()),
        gtk4::gio::Cancellable::NONE,
        move |result| {
            let Some(widget) = widget_weak.upgrade() else {
                return;
            };
            match result {
                Ok(file) => {
                    let Some(zip_path) = file.path() else {
                        return;
                    };
                    match create_zip(&project_path, &zip_path) {
                        Ok(()) => {
                            let msg = format!(
                                "Exported to {}",
                                zip_path.file_name().unwrap_or_default().to_string_lossy()
                            );
                            show_toast(&widget, &msg);
                        }
                        Err(e) => {
                            show_toast(&widget, &format!("Export failed: {}", e));
                        }
                    }
                }
                Err(_) => {}
            }
        },
    );
}

fn create_zip(project_path: &str, zip_path: &std::path::Path) -> Result<(), String> {
    let file = fs::File::create(zip_path).map_err(|e| e.to_string())?;
    let mut zip = zip::ZipWriter::new(file);
    let options = zip::write::SimpleFileOptions::default()
        .compression_method(zip::CompressionMethod::Deflated);

    fn add_dir(
        zip: &mut zip::ZipWriter<fs::File>,
        options: zip::write::SimpleFileOptions,
        base: &Path,
        dir: &Path,
    ) -> Result<(), String> {
        for entry in fs::read_dir(dir).map_err(|e| e.to_string())? {
            let entry = entry.map_err(|e| e.to_string())?;
            let path = entry.path();
            let relative = path.strip_prefix(base).map_err(|e| e.to_string())?;
            if path.is_dir() {
                add_dir(zip, options, base, &path)?;
            } else {
                zip.start_file(relative.to_string_lossy().as_ref(), options)
                    .map_err(|e| e.to_string())?;
                let content = fs::read(&path).map_err(|e| e.to_string())?;
                std::io::Write::write_all(zip, &content).map_err(|e| e.to_string())?;
            }
        }
        Ok(())
    }

    add_dir(
        &mut zip,
        options,
        Path::new(project_path),
        Path::new(project_path),
    )?;
    zip.finish().map_err(|e| e.to_string())?;
    Ok(())
}

fn save_existing_pdf(widget: &gtk4::Widget, source_path: &Path) {
    let dialog = gtk4::FileDialog::new();
    dialog.set_title("Save Research Report");
    dialog.set_initial_name(Some("report.pdf"));

    let source_path = source_path.to_path_buf();
    let widget_weak = widget.downgrade();

    dialog.save(
        widget
            .root()
            .as_ref()
            .and_then(|r| r.downcast_ref::<gtk4::Window>()),
        gtk4::gio::Cancellable::NONE,
        move |result| {
            let Some(widget) = widget_weak.upgrade() else {
                return;
            };
            if let Ok(file) = result {
                if let Some(dest_path) = file.path() {
                    if fs::copy(&source_path, &dest_path).is_ok() {
                        let msg = format!(
                            "Saved to {}",
                            dest_path.file_name().unwrap_or_default().to_string_lossy()
                        );
                        show_toast(&widget, &msg);
                    } else {
                        show_toast(&widget, "Save failed");
                    }
                }
            }
        },
    );
}

fn create_gnome_app_dialog(widget: &gtk4::Widget, project_path: &str) {
    let dialog = gtk4::Dialog::builder()
        .title("Create App")
        .modal(true)
        .build();

    let content_area = dialog.content_area();
    content_area.set_spacing(12);
    content_area.set_margin_top(12);
    content_area.set_margin_bottom(12);
    content_area.set_margin_start(12);
    content_area.set_margin_end(12);

    let label = Label::new(Some("Enter a name for your application:"));
    content_area.append(&label);

    let entry = gtk4::Entry::new();
    entry.set_placeholder_text(Some("App Name"));
    entry.set_text("My Gaia App");
    content_area.append(&entry);

    dialog.add_button("Cancel", gtk4::ResponseType::Cancel);
    dialog.add_button("Create", gtk4::ResponseType::Ok);

    let project_path = project_path.to_string();
    let widget_weak = widget.downgrade();

    dialog.connect_response(move |dlg, response| {
        if response == gtk4::ResponseType::Ok {
            let app_name = entry.text().to_string();
            let app_name = app_name.trim().to_string();
            if !app_name.is_empty() {
                create_gnome_app(&project_path, &app_name, &widget_weak);
            }
        }
        dlg.close();
    });

    if let Some(window) = widget
        .root()
        .and_then(|r| r.downcast_ref::<gtk4::Window>().cloned())
    {
        dialog.set_transient_for(Some(&window));
    }
    dialog.present();
}

fn create_gnome_app(project_path: &str, app_name: &str, widget_weak: &glib::WeakRef<gtk4::Widget>) {
    let slug: String = app_name
        .chars()
        .filter(|c| c.is_alphanumeric() || *c == '.' || *c == '_' || *c == '-' || *c == ' ')
        .collect::<String>()
        .trim()
        .replace(' ', "_")
        .to_lowercase();
    let slug = if slug.is_empty() {
        "gaia_app".to_string()
    } else {
        slug
    };

    let home = dirs::home_dir().unwrap_or_default();
    let base_dir = home.join(".local/share/gaia_apps");
    let app_dir = base_dir.join(&slug);
    let www_dir = app_dir.join("www");

    if www_dir.exists() {
        let _ = fs::remove_dir_all(&www_dir);
    }
    let _ = fs::create_dir_all(&app_dir);

    if let Err(e) = copy_dir_recursive(project_path, &www_dir) {
        if let Some(w) = widget_weak.upgrade() {
            show_toast(&w, &format!("Error: {}", e));
        }
        return;
    }

    let icon_path = app_dir.join("icon.png");
    generate_app_icon(app_name, &icon_path);

    let script_path = app_dir.join("main.py");
    let wrapper_code = get_app_wrapper_code(app_name, &slug);
    let _ = fs::write(&script_path, wrapper_code);

    let desktop_dir = home.join(".local/share/applications");
    let _ = fs::create_dir_all(&desktop_dir);
    let desktop_file = desktop_dir.join(format!("com.gaia.{}.desktop", slug));
    let desktop_content = format!(
        "[Desktop Entry]\n\
         Name={}\n\
         Comment=Created with Gaia\n\
         Exec=python3 \"{}\"\n\
         Icon={}\n\
         Terminal=false\n\
         Type=Application\n\
         Categories=Utility;\n\
         StartupNotify=true\n\
         StartupWMClass=com.gaia.{}\n\
         Keywords=Gaia;Web;\n",
        app_name,
        script_path.display(),
        icon_path.display(),
        slug
    );
    let _ = fs::write(&desktop_file, desktop_content);

    if let Some(w) = widget_weak.upgrade() {
        show_toast(&w, &format!("App '{}' created!", app_name));
    }
}

fn copy_dir_recursive(src: &str, dst: &Path) -> Result<(), String> {
    fs::create_dir_all(dst).map_err(|e| e.to_string())?;
    for entry in fs::read_dir(src).map_err(|e| e.to_string())? {
        let entry = entry.map_err(|e| e.to_string())?;
        let path = entry.path();
        let dest = dst.join(entry.file_name());
        if path.is_dir() {
            copy_dir_recursive(&path.to_string_lossy(), &dest)?;
        } else {
            fs::copy(&path, &dest).map_err(|e| e.to_string())?;
        }
    }
    Ok(())
}

fn generate_app_icon(app_name: &str, output_path: &Path) {
    let size = 128i32;
    let mut surface = cairo::ImageSurface::create(cairo::Format::ARgb32, size, size).unwrap();
    let ctx = cairo::Context::new(&surface).unwrap();

    let (r1, g1, b1, r2, g2, b2) = {
        let seed = app_name.len() as f64 * 0.1;
        let h1 = (seed * 2.7) % 1.0;
        let h2 = (seed * 1.3 + 0.5) % 1.0;
        (h1, (h1 + 0.33) % 1.0, (h1 + 0.66) % 1.0, h2, (h2 + 0.33) % 1.0, (h2 + 0.66) % 1.0)
    };

    let pat = cairo::LinearGradient::new(0.0, 0.0, size as f64, size as f64);
    pat.add_color_stop_rgb(0.0, r1, g1, b1);
    pat.add_color_stop_rgb(1.0, r2, g2, b2);

    let _ = ctx.set_source(&pat);
    ctx.rectangle(0.0, 0.0, size as f64, size as f64);
    let _ = ctx.fill();

    let initials: String = app_name
        .split_whitespace()
        .take(2)
        .filter_map(|w| w.chars().next())
        .collect::<String>()
        .to_uppercase();
    let initials = if initials.is_empty() { "??" } else { &initials };

    ctx.select_font_face("Sans", cairo::FontSlant::Normal, cairo::FontWeight::Bold);
    ctx.set_font_size(size as f64 * 0.5);

    let extents = ctx.text_extents(initials).unwrap();
    let _ = ctx.move_to(
        size as f64 / 2.0 - extents.width() / 2.0 - extents.x_bearing(),
        size as f64 / 2.0 + extents.height() / 2.0,
    );
    ctx.set_source_rgb(1.0, 1.0, 1.0);
    let _ = ctx.show_text(initials);

    let stride = surface.stride() as usize;
    let width = size as usize;
    let height = size as usize;
    let data = surface.data().unwrap();
    let pixels = &*data;

    let mut png_data = Vec::new();
    {
        let mut encoder = png::Encoder::new(&mut png_data, width as u32, height as u32);
        encoder.set_color(png::ColorType::Rgba);
        encoder.set_depth(png::BitDepth::Eight);
        let mut writer = encoder.write_header().unwrap();

        for y in 0..height {
            let start = y * stride;
            let row = &pixels[start..start + width * 4];
            let mut rgba = Vec::with_capacity(width * 4);
            for x in 0..width {
                let p = x * 4;
                rgba.push(row[p + 2]);
                rgba.push(row[p + 1]);
                rgba.push(row[p + 0]);
                rgba.push(row[p + 3]);
            }
            writer.write_image_data(&rgba).unwrap();
        }
        writer.finish().unwrap();
    }
    let _ = fs::write(output_path, png_data);
}

fn get_app_wrapper_code(app_name: &str, app_id: &str) -> String {
    format!(
        r#"import sys
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

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        header = Adw.HeaderBar()
        box.append(header)

        webview = WebKit.WebView()
        webview.set_vexpand(True)
        webview.set_hexpand(True)

        settings = webview.get_settings()
        settings.set_allow_file_access_from_file_urls(True)
        settings.set_allow_universal_access_from_file_urls(True)

        base_dir = os.path.dirname(os.path.abspath(__file__))
        index_path = os.path.join(base_dir, "www", "index.html")

        webview.load_uri(f"file://{{index_path}}")

        box.append(webview)
        win.set_content(box)
        win.present()

if __name__ == "__main__":
    app = MyApp()
    app.run(sys.argv)
"#
    )
}

impl Default for ArtifactsPanel {
    fn default() -> Self {
        Self::new()
    }
}
