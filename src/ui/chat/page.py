import gi
import threading
import json
import re
import time
import os
import traceback

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib, Gio, Gdk

from src.core.chat_storage import ChatStorage
from src.ui.utils import markdown_to_pango
from src.ui.components import SourceCard, ArtifactCard, ResearchCard
from src.core.ai_client import AIClient
from src.tools.manager import ToolManager
from src.core.tool_call_parser import ToolCallParser
from src.core.tool_call_parser import ToolCallParser
from src.core.prompt_manager import PromptManager
from src.core.language_manager import LanguageManager

class ChatPage(Gtk.Box):
    """A single chat page containing the chat UI."""
    
    def __init__(self, chat_data: dict, storage: ChatStorage, lazy_loading: bool = False, *args, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, *args, **kwargs)
        
        self.chat_data = chat_data
        self.storage = storage
        self.history = chat_data.get('history', [])
        self.lazy_loading = lazy_loading
        self.prompt_manager = PromptManager()
        self.lang_manager = LanguageManager()
        
        self.loaded_messages = 0
        self.max_visible_messages = 100
        self.batch_size = 20
        self._markdown_cache_size_limit = 200
        self._markdown_cache = {}
        self._markdown_cache_order = []
        self._deferred_sources_artifacts = []  # Store sources/artifacts to add later
        
        # Subscribe to centralized status updates
        from src.core.status.manager import StatusManager, TOOL_STATUS_UPDATE
        self.status_manager = StatusManager()
        self.status_handler_id = self.status_manager.connect(TOOL_STATUS_UPDATE, self._on_tool_status_update)

        # Watch for tab changes to clean up resources
        self.connect("unmap", self._on_unmap)
        

        
        # Generation State
        self._is_generating = False
        self._cancel_event = threading.Event()
        
        # Chat Area
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_vexpand(True)
        self.append(self.scrolled)
        
        self.chat_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.chat_box.set_spacing(6)
        self.chat_box.set_margin_top(12)
        self.chat_box.set_margin_bottom(12)
        self.chat_box.set_margin_start(12)
        self.chat_box.set_margin_end(12)
        self.chat_box.add_css_class("chat-box")
        self.scrolled.set_child(self.chat_box)
        
        # Input Area
        self.input_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.input_box.set_margin_start(12)
        self.input_box.set_margin_end(12)
        self.input_box.set_margin_bottom(12)
        self.input_box.set_margin_top(6)
        self.input_box.set_spacing(10)
        
        self.entry = Gtk.Entry()
        self.entry.set_hexpand(True)
        self.entry.set_placeholder_text(self.lang_manager.get("chat.placeholder"))
        self.entry.connect("activate", self.on_entry_activate)
        self.input_box.append(self.entry)
        
        self.send_button = Gtk.Button()
        self.send_button.set_icon_name("mail-send-symbolic")
        self.send_button.set_tooltip_text(self.lang_manager.get("chat.send_tooltip"))
        self.send_button.add_css_class("suggested-action")
        self.send_button.connect("clicked", self.on_send_clicked)
        self.input_box.append(self.send_button)
        
        self.append(self.input_box)
        
        # Load existing messages in batches on idle (only if not lazy loading)
        if not self.lazy_loading:
            GLib.idle_add(self._load_history_batch)
    
    def _load_history_batch(self):
        """Load existing messages from history in batches using threading."""
        if not hasattr(self, '_loading_thread') or not self._loading_thread.is_alive():
            self._loading_thread = threading.Thread(target=self._load_messages_in_thread, daemon=True)
            self._loading_thread.start()
    
    def _load_messages_in_thread(self):
        """Load messages in a background thread, then update UI on main thread."""
        batch_size = self.batch_size
        total_messages = len(self.history)
        
        start_index = max(0, total_messages - self.max_visible_messages)
        self.loaded_messages = start_index
        
        while self.loaded_messages < total_messages:
            start = self.loaded_messages
            end = min(start + batch_size, total_messages)
            
            batch_messages = []
            for i in range(start, end):
                msg = self.history[i]
                metadata = msg.get('metadata')
                content = msg['content']
                
                if content not in self._markdown_cache:
                    self._markdown_cache[content] = markdown_to_pango(content)
                    self._markdown_cache_order.append(content)
                    if len(self._markdown_cache_order) > self._markdown_cache_size_limit:
                        oldest = self._markdown_cache_order.pop(0)
                        if oldest in self._markdown_cache:
                            del self._markdown_cache[oldest]
                parsed_content = self._markdown_cache[content]
                
                batch_messages.append((
                    msg['role'],
                    parsed_content,
                    content,
                    metadata,
                    metadata and 'sources' in metadata,
                    metadata and 'artifacts' in metadata,
                    metadata.get('sources', []) if metadata else [],
                    metadata.get('artifacts', []) if metadata else []
                ))
            
            self.loaded_messages = end
            GLib.idle_add(self._add_batch_to_ui, batch_messages)
            time.sleep(0.003)
        
        GLib.idle_add(self._scroll_to_bottom)
    
    def _add_batch_to_ui(self, batch_messages):
        if not hasattr(self, 'chat_box') or not self.chat_box:
            return False
            
        for role, parsed_content, original_content, metadata, has_sources, has_artifacts, sources, artifacts in batch_messages:
            self._add_message_with_parsed_content(role, parsed_content, original_content, metadata=metadata, save=False, scroll=False)
            
            # Add sources and artifacts AFTER the message bubble
            if has_sources and sources:
                self.add_sources_to_ui(sources)
            if has_artifacts and artifacts:
                self.add_artifacts_to_ui(artifacts)
        return False
    
    def _add_deferred_artifacts(self):
        for art_type, data in self._deferred_sources_artifacts:
            if art_type == 'sources':
                self.add_sources_to_ui(data)
            elif art_type == 'artifacts':
                self.add_artifacts_to_ui(data)
        self._deferred_sources_artifacts.clear()
        return False
    
    def _on_tool_status_update(self, manager, project_id, message):
        """Handle centralized status updates."""
        # Only update if this page corresponds to the project_id
        if project_id == self.chat_data.get("id"):
            GLib.idle_add(self.show_spinner, message)

    def _on_unmap(self, widget):
        if self.status_handler_id:
            self.status_manager.disconnect(self.status_handler_id)
            self.status_handler_id = None
            

        self._markdown_cache.clear()
        self._markdown_cache_order.clear()
        return False
    

    
    def on_entry_activate(self, entry):
        self.on_send_clicked(entry)

    def on_send_clicked(self, button):
        if self._is_generating:
            # Handle Stop
            self._cancel_event.set()
            self.send_button.set_sensitive(False) # Disable temporarily while stopping
            return

        text = self.entry.get_text().strip()
        if not text:
            return
        
        self.entry.set_sensitive(False)
        self.entry.set_text("")
        
        # Set Generating State
        self._is_generating = True
        self._cancel_event.clear()
        self.send_button.set_icon_name("process-stop-symbolic")
        self.send_button.set_tooltip_text(self.lang_manager.get("chat.stop_tooltip"))
        
        self.add_message("user", text)
        
        def run_with_exception_handler():
            try:
                self.run_ai(text)
            except Exception as e:
                print(f"[DEBUG thread] EXCEPTION in run_ai: {e}")
                traceback.print_exc()
                GLib.idle_add(self.enable_ui)
        
        thread = threading.Thread(target=run_with_exception_handler, daemon=True)
        thread.start()

    def enable_ui(self):
        self._is_generating = False
        self._cancel_event.clear()
        self.entry.set_sensitive(True)
        self.send_button.set_sensitive(True)
        self.send_button.set_icon_name("mail-send-symbolic")
        self.send_button.set_tooltip_text(self.lang_manager.get("chat.send_tooltip"))
        self.entry.grab_focus()

    def add_message(self, role: str, text: str, metadata: dict = None, parsed_text: str = None):
        if '<tool_call>' in text:
            text = text.split('<tool_call>')[0].strip()
        
        if not self.chat_data.get('_is_persisted', True):
            self.chat_data['_is_persisted'] = True
            self.storage.save_chat(self.chat_data)
        
        msg = {'role': role, 'content': text}
        if metadata:
            msg['metadata'] = metadata
        self.history.append(msg)
        
        # Auto-update title if it's the first user message
        if role == "user":
            current_title = self.chat_data.get('title', self.lang_manager.get("window.new_chat"))
            if current_title in [self.lang_manager.get("window.new_chat"), "New Chat", "New chat", None]:
                new_title = text[:30] + "..." if len(text) > 30 else text
                self.chat_data['title'] = new_title
                
                # Update UI Tab
                root = self.get_native()
                if hasattr(root, 'tab_view'):
                    page = root.tab_view.get_page(self)
                    if page:
                        page.set_title(new_title)
        
        try:
            self.chat_data['history'] = self.history.copy()
            self.storage.save_chat(self.chat_data)
        except Exception as e:
            print(f"[DEBUG] Error saving chat: {e}")
            
        self._add_message_ui(role, text, metadata=metadata, save=False, parsed_text=parsed_text)
    
    def _add_message_ui(self, role: str, text: str, metadata: dict = None, save: bool = True, scroll: bool = True, parsed_text: str = None):
        if parsed_text is None:
            parsed_text = markdown_to_pango(text)
        return self._add_message_with_parsed_content(role, parsed_text, text, metadata, save, scroll)
    
    def _add_message_with_parsed_content(self, role: str, parsed_text: str, original_text: str, metadata: dict = None, save: bool = True, scroll: bool = True):
        msg_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        msg_row.add_css_class("message-row")
        msg_row.set_halign(Gtk.Align.END if role == "user" else Gtk.Align.START)
        
        bubble = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        bubble.add_css_class("message-bubble")
        bubble.add_css_class("user-message" if role == "user" else "ai-message")
        
        msg_label = Gtk.Label()
        msg_label.set_use_markup(True)
        msg_label.set_markup(parsed_text)
        msg_label.set_wrap(True)
        msg_label.set_max_width_chars(50)
        msg_label.set_xalign(0)
        msg_label.set_selectable(True)
        bubble.append(msg_label)
        
        if metadata and 'plan' in metadata and not metadata.get('plan_approved'):
            self._add_plan_button(bubble)

        msg_row.append(bubble)
        self.chat_box.append(msg_row)
        if scroll:
            self._scroll_to_bottom()
        return msg_label
    
    def _scroll_to_bottom(self):
        def do_scroll():
            adj = self.scrolled.get_vadjustment()
            if adj:
                adj.set_value(adj.get_upper() - adj.get_page_size())
            return False
        GLib.idle_add(do_scroll)

    def update_last_message(self, text: str, parsed_text: str = None):
        if '<tool_call>' in text:
            text = text.split('<tool_call>')[0].strip()
        
        child = self.chat_box.get_last_child()
        while child:
            if child.has_css_class("message-row"):
                break
            child = child.get_prev_sibling()
            
        if not child:
            return

        def find_label(widget):
            if isinstance(widget, Gtk.Label): return widget
            if hasattr(widget, 'get_first_child'):
                c = widget.get_first_child()
                while c:
                    res = find_label(c)
                    if res: return res
                    c = c.get_next_sibling()
            return None

        label = find_label(child)
        if label:
            if parsed_text is None:
                parsed_text = markdown_to_pango(text)
            label.set_markup(parsed_text)
            
            if "[/PLAN]" in text:
                bubble = label.get_parent()
                if 'plan' not in (self.history[-1].get('metadata') or {}):
                    self.update_last_message_metadata({'plan': True})
                self._add_plan_button(bubble)
        
        if self.history and self.history[-1]['role'] == 'assistant':
            self.history[-1]['content'] = text

        self._scroll_to_bottom()

    def update_last_message_metadata(self, metadata: dict):
        if self.history and self.history[-1]['role'] == 'assistant':
            if 'metadata' not in self.history[-1]:
                self.history[-1]['metadata'] = {}
            self.history[-1]['metadata'].update(metadata)
            
            chat = self.storage.load_chat(self.chat_data['id'])
            if chat and chat['history']:
                if 'metadata' not in chat['history'][-1]:
                    chat['history'][-1]['metadata'] = {}
                chat['history'][-1]['metadata'].update(metadata)
                self.storage.save_chat(chat)

    def show_spinner(self, text: str = None):
        if text is None:
            text = self.prompt_manager.get("ui.spinner.thinking")
        if hasattr(self, 'spinner_box') and self.spinner_box:
            c = self.spinner_box.get_first_child()
            while c:
                if isinstance(c, Gtk.Label):
                    c.set_text(text)
                    return
                c = c.get_next_sibling()
            return

        self.spinner_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.spinner_box.set_halign(Gtk.Align.START)
        self.spinner_box.set_margin_start(10)
        self.spinner_box.set_margin_bottom(5)
        self.spinner_box.add_css_class("spinner-box")
        
        spinner = Gtk.Spinner()
        spinner.start()
        self.spinner_box.append(spinner)
        
        label = Gtk.Label(label=text)
        label.set_margin_start(10)
        label.add_css_class("dim-label")
        self.spinner_box.append(label)
        
        self.chat_box.append(self.spinner_box)
        self._scroll_to_bottom()

    def remove_spinner(self):
        if hasattr(self, 'spinner_box') and self.spinner_box:
            self.chat_box.remove(self.spinner_box)
            self.spinner_box = None

    def replace_spinner_with_msg(self, role: str, text: str, metadata: dict = None, parsed_text: str = None):
        self.remove_spinner()
        self.add_message(role, text, metadata=metadata, parsed_text=parsed_text)

    def add_sources_to_ui(self, sources: list):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main_box.set_spacing(6)
        main_box.set_margin_top(12)
        main_box.set_margin_bottom(12)
        main_box.set_hexpand(True)
        main_box.add_css_class("sources-container")
        
        main_box.add_css_class("sources-container")
        
        header = Gtk.Label(label=self.lang_manager.get("chat.sources_header"))
        header.add_css_class("dim-label")
        header.set_halign(Gtk.Align.START)
        header.set_margin_start(4)
        main_box.append(header)
        
        # Use ListBox for compact vertical list
        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        listbox.add_css_class("sources-listbox")
        
        for source in sources:
            card = SourceCard(
                title=source.get('title', 'Untitled'),
                url=source.get('url', ''),
                snippet=source.get('snippet', ''),
                image_url=source.get('image_url'),
                favicon_url=source.get('favicon_url')
            )
            listbox.append(card)
        
        main_box.append(listbox)
        
        msg_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        msg_row.set_halign(Gtk.Align.FILL)
        msg_row.set_margin_start(40)
        msg_row.set_margin_end(40)
        msg_row.append(main_box)
        self.chat_box.append(msg_row)
        self._scroll_to_bottom()

    def add_artifacts_to_ui(self, artifacts: list):
        artifacts_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        artifacts_box.set_spacing(6)
        artifacts_box.set_margin_top(12)
        artifacts_box.set_margin_bottom(12)
        
        has_web = any(art.get('language') == 'html' for art in artifacts)
        
        if has_web:
            first_path = artifacts[0].get('path')
            if first_path:
                if "deepresearch" in first_path:
                    # Deep Research - Load directly into Artifacts Panel with research mode
                    project_dir = os.path.dirname(first_path)
                    
                    def load_research_panel():
                        root = self.get_native()
                        if hasattr(root, "artifacts_panel"):
                            root.artifacts_panel.load_project(project_dir, is_research=True)
                            root.show_artifacts()
                            
                    GLib.idle_add(load_research_panel)
                else:
                    # Web Project - Load directly into Artifacts Panel, no chat card
                    project_dir = os.path.dirname(first_path)
                    
                    def load_into_panel():
                        root = self.get_native()
                        if hasattr(root, "artifacts_panel"):
                            root.artifacts_panel.load_project(project_dir)
                            root.show_artifacts()
                            
                    GLib.idle_add(load_into_panel)
                    # Do not append anything to chat if it's just a web project update
        else:
            for art in artifacts:
                card = ArtifactCard(
                    filename=art.get('filename', 'Unknown'),
                    path=art.get('path', ''),
                    language=art.get('language', '')
                )
                artifacts_box.append(card)
        
            msg_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            msg_row.set_halign(Gtk.Align.START)
            msg_row.set_margin_start(40)
            msg_row.set_margin_top(16)
            msg_row.append(artifacts_box)
            self.chat_box.append(msg_row)
            self._scroll_to_bottom()

    def run_ai(self, user_text: str, is_hidden: bool = False):
        client = AIClient()
        tm = ToolManager()
        tm.load_tools()
        tools_def = tm.get_ollama_tools_definitions()
        
        # Dynamically build system prompt based on enabled tools
        enabled_map = tm.config.get("enabled_tools", {})
        
        system_prompt = self.prompt_manager.get_system_prompt(enabled_map)

        messages = [{
            'role': 'system', 
            'content': system_prompt
        }]
        messages.extend(self.history)
        
        is_plan_approval = "The user approved the plan" in user_text
        
        if not is_hidden:
            messages.append({'role': 'user', 'content': user_text})

        MAX_TURNS = 5
        turn = 0
        has_shown_initial_ui = False
        current_metadata = {}
        accumulated_ui_text = ""
        
        try:
            while turn < MAX_TURNS:
                if self._cancel_event.is_set():
                    break
                turn += 1
                if not has_shown_initial_ui:
                    GLib.idle_add(self.show_spinner)

                full_content = ""
                pending_tool_calls = []
                last_update_time = 0
                
                try:
                    # Check cancellation before stream
                    if self._cancel_event.is_set():
                        break

                    stream = client.stream_response(messages, tools=tools_def)
                    for chunk in stream:
                        if self._cancel_event.is_set():
                            break
                        msg_chunk = chunk.get('message', {})
                        content_chunk = msg_chunk.get('content', '')
                        if msg_chunk.get('tool_calls'):
                            pending_tool_calls.extend(msg_chunk['tool_calls'])
                        if content_chunk:
                            full_content += content_chunk
                            if '<tool_call>' in full_content:
                                streaming_display = re.sub(r'<tool_call>[^<]*(?:</tool_call>|$)', '', full_content, flags=re.DOTALL)
                                streaming_display = re.sub(r'<tool_call.*$', '', streaming_display, flags=re.DOTALL) 
                            else:
                                streaming_display = full_content
                            display_text = accumulated_ui_text + streaming_display
                            
                            if not has_shown_initial_ui:
                                if display_text.strip():
                                    GLib.idle_add(self.replace_spinner_with_msg, "assistant", display_text)
                                    has_shown_initial_ui = True
                                    if current_metadata.get('sources'):
                                        GLib.idle_add(self.add_sources_to_ui, current_metadata['sources'])
                                    if current_metadata.get('artifacts'):
                                        GLib.idle_add(self.add_artifacts_to_ui, current_metadata['artifacts'])
                                    last_update_time = time.time()
                            else:
                                current_time = time.time()
                                if current_time - last_update_time > 0.1:
                                    parsed_display = markdown_to_pango(display_text)
                                    GLib.idle_add(self.update_last_message, display_text, parsed_display)
                                    last_update_time = current_time
                except Exception as e:
                    print(f"[DEBUG] Stream error: {e}")

                clean_content, parsed_calls = ToolCallParser.parse_tool_calls(full_content, project_id=self.chat_data['id'])
                if clean_content.strip():
                    accumulated_ui_text += clean_content + "\n"
                    if has_shown_initial_ui:
                        parsed_acc = markdown_to_pango(accumulated_ui_text)
                        GLib.idle_add(self.update_last_message, accumulated_ui_text, parsed_acc)
                if parsed_calls:
                    pending_tool_calls.extend(parsed_calls)
                
                if not pending_tool_calls:
                    break
                
                # CRITICAL: Stop for plan approval IF a plan is present and this isn't the approval turn
                if "[PLAN]" in (accumulated_ui_text + full_content) and not is_plan_approval:
                    print("[DEBUG] Plan detected, stopping for approval.")
                    break
                
                if not has_shown_initial_ui:
                    GLib.idle_add(self.show_spinner, self.prompt_manager.get("ui.spinner.generating"))
                
                messages.append({'role': 'assistant', 'content': clean_content if clean_content.strip() else None, 'tool_calls': pending_tool_calls})
                all_sources, all_artifacts = [], []
                
                for tool_call in pending_tool_calls:
                    try:
                        fname = tool_call['function']['name']
                        args = tool_call['function']['arguments']
                        
                        # Dynamic Status Update via StatusManager
                        # The tool execution wrapper in ToolManager now handles calling StatusManager
                        # We just need to make sure we are listening to signals.
                        # (Note: Listener is set up in __init__ now)
                        
                        print(f"[DEBUG] Executing tool {fname} with args: {args}")
                        # We don't need to pass a local lambda anymore if ToolManager handles it,
                        # BUT ToolManager passes a wrapper that calls StatusManager.
                        # So we can pass None or just let it do its thing.
                        # Actually, ToolManager expects us to NOT pass it unless we want extra local handling.
                        # We'll rely on the signal.
                        
                        # We'll rely on the signal.
                        
                        # Fix for "multiple values for keyword argument 'project_id'"
                        # We force the project_id from the chat_data to be the authority
                        project_id = self.chat_data["id"]
                        
                        # Remove project_id from args if it exists to avoid double passing
                        if "project_id" in args:
                            del args["project_id"]
                        
                        result = tm.execute_tool(fname, project_id=project_id, **args)
                        
                        sources_matches = re.finditer(r'\[SOURCES\](.*?)\[/SOURCES\]', str(result), re.DOTALL)
                        for match in sources_matches:
                            try: all_sources.extend(json.loads(match.group(1).strip()))
                            except: pass
                        artifact_matches = re.finditer(r'\[ARTIFACT\](.*?)\[/ARTIFACT\]', str(result), re.DOTALL)
                        for match in artifact_matches:
                            try:
                                datum = json.loads(match.group(1).strip())
                                all_artifacts.append(datum)
                                
                                # Auto-refresh preview if web-related files change
                                if datum.get('language') in ['html', 'css', 'javascript']:
                                    root = self.get_native()
                                    if hasattr(root, "artifacts_panel"):
                                        project_dir = os.path.dirname(datum['path'])
                                        GLib.idle_add(root.artifacts_panel.load_project, project_dir)
                                        GLib.idle_add(root.show_artifacts)
                            except: pass
                        messages.append({'role': 'tool', 'tool_call_id': tool_call.get('id', f"call_{fname}_{id(tool_call)}"), 'content': str(result)})
                        print(f"[DEBUG] Tool {fname} returned: {str(result)}")
                    except Exception as te:
                        error_msg = f"Error executing tool {tool_call.get('function', {}).get('name', 'unknown')}: {str(te)}"
                        print(f"[DEBUG] {error_msg}")
                        messages.append({'role': 'tool', 'tool_call_id': tool_call.get('id', f"call_error_{id(tool_call)}"), 'content': error_msg})

                if all_sources: current_metadata['sources'] = all_sources
                if all_artifacts: current_metadata['artifacts'] = all_artifacts
                
                if has_shown_initial_ui:
                    if current_metadata: GLib.idle_add(self.update_last_message_metadata, current_metadata)
                    if all_sources: GLib.idle_add(self.add_sources_to_ui, all_sources)
                    if all_artifacts: GLib.idle_add(self.add_artifacts_to_ui, all_artifacts)

                any_error = False
                for msg in messages:
                    if msg.get('role') == 'tool':
                        if "error" in str(msg.get('content', '')).lower() or "failed" in str(msg.get('content', '')).lower():
                            any_error = True
                            break
                if not any_error:
                    pass # Continue to next turn to let AI process results

            if not has_shown_initial_ui:
                final_text = accumulated_ui_text.strip() or ("" if turn <= 1 else self.prompt_manager.get("ui.spinner.completed"))
                if final_text or current_metadata:
                    parsed_final = markdown_to_pango(final_text) if final_text else None
                    GLib.idle_add(self.replace_spinner_with_msg, "assistant", final_text, current_metadata, parsed_final)
                else:
                    GLib.idle_add(self.remove_spinner)
                if current_metadata.get('sources'): GLib.idle_add(self.add_sources_to_ui, current_metadata['sources'])
                if current_metadata.get('artifacts'): GLib.idle_add(self.add_artifacts_to_ui, current_metadata['artifacts'])
            elif current_metadata:
                GLib.idle_add(self.update_last_message_metadata, current_metadata)

            # Check for plan after the loop ends or if it was interrupted
            combined_text = accumulated_ui_text + full_content
            plan_match = re.search(r'\[PLAN\](.*?)(?:\[/PLAN\]|$)', combined_text, re.DOTALL)
            if plan_match:
                plan_text = plan_match.group(1).strip()
                if plan_text:
                    if 'plan' not in current_metadata:
                        current_metadata['plan'] = plan_text
                        GLib.idle_add(self.update_last_message_metadata, current_metadata)
                    GLib.idle_add(self._refresh_last_bubble_with_plan)

            # Handle Cancellation / User Stop
            if self._cancel_event.is_set():
                print("[DEBUG] User stopped generation.")
                # Mark history as stopped, but do NOT show in UI
                if self.history and self.history[-1]['role'] == 'assistant':
                    self.history[-1]['content'] += " [stopped by user]"
                    self.chat_data['history'] = self.history.copy()
                    self.storage.save_chat(self.chat_data)
                
        except Exception as e:
            GLib.idle_add(self.remove_spinner)
            GLib.idle_add(self._add_message_ui, "system", f"Error: {e}", False)
            # Ensure we save any progress
            self.chat_data['history'] = self.history.copy()
            self.storage.save_chat(self.chat_data)
        finally:
            GLib.idle_add(self.enable_ui)

    def _add_plan_button(self, bubble):
        """Add a plan button to a bubble if not already present."""
        has_button = False
        child = bubble.get_first_child()
        while child:
            if child.has_css_class("plan-button-box"):
                has_button = True
                break
            child = child.get_next_sibling()
            
        if not has_button:
            btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            btn_box.set_margin_top(8)
            btn_box.add_css_class("plan-button-box")
            
            proceed_btn = Gtk.Button(label=self.lang_manager.get("chat.proceed_button"))
            proceed_btn.add_css_class("suggested-action")
            proceed_btn.add_css_class("plan-proceed-button")
            
            def on_click(btn):
                btn.set_sensitive(False)
                btn.set_label(self.lang_manager.get("chat.executing_button"))
                self.on_plan_proceed()
            
            proceed_btn.connect("clicked", on_click)
            btn_box.append(proceed_btn)
            bubble.append(btn_box)

    def _refresh_last_bubble_with_plan(self):
        msg_row = self.chat_box.get_last_child()
        if not msg_row: return
        bubble = msg_row.get_first_child()
        if not bubble: return
        self._add_plan_button(bubble)

    def on_plan_proceed(self):
        self.update_last_message_metadata({'plan_approved': True})
        def run_with_exception_handler():
            try:
                self.run_ai(self.prompt_manager.get("ui.plan_approval_message"))
            except Exception as e:
                traceback.print_exc()
                GLib.idle_add(self.enable_ui)
        thread = threading.Thread(target=run_with_exception_handler, daemon=True)
        thread.start()
