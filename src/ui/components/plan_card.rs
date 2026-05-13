use libadwaita as adw;
use adw::prelude::*;
use gtk4::prelude::*;
use std::cell::RefCell;
use std::rc::Rc;

use crate::ui::utils::markdown_to_pango;

pub struct PlanConfirmationCard {
    pub widget: gtk4::Frame,
    on_proceed: Rc<RefCell<Option<Box<dyn Fn() + 'static>>>>,
}

impl PlanConfirmationCard {
    pub fn new(plan_data: &serde_json::Value, on_proceed: Box<dyn Fn() + 'static>) -> Self {
        let frame = gtk4::Frame::new(None);
        frame.add_css_class("card");

        let main_box = gtk4::Box::new(gtk4::Orientation::Vertical, 16);
        main_box.set_margin_top(16);
        main_box.set_margin_bottom(16);
        main_box.set_margin_start(16);
        main_box.set_margin_end(16);

        let header_box = gtk4::Box::new(gtk4::Orientation::Vertical, 12);

        let title = gtk4::Label::new(None);
        title.set_markup("<span size='large' weight='bold'>Proposed Plan</span>");
        title.set_halign(gtk4::Align::Start);
        header_box.append(&title);

        if let Some(desc) = plan_data.get("description").and_then(|v| v.as_str()) {
            let mut desc = desc.to_string();
            // strip clean logs prefix
            if let Some(idx) = desc.find("---") {
                if let Some(end_idx) = desc[idx + 3..].find("---") {
                    let actual_end = idx + 3 + end_idx + 3;
                    if actual_end < desc.len() {
                        desc = desc[actual_end..].trim().to_string();
                    }
                }
            }
            let parsed = markdown_to_pango(&desc);
            let desc_label = gtk4::Label::new(None);
            desc_label.set_markup(&parsed);
            desc_label.set_wrap(true);
            desc_label.set_max_width_chars(60);
            desc_label.set_halign(gtk4::Align::Start);
            desc_label.add_css_class("dim-label");
            header_box.append(&desc_label);
        }

        main_box.append(&header_box);

        if let Some(files) = plan_data.get("files").and_then(|v| v.as_array()) {
            let scrolled = gtk4::ScrolledWindow::new();
            scrolled.set_min_content_height((files.len() as i32 * 60).min(350));
            scrolled.set_propagate_natural_height(true);

            let pref_group = adw::PreferencesGroup::new();
            pref_group.set_title("Files to Create");

            for f in files {
                let row = libadwaita::ActionRow::new();
                row.set_title(
                    f.get("filename")
                        .and_then(|v| v.as_str())
                        .unwrap_or("Unknown File"),
                );

                if let Some(deps) = f.get("dependencies").and_then(|v| v.as_array()) {
                    let dep_strs: Vec<&str> = deps.iter().filter_map(|d| d.as_str()).collect();
                    let mut display = dep_strs.join(", ");
                    if display.len() > 50 {
                        display = format!("{}...", &display[..47]);
                    }
                    row.set_subtitle(&format!("Imports: {display}"));
                }

                let fn_lower = f
                    .get("filename")
                    .and_then(|v| v.as_str())
                    .unwrap_or("")
                    .to_lowercase();
                let icon_name = if fn_lower.ends_with(".html") {
                    "text-html-symbolic"
                } else if fn_lower.ends_with(".css") {
                    "text-css-symbolic"
                } else if fn_lower.ends_with(".js") {
                    "text-x-javascript-symbolic"
                } else if fn_lower.ends_with(".py") {
                    "text-x-python-symbolic"
                } else if fn_lower.ends_with(".md") {
                    "text-markdown-symbolic"
                } else {
                    "text-x-generic-symbolic"
                };
                let icon = gtk4::Image::from_icon_name(icon_name);
                row.add_prefix(&icon);

                pref_group.add(&row);
            }

            scrolled.set_child(Some(&pref_group));
            main_box.append(&scrolled);
        }

        let btn_box = gtk4::Box::new(gtk4::Orientation::Horizontal, 0);
        btn_box.set_halign(gtk4::Align::End);
        btn_box.set_margin_top(8);

        let proceed_btn = gtk4::Button::builder()
            .label("Proceed with Plan")
            .css_classes(["suggested-action", "pill"])
            .build();

        let on_proceed = Rc::new(RefCell::new(Some(on_proceed)));
        let on_proceed_clone = Rc::clone(&on_proceed);
        proceed_btn.connect_clicked(move |btn| {
            btn.set_sensitive(false);
            btn.set_label("Build Queued...");
            if let Some(ref cb) = *on_proceed_clone.borrow() {
                cb();
            }
        });

        btn_box.append(&proceed_btn);
        main_box.append(&btn_box);
        frame.set_child(Some(&main_box));

        PlanConfirmationCard {
            widget: frame,
            on_proceed,
        }
    }
}
