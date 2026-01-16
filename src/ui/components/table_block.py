import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Pango
from src.ui.utils import markdown_to_pango

class TableBlock(Gtk.Box):
    """A widget for displaying Markdown tables using native Gtk widgets."""
    
    def __init__(self, content: str, *args, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, *args, **kwargs)
        self.add_css_class("table-block")
        self.add_css_class("card") # Native Adwaita card look
        
        # Make the box itself expand
        # self.set_vexpand(True) # Removed to let it fit content naturally
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        # User Feedback: "I see only 3 lines... expand it and fit... for 10 lines"
        # We explicitly set a larger MIN height to guarantee visibility.
        # ~300px ensures roughly 8-10 lines are always visible, preventing the "slit" look.
        scrolled.set_min_content_height(300) 
        scrolled.set_max_content_height(500) # Cap at ~12-15 lines for scrolling
        
        scrolled.set_propagate_natural_width(True)
        scrolled.set_propagate_natural_height(True)
        # We leave vexpand=False so it doesn't claim empty space in the *parent* beyond natural height.
        # scrolled.set_vexpand(True) # Removed to avoid gratuitous expansion
        
        # Grid for the table
        self.grid = Gtk.Grid()
        self.grid.set_column_spacing(0)
        self.grid.set_row_spacing(6)
        self.grid.set_margin_top(16)
        self.grid.set_margin_bottom(16)
        self.grid.set_margin_start(16)
        self.grid.set_margin_end(16)
        
        self.parse_and_build(content)
        
        scrolled.set_child(self.grid)
        self.append(scrolled)
        
    def parse_and_build(self, text):
        lines = text.strip().split('\n')
        if len(lines) < 2: 
            return # Not a valid table

        # Parse header
        headers = [h.strip() for h in lines[0].strip('|').split('|')]
        
        # Check if second line is separator
        has_separator = False
        start_row = 1
        if len(lines) > 1 and set(lines[1].strip()) & set('-|'):
             has_separator = True
             start_row = 2
        
        n_cols = len(headers)
        
        # Render Headers
        for col_idx, header_text in enumerate(headers):
            # Add vertical separator before column if not first
            if col_idx > 0:
                vsep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
                self.grid.attach(vsep, col_idx * 2 - 1, 0, 1, 1)

            label = Gtk.Label()
            label.set_markup(f"<b>{header_text}</b>")
            label.add_css_class("heading") 
            label.set_halign(Gtk.Align.START)
            label.set_xalign(0)
            label.set_margin_start(6)
            label.set_margin_end(6)
            # Use col_idx * 2 to leave room for separators
            self.grid.attach(label, col_idx * 2, 0, 1, 1)
        
        # Add Header Separator
        # Spans all columns (n_cols + n_separators)
        total_grid_cols = n_cols * 2 - 1
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        self.grid.attach(sep, 0, 1, total_grid_cols, 1)
            
        # Render Rows
        grid_row_idx = 2 # Start after header (0) and separator (1)
        
        for row_idx, line in enumerate(lines[start_row:]):
            if not line.strip(): continue
            cells = [c.strip() for c in line.strip('|').split('|')]
            
            # Add row separator for subsequent rows
            if row_idx > 0:
                 sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
                 sep.add_css_class("dim-separator") 
                 self.grid.attach(sep, 0, grid_row_idx, total_grid_cols, 1)
                 grid_row_idx += 1
            
            for col_idx, cell_text in enumerate(cells):
                if col_idx >= n_cols: break 
                
                # Vertical separator
                if col_idx > 0:
                    vsep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
                    self.grid.attach(vsep, col_idx * 2 - 1, grid_row_idx, 1, 1)

                label = Gtk.Label()
                label.set_use_markup(True)
                markup = markdown_to_pango(cell_text)
                label.set_markup(markup)
                
                label.set_halign(Gtk.Align.START)
                label.set_xalign(0)
                label.set_wrap(True)
                label.set_max_width_chars(50) # Increased wrap width
                label.set_selectable(True)
                label.set_margin_start(6)
                label.set_margin_end(6)
                
                self.grid.attach(label, col_idx * 2, grid_row_idx, 1, 1)
            
            grid_row_idx += 1
