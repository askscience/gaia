use gtk4::prelude::*;
use gtk4::{gdk, gio, glib};
use std::cell::RefCell;
use std::rc::Rc;

pub struct WallpaperGrid {
    pub widget: gtk4::Box,
    #[allow(dead_code)]
    images: serde_json::Value,
    #[allow(dead_code)]
    on_click_callback: Option<Rc<RefCell<Box<dyn Fn(usize) + 'static>>>>,
}

impl WallpaperGrid {
    pub fn new(
        images: serde_json::Value,
        on_click_callback: Option<Box<dyn Fn(usize) + 'static>>,
    ) -> Self {
        let outer = gtk4::Box::new(gtk4::Orientation::Vertical, 0);
        outer.set_spacing(10);
        outer.set_margin_top(10);
        outer.set_margin_bottom(10);

        let flowbox = gtk4::FlowBox::new();
        flowbox.set_valign(gtk4::Align::Start);
        flowbox.set_max_children_per_line(2);
        flowbox.set_min_children_per_line(2);
        flowbox.set_selection_mode(gtk4::SelectionMode::None);
        flowbox.set_column_spacing(10);
        flowbox.set_row_spacing(10);

        let cb_rc = on_click_callback.map(|cb| Rc::new(RefCell::new(cb)));

        let images_clone = images.clone();
        if let Some(arr) = images.as_array() {
            for (i, img_data) in arr.iter().enumerate() {
                let child =
                    Self::create_card(i + 1, img_data, cb_rc.as_ref().map(|rc| Rc::clone(rc)));
                flowbox.append(&child);
            }
        }

        outer.append(&flowbox);

        WallpaperGrid {
            widget: outer,
            images: images_clone,
            on_click_callback: cb_rc,
        }
    }

    fn create_card(
        index: usize,
        img_data: &serde_json::Value,
        on_click: Option<Rc<RefCell<Box<dyn Fn(usize) + 'static>>>>,
    ) -> gtk4::Widget {
        let frame = gtk4::Frame::new(None);
        frame.add_css_class("card");

        let card = gtk4::Box::new(gtk4::Orientation::Vertical, 0);
        card.set_size_request(160, 150);

        let overlay = gtk4::Overlay::new();

        let picture = gtk4::Picture::new();
        picture.set_content_fit(gtk4::ContentFit::Cover);
        picture.set_can_shrink(true);
        picture.set_size_request(-1, 140);

        let url = img_data
            .get("url")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();
        Self::load_image_async(&url, picture.clone());
        overlay.set_child(Some(&picture));

        let badge_label = gtk4::Label::new(Some(&index.to_string()));
        badge_label.add_css_class("caption-xsmall");
        let badge_box = gtk4::Box::new(gtk4::Orientation::Horizontal, 0);
        badge_box.add_css_class("badge-pill");
        badge_box.append(&badge_label);
        badge_box.set_halign(gtk4::Align::End);
        badge_box.set_valign(gtk4::Align::Start);
        badge_box.set_margin_top(8);
        badge_box.set_margin_end(8);

        let provider = gtk4::CssProvider::new();
        let css = ".badge-pill { background-color: rgba(0,0,0,0.6); color: white; border-radius: 12px; padding: 2px 8px; }";
        provider.load_from_data(css);
        if let Some(display) = gdk::Display::default() {
            gtk4::style_context_add_provider_for_display(
                &display,
                &provider,
                gtk4::STYLE_PROVIDER_PRIORITY_APPLICATION,
            );
        }

        overlay.add_overlay(&badge_box);
        card.append(&overlay);

        let desc = img_data
            .get("description")
            .and_then(|v| v.as_str())
            .unwrap_or("Wallpaper");
        let label = gtk4::Label::new(Some(desc));
        label.set_wrap(false);
        label.set_max_width_chars(25);
        label.add_css_class("caption");
        label.set_margin_top(6);
        label.set_margin_bottom(6);
        label.set_margin_start(6);
        label.set_margin_end(6);
        card.append(&label);

        frame.set_child(Some(&card));

        let btn = gtk4::Button::builder().css_classes(["flat"]).build();
        btn.set_child(Some(&frame));

        if let Some(cb) = on_click {
            btn.connect_clicked(move |_| {
                cb.borrow()(index);
            });
        }

        btn.upcast::<gtk4::Widget>()
    }

    fn load_image_async(url: &str, picture: gtk4::Picture) {
        let url = url.to_string();
        glib::spawn_future_local(async move {
            let client = reqwest::Client::builder()
                .user_agent("Mozilla/5.0 GaiaBot/1.0")
                .build()
                .ok();
            if let Some(client) = client {
                if let Ok(resp) = client
                    .get(&url)
                    .timeout(std::time::Duration::from_secs(10))
                    .send()
                    .await
                {
                    if let Ok(bytes) = resp.bytes().await {
                        if let Ok(texture) = gdk::Texture::from_bytes(&glib::Bytes::from(&bytes[..])) {
                            picture.set_paintable(Some(&texture));
                        }
                    }
                }
            }
        });
    }
}
