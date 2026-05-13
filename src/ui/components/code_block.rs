use gtk4::prelude::*;
use gtk4::{gdk, glib};

pub struct CodeBlock {
    pub widget: gtk4::Box,
}

impl CodeBlock {
    pub fn new(language: &str, code: &str) -> Self {
        let widget = gtk4::Box::new(gtk4::Orientation::Vertical, 0);
        widget.add_css_class("code-block");

        let header = gtk4::Box::new(gtk4::Orientation::Horizontal, 0);
        header.add_css_class("code-header");

        let lang_label = gtk4::Label::new(Some(&language.to_uppercase()));
        lang_label.add_css_class("code-lang-label");
        lang_label.set_hexpand(true);
        lang_label.set_halign(gtk4::Align::Start);
        header.append(&lang_label);

        let content = code.to_string();
        let copy_btn = gtk4::Button::builder()
            .icon_name("edit-copy-symbolic")
            .css_classes(["flat", "copy-button"])
            .tooltip_text("Copy")
            .build();
        let content = content.to_string();
        copy_btn.connect_clicked(move |btn| {
            if let Some(display) = gdk::Display::default() {
                let clipboard = display.clipboard();
                clipboard.set_text(&content);
            }
            btn.set_icon_name("object-select-symbolic");
            let btn_clone = btn.clone();
            glib::timeout_add_local(std::time::Duration::from_millis(1000), move || {
                btn_clone.set_icon_name("edit-copy-symbolic");
                glib::ControlFlow::Break
            });
        });
        header.append(&copy_btn);

        widget.append(&header);

        let scrolled = gtk4::ScrolledWindow::new();
        scrolled.set_policy(gtk4::PolicyType::Automatic, gtk4::PolicyType::Never);
        scrolled.set_max_content_height(400);

        let text_view = gtk4::TextView::new();
        text_view.set_editable(false);
        text_view.set_monospace(true);
        text_view.set_wrap_mode(gtk4::WrapMode::None);
        text_view.add_css_class("code-content");

        let buffer = text_view.buffer();
        buffer.set_text(code);

        scrolled.set_child(Some(&text_view));
        widget.append(&scrolled);

        CodeBlock { widget }
    }
}
