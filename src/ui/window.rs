use std::cell::RefCell;
use std::collections::HashMap;
use std::rc::Rc;

use libadwaita as adw;
use adw::prelude::*;
use gtk4::prelude::*;
use gtk4::{gio, glib};
use serde_json::Value;

use crate::chat::ChatStorage;
use crate::config::get_artifacts_dir;
use crate::ui::chat::ChatPage;
use crate::i18n::LANG;
use crate::network::proxy::apply_proxy_settings;
use crate::ui::artifacts_panel::ArtifactsPanel;
use crate::ui::settings::SettingsWindow;

pub struct MainWindow {
    pub window: adw::ApplicationWindow,
    pub tab_view: adw::TabView,
    chat_pages: RefCell<HashMap<String, Rc<ChatPage>>>,
    pub artifacts_panel: Rc<ArtifactsPanel>,
    pub artifacts_button: gtk4::ToggleButton,
    pub main_paned: gtk4::Paned,
    pub tab_overview: adw::TabOverview,
    storage: Rc<ChatStorage>,
    creating_chat: RefCell<bool>,
    all_chats: RefCell<Vec<Value>>,
    saved_paned_position: RefCell<i32>,
}

impl MainWindow {
    pub fn new(app: &adw::Application, storage: ChatStorage) -> Rc<Self> {
        apply_proxy_settings();

        let lang_guard = LANG.lock().unwrap();
        let title = lang_guard.get("window.title");
        let new_chat_label = lang_guard.get("window.new_chat");
        let show_artifacts_label = lang_guard.get("window.show_artifacts");
        let view_all_chats_label = lang_guard.get("window.view_all_chats");
        let menu_settings = lang_guard.get("window.menu.settings");
        let menu_about = lang_guard.get("window.menu.about");
        drop(lang_guard);

        let window = adw::ApplicationWindow::new(app);
        window.set_title(Some(&title));
        window.set_default_size(800, 600);
        window.set_icon_name(Some("icon"));

        let storage = Rc::new(storage);

        let tab_view = adw::TabView::new();

        let main_paned = gtk4::Paned::new(gtk4::Orientation::Horizontal);
        main_paned.set_wide_handle(true);
        window.set_content(Some(&main_paned));

        let tab_overview = adw::TabOverview::new();
        tab_overview.set_view(Some(&tab_view));
        tab_overview.set_enable_new_tab(false);
        main_paned.set_start_child(Some(&tab_overview));
        tab_overview.set_hexpand(true);

        let artifacts_panel = Rc::new(ArtifactsPanel::new());
        main_paned.set_end_child(Some(&artifacts_panel.widget));
        artifacts_panel.widget.set_size_request(300, -1);
        artifacts_panel.widget.set_visible(false);

        let main_box = gtk4::Box::new(gtk4::Orientation::Vertical, 0);
        tab_overview.set_child(Some(&main_box));

        let header_bar = adw::HeaderBar::new();
        main_box.append(&header_bar);

        let new_chat_button = gtk4::Button::from_icon_name("tab-new-symbolic");
        new_chat_button.set_tooltip_text(Some(&new_chat_label));
        header_bar.pack_start(&new_chat_button);

        let menu = gio::Menu::new();
        menu.append(Some(&menu_settings), Some("win.preferences"));
        menu.append(Some(&menu_about), Some("win.about"));

        let menu_button = gtk4::MenuButton::new();
        menu_button.set_icon_name("open-menu-symbolic");
        menu_button.set_menu_model(Some(&menu));
        header_bar.pack_end(&menu_button);

        let artifacts_button = gtk4::ToggleButton::new();
        artifacts_button.set_icon_name("sidebar-show-symbolic");
        artifacts_button.set_tooltip_text(Some(&show_artifacts_label));
        header_bar.pack_end(&artifacts_button);

        let tab_overview_button = gtk4::Button::from_icon_name("view-grid-symbolic");
        tab_overview_button.set_tooltip_text(Some(&view_all_chats_label));
        tab_overview_button.set_action_name(Some("overview.open"));
        header_bar.pack_end(&tab_overview_button);

        main_box.append(&tab_view);

        let action_pref = gio::SimpleAction::new("preferences", None);
        let action_about = gio::SimpleAction::new("about", None);

        window.add_action(&action_pref);
        window.add_action(&action_about);

        let main_window = Rc::new(MainWindow {
            window,
            tab_view: tab_view.clone(),
            chat_pages: RefCell::new(HashMap::new()),
            artifacts_panel,
            artifacts_button: artifacts_button.clone(),
            main_paned,
            tab_overview,
            storage,
            creating_chat: RefCell::new(false),
            all_chats: RefCell::new(Vec::new()),
            saved_paned_position: RefCell::new(400),
        });

        let mw = main_window.clone();
        action_pref.connect_activate(move |_, _| {
            mw.show_preferences();
        });

        let mw = main_window.clone();
        action_about.connect_activate(move |_, _| {
            mw.show_about();
        });

        let mw = main_window.clone();
        new_chat_button.connect_clicked(move |_| {
            mw.create_new_chat();
        });

        let mw = main_window.clone();
        artifacts_button.connect_toggled(move |btn| {
            mw.on_artifacts_toggled(btn);
        });

        let mw = main_window.clone();
        tab_view.connect_selected_page_notify(move |_tv| {
            mw.on_tab_changed();
        });

        let mw = main_window.clone();
        tab_view.connect_close_page(move |tv, page| {
            let child = page.child();
            let chat_pages = mw.chat_pages.borrow();
            let chat_id = chat_pages
                .iter()
                .find(|(_, cp)| cp.widget == child)
                .map(|(id, _)| id.clone());

            drop(chat_pages);

            if let Some(ref id) = chat_id {
                mw.storage.delete_chat(id);
                mw.chat_pages.borrow_mut().remove(id);
            }

            tv.close_page_finish(page, true);

            if tv.n_pages() == 0 && !*mw.creating_chat.borrow() {
                let mw2 = mw.clone();
                glib::timeout_add_local_once(std::time::Duration::from_millis(200), move || {
                    if mw2.tab_view.n_pages() == 0 {
                        mw2.create_new_chat();
                    }
                });
            }

            glib::Propagation::Stop
        });

        main_window.create_initial_chat();
        main_window.load_existing_chats();

        main_window
    }

