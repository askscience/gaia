use gtk4::gdk;
use gtk4::prelude::*;

pub struct ArtifactCard {
    pub widget: gtk4::Frame,
}

impl ArtifactCard {
    pub fn new(filename: &str, path: &str, language: &str) -> Self {
        let frame = gtk4::Frame::new(None);
        frame.add_css_class("card");

        let box_ = gtk4::Box::new(gtk4::Orientation::Horizontal, 12);
        box_.set_margin_top(8);
        box_.set_margin_bottom(8);
        box_.set_margin_start(8);
        box_.set_margin_end(8);

        let icon_name = match language {
            "html" => "text-html-symbolic",
            "css" => "text-css-symbolic",
            "javascript" => "text-x-javascript-symbolic",
            _ => "text-x-generic-symbolic",
        };
        let icon = gtk4::Image::from_icon_name(icon_name);
        icon.set_pixel_size(24);
        box_.append(&icon);

        let label = gtk4::Label::new(Some(filename));
        label.set_hexpand(true);
        label.set_halign(gtk4::Align::Start);
        box_.append(&label);

        frame.set_child(Some(&box_));

        let gesture = gtk4::GestureClick::new();
        frame.add_controller(gesture);
        if let Some(cursor) = gdk::Cursor::from_name("pointer", None) {
            frame.set_cursor(Some(&cursor));
        }

        ArtifactCard { widget: frame }
    }
}
