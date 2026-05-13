mod ai;
mod chat;
mod concurrency;
mod config;
mod i18n;
mod network;
mod prompt;
mod status;
mod tools;
mod ui;
mod voice;

use libadwaita as adw;
use adw::prelude::*;
use gtk4::prelude::*;
use gtk4::{gio, glib};

fn main() -> glib::ExitCode {
    unsafe { std::env::set_var("WEBKIT_DISABLE_SANDBOX", "1"); }

    env_logger::init();

    let app = adw::Application::builder()
        .application_id("io.github.askscience.gaia")
        .build();

    app.connect_activate(|app| {
        load_css();

        if let Some(window) = app.active_window() {
            window.present();
            return;
        }

        let storage = chat::ChatStorage::new(None);
        let window = ui::MainWindow::new(app, storage);
        window.present();
    });

    app.run()
}

fn load_css() {
    let css = include_str!("ui/css/style.css");
    let provider = gtk4::CssProvider::new();
    provider.load_from_data(css);

    if let Some(display) = gtk4::gdk::Display::default() {
        gtk4::style_context_add_provider_for_display(
            &display,
            &provider,
            gtk4::STYLE_PROVIDER_PRIORITY_APPLICATION,
        );
    }
}