    pub fn present(&self) {
        self.window.present();
    }

    fn show_preferences(self: &Rc<Self>) {
        let settings = SettingsWindow::new(&self.window);
        settings.present();
    }

    fn show_about(self: &Rc<Self>) {
        let lang_guard = LANG.lock().unwrap();
        let about = adw::AboutWindow::builder()
            .transient_for(&self.window)
            .application_name(lang_guard.get("window.about.name"))
            .application_icon("io.github.askscience.gaia")
            .developer_name(lang_guard.get("window.about.developer"))
            .version("0.5.0")
            .comments(lang_guard.get("window.about.comments"))
            .copyright(lang_guard.get("window.about.copyright"))
            .website("https://github.com/askscience/gaia")
            .issue_url("https://github.com/askscience/gaia/issues")
            .license_type(gtk4::License::Gpl30)
            .build();
        drop(lang_guard);

        about.present();
    }

    fn create_initial_chat(&self) {
        if *self.creating_chat.borrow() {
            return;
        }
        *self.creating_chat.borrow_mut() = true;

        let chat = self.storage.create_chat("", false);
        self.add_chat_tab(&chat, false);
        *self.creating_chat.borrow_mut() = false;
    }

    fn load_existing_chats(&self) {
        let storage = self.storage.clone();
        let chats = storage.list_chats();

        for chat in &chats {
            self.add_chat_tab(chat, true);
        }
    }

    pub fn create_new_chat(self: &Rc<Self>) -> Option<adw::TabPage> {
        if *self.creating_chat.borrow() {
            return None;
        }

        *self.creating_chat.borrow_mut() = true;

        let chat = self.storage.create_chat("", false);
        let tab_page = self.add_chat_tab(&chat, false);
        self.tab_view.set_selected_page(&tab_page);

        *self.creating_chat.borrow_mut() = false;

        Some(tab_page)
    }

    fn add_chat_tab(&self, chat: &Value, lazy: bool) -> adw::TabPage {
        let chat_page = Rc::new(ChatPage::new(chat, self.storage.clone(), lazy));
        let chat_id = chat["id"].as_str().unwrap_or("").to_string();
        self.chat_pages
            .borrow_mut()
            .insert(chat_id, chat_page.clone());

        let tab_page = self.tab_view.append(&chat_page.widget);

        let lang_guard = LANG.lock().unwrap();
        let default_title = lang_guard.get("window.new_chat");
        drop(lang_guard);

        tab_page.set_title(
            chat.get("title")
                .and_then(|t| t.as_str())
                .unwrap_or(&default_title),
        );

        let icon = gio::ThemedIcon::new("user-available-symbolic");
        tab_page.set_icon(Some(&icon));

        tab_page
    }

    fn on_artifacts_toggled(&self, button: &gtk4::ToggleButton) {
        self.artifacts_panel.widget.set_visible(button.is_active());
        if button.is_active() {
            let current_pos = self.main_paned.position();
            let width = self.window.width();
            if current_pos <= 0 || current_pos >= width - 50 {
                self.main_paned.set_position(width - 400);
            }
        }
    }

    pub fn show_artifacts(&self) {
        self.artifacts_button.set_active(true);
        self.artifacts_panel.widget.set_visible(true);
        let current_pos = self.main_paned.position();
        let width = self.window.width();
        if current_pos <= 0 || current_pos >= width - 50 {
            self.main_paned.set_position(width - 400);
        }
    }

    fn on_tab_changed(&self) {
        self.artifacts_panel.clear();

        let selected_page = self.tab_view.selected_page();
        if let Some(page) = selected_page {
            let child = page.child();
            let chat_pages = self.chat_pages.borrow();
            for chat_page in chat_pages.values() {
                if chat_page.widget == child {
                    chat_page.restore_artifacts(&self.artifacts_panel);
                    if chat_page.lazy_loading {
                        let cp = chat_page.clone();
                        glib::idle_add_local_once(move || {
                            cp._load_history_batch();
                        });
                    }
                    break;
                }
            }
        }
    }

    pub fn get_active_chat_page(&self) -> Option<Rc<ChatPage>> {
        let selected_page = self.tab_view.selected_page()?;
        let child = selected_page.child();
        let chat_pages = self.chat_pages.borrow();
        for chat_page in chat_pages.values() {
            if chat_page.widget == child {
                return Some(chat_page.clone());
            }
        }
        None
    }

    pub fn refresh_active_artifacts(&self) {
        if let Some(page) = self.get_active_chat_page() {
            let project_id = page.chat_data["id"].as_str().unwrap_or("");
            let base_dir = get_artifacts_dir();
            let project_path = base_dir.join(project_id);
            if let Some(path_str) = project_path.to_str() {
                self.artifacts_panel
                    .load_project(path_str, false, true);
            }
        }
    }
}
