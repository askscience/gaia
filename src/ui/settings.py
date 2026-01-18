import gi
import os
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw
from src.core.config import ConfigManager
from src.core.ai_client import AIClient
from src.tools.manager import ToolManager
from src.core.network.proxy import apply_proxy_settings
from src.core.language_manager import LanguageManager
from src.voice.manager import VoiceManager
from src.voice.installer import VoiceInstaller

class SettingsWindow(Adw.PreferencesWindow):
    def __init__(self, parent=None):
        super().__init__(modal=True, transient_for=parent)
        self.lang_manager = LanguageManager()
        self.set_title(self.lang_manager.get("settings.title"))
        self.config = ConfigManager()
        self.ai_client = AIClient()
        # Initialize VoiceManager to ensure model validation occurs
        self.voice_manager = VoiceManager()

        # General Page
        page = Adw.PreferencesPage()
        page.set_title(self.lang_manager.get("settings.general.title"))
        page.set_icon_name("preferences-system-symbolic")
        self.add(page)



        # AI Group
        ai_group = Adw.PreferencesGroup()
        ai_group.set_title(self.lang_manager.get("settings.general.ai_config_title"))
        ai_group.set_description(self.lang_manager.get("settings.general.ai_config_desc"))
        page.add(ai_group)

        # General Group (Language)
        gen_group = Adw.PreferencesGroup()
        gen_group.set_title(self.lang_manager.get("settings.general.title"))
        # Insert before AI group
        page.remove(ai_group)
        page.add(gen_group)
        page.add(ai_group)

        # Language Selection
        self.lang_row = Adw.ComboRow()
        self.lang_row.set_title(self.lang_manager.get("settings.general.language_title", default="Language"))
        self.lang_row.set_subtitle(self.lang_manager.get("settings.general.language_subtitle", default="Requires restart"))
        
        # Map: Display Name -> Code
        self.lang_map = ["auto", "en", "it", "de", "es", "fr"]
        display_names = ["System Default (Auto)", "English", "Italiano", "Deutsch", "Español", "Français"]
        self.lang_row.set_model(Gtk.StringList.new(display_names))
        
        # Set current selection
        current_lang = self.config.get("app_language", "auto")
        if current_lang in self.lang_map:
            self.lang_row.set_selected(self.lang_map.index(current_lang))
        
        self.lang_row.connect("notify::selected-item", self.on_language_changed)
        gen_group.add(self.lang_row)
        
        # Voice Mode is now in a separate page
        
        # --- Voice Mode Page ---
        voice_page = Adw.PreferencesPage()
        voice_page.set_title(self.lang_manager.get("settings.voice.title")) 
        voice_page.set_icon_name("audio-input-microphone-symbolic")
        self.add(voice_page)
        
        voice_group = Adw.PreferencesGroup()
        voice_group.set_title(self.lang_manager.get("settings.voice.config_title"))
        voice_group.set_description(self.lang_manager.get("settings.voice.config_desc"))
        voice_page.add(voice_group)

        # Voice Mode Toggle
        self.voice_row = Adw.SwitchRow()
        self.voice_row.set_title(self.lang_manager.get("settings.voice.enable_title"))
        self.voice_row.set_subtitle(self.lang_manager.get("settings.voice.enable_subtitle"))
        self.voice_row.set_active(self.config.get("voice_mode_enabled", False))
        self.voice_row.connect("notify::active", self.on_voice_mode_toggled)
        voice_group.add(self.voice_row)
        
        # Voice Installer Button
        self.installer_row = Adw.ActionRow()
        self.installer_row.set_title(self.lang_manager.get("settings.voice.resources_title"))
        self.installer_row.set_subtitle(self.lang_manager.get("settings.voice.resources_subtitle"))
        
        self.install_btn = Gtk.Button(label=self.lang_manager.get("settings.voice.install_btn"))
        self.install_btn.set_valign(Gtk.Align.CENTER)
        self.install_btn.connect("clicked", self.on_voice_install_clicked)
        self.installer_row.add_suffix(self.install_btn)
        voice_group.add(self.installer_row)
        
        # Voice Selector
        self.voice_select_row = Adw.ComboRow()
        self.voice_select_row.set_title(self.lang_manager.get("settings.voice.model_title"))
        self.voice_select_row.set_subtitle(self.lang_manager.get("settings.voice.model_subtitle"))
        self.voice_select_row_handler_id = self.voice_select_row.connect("notify::selected-item", self.on_voice_model_changed)
        voice_group.add(self.voice_select_row)

        
        # Update Installer Status
        self.installer = VoiceInstaller()
        self._update_voice_install_status()
        self._populate_voice_models()

        # Provider Selection
        self.provider_row = Adw.ComboRow()
        self.provider_row.set_title(self.lang_manager.get("settings.general.provider_title"))
        self.provider_row.set_subtitle(self.lang_manager.get("settings.general.provider_subtitle"))
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
        self.api_key_row.set_title(self.lang_manager.get("settings.general.api_key_title"))
        key_name = f"{current_provider}_api_key"
        self.api_key_row.set_text(self.config.get(key_name, self.config.get("api_key", "")))
        self.api_key_handler_id = self.api_key_row.connect("changed", self.on_api_key_changed)
        ai_group.add(self.api_key_row)

        # Z.ai Coding Plan Toggle (only visible for Z.ai)
        self.zai_coding_row = Adw.SwitchRow()
        self.zai_coding_row.set_title(self.lang_manager.get("settings.general.zai_coding_title"))
        self.zai_coding_row.set_subtitle(self.lang_manager.get("settings.general.zai_coding_subtitle"))
        self.zai_coding_row.set_active(self.config.get("zai_coding_plan", False))
        self.zai_coding_row.connect("notify::active", self.on_zai_coding_changed)
        ai_group.add(self.zai_coding_row)

        # Model Selection (ComboRow)
        self.model_row = Adw.ComboRow()
        self.model_row.set_title(self.lang_manager.get("settings.general.model_title"))
        self.model_row.set_subtitle(self.lang_manager.get("settings.general.model_subtitle"))
        self.model_row.set_subtitle(self.lang_manager.get("settings.general.model_subtitle"))
        ai_group.add(self.model_row)

        # Image Search APIs Group (Moved from Deep Research)
        img_group = Adw.PreferencesGroup()
        img_group.set_title(self.lang_manager.get("settings.deep_research.image_search_title", default="Image Search"))
        img_group.set_description(self.lang_manager.get("settings.deep_research.image_search_desc", default="Configure APIs for image integration."))
        page.add(img_group) # Add to General Page

        # Unsplash Key
        self.unsplash_key_row = Adw.PasswordEntryRow()
        self.unsplash_key_row.set_title(self.lang_manager.get("settings.deep_research.unsplash_key", default="Unsplash Access Key"))
        self.unsplash_key_row.set_text(self.config.get("unsplash_access_key", ""))
        self.unsplash_key_row.connect("changed", self.on_unsplash_key_changed)
        img_group.add(self.unsplash_key_row)

        # Pexels Key
        self.pexels_key_row = Adw.PasswordEntryRow()
        self.pexels_key_row.set_title(self.lang_manager.get("settings.deep_research.pexels_key", default="Pexels API Key"))
        self.pexels_key_row.set_text(self.config.get("pexels_api_key", ""))
        self.pexels_key_row.connect("changed", self.on_pexels_key_changed)
        img_group.add(self.pexels_key_row)

        # Add refresh button to the model row
        refresh_btn = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        refresh_btn.set_valign(Gtk.Align.CENTER)
        refresh_btn.set_tooltip_text(self.lang_manager.get("settings.general.refresh_model_tooltip"))
        refresh_btn.connect("clicked", lambda b: self._refresh_models())
        self.model_row.add_suffix(refresh_btn)
        
        self.model_row_handler_id = self.model_row.connect("notify::selected", self.on_model_selected)

        self._update_visibility()
        self._refresh_models()
        
        
        # Tools Page
        tools_page = Adw.PreferencesPage()
        tools_page.set_title(self.lang_manager.get("settings.tools.title"))
        tools_page.set_icon_name("applications-utilities-symbolic")
        self.add(tools_page)
        
        # Tools Group
        tools_group = Adw.PreferencesGroup()
        tools_group.set_title(self.lang_manager.get("settings.tools.enabled_tools_title"))
        tools_group.set_description(self.lang_manager.get("settings.tools.enabled_tools_desc"))
        tools_page.add(tools_group)

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
                # show full description from LanguageManager
                desc_key = f"settings.tools.descriptions.{tool_name}"
                desc = self.lang_manager.get(desc_key)
                # Fallback to tool.description if missing (or maybe just show missing string?)
                # lang_manager.get returns formatted string or [Missing...], but if it's missing let's see.
                # Actually lang_manager.get returns "[Missing string...]" if not found.
                # If the key is missing in generic languages, we might want to fallback to English? 
                # But LanguageManager handles fallback.
                
                # Check if it returned a missing string indicator
                if "[Missing" in desc:
                    desc = tool.description
                    
                row.set_subtitle(desc)
            
            # Default to True (Active) if not in config
            is_active = enabled_tools.get(tool_name, True)
            row.set_active(is_active)
            
            # Use a lambda that captures the current tool_name
            row.connect("notify::active", lambda r, p, name=tool_name: self.on_tool_toggled(r, p, name))
            tools_group.add(row)

        # Add Calendar Tools Master Toggle
        cal_tools = ['calendar_add_event', 'calendar_remove_event', 'calendar_create', 'calendar_list_events', 'calendar_list_sources']
        cal_row = Adw.SwitchRow()
        cal_row.set_title(self.lang_manager.get("settings.tools.calendar_integration_title"))
        cal_row.set_subtitle(self.lang_manager.get("settings.tools.calendar_integration_subtitle"))
        
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

        # Web Builder Configuration
        wb_group = Adw.PreferencesGroup()
        wb_group.set_title("Web Builder")
        wb_group.set_description("Configure automated web project generation.")
        tools_page.add(wb_group)

        # Max Files
        wb_max_files_row = Adw.ActionRow()
        wb_max_files_row.set_title("Maximum File Count")
        wb_max_files_row.set_subtitle("Limit the number of files generated to prevent rate limits.")
        
        # Default 5, Range 1-20
        wb_files_adj = Gtk.Adjustment.new(self.config.get("web_builder_max_files", 5), 1, 20, 1, 1, 0)
        self.wb_files_spin = Gtk.SpinButton.new(wb_files_adj, 1, 0)
        self.wb_files_spin.set_valign(Gtk.Align.CENTER)
        self.wb_files_spin.connect("value-changed", self.on_wb_max_files_changed)
        wb_max_files_row.add_suffix(self.wb_files_spin)
        wb_group.add(wb_max_files_row)

        
        # Shortcuts Group
        shortcut_group = Adw.PreferencesGroup()
        shortcut_group.set_title(self.lang_manager.get("settings.shortcuts.title"))
        shortcut_group.set_description(self.lang_manager.get("settings.shortcuts.desc"))
        page.add(shortcut_group)
        
        shortcut_info = Adw.ActionRow()
        shortcut_info.set_title(self.lang_manager.get("settings.shortcuts.toggle_assistant"))
        shortcut_info.set_subtitle(self.lang_manager.get("settings.shortcuts.toggle_assistant_subtitle"))
        shortcut_group.add(shortcut_info)

        # Network Group
        net_group = Adw.PreferencesGroup()
        net_group.set_title(self.lang_manager.get("settings.network.title"))
        net_group.set_description(self.lang_manager.get("settings.network.desc"))
        page.add(net_group)

        # Proxy Toggle
        self.proxy_row = Adw.SwitchRow()
        self.proxy_row.set_title(self.lang_manager.get("settings.network.enable_proxy"))
        self.proxy_row.set_subtitle(self.lang_manager.get("settings.network.enable_proxy_subtitle"))
        self.proxy_row.set_active(self.config.get("proxy_enabled", False))
        self.proxy_row.connect("notify::active", self.on_proxy_toggled)
        net_group.add(self.proxy_row)

        # Proxy URL
        self.proxy_url_row = Adw.EntryRow()
        self.proxy_url_row.set_title(self.lang_manager.get("settings.network.proxy_url"))
        self.proxy_url_row.set_text(self.config.get("proxy_url", ""))
        self.proxy_url_row.connect("apply", self.on_proxy_url_changed)
        self.proxy_url_row.connect("entry-activated", self.on_proxy_url_changed)
        self.proxy_url_row.connect("changed", self.on_proxy_url_changed)
        
        # Tor Refresh Button
        self.tor_refresh_btn = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        self.tor_refresh_btn.set_valign(Gtk.Align.CENTER)
        self.tor_refresh_btn.set_tooltip_text(self.lang_manager.get("settings.network.refresh_tor_tooltip"))
        self.tor_refresh_btn.connect("clicked", self.on_refresh_tor_clicked)
        self.proxy_url_row.add_suffix(self.tor_refresh_btn)
        
        net_group.add(self.proxy_url_row)
        
        self._update_proxy_visibility()

        # Deep Research Page
        dr_page = Adw.PreferencesPage()
        dr_page.set_title(self.lang_manager.get("settings.deep_research.title"))
        dr_page.set_icon_name("system-search-symbolic")
        self.add(dr_page)

        # Research Group
        dr_group = Adw.PreferencesGroup()
        dr_group.set_title(self.lang_manager.get("settings.deep_research.research_params_title"))
        dr_group.set_description(self.lang_manager.get("settings.deep_research.research_params_desc"))
        dr_page.add(dr_group)

        # Max Loops
        self.max_loops_row = Adw.ActionRow()
        self.max_loops_row.set_title(self.lang_manager.get("settings.deep_research.max_loops"))
        self.max_loops_row.set_subtitle(self.lang_manager.get("settings.deep_research.max_loops_subtitle"))
        
        loops_adj = Gtk.Adjustment.new(self.config.get("dr_max_loops", 3), 1, 10, 1, 1, 0)
        self.loops_spin = Gtk.SpinButton.new(loops_adj, 1, 0)
        self.loops_spin.set_valign(Gtk.Align.CENTER)
        self.loops_spin.connect("value-changed", self.on_max_loops_changed)
        self.max_loops_row.add_suffix(self.loops_spin)
        dr_group.add(self.max_loops_row)

        # Max Results
        self.max_results_row = Adw.ActionRow()
        self.max_results_row.set_title(self.lang_manager.get("settings.deep_research.max_results"))
        self.max_results_row.set_subtitle(self.lang_manager.get("settings.deep_research.max_results_subtitle"))
        
        results_adj = Gtk.Adjustment.new(self.config.get("dr_max_results", 3), 1, 10, 1, 1, 0)
        self.results_spin = Gtk.SpinButton.new(results_adj, 1, 0)
        self.results_spin.set_valign(Gtk.Align.CENTER)
        self.results_spin.connect("value-changed", self.on_max_results_changed)
        self.max_results_row.add_suffix(self.results_spin)
        dr_group.add(self.max_results_row)

        # Max Scrape Length
        self.scrape_len_row = Adw.ActionRow()
        self.scrape_len_row.set_title(self.lang_manager.get("settings.deep_research.max_scrape_length"))
        self.scrape_len_row.set_subtitle(self.lang_manager.get("settings.deep_research.max_scrape_length_subtitle"))
        
        scrape_adj = Gtk.Adjustment.new(self.config.get("dr_max_scrape_length", 5000), 1000, 20000, 500, 1000, 0)
        self.scrape_spin = Gtk.SpinButton.new(scrape_adj, 1, 0)
        self.scrape_spin.set_valign(Gtk.Align.CENTER)
        self.scrape_spin.connect("value-changed", self.on_max_scrape_length_changed)
        self.scrape_len_row.add_suffix(self.scrape_spin)
        dr_group.add(self.scrape_len_row)

        # Output Depth (Outline Steps)
        self.outline_steps_row = Adw.ActionRow()
        self.outline_steps_row.set_title(self.lang_manager.get("settings.deep_research.outline_depth"))
        self.outline_steps_row.set_subtitle(self.lang_manager.get("settings.deep_research.outline_depth_subtitle"))
        
        outline_adj = Gtk.Adjustment.new(self.config.get("dr_outline_steps", 5), 3, 15, 1, 1, 0)
        self.outline_spin = Gtk.SpinButton.new(outline_adj, 1, 0)
        self.outline_spin.set_valign(Gtk.Align.CENTER)
        self.outline_spin.connect("value-changed", self.on_outline_steps_changed)
        self.outline_steps_row.add_suffix(self.outline_spin)
        dr_group.add(self.outline_steps_row)

        # Search Breadth (Queries per Section)
        self.search_breadth_row = Adw.ActionRow()
        self.search_breadth_row.set_title(self.lang_manager.get("settings.deep_research.search_breadth"))
        self.search_breadth_row.set_subtitle(self.lang_manager.get("settings.deep_research.search_breadth_subtitle"))
        
        breadth_adj = Gtk.Adjustment.new(self.config.get("dr_search_breadth", 3), 1, 10, 1, 1, 0)
        self.breadth_spin = Gtk.SpinButton.new(breadth_adj, 1, 0)
        self.breadth_spin.set_valign(Gtk.Align.CENTER)
        self.breadth_spin.connect("value-changed", self.on_search_breadth_changed)
        self.search_breadth_row.add_suffix(self.breadth_spin)
        dr_group.add(self.search_breadth_row)

        # Integrate Images Toggle
        self.integrate_images_row = Adw.SwitchRow()
        self.integrate_images_row.set_title(self.lang_manager.get("settings.deep_research.integrate_images_title", default="Integrate Images"))
        self.integrate_images_row.set_subtitle(self.lang_manager.get("settings.deep_research.integrate_images_subtitle", default="Search for and include images in the report."))
        self.integrate_images_row.set_active(self.config.get("dr_integrate_images", True))
        self.integrate_images_row.connect("notify::active", self.on_integrate_images_toggled)
        dr_group.add(self.integrate_images_row)

        # Scrape Settings Group
        scrape_group = Adw.PreferencesGroup()
        scrape_group.set_title(self.lang_manager.get("settings.deep_research.scraping_config_title"))
        scrape_group.set_description(self.lang_manager.get("settings.deep_research.scraping_config_desc"))
        dr_page.add(scrape_group)

        # Min Extracted Size
        self.min_size_row = Adw.ActionRow()
        self.min_size_row.set_title(self.lang_manager.get("settings.deep_research.min_extracted_size"))
        self.min_size_row.set_subtitle(self.lang_manager.get("settings.deep_research.min_extracted_size_subtitle"))
        
        current_scrape = self.config.get("scrape_settings", {})
        min_size_adj = Gtk.Adjustment.new(current_scrape.get("min_extracted_size", 250), 0, 1000, 10, 50, 0)
        self.min_size_spin = Gtk.SpinButton.new(min_size_adj, 1, 0)
        self.min_size_spin.set_valign(Gtk.Align.CENTER)
        self.min_size_spin.connect("value-changed", self.on_scrape_setting_changed, "min_extracted_size")
        self.min_size_row.add_suffix(self.min_size_spin)
        scrape_group.add(self.min_size_row)

        # Min Output Size
        self.min_out_row = Adw.ActionRow()
        self.min_out_row.set_title(self.lang_manager.get("settings.deep_research.min_output_size"))
        self.min_out_row.set_subtitle(self.lang_manager.get("settings.deep_research.min_output_size_subtitle"))
        
        min_out_adj = Gtk.Adjustment.new(current_scrape.get("min_output_size", 1), 0, 1000, 10, 50, 0)
        self.min_out_spin = Gtk.SpinButton.new(min_out_adj, 1, 0)
        self.min_out_spin.set_valign(Gtk.Align.CENTER)
        self.min_out_spin.connect("value-changed", self.on_scrape_setting_changed, "min_output_size")
        self.min_out_row.add_suffix(self.min_out_spin)
        scrape_group.add(self.min_out_row)


        # Search Configuration Group
        search_group = Adw.PreferencesGroup()
        search_group.set_title(self.lang_manager.get("settings.deep_research.search_config_title"))
        search_group.set_description(self.lang_manager.get("settings.deep_research.search_config_desc"))
        dr_page.add(search_group)

        # Brave Search API Key
        self.brave_key_row = Adw.PasswordEntryRow()
        self.brave_key_row.set_title(self.lang_manager.get("settings.deep_research.brave_key"))
        self.brave_key_row.set_text(self.config.get("brave_search_api_key", ""))
        self.brave_key_row.connect("changed", self.on_brave_key_changed)
        search_group.add(self.brave_key_row)

        # Advanced Configuration Group
        adv_group = Adw.PreferencesGroup()
        adv_group.set_title(self.lang_manager.get("settings.deep_research.advanced_config_title"))
        adv_group.set_description(self.lang_manager.get("settings.deep_research.advanced_config_desc"))
        dr_page.add(adv_group)

        # Max Concurrent Searches
        self.conc_search_row = Adw.ActionRow()
        self.conc_search_row.set_title(self.lang_manager.get("settings.deep_research.concurrent_searches"))
        self.conc_search_row.set_subtitle(self.lang_manager.get("settings.deep_research.concurrent_searches_subtitle"))
        
        # Default 1, Range 1-10
        conc_search_adj = Gtk.Adjustment.new(self.config.get("dr_max_concurrent_searches", 1), 1, 10, 1, 1, 0)
        self.conc_search_spin = Gtk.SpinButton.new(conc_search_adj, 1, 0)
        self.conc_search_spin.set_valign(Gtk.Align.CENTER)
        self.conc_search_spin.connect("value-changed", self.on_concurrent_searches_changed)
        self.conc_search_row.add_suffix(self.conc_search_spin)
        adv_group.add(self.conc_search_row)

        # Max Concurrent LLM Calls
        self.conc_llm_row = Adw.ActionRow()
        self.conc_llm_row.set_title(self.lang_manager.get("settings.deep_research.concurrent_llm"))
        self.conc_llm_row.set_subtitle(self.lang_manager.get("settings.deep_research.concurrent_llm_subtitle"))
        
        # Default 1, Range 1-10
        conc_llm_adj = Gtk.Adjustment.new(self.config.get("dr_max_concurrent_llm", 1), 1, 10, 1, 1, 0)
        self.conc_llm_spin = Gtk.SpinButton.new(conc_llm_adj, 1, 0)
        self.conc_llm_spin.set_valign(Gtk.Align.CENTER)
        self.conc_llm_spin.connect("value-changed", self.on_concurrent_llm_changed)
        self.conc_llm_row.add_suffix(self.conc_llm_spin)
        adv_group.add(self.conc_llm_row)




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

    def on_language_changed(self, row, param):
        """Handle language change."""
        idx = row.get_selected()
        if idx < 0 or idx >= len(self.lang_map): return
        
        new_lang = self.lang_map[idx]
        old_lang = self.config.get("app_language", "auto")
        
        if new_lang != old_lang:
            self.config.set("app_language", new_lang)
            # Update voice models immediately to reflect language change (even if UI restart is needed for labels)
            self._populate_voice_models()
            
            # Show restart warning
            self._show_restart_dialog()
            
    def on_voice_mode_toggled(self, row, pspec):
        is_active = row.get_active()
        self.config.set("voice_mode_enabled", is_active)
        
        vm = VoiceManager()
        if is_active:
             # Show info message before hiding
             dialog = Adw.MessageDialog(
                 transient_for=self,
                 heading=self.lang_manager.get("settings.voice.activated_title"),
                 body=self.lang_manager.get("settings.voice.activated_body"),
             )
             dialog.add_response("ok", "OK")
             dialog.connect("response", lambda d, r: self._activate_voice_mode(vm))
             dialog.present()
        else:
            vm.stop_voice_mode()
            
    def _activate_voice_mode(self, vm):
        vm.start_voice_mode()
        # Close settings window
        self.close()

    def _update_voice_install_status(self):
        status = self.installer.check_status()
        self.is_piper_installed = status["piper_bin"]
        
        # Check sounddevice availability
        try:
            import sounddevice as sd
            has_audio = (sd is not None)
            # Optional: check query_devices? 
        except:
            has_audio = False
            
        # Helper to check vosk model
        current_lang = self.config.get("app_language", "en")
        if current_lang == "auto": current_lang = "en"
        model_path = self.config.get(f"vosk_model_path_{current_lang}")
        if not model_path: model_path = self.config.get("vosk_model_path")
        is_model_installed = model_path and os.path.exists(model_path)
        
        # Overall readiness
        is_ready = self.is_piper_installed and is_model_installed and has_audio
        
        self.voice_row.set_sensitive(is_ready)
        if not is_ready and self.voice_row.get_active():
             self.voice_row.set_active(False)
             self.config.set("voice_mode_enabled", False)
        
        if is_ready:
             self.installer_row.set_subtitle(self.lang_manager.get("settings.voice.status_installed"))
             self.install_btn.set_label(self.lang_manager.get("settings.voice.reinstall_btn"))
             self.install_btn.add_css_class("success")
        else:
             missing = []
             if not has_audio: missing.append(self.lang_manager.get("settings.voice.missing_audio"))
             if not self.is_piper_installed: missing.append(self.lang_manager.get("settings.voice.missing_speaker"))
             if not is_model_installed: missing.append(self.lang_manager.get("settings.voice.missing_model"))
             
             missing_str = self.lang_manager.get("settings.voice.status_missing") + ", ".join(missing)
             self.installer_row.set_subtitle(missing_str)
             self.install_btn.set_label(self.lang_manager.get("settings.voice.install_btn_short"))
             self.install_btn.remove_css_class("success")

    def on_voice_install_clicked(self, btn):
        # Disable button
        self.install_btn.set_sensitive(False)
        self.install_btn.set_label(self.lang_manager.get("settings.voice.installing_btn"))
        
        # Progress Dialog? Or just update subtitle
        current_lang = self.config.get("app_language", "en")
        if current_lang == "auto": current_lang = "en"
        
        def run_install():
            def progress(p, msg):
                from gi.repository import GLib
                # Update UI
                GLib.idle_add(lambda: self.installer_row.set_subtitle(f"{msg} ({int(p*100)}%)"))
            
            # Install Piper
            if not self.installer.install_piper(current_lang, progress):
                 print("Failed to install Piper")
            
            # Install Vosk Model
            if not self.installer.install_vosk_model(current_lang, progress):
                 print(f"Failed to install Vosk model for {current_lang}")
                 
            # Install Piper Voice (TODO: add to installer)
            # For now, Piper release might contain voices or we need separate download? 
            # In installer implementation I only added piper binary download.
            # I must fix Installer to download voice!
            
            from gi.repository import GLib
            GLib.idle_add(self._on_install_complete)

        import threading
        threading.Thread(target=run_install, daemon=True).start()

    def _on_install_complete(self):
        self.install_btn.set_sensitive(True)
        self._update_voice_install_status()
        self._populate_voice_models()

    def _populate_voice_models(self):
        """Scan for available .onnx models in Piper directory."""
        piper_dir = os.path.join(os.path.expanduser("~/.gaia/voice/piper"))
        voices = []
        
        if os.path.exists(piper_dir):
            for root, dirs, files in os.walk(piper_dir):
                for f in files:
                    if f.endswith(".onnx"):
                        # Found a model
                        # Name it properly (filename without extension)
                        voices.append(f[:-5]) # Remove .onnx
        
        if not voices:
            voices = ["Default"]
            self.voice_select_row.set_sensitive(False)
        else:
            self.voice_select_row.set_sensitive(True)
            
        model = Gtk.StringList.new(voices)
        self.voice_select_row.set_model(model)
        
        # Set selection
        current_lang = self.config.get("app_language", "en")
        if current_lang == "auto": current_lang = "en"
        
        # Use the specific getter to resolve preference -> default
        current = self.voice_manager.get_voice_for_language(current_lang)

        if current in voices:
            try:
                # Block signal to prevent saving this as a user preference just because we selected it in UI
                self.voice_select_row.handler_block(self.voice_select_row_handler_id)
                self.voice_select_row.set_selected(voices.index(current))
                self.voice_select_row.handler_unblock(self.voice_select_row_handler_id)
            except: pass
        else:
            # Current preference not available or invalid (discovery fallback used potentially)
            # Try to select the discovered 'current' if available in list
             if current in voices:
                try:
                    self.voice_select_row.handler_block(self.voice_select_row_handler_id)
                    self.voice_select_row.set_selected(voices.index(current))
                    self.voice_select_row.handler_unblock(self.voice_select_row_handler_id)
                except: pass
             elif len(voices) > 0:
                 # Default to first one?
                 pass 
             
    def on_voice_model_changed(self, row, item):
        model = row.get_model()
        if not model: return
        idx = row.get_selected()
        if idx >= 0:
            val = model.get_string(idx)
            if val != "Default":
                # Save ONLY to preferences, not global piper_voice_model (legacy)
                # Or save to both to be safe, but prefs is source of truth
                self.config.set("piper_voice_model", val)
                
                # Update language-specific preference
                current_lang = self.config.get("app_language", "en")
                if current_lang == "auto": current_lang = "en"
                
                voice_prefs = self.config.get("voice_preferences", {})
                voice_prefs[current_lang] = val
                self.config.set("voice_preferences", voice_prefs)

    def _show_restart_dialog(self):
        """Warn user that restart is needed."""
        dialog = Adw.MessageDialog(
             transient_for=self,
             heading=self.lang_manager.get("settings.dialogs.restart_required_title", default="Restart Required"),
             body=self.lang_manager.get("settings.dialogs.restart_required_body", default="Please restart Gaia to apply language changes."),
        )
        dialog.add_response("ok", self.lang_manager.get("settings.dialogs.ok"))
        dialog.present()

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

    def on_brave_key_changed(self, entry):
        self.config.set("brave_search_api_key", entry.get_text())

    def on_concurrent_searches_changed(self, spin):
        self.config.set("dr_max_concurrent_searches", int(spin.get_value()))

    def on_concurrent_llm_changed(self, spin):
        self.config.set("dr_max_concurrent_llm", int(spin.get_value()))

    def on_calendar_group_toggled(self, row, tools_list):
        """Handle toggle for the calendar tool group."""
        enabled_map = self.config.get("enabled_tools", {}).copy()
        is_active = row.get_active()
        for t in tools_list:
            enabled_map[t] = is_active
        self.config.set("enabled_tools", enabled_map)

    def on_integrate_images_toggled(self, row, pspec):
        self.config.set("dr_integrate_images", row.get_active())

    def on_proxy_toggled(self, row, pspec):
        self.config.set("proxy_enabled", row.get_active())
        apply_proxy_settings()
        self._update_proxy_visibility()

    def on_proxy_url_changed(self, entry):
        self.config.set("proxy_url", entry.get_text())
        if self.proxy_row.get_active():
            apply_proxy_settings()

    def _update_proxy_visibility(self):
        is_enabled = self.proxy_row.get_active()
        self.proxy_url_row.set_sensitive(is_enabled)
        
        # Check for Tor
        url = self.proxy_url_row.get_text()
        is_tor = "9050" in url # Simple check for default Tor port
        self.tor_refresh_btn.set_visible(is_enabled and is_tor)

    def on_refresh_tor_clicked(self, btn):
        from src.core.network.tor import renew_tor_identity
        
        def run_renew():
            # Disable button and show spinner state if possible (icon change)
            from gi.repository import GLib
            GLib.idle_add(btn.set_sensitive, False)
            
            success, reason = renew_tor_identity()
            
            def handle_result():
                btn.set_sensitive(True)
                if success:
                    print("Tor Identity Renewed")
                    # Visual feedback: Flash checkmark? 
                    # For now, just logging is fine, maybe temporary tooltip change
                    btn.set_icon_name("object-select-symbolic")
                    GLib.timeout_add(2000, lambda: btn.set_icon_name("view-refresh-symbolic"))
                else:
                    print(f"Tor Renew Failed: {reason}")
                    btn.set_icon_name("dialog-error-symbolic")
                    GLib.timeout_add(2000, lambda: btn.set_icon_name("view-refresh-symbolic"))
                    
                    if "ConnectionRefused" in reason or "PermissionDenied" in reason or "AuthFailed" in reason:
                        self._prompt_enable_control_port()
            
            GLib.idle_add(handle_result)
            
        import threading
        threading.Thread(target=run_renew, daemon=True).start()

    def _prompt_enable_control_port(self):
        """Ask user to enable Tor Control Port."""
        dialog = Adw.MessageDialog(
             transient_for=self,
             heading=self.lang_manager.get("settings.dialogs.tor_unavailable_title"),
             body=self.lang_manager.get("settings.dialogs.tor_unavailable_body"),
        )
        dialog.add_response("cancel", self.lang_manager.get("settings.dialogs.cancel"))
        dialog.add_response("enable", self.lang_manager.get("settings.dialogs.enable"))
        dialog.set_response_appearance("enable", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", self._on_enable_tor_response)
        dialog.present()

    def _on_enable_tor_response(self, dialog, response):
        if response == "enable":
            self._run_pkexec_tor_config()
            
    def _run_pkexec_tor_config(self):
        import subprocess
        import secrets
        
        # Generate random password
        pwd = secrets.token_hex(16)
        
        # Hash it
        try:
            res = subprocess.run(["tor", "--hash-password", pwd], capture_output=True, text=True)
            hashed_pwd = res.stdout.strip()
            if not hashed_pwd:
                 raise Exception("Could not hash password")
        except Exception as e:
             from gi.repository import GLib
             GLib.idle_add(self._on_tor_config_complete, 1, f"Hashing failed: {e}")
             return

        # Save to config immediately
        self.config.set("tor_control_password", pwd)

        # Script to replace/add HashedControlPassword
        # We start fresh or replace existing ControlPort/Auth lines to avoid conflicts
        script = f"""
        # Backup
        cp /etc/tor/torrc /etc/tor/torrc.bak.gaia
        
        # Remove old Gaia configs or conflicting auth
        sed -i '/ControlPort 9051/d' /etc/tor/torrc
        sed -i '/CookieAuthentication/d' /etc/tor/torrc
        sed -i '/HashedControlPassword/d' /etc/tor/torrc
        
        # Add new config
        echo "ControlPort 9051" >> /etc/tor/torrc
        echo "HashedControlPassword {hashed_pwd}" >> /etc/tor/torrc
        
        systemctl restart tor
        """
        
        def run_config():
            try:
                print(f"[Tor Config] Running pkexec script...")
                cmd = ["pkexec", "bash", "-c", script]
                process = subprocess.run(cmd, capture_output=True, text=True)
                
                print(f"[Tor Config] Return code: {process.returncode}")
                # print(f"[Tor Config] Stdout: {process.stdout}") # May contain sensitively info? No, just echo.
                print(f"[Tor Config] Stderr: {process.stderr}")

                from gi.repository import GLib
                GLib.idle_add(self._on_tor_config_complete, process.returncode, process.stderr)
            except Exception as e:
                print(f"[Tor Config] Exception: {e}")
                from gi.repository import GLib
                GLib.idle_add(self._on_tor_config_complete, 1, str(e))

        import threading
        threading.Thread(target=run_config, daemon=True).start()

    def _on_tor_config_complete(self, returncode, stderr):
        if returncode == 0:
            dialog = Adw.MessageDialog(
                 transient_for=self,
                 heading=self.lang_manager.get("settings.dialogs.success"),
                 body=self.lang_manager.get("settings.dialogs.tor_enabled_body"),
            )
            dialog.add_response("ok", self.lang_manager.get("settings.dialogs.ok"))
            dialog.present()
        else:
            msg = "The operation failed."
            if "not authorized" in str(stderr).lower():
                msg = "Permission denied."
            elif stderr:
                msg = f"Error: {stderr}"
                
            dialog = Adw.MessageDialog(
                 transient_for=self,
                 heading=self.lang_manager.get("settings.dialogs.config_failed"),
                 body=msg,
            )
            dialog.add_response("close", self.lang_manager.get("settings.dialogs.close"))
            dialog.present()


    def on_wb_max_files_changed(self, spin):
        self.config.set("web_builder_max_files", int(spin.get_value()))
