use gtk4::prelude::*;

use crate::ui::utils::markdown_to_pango;

pub struct TableBlock {
    pub widget: gtk4::Box,
}

impl TableBlock {
    pub fn new(content: &str) -> Self {
        let outer = gtk4::Box::new(gtk4::Orientation::Vertical, 0);
        outer.add_css_class("table-block");
        outer.add_css_class("card");

        let scrolled = gtk4::ScrolledWindow::new();
        scrolled.set_policy(gtk4::PolicyType::Automatic, gtk4::PolicyType::Automatic);
        scrolled.set_min_content_height(300);
        scrolled.set_max_content_height(500);
        scrolled.set_propagate_natural_width(true);
        scrolled.set_propagate_natural_height(true);

        let grid = gtk4::Grid::new();
        grid.set_column_spacing(0);
        grid.set_row_spacing(6);
        grid.set_margin_top(16);
        grid.set_margin_bottom(16);
        grid.set_margin_start(16);
        grid.set_margin_end(16);

        TableBlock::parse_and_build(&grid, content);

        scrolled.set_child(Some(&grid));
        outer.append(&scrolled);

        TableBlock { widget: outer }
    }

    fn parse_and_build(grid: &gtk4::Grid, text: &str) {
        let lines: Vec<&str> = text.trim().lines().collect();
        if lines.len() < 2 {
            return;
        }

        let headers: Vec<String> = lines[0]
            .trim_matches('|')
            .split('|')
            .map(|h| h.trim().to_string())
            .collect();

        let mut start_row: usize = 1;
        if lines.len() > 1 {
            let sep_line = lines[1].trim();
            if sep_line
                .chars()
                .all(|c| c == '|' || c == '-' || c == ':' || c == ' ')
            {
                start_row = 2;
            }
        }

        let n_cols = headers.len();
        let total_grid_cols: i32 = (n_cols as i32) * 2 - 1;

        // Render headers
        for (col_idx, header_text) in headers.iter().enumerate() {
            if col_idx > 0 {
                let vsep = gtk4::Separator::new(gtk4::Orientation::Vertical);
                grid.attach(&vsep, (col_idx * 2 - 1) as i32, 0, 1, 1);
            }

            let label = gtk4::Label::new(None);
            label.set_markup(&format!("<b>{}</b>", gtk4::glib::markup_escape_text(header_text)));
            label.add_css_class("heading");
            label.set_halign(gtk4::Align::Start);
            label.set_xalign(0.0);
            label.set_margin_start(6);
            label.set_margin_end(6);
            grid.attach(&label, (col_idx * 2) as i32, 0, 1, 1);
        }

        // Header separator
        let sep = gtk4::Separator::new(gtk4::Orientation::Horizontal);
        grid.attach(&sep, 0, 1, total_grid_cols, 1);

        // Render rows
        let mut grid_row_idx: i32 = 2;
        for (row_idx, line) in lines[start_row..].iter().enumerate() {
            if line.trim().is_empty() {
                continue;
            }
            let cells: Vec<String> = line
                .trim_matches('|')
                .split('|')
                .map(|c| c.trim().to_string())
                .collect();

            if row_idx > 0 {
                let sep = gtk4::Separator::new(gtk4::Orientation::Horizontal);
                sep.add_css_class("dim-separator");
                grid.attach(&sep, 0, grid_row_idx, total_grid_cols, 1);
                grid_row_idx += 1;
            }

            for (col_idx, cell_text) in cells.iter().enumerate() {
                if col_idx >= n_cols {
                    break;
                }

                if col_idx > 0 {
                    let vsep = gtk4::Separator::new(gtk4::Orientation::Vertical);
                    grid.attach(&vsep, (col_idx * 2 - 1) as i32, grid_row_idx, 1, 1);
                }

                let label = gtk4::Label::new(None);
                label.set_use_markup(true);
                let markup = markdown_to_pango(cell_text);
                label.set_markup(&markup);
                label.set_halign(gtk4::Align::Start);
                label.set_xalign(0.0);
                label.set_wrap(true);
                label.set_max_width_chars(50);
                label.set_selectable(true);
                label.set_margin_start(6);
                label.set_margin_end(6);
                grid.attach(&label, (col_idx * 2) as i32, grid_row_idx, 1, 1);
            }

            grid_row_idx += 1;
        }
    }
}
