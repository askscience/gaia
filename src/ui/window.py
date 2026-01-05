import gi
import threading

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Gio, GLib, Gdk

from src.core.chat_storage import ChatStorage
from src.ui.artifacts_panel import ArtifactsPanel
from src.ui.chat.page import ChatPage
from src.core.network.proxy import apply_proxy_settings # Proxy support
from src.core.language_manager import LanguageManager

class MainWindow(Adw.ApplicationWindow):
    def __init__(self, storage: ChatStorage, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Apply global network settings on startup
        apply_proxy_settings()

        self.lang_manager = LanguageManager()
        self.set_title(self.lang_manager.get("window.title"))
        self.set_default_size(800, 600)
        self.set_icon_name("icon")
        
        self.storage = storage
        self.chat_pages = {}  # chat_id -> ChatPage
        self.all_chats = []  # Store all chat data for lazy loading
        self._creating_chat = False  # Flag to prevent recursive creation

        # Tab View
        self.tab_view = Adw.TabView()
        self.tab_view.connect("close-page", self.on_close_page)
        self.tab_view.connect("notify::selected-page", self.on_tab_changed)
        
        # Main Resizable Layout
        self.main_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.main_paned.set_wide_handle(True)
        self.set_content(self.main_paned)

        # Tab Overview (Left side)
        self.tab_overview = Adw.TabOverview()
        self.tab_overview.set_view(self.tab_view)
        self.tab_overview.set_enable_new_tab(False)
        self.main_paned.set_start_child(self.tab_overview)
        self.tab_overview.set_hexpand(True)

        # Artifacts Sidebar (Right side)
        self.artifacts_panel = ArtifactsPanel()
        self.main_paned.set_end_child(self.artifacts_panel)
        self.artifacts_panel.set_size_request(300, -1)
        self.artifacts_panel.set_visible(False)

        # Main content box (child of tab_overview)
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.tab_overview.set_child(self.main_box)
        
        # Header Bar
        self.header_bar = Adw.HeaderBar()
        self.main_box.append(self.header_bar)
        
        
        # New Chat Button (left side)
        self.new_chat_button = Gtk.Button()
        self.new_chat_button.set_icon_name("tab-new-symbolic")
        self.new_chat_button.set_tooltip_text(self.lang_manager.get("window.new_chat"))
        self.new_chat_button.connect("clicked", self.on_new_chat_clicked)
        self.header_bar.pack_start(self.new_chat_button)
        
        # Internal state for fullscreen
        self.saved_paned_position = 400 # Default fallback


        # Menu Button (rightmost)
        menu = Gio.Menu()
        self.menu_button = Gtk.MenuButton()
        self.menu_button.set_icon_name("open-menu-symbolic")
        self.menu_button.set_menu_model(menu)
        self.header_bar.pack_end(self.menu_button)
        
        # Artifacts Toggle (right side)
        self.artifacts_button = Gtk.ToggleButton()
        self.artifacts_button.set_icon_name("sidebar-show-symbolic")
        self.artifacts_button.set_tooltip_text(self.lang_manager.get("window.show_artifacts"))
        self.artifacts_button.connect("toggled", self.on_artifacts_toggled)
        self.header_bar.pack_end(self.artifacts_button)

        # Tab Overview Button (4-squares icon, to the left of menu)
        self.tab_overview_button = Gtk.Button()
        self.tab_overview_button.set_icon_name("view-grid-symbolic")
        self.tab_overview_button.set_tooltip_text(self.lang_manager.get("window.view_all_chats"))
        self.tab_overview_button.set_action_name("overview.open")
        self.header_bar.pack_end(self.tab_overview_button)
        
        # Actions
        action_pref = Gio.SimpleAction.new("preferences", None)
        action_pref.connect("activate", self.on_preferences_action)
        self.add_action(action_pref)
        
        action_about = Gio.SimpleAction.new("about", None)
        action_about.connect("activate", self.on_about_action)
        self.add_action(action_about)
        
        menu.append(self.lang_manager.get("window.menu.settings"), "win.preferences")
        menu.append(self.lang_manager.get("window.menu.about"), "win.about")
        
        # Tab View goes after header
        self.main_box.append(self.tab_view)
        
        # Always create a new chat first
        self._create_initial_chat()
        
        # Then load existing chats in background
        GLib.idle_add(self._load_existing_chats)


    def toggle_artifact_fullscreen(self):
        """Toggle the visibility of the chat pane to make artifacts fullscreen."""
        chat_view = self.main_paned.get_start_child()
        is_visible = chat_view.get_visible()
        
        if is_visible:
            # Going fullscreen -> Hide chat
            self.saved_paned_position = self.main_paned.get_position()
            chat_view.set_visible(False)
        else:
            # Exiting fullscreen -> Show chat
            chat_view.set_visible(True)
            self.main_paned.set_position(self.saved_paned_position)

    def _create_initial_chat(self):
        """Create the initial chat on startup."""
        if not self._creating_chat:
            self._creating_chat = True
            # Create unsaved chat - will be persisted on first message
            chat = self.storage.create_chat(save=False)
            self._add_chat_tab(chat)
            self._creating_chat = False

    def _load_existing_chats(self):
        """Load existing chat data - create tabs for all but lazy-load only active one."""
        def load_in_thread():
            try:
                # Heavy IO: List all chats
                chats = self.storage.list_chats()
                
                # Store all chats for lazy loading
                self.all_chats = chats
                
                # Update UI on main thread
                GLib.idle_add(self._populate_chat_tabs, chats)
            except Exception as e:
                print(f"[DEBUG] Error loading chats: {e}")

        thread = threading.Thread(target=load_in_thread, daemon=True)
        thread.start()
        return False

    def _populate_chat_tabs(self, chats):
        """Populate tabs from the loaded chats list (runs on main thread)."""
        # Create tabs for all existing chats (all lazy loaded since we have a new chat active)
        for i, chat in enumerate(chats):
            self._add_chat_tab(chat, lazy=True)
        return False
    
    def _add_chat_tab(self, chat: dict, lazy: bool = False) -> Adw.TabPage:
        """Add a chat as a new tab."""
        # If chat is just metadata (no history), load full data if not lazy
        if 'history' not in chat and not lazy:
            full_chat = self.storage.load_chat(chat['id'])
            if full_chat:
                chat = full_chat
        
        page = ChatPage(chat, self.storage, lazy_loading=lazy)
        self.chat_pages[chat['id']] = page
        
        tab_page = self.tab_view.append(page)
        tab_page.set_title(chat.get('title', self.lang_manager.get("window.new_chat")))
        tab_page.set_icon(Gio.ThemedIcon.new("user-available-symbolic"))
        
        return tab_page
    
    def create_new_chat(self) -> Adw.TabPage:
        """Create a new chat and add it as a tab."""
        if self._creating_chat:
            return None
        
        self._creating_chat = True
        try:
            # Create unsaved chat - will be persisted on first message
            chat = self.storage.create_chat(save=False)
            tab_page = self._add_chat_tab(chat)
            self.tab_view.set_selected_page(tab_page)
            return tab_page
        finally:
            self._creating_chat = False

    def on_preferences_action(self, action, param):
        from src.ui.settings import SettingsWindow
        settings = SettingsWindow(parent=self)
        settings.present()

    def on_about_action(self, action, param):
        """Show the About dialog."""
        about = Adw.AboutWindow(transient_for=self)
        about.set_application_name(self.lang_manager.get("window.about.name"))
        about.set_application_icon("com.askscience.gaia")
        about.set_developer_name(self.lang_manager.get("window.about.developer"))
        about.set_version("0.2.4")
        about.set_comments(self.lang_manager.get("window.about.comments"))
        about.set_copyright(self.lang_manager.get("window.about.copyright"))
        about.set_website("https://github.com/askscience/gaia")
        about.set_issue_url("https://github.com/askscience/gaia/issues")
        about.set_license_type(Gtk.License.GPL_3_0)
        about.present()
    
    def on_new_chat_clicked(self, button):
        """Handle new chat button click."""
        self.create_new_chat()
    
    def on_close_page(self, tab_view, page):
        """Handle tab close - delete the chat."""
        child = page.get_child()
        if isinstance(child, ChatPage):
            chat_id = child.chat_data['id']
            self.storage.delete_chat(chat_id)
            if chat_id in self.chat_pages:
                del self.chat_pages[chat_id]
        
        # Allow the close
        tab_view.close_page_finish(page, True)
        
        # If no tabs left, create one (with delay and guard)
        if tab_view.get_n_pages() == 0 and not self._creating_chat:
            GLib.timeout_add(200, self._create_chat_if_empty)
        
        return Gdk.EVENT_STOP
    
    def _create_chat_if_empty(self):
        """Create a chat only if there are no tabs."""
        if self.tab_view.get_n_pages() == 0 and not self._creating_chat:
            self.create_new_chat()
        return False  # Don't repeat

    def on_artifacts_toggled(self, button):
        self.artifacts_panel.set_visible(button.get_active())
        if button.get_active():
            # Ensure the paned handle is at a reasonable position
            current_pos = self.main_paned.get_position()
            if current_pos <= 0 or current_pos >= self.get_width() - 50:
                self.main_paned.set_position(self.get_width() - 400)

    def show_artifacts(self):
        self.artifacts_button.set_active(True)
        self.artifacts_panel.set_visible(True)
        current_pos = self.main_paned.get_position()
        if current_pos <= 0 or current_pos >= self.get_width() - 50:
            self.main_paned.set_position(self.get_width() - 400)

    def on_tab_changed(self, *args):
        """Handle tab changes and trigger lazy loading."""
        self.artifacts_panel.clear()
        
        # Trigger lazy loading for the selected tab if needed
        selected_page = self.tab_view.get_selected_page()
        if selected_page:
            child = selected_page.get_child()
            if isinstance(child, ChatPage) and child.lazy_loading:
                child.lazy_loading = False
                # Load limited chat data if we only have metadata
                if 'history' not in child.chat_data:
                    # Only load the most recent messages for performance
                    full_chat = self.storage.load_chat(child.chat_data['id'], limit_messages=child.max_visible_messages)
                    if full_chat:
                        child.chat_data = full_chat
                        child.history = full_chat.get('history', [])
                GLib.idle_add(child._load_history_batch)
