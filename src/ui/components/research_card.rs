use gtk4::prelude::*;
use gtk4::{gio, glib};

use crate::i18n::manager::LanguageManager;

pub struct ResearchCard {
    pub widget: gtk4::Frame,
}

impl ResearchCard {
    pub fn new(title: &str, path: &str) -> Self {
        let lang = LanguageManager::instance();
        let lang = lang.lock().unwrap();

        let frame = gtk4::Frame::new(None);
        frame.add_css_class("card");

        let main_box = gtk4::Box::new(gtk4::Orientation::Vertical, 8);
        main_box.set_margin_top(12);
        main_box.set_margin_bottom(12);
        main_box.set_margin_start(12);
        main_box.set_margin_end(12);

        let header = gtk4::Box::new(gtk4::Orientation::Horizontal, 12);

        let icon = gtk4::Image::from_icon_name("system-search-symbolic");
        icon.set_pixel_size(32);
        header.append(&icon);

        let text_vbox = gtk4::Box::new(gtk4::Orientation::Vertical, 0);

        let title_label = gtk4::Label::new(Some(title));
        title_label.add_css_class("source-title");
        title_label.set_halign(gtk4::Align::Start);
        text_vbox.append(&title_label);

        let type_label = gtk4::Label::new(Some(&lang.get("components.research_card.type_label")));
        type_label.add_css_class("dim-label");
        type_label.set_halign(gtk4::Align::Start);
        text_vbox.append(&type_label);

        header.append(&text_vbox);
        main_box.append(&header);

        let button_box = gtk4::Box::new(gtk4::Orientation::Horizontal, 8);
        button_box.set_margin_top(8);

        let view_btn = gtk4::Button::with_label(&lang.get("components.research_card.view_button"));
        view_btn.add_css_class("suggested-action");
        button_box.append(&view_btn);

        let pdf_btn = gtk4::Button::with_label(&lang.get("components.research_card.pdf_button"));
        button_box.append(&pdf_btn);

        main_box.append(&button_box);
        frame.set_child(Some(&main_box));

        ResearchCard { widget: frame }
    }
}
