import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw
from src.core.config import ConfigManager
from src.core.ai_client import AIClient

class SettingsWindow(Adw.PreferencesWindow):
    def __init__(self, parent=None):
        super().__init__(modal=True, transient_for=parent)
        self.set_title("Settings")
        self.config = ConfigManager()
        self.ai_client = AIClient()

        # General Page
        page = Adw.PreferencesPage()
        page.set_title("General")
        page.set_icon_name("preferences-system-symbolic")
        self.add(page)

        # AI Group
        ai_group = Adw.PreferencesGroup()
        ai_group.set_title("AI Configuration")
        ai_group.set_description("Configure the AI provider and model.")
        page.add(ai_group)

        # Provider Selection
        self.provider_row = Adw.ComboRow()
        self.provider_row.set_title("Provider")
        self.provider_row.set_subtitle("Select the AI service provider")
        providers = ["Ollama", "OpenAI", "Google Gemini", "Anthropic Claude", "Mistral", "Z.ai"]
        self.provider_row.set_model(Gtk.StringList.new(providers))
        ai_group.add(self.provider_row)

        provider_map = {
            0: "ollama", 1: "openai", 2: "gemini", 
            3: "anthropic", 4: "mistral", 5: "zai"
        }
        self.rev_provider_map = {v: k for k, v in provider_map.items()}

        current_provider = self.config.get("provider", "ollama")
        # Block signal during initial set_selected
        self.provider_row.set_selected(self.rev_provider_map.get(current_provider, 0))
        self.provider_row_handler_id = self.provider_row.connect("notify::selected", self.on_provider_changed)

        # API Key Entry
        self.api_key_row = Adw.PasswordEntryRow()
        self.api_key_row.set_title("API Key")
        key_name = f"{current_provider}_api_key"
        self.api_key_row.set_text(self.config.get(key_name, self.config.get("api_key", "")))
        self.api_key_handler_id = self.api_key_row.connect("changed", self.on_api_key_changed)
        ai_group.add(self.api_key_row)

        # Z.ai Coding Plan Toggle (only visible for Z.ai)
        self.zai_coding_row = Adw.SwitchRow()
        self.zai_coding_row.set_title("Use Coding Plan API")
        self.zai_coding_row.set_subtitle("Enable for GLM Coding Plan (requires coding subscription)")
        self.zai_coding_row.set_active(self.config.get("zai_coding_plan", False))
        self.zai_coding_row.connect("notify::active", self.on_zai_coding_changed)
        ai_group.add(self.zai_coding_row)

        # Model Selection (ComboRow)
        self.model_row = Adw.ComboRow()
        self.model_row.set_title("Model")
        self.model_row.set_subtitle("Select the specific model to use")
        ai_group.add(self.model_row)

        # Add refresh button to the model row
        refresh_btn = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        refresh_btn.set_valign(Gtk.Align.CENTER)
        refresh_btn.set_tooltip_text("Refresh Model List")
        refresh_btn.connect("clicked", lambda b: self._refresh_models())
        self.model_row.add_suffix(refresh_btn)
        
        self.model_row_handler_id = self.model_row.connect("notify::selected", self.on_model_selected)

        self._update_visibility()
        self._refresh_models()
        
        # Shortcuts Group
        shortcut_group = Adw.PreferencesGroup()
        shortcut_group.set_title("Shortcuts")
        shortcut_group.set_description("Global shortcuts must be configured in GNOME Settings.")
        page.add(shortcut_group)
        
        shortcut_info = Adw.ActionRow()
        shortcut_info.set_title("Toggle Assistant")
        shortcut_info.set_subtitle("Default: Super+Space (Needs manual setup)")
        shortcut_group.add(shortcut_info)

        # Deep Research Page
        dr_page = Adw.PreferencesPage()
        dr_page.set_title("Deep Research")
        dr_page.set_icon_name("system-search-symbolic")
        self.add(dr_page)

        # Research Group
        dr_group = Adw.PreferencesGroup()
        dr_group.set_title("Research Parameters")
        dr_group.set_description("Configure the behavior of the Deep Research Agent.")
        dr_page.add(dr_group)

        # Max Loops
        self.max_loops_row = Adw.ActionRow()
        self.max_loops_row.set_title("Max Research Loops")
        self.max_loops_row.set_subtitle("Maximum number of iterations for refining results")
        
        loops_adj = Gtk.Adjustment.new(self.config.get("dr_max_loops", 3), 1, 10, 1, 1, 0)
        self.loops_spin = Gtk.SpinButton.new(loops_adj, 1, 0)
        self.loops_spin.set_valign(Gtk.Align.CENTER)
        self.loops_spin.connect("value-changed", self.on_max_loops_changed)
        self.max_loops_row.add_suffix(self.loops_spin)
        dr_group.add(self.max_loops_row)

        # Max Results
        self.max_results_row = Adw.ActionRow()
        self.max_results_row.set_title("Max Search Results")
        self.max_results_row.set_subtitle("Results per sub-query")
        
        results_adj = Gtk.Adjustment.new(self.config.get("dr_max_results", 3), 1, 10, 1, 1, 0)
        self.results_spin = Gtk.SpinButton.new(results_adj, 1, 0)
        self.results_spin.set_valign(Gtk.Align.CENTER)
        self.results_spin.connect("value-changed", self.on_max_results_changed)
        self.max_results_row.add_suffix(self.results_spin)
        dr_group.add(self.max_results_row)

        # Max Scrape Length
        self.scrape_len_row = Adw.ActionRow()
        self.scrape_len_row.set_title("Max Scrape Length")
        self.scrape_len_row.set_subtitle("Maximum characters to extract per page")
        
        scrape_adj = Gtk.Adjustment.new(self.config.get("dr_max_scrape_length", 5000), 1000, 20000, 500, 1000, 0)
        self.scrape_spin = Gtk.SpinButton.new(scrape_adj, 1, 0)
        self.scrape_spin.set_valign(Gtk.Align.CENTER)
        self.scrape_spin.connect("value-changed", self.on_max_scrape_length_changed)
        self.scrape_len_row.add_suffix(self.scrape_spin)
        dr_group.add(self.scrape_len_row)

        # Output Depth (Outline Steps)
        self.outline_steps_row = Adw.ActionRow()
        self.outline_steps_row.set_title("Outline Depth")
        self.outline_steps_row.set_subtitle("Number of sections in the generated report")
        
        outline_adj = Gtk.Adjustment.new(self.config.get("dr_outline_steps", 5), 3, 15, 1, 1, 0)
        self.outline_spin = Gtk.SpinButton.new(outline_adj, 1, 0)
        self.outline_spin.set_valign(Gtk.Align.CENTER)
        self.outline_spin.connect("value-changed", self.on_outline_steps_changed)
        self.outline_steps_row.add_suffix(self.outline_spin)
        dr_group.add(self.outline_steps_row)

        # Search Breadth (Queries per Section)
        self.search_breadth_row = Adw.ActionRow()
        self.search_breadth_row.set_title("Search Breadth")
        self.search_breadth_row.set_subtitle("Number of search queries per section")
        
        breadth_adj = Gtk.Adjustment.new(self.config.get("dr_search_breadth", 3), 1, 10, 1, 1, 0)
        self.breadth_spin = Gtk.SpinButton.new(breadth_adj, 1, 0)
        self.breadth_spin.set_valign(Gtk.Align.CENTER)
        self.breadth_spin.connect("value-changed", self.on_search_breadth_changed)
        self.search_breadth_row.add_suffix(self.breadth_spin)
        dr_group.add(self.search_breadth_row)

    def _update_visibility(self):
        selected = self.provider_row.get_selected()
        # Hide API key for Ollama (index 0)
        self.api_key_row.set_visible(selected != 0)
        # Show Z.ai coding plan toggle only for Z.ai (index 5)
        self.zai_coding_row.set_visible(selected == 5)

    def _refresh_models(self):
        """Fetch models from the current provider and populate the combo row."""
        # Show "Refreshing..." state
        self.model_row.set_model(Gtk.StringList.new(["Refreshing..."]))
        self.model_row.set_sensitive(False)

        def do_refresh():
            self.ai_client = AIClient() 
            models = self.ai_client.list_models()
            
            def update_ui():
                    provider = self.config.get("provider", "ollama")
                    model_key = f"{provider}_model"
                    current_model = self.config.get(model_key, self.config.get("model", ""))
                    
                    # Ensure the current model stays in the list even if dynamic fetch missed it
                    if current_model and current_model not in models and current_model != "Refreshing...":
                        models.insert(0, current_model)

                    # Block signal to avoid re-triggering save while loading
                    self.model_row.handler_block(self.model_row_handler_id)
                    
                    string_list = Gtk.StringList.new(models)
                    self.model_row.set_model(string_list)
                    self.model_row.set_sensitive(True)

                    if current_model in models:
                        self.model_row.set_selected(models.index(current_model))
                    else:
                        # Only set 0 if there's no stored preference
                        self.model_row.set_selected(0)
                        if models and not current_model:
                            self.config.set(model_key, models[0])
                    
                    self.model_row.handler_unblock(self.model_row_handler_id)
            
            from gi.repository import GLib
            GLib.idle_add(update_ui)

        import threading
        threading.Thread(target=do_refresh, daemon=True).start()

    def on_provider_changed(self, row, pspec):
        provider_map = {
            0: "ollama", 1: "openai", 2: "gemini", 
            3: "anthropic", 4: "mistral", 5: "zai"
        }
        selected_index = row.get_selected()
        provider = provider_map.get(selected_index, "ollama")
        self.config.set("provider", provider)
        
        # Update API key field with the key for this provider
        key_name = f"{provider}_api_key"
        stored_key = self.config.get(key_name, "")
        
        # Block signal so we don't overwrite with old field text
        self.api_key_row.handler_block(self.api_key_handler_id)
        self.api_key_row.set_text(stored_key)
        self.api_key_row.handler_unblock(self.api_key_handler_id)
        
        self._update_visibility()
        self._refresh_models()

    def on_api_key_changed(self, entry):
        provider = self.config.get("provider", "ollama")
        key_name = f"{provider}_api_key"
        self.config.set(key_name, entry.get_text())
        # Also sync to generic 'api_key' for compatibility
        self.config.set("api_key", entry.get_text())
    def on_model_selected(self, row, pspec):
        selected_index = row.get_selected()
        model_list = row.get_model()
        if selected_index != -1 and model_list:
            selected_model = model_list.get_string(selected_index)
            if selected_model != "No models found" and selected_model != "Refreshing...":
                provider = self.config.get("provider", "ollama")
                model_key = f"{provider}_model"
                self.config.set(model_key, selected_model)
                # Keep global model in sync for simple usage
                self.config.set("model", selected_model)

    def on_zai_coding_changed(self, row, pspec):
        """Handle Z.ai Coding Plan toggle change."""
        self.config.set("zai_coding_plan", row.get_active())

    def on_max_loops_changed(self, spin):
        self.config.set("dr_max_loops", int(spin.get_value()))

    def on_max_results_changed(self, spin):
        self.config.set("dr_max_results", int(spin.get_value()))

    def on_max_scrape_length_changed(self, spin):
        self.config.set("dr_max_scrape_length", int(spin.get_value()))

    def on_outline_steps_changed(self, spin):
        self.config.set("dr_outline_steps", int(spin.get_value()))

    def on_search_breadth_changed(self, spin):
        self.config.set("dr_search_breadth", int(spin.get_value()))
