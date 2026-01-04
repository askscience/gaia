import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw
from src.core.config import ConfigManager
from src.core.ai_client import AIClient
from src.tools.manager import ToolManager
from src.core.network.proxy import apply_proxy_settings

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

        # Network Group
        net_group = Adw.PreferencesGroup()
        net_group.set_title("Network")
        net_group.set_description("Configure global network settings.")
        page.add(net_group)

        # Proxy Toggle
        self.proxy_row = Adw.SwitchRow()
        self.proxy_row.set_title("Enable Proxy")
        self.proxy_row.set_subtitle("Route traffic through a custom proxy")
        self.proxy_row.set_active(self.config.get("proxy_enabled", False))
        self.proxy_row.connect("notify::active", self.on_proxy_toggled)
        net_group.add(self.proxy_row)

        # Proxy URL
        self.proxy_url_row = Adw.EntryRow()
        self.proxy_url_row.set_title("Proxy URL")
        self.proxy_url_row.set_text(self.config.get("proxy_url", ""))
        self.proxy_url_row.connect("apply", self.on_proxy_url_changed) # Apply on Enter
        self.proxy_url_row.connect("entry-activated", self.on_proxy_url_changed)
        
        # Debounce/Save on focus out could be better, but 'changed' is too aggressive for applying network settings 
        # that might break connections immediately. Let's use 'changed' but just save config, apply happens there?
        # Actually for EntryRow 'changed' is fine if we just update config. 
        # Only apply when toggled or maybe explicitly?
        # Let's use 'changed' to save config, and apply on every change? might be spammy.
        # Ideally apply only when valid. For now, let's use 'changed' to save.
        self.proxy_url_row.connect("changed", self.on_proxy_url_changed)
        
        net_group.add(self.proxy_url_row)
        
        self._update_proxy_visibility()

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
        
        # Tools Group
        tools_group = Adw.PreferencesGroup()
        tools_group.set_title("Tools")
        tools_group.set_description("Enable or disable specific AI tools.")
        page.add(tools_group)

        # Dynamically load tools and add toggles
        self.tool_manager = ToolManager()
        self.tool_manager.load_tools()
        
        enabled_tools = self.config.get("enabled_tools", {})
        
        # Sort tools by name for consistent display
        sorted_tool_names = sorted(self.tool_manager.tools.keys())
        
        for tool_name in sorted_tool_names:
            # Skip individual calendar tools
            if tool_name in ['calendar_add_event', 'calendar_remove_event', 'calendar_create', 'calendar_list_events', 'calendar_list_sources']:
                continue

            tool = self.tool_manager.tools[tool_name]
            row = Adw.SwitchRow()
            # Format tool name: "file_editor" -> "File Editor"
            display_name = tool.name.replace("_", " ").title()
            row.set_title(display_name)
            
            if hasattr(tool, 'description'):
                # show full description
                row.set_subtitle(tool.description)
            
            # Default to True (Active) if not in config
            is_active = enabled_tools.get(tool_name, True)
            row.set_active(is_active)
            
            # Use a lambda that captures the current tool_name
            row.connect("notify::active", lambda r, p, name=tool_name: self.on_tool_toggled(r, p, name))
            tools_group.add(row)

        # Add Calendar Tools Master Toggle
        cal_tools = ['calendar_add_event', 'calendar_remove_event', 'calendar_create', 'calendar_list_events', 'calendar_list_sources']
        cal_row = Adw.SwitchRow()
        cal_row.set_title("Calendar Integration")
        cal_row.set_subtitle("Enable GNOME Calendar management tools")
        
        # Check if all are enabled (default True)
        is_cal_active = all(enabled_tools.get(t, True) for t in cal_tools)
        cal_row.set_active(is_cal_active)
        cal_row.connect("notify::active", lambda r, p: self.on_calendar_group_toggled(r, cal_tools))
        
        # Insert at the top of tools group (or append, but top is nice)
        # To insert at top we need to use insert_child_at_index or just add it first?
        # AdwPreferencesGroup doesn't easily support index insert for rows? 
        # Actually it does, but 'add' appends. Let's just append it.
        # Wait, we filtered them out, so we need to add this row. 
        # Let's add it at the start of the loop? No, just add it here.
        tools_group.add(cal_row)
        
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

        # Scrape Settings Group
        scrape_group = Adw.PreferencesGroup()
        scrape_group.set_title("Scraping Configuration")
        scrape_group.set_description("Advanced settings for content extraction (Trafilatura).")
        dr_page.add(scrape_group)

        # Min Extracted Size
        self.min_size_row = Adw.ActionRow()
        self.min_size_row.set_title("Min Extracted Size")
        self.min_size_row.set_subtitle("Minimum size of extracted text blocks")
        
        current_scrape = self.config.get("scrape_settings", {})
        min_size_adj = Gtk.Adjustment.new(current_scrape.get("min_extracted_size", 250), 0, 1000, 10, 50, 0)
        self.min_size_spin = Gtk.SpinButton.new(min_size_adj, 1, 0)
        self.min_size_spin.set_valign(Gtk.Align.CENTER)
        self.min_size_spin.connect("value-changed", self.on_scrape_setting_changed, "min_extracted_size")
        self.min_size_row.add_suffix(self.min_size_spin)
        scrape_group.add(self.min_size_row)

        # Min Output Size
        self.min_out_row = Adw.ActionRow()
        self.min_out_row.set_title("Min Output Size")
        self.min_out_row.set_subtitle("Minimum total size of extracted content")
        
        min_out_adj = Gtk.Adjustment.new(current_scrape.get("min_output_size", 1), 0, 1000, 10, 50, 0)
        self.min_out_spin = Gtk.SpinButton.new(min_out_adj, 1, 0)
        self.min_out_spin.set_valign(Gtk.Align.CENTER)
        self.min_out_spin.connect("value-changed", self.on_scrape_setting_changed, "min_output_size")
        self.min_out_row.add_suffix(self.min_out_spin)
        scrape_group.add(self.min_out_row)

        # Image Search APIs Group
        img_group = Adw.PreferencesGroup()
        img_group.set_title("Image Search APIs")
        img_group.set_description("Provide API keys to include high-quality images with attribution in your reports.")
        dr_page.add(img_group)

        # Unsplash Key
        self.unsplash_key_row = Adw.PasswordEntryRow()
        self.unsplash_key_row.set_title("Unsplash Access Key")
        self.unsplash_key_row.set_text(self.config.get("unsplash_access_key", ""))
        self.unsplash_key_row.connect("changed", self.on_unsplash_key_changed)
        img_group.add(self.unsplash_key_row)

        # Pexels Key
        self.pexels_key_row = Adw.PasswordEntryRow()
        self.pexels_key_row.set_title("Pexels API Key")
        self.pexels_key_row.set_text(self.config.get("pexels_api_key", ""))
        self.pexels_key_row.connect("changed", self.on_pexels_key_changed)
        img_group.add(self.pexels_key_row)

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

    def on_tool_toggled(self, row, pspec, tool_name):
        """Handle tool toggle changes."""
        enabled_map = self.config.get("enabled_tools", {}).copy()
        enabled_map[tool_name] = row.get_active()
        self.config.set("enabled_tools", enabled_map)

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

    def on_scrape_setting_changed(self, spin, key):
        """Update a specific key in the scrape_settings dictionary."""
        current_settings = self.config.get("scrape_settings", {}).copy()
        current_settings[key] = int(spin.get_value())
        self.config.set("scrape_settings", current_settings)

    def on_unsplash_key_changed(self, entry):
        self.config.set("unsplash_access_key", entry.get_text())

    def on_pexels_key_changed(self, entry):
        self.config.set("pexels_api_key", entry.get_text())

    def on_calendar_group_toggled(self, row, tools_list):
        """Handle toggle for the calendar tool group."""
        enabled_map = self.config.get("enabled_tools", {}).copy()
        is_active = row.get_active()
        for t in tools_list:
            enabled_map[t] = is_active
        self.config.set("enabled_tools", enabled_map)

    def on_proxy_toggled(self, row, pspec):
        self.config.set("proxy_enabled", row.get_active())
        apply_proxy_settings()
        self._update_proxy_visibility()

    def on_proxy_url_changed(self, entry):
        self.config.set("proxy_url", entry.get_text())
        if self.proxy_row.get_active():
            apply_proxy_settings()

    def _update_proxy_visibility(self):
        self.proxy_url_row.set_sensitive(self.proxy_row.get_active())

