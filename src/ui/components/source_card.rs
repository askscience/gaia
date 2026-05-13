use gtk4::prelude::*;
use gtk4::{gdk, gio, glib};

pub struct SourceCard {
    pub widget: gtk4::Box,
}

impl SourceCard {
    pub fn new(
        title: &str,
        url: &str,
        snippet: &str,
        image_url: Option<&str>,
        favicon_url: Option<&str>,
    ) -> Self {
        let outer = gtk4::Box::new(gtk4::Orientation::Horizontal, 12);
        outer.add_css_class("source-row");
        outer.set_margin_top(6);
        outer.set_margin_bottom(6);
        outer.set_margin_start(12);
        outer.set_margin_end(12);

        let favicon_image = gtk4::Image::new();
        favicon_image.set_pixel_size(20);
        favicon_image.add_css_class("source-favicon");
        favicon_image.set_icon_name(Some("applications-internet-symbolic"));
        favicon_image.set_valign(gtk4::Align::Center);
        outer.append(&favicon_image);

        let text_box = gtk4::Box::new(gtk4::Orientation::Vertical, 2);
        text_box.set_hexpand(true);
        text_box.set_valign(gtk4::Align::Center);

        let title_label = gtk4::Label::new(Some(title));
        title_label.add_css_class("source-title");
        title_label.set_halign(gtk4::Align::Start);
        title_label.set_xalign(0.0);
        text_box.append(&title_label);

        let domain = url
            .split("://")
            .nth(1)
            .unwrap_or(url)
            .split('/')
            .next()
            .unwrap_or(url);
        let domain_label = gtk4::Label::new(Some(domain));
        domain_label.add_css_class("source-domain");
        domain_label.set_halign(gtk4::Align::Start);
        domain_label.set_xalign(0.0);
        text_box.append(&domain_label);

        outer.append(&text_box);

        let thumbnail = gtk4::Picture::new();
        thumbnail.set_content_fit(gtk4::ContentFit::Cover);
        thumbnail.set_size_request(64, 64);
        thumbnail.add_css_class("source-thumbnail");
        thumbnail.set_visible(false);
        thumbnail.set_valign(gtk4::Align::Center);
        outer.append(&thumbnail);

        let url_clone = url.to_string();
        let gesture = gtk4::GestureClick::new();
        gesture.connect_released(move |_, _, _, _| {
            let _ =
                gio::AppInfo::launch_default_for_uri(&url_clone, None::<&gio::AppLaunchContext>);
        });
        outer.add_controller(gesture);
        if let Some(cursor) = gdk::Cursor::from_name("pointer", None) {
            outer.set_cursor(Some(&cursor));
        }

        Self::load_images(
            &outer,
            &favicon_image,
            &thumbnail,
            url,
            favicon_url,
            image_url,
            snippet,
        );

        SourceCard { widget: outer }
    }

    fn load_images(
        outer: &gtk4::Box,
        favicon_image: &gtk4::Image,
        thumbnail: &gtk4::Picture,
        url: &str,
        favicon_url: Option<&str>,
        image_url: Option<&str>,
        _snippet: &str,
    ) {
        let fav_url = favicon_url.map(|s| s.to_string()).unwrap_or_else(|| {
            let domain = url
                .split("://")
                .nth(1)
                .unwrap_or(url)
                .split('/')
                .next()
                .unwrap_or("");
            format!("https://www.google.com/s2/favicons?sz=64&domain={domain}")
        });

        let img_url = image_url.map(|s| s.to_string());

        let favicon_image = favicon_image.clone();
        let thumbnail = thumbnail.clone();

        glib::spawn_future_local(async move {
            let client = reqwest::Client::builder()
                .user_agent("Mozilla/5.0")
                .build()
                .ok();

            if let Some(client) = client {
                if let Ok(resp) = client
                    .get(&fav_url)
                    .timeout(std::time::Duration::from_secs(5))
                    .send()
                    .await
                {
                    if let Ok(bytes) = resp.bytes().await {
                        if let Ok(texture) = gdk::Texture::from_bytes(&glib::Bytes::from(&bytes[..])) {
                            favicon_image.set_paintable(Some(&texture));
                        }
                    }
                }

                if let Some(ref img_url) = img_url {
                    if let Ok(resp) = client
                        .get(img_url)
                        .timeout(std::time::Duration::from_secs(5))
                        .send()
                        .await
                    {
                        if let Ok(bytes) = resp.bytes().await {
                            if let Ok(texture) = gdk::Texture::from_bytes(&glib::Bytes::from(&bytes[..])) {
                                thumbnail.set_paintable(Some(&texture));
                                thumbnail.set_visible(true);
                            }
                        }
                    }
                }
            }
        });
    }
}
