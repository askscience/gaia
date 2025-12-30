import gi
import json
import threading

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Gio, GLib, Gdk

from src.core.chat_storage import ChatStorage
from src.ui.artifacts.panel import ArtifactsPanel


class ChatPage(Gtk.Box):
    """A single chat page containing the chat UI."""
    
    def __init__(self, chat_data: dict, storage: ChatStorage, lazy_loading: bool = False, *args, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, *args, **kwargs)
        
        self.chat_data = chat_data
        self.storage = storage
        self.history = chat_data.get('history', [])
        self.lazy_loading = lazy_loading
        
        self.loaded_messages = 0
        self.max_visible_messages = 100
        self.batch_size = 20
        self._markdown_cache_size_limit = 200
        self._markdown_cache = {}
        self._markdown_cache_order = []
        self._deferred_sources_artifacts = []  # Store sources/artifacts to add later
        
        # Watch for tab changes to clean up resources
        self.connect("unmap", self._on_unmap)
        
        # Storage save throttling for streaming
        self._save_pending = False
        self._save_timeout_id = None
        
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
        self.entry.set_placeholder_text("Type a message...")
        self.entry.connect("activate", self.on_entry_activate)
        self.input_box.append(self.entry)
        
        self.send_button = Gtk.Button()
        self.send_button.set_icon_name("mail-send-symbolic")
        self.send_button.set_tooltip_text("Send")
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
        import time
        from src.ui.utils import markdown_to_pango
        
        batch_size = self.batch_size
        total_messages = len(self.history)
        
        # Only load the most recent max_visible_messages messages for performance
        start_index = max(0, total_messages - self.max_visible_messages)
        self.loaded_messages = start_index
        
        while self.loaded_messages < total_messages:
            start = self.loaded_messages
            end = min(start + batch_size, total_messages)
            
            # Prepare batch data with markdown parsed in background thread
            batch_messages = []
            for i in range(start, end):
                msg = self.history[i]
                metadata = msg.get('metadata')
                content = msg['content']
                
                # Parse markdown in background thread with LRU caching
                if content not in self._markdown_cache:
                    self._markdown_cache[content] = markdown_to_pango(content)
                    self._markdown_cache_order.append(content)
                    # Prune cache if it exceeds limit
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
            
            # Schedule UI update on main thread
            GLib.idle_add(self._add_batch_to_ui, batch_messages)
            
            # Small sleep to prevent overwhelming the UI
            time.sleep(0.003)
        
        # All loaded, scroll to bottom on main thread
        GLib.idle_add(self._scroll_to_bottom)
        # Add sources and artifacts after all messages loaded
        GLib.idle_add(self._add_deferred_artifacts)
    
    def _add_batch_to_ui(self, batch_messages):
        """Add a batch of messages to the UI (runs on main thread)."""
        # Check if UI is still valid to avoid updates on closed tabs
        if not hasattr(self, 'chat_box') or not self.chat_box:
            return
            
        for role, parsed_content, original_content, metadata, has_sources, has_artifacts, sources, artifacts in batch_messages:
            # Create message with pre-parsed markdown
            self._add_message_with_parsed_content(role, parsed_content, original_content, metadata=metadata, save=False, scroll=False)
            # Defer sources/artifacts for smoother initial load
            if has_sources and sources:
                self._deferred_sources_artifacts.append(('sources', sources))
            if has_artifacts and artifacts:
                self._deferred_sources_artifacts.append(('artifacts', artifacts))
                
        # Force a UI update to show progress
        return False
    
    def _add_deferred_artifacts(self):
        """Add deferred sources and artifacts after all messages are loaded."""
        for art_type, data in self._deferred_sources_artifacts:
            if art_type == 'sources':
                self.add_sources_to_ui(data)
            elif art_type == 'artifacts':
                self.add_artifacts_to_ui(data)
        self._deferred_sources_artifacts.clear()
        return False
    
    def _on_unmap(self, widget):
        """Clean up resources when page is unmapped (e.g., switching tabs)."""
        # Cancel any pending saves
        if self._save_timeout_id:
            GLib.source_remove(self._save_timeout_id)
            self._save_timeout_id = None
        
        # Save pending changes if any
        if self._save_pending:
            self._do_save()
        
        # Clear markdown cache to free memory
        self._markdown_cache.clear()
        self._markdown_cache_order.clear()
        return False
    
    def _schedule_save(self):
        """Schedule a throttled save operation."""
        if not self._save_pending:
            self._save_pending = True
        
        # Cancel any existing timeout
        if self._save_timeout_id:
            GLib.source_remove(self._save_timeout_id)
        
        # Schedule save with a delay to batch rapid updates
        self._save_timeout_id = GLib.timeout_add(2000, self._do_save)
    
    def _do_save(self):
        """Actually save to storage."""
        if not self._save_pending:
            return False
        
        try:
            # Only save if chat has been persisted (first message sent)
            if not self.chat_data.get('_is_persisted', True):
                # Still unsaved (no messages), skip
                self._save_pending = False
                self._save_timeout_id = None
                return False
            
            # Update chat_data with current history and save
            self.chat_data['history'] = self.history.copy()
            self.storage.save_chat(self.chat_data)
        except Exception as e:
            print(f"[DEBUG] Error saving chat: {e}")
        
        self._save_pending = False
        self._save_timeout_id = None
        return False
    
    def on_entry_activate(self, entry):
        self.on_send_clicked(entry)

    def on_send_clicked(self, button):
        print("[DEBUG on_send_clicked] Called!")
        text = self.entry.get_text().strip()
        if not text:
            print("[DEBUG on_send_clicked] Empty text, returning")
            return
        
        print(f"[DEBUG on_send_clicked] Text: {text}")
        self.entry.set_sensitive(False)
        self.send_button.set_sensitive(False)
        
        self.add_message("user", text)
        self.entry.set_text("")
        
        # Run AI in background with exception handling
        import threading
        import traceback
        
        def run_with_exception_handler():
            try:
                print("[DEBUG thread] Starting run_ai...")
                self.run_ai(text)
                print("[DEBUG thread] run_ai completed.")
            except Exception as e:
                print(f"[DEBUG thread] EXCEPTION in run_ai: {e}")
                traceback.print_exc()
                GLib.idle_add(self.enable_ui)
        
        thread = threading.Thread(target=run_with_exception_handler)
        thread.daemon = True
        thread.start()
        print("[DEBUG on_send_clicked] Thread started")

    def enable_ui(self):
        self.entry.set_sensitive(True)
        self.send_button.set_sensitive(True)
        self.entry.grab_focus()

    def add_message(self, role: str, text: str, metadata: dict = None, parsed_text: str = None):
        """Add a message, save to storage, and update UI."""
        # Defensive filter: never save tool call XML to history
        if '<tool_call>' in text:
            text = text.split('<tool_call>')[0].strip()
        
        # Persist unsaved chats on first message
        if not self.chat_data.get('_is_persisted', True):
            self.chat_data['_is_persisted'] = True
            self.storage.save_chat(self.chat_data)
            print(f"[DEBUG] Chat {self.chat_data['id']} persisted on first message")
        
        # Update local history
        msg = {'role': role, 'content': text}
        if metadata:
            msg['metadata'] = metadata
        self.history.append(msg)
        
        # Schedule throttled save instead of immediate save
        self._schedule_save()
        
        # Update UI
        self._add_message_ui(role, text, metadata=metadata, save=False, parsed_text=parsed_text)
    
    def _add_message_ui(self, role: str, text: str, metadata: dict = None, save: bool = True, scroll: bool = True, parsed_text: str = None):
        """Add a message bubble to the chat UI."""
        from src.ui.utils import markdown_to_pango
        if parsed_text is None:
            parsed_text = markdown_to_pango(text)
        return self._add_message_with_parsed_content(role, parsed_text, text, metadata, save, scroll)
    
    def _add_message_with_parsed_content(self, role: str, parsed_text: str, original_text: str, metadata: dict = None, save: bool = True, scroll: bool = True):
        """Add a message bubble to the chat UI with pre-parsed markdown (optimized for batch loading)."""
        # Create message row
        msg_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        msg_row.add_css_class("message-row")
        
        if role == "user":
            msg_row.set_halign(Gtk.Align.END)
        else:
            msg_row.set_halign(Gtk.Align.START)
        
        # Create bubble
        bubble = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        bubble.add_css_class("message-bubble")
        
        if role == "user":
            bubble.add_css_class("user-message")
        else:
            bubble.add_css_class("ai-message")
        
        # Message label
        msg_label = Gtk.Label()
        msg_label.set_use_markup(True)
        msg_label.set_markup(parsed_text)
        msg_label.set_wrap(True)
        msg_label.set_max_width_chars(50)
        msg_label.set_xalign(0)
        msg_label.set_selectable(True)
        
        bubble.append(msg_label)
        
        # Add inline Proceed button if a plan is present
        if metadata and 'plan' in metadata:
            btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            btn_box.set_margin_top(8)
            btn_box.add_css_class("plan-button-box")
            
            proceed_btn = Gtk.Button(label="Proceed with Plan")
            proceed_btn.add_css_class("suggested-action")
            proceed_btn.add_css_class("plan-proceed-button")
            
            def on_click(btn):
                btn.set_sensitive(False)
                btn.set_label("Executing...")
                self.on_plan_proceed()
            
            proceed_btn.connect("clicked", on_click)
            btn_box.append(proceed_btn)
            bubble.append(btn_box)

        msg_row.append(bubble)
        
        self.chat_box.append(msg_row)
        if scroll:
            self._scroll_to_bottom()
        
        return msg_label
    
    def _scroll_to_bottom(self):
        """Scroll chat to the bottom."""
        def do_scroll():
            adj = self.scrolled.get_vadjustment()
            if adj:
                adj.set_value(adj.get_upper() - adj.get_page_size())
            return False
        GLib.idle_add(do_scroll)

    def update_last_message(self, text: str, parsed_text: str = None):
        """Update the last AI message during streaming.
        
        Args:
            text: The raw text content.
            parsed_text: Optional pre-parsed Pango markup. If provided, avoids main-thread parsing.
        """
        from src.ui.utils import markdown_to_pango
        
        # Defensive filter: strip any tool call XML that might sneak through
        if '<tool_call>' in text:
            text = text.split('<tool_call>')[0].strip()
        
        child = self.chat_box.get_last_child()
        
        # Search backwards for the actual message row (skipping sources/artifacts/spinners)
        # This fixes the truncation bug when sources are appended *after* the text bubble
        while child:
            if child.has_css_class("message-row"):
                break
            child = child.get_prev_sibling()
            
        if not child:
            return

        # Find the last message label
        def find_label(widget):
            if isinstance(widget, Gtk.Label): return widget
            if hasattr(widget, 'get_first_child'):
                child = widget.get_first_child()
                while child:
                    res = find_label(child)
                    if res: return res
                    child = child.get_next_sibling()
            return None

        label = find_label(child)
        if label:
            # Parse markdown only if not provided
            if parsed_text is None:
                parsed_text = markdown_to_pango(text)
            
            label.set_markup(parsed_text)
            
            # Dynamic Proceed Button: Check if we need to add the button during streaming
            # Logic: If [/PLAN] is in text AND button is not already in bubble
            if "[/PLAN]" in text:
                bubble = label.get_parent()
                # Check if button box already exists
                has_button = False
                child_iter = bubble.get_first_child()
                while child_iter:
                    if child_iter.has_css_class("plan-button-box"):
                        has_button = True
                        break
                    child_iter = child_iter.get_next_sibling()
                
                if not has_button:
                    # Add the button dynamically
                    btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
                    btn_box.set_margin_top(8)
                    btn_box.add_css_class("plan-button-box")
                    
                    proceed_btn = Gtk.Button(label="Proceed with Plan")
                    proceed_btn.add_css_class("suggested-action")
                    proceed_btn.add_css_class("plan-proceed-button")
                    
                    def on_click(btn):
                        btn.set_sensitive(False)
                        btn.set_label("Executing...")
                        self.on_plan_proceed()
                    
                    proceed_btn.connect("clicked", on_click)
                    btn_box.append(proceed_btn)
                    bubble.append(btn_box)
                    
                    # Update metadata so it persists after restart
                    self.update_last_message_metadata({'plan': True})
        
        # Update history and schedule throttled save
        if self.history and self.history[-1]['role'] == 'assistant':
            self.history[-1]['content'] = text
            # Use throttled save to avoid disk I/O on every streaming update
            self._schedule_save()
        
        self._scroll_to_bottom()
    def update_last_message_metadata(self, metadata: dict):
        """Update metadata of the last message in storage."""
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

    def show_spinner(self, text: str = "Thinking..."):
        if hasattr(self, 'spinner_box') and self.spinner_box:
            # Update existing spinner text
            child = self.spinner_box.get_first_child()
            while child:
                if isinstance(child, Gtk.Label):
                    child.set_text(text)
                    return
                child = child.get_next_sibling()
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
        """Add source cards to the chat UI."""
        from src.ui.widgets import SourceCard
        
        # Main container (Vertical)
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main_box.set_spacing(8)
        main_box.set_margin_top(12)
        main_box.set_margin_bottom(12)
        main_box.set_hexpand(True) # IMPORTANT for responsiveness
        main_box.add_css_class("sources-container")
        
        # Header
        header = Gtk.Label(label="Sources")
        header.add_css_class("dim-label")
        header.set_halign(Gtk.Align.START)
        header.set_margin_start(4)
        main_box.append(header)
        
        # Grid (Responsive FlowBox)
        flowbox = Gtk.FlowBox()
        flowbox.set_valign(Gtk.Align.START)
        flowbox.set_halign(Gtk.Align.FILL) # Fill width
        flowbox.set_hexpand(True) 
        flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        flowbox.set_row_spacing(10)
        flowbox.set_column_spacing(10)
        
        # Determine columns based on available space is automatic with FlowBox 
        # given that SourceCards have a minimum width (set in widgets.py)
        # We allow up to 4 columns on very wide screens
        flowbox.set_max_children_per_line(10) 
        flowbox.set_min_children_per_line(1)
        
        for source in sources:
            card = SourceCard(
                title=source.get('title', 'Untitled'),
                url=source.get('url', ''),
                snippet=source.get('snippet', ''),
                image_url=source.get('image_url'),
                favicon_url=source.get('favicon_url')
            )
            # No need to set hexpand on card for FlowBox, it handles it
            flowbox.append(card)
        
        main_box.append(flowbox)
        
        # Add to chat box (left aligned like AI)
        msg_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        msg_row.set_halign(Gtk.Align.FILL) # Fill width for grid
        msg_row.set_margin_start(40) # Align with AI message bubble
        msg_row.set_margin_end(40)   # Right margin too
        msg_row.append(main_box)
        
        self.chat_box.append(msg_row)
        self._scroll_to_bottom()

    def add_artifacts_to_ui(self, artifacts: list):
        """Add artifact cards to the chat UI."""
        from src.ui.widgets import ProjectCard, ArtifactCard
        
        artifacts_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        artifacts_box.set_spacing(6)
        artifacts_box.set_margin_top(12)
        artifacts_box.set_margin_bottom(12)
        
        # Check if we have a project (multiple files or HTML)
        has_web = any(art.get('language') == 'html' for art in artifacts)
        
        if has_web:
            # Add Project Card first if it's a website
            # For now, we'll use the directory of the first artifact
            import os
            first_path = artifacts[0].get('path')
            if first_path:
                project_dir = os.path.dirname(first_path)
                index_path = next((art.get('path') for art in artifacts if art.get('filename') == 'index.html'), first_path)
                # Pass all artifacts to the project card
                project_card = ProjectCard("Website Project", project_dir, index_path, artifacts=artifacts)
                artifacts_box.append(project_card)
        else:
            # Only add individual file cards if NOT a web project (or add mixed logic later)
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
        msg_row.set_margin_top(16) # Ensure visual separation from text bubble
        msg_row.append(artifacts_box)
        
        self.chat_box.append(msg_row)
        self._scroll_to_bottom()
 
        self._scroll_to_bottom()

    def run_ai(self, user_text: str, is_hidden: bool = False):
        from src.core.ai_client import AIClient
        from src.tools.manager import ToolManager
        import re
        import json
        import time
        from src.core.tool_call_parser import ToolCallParser
        
        client = AIClient()
        tm = ToolManager()
        tm.load_tools()
        
        tools_def = tm.get_ollama_tools_definitions()
        print(f"[DEBUG run_ai] Tool definitions: {len(tools_def)} tools")
        
        # Prepare messages
        messages = []
        messages.append({
            'role': 'system', 
            'content': (
                "You are Dust AI, a helpful assistant for building web projects. "
                "You have access to these tools:\n\n"
                "TOOL CALLING FORMAT:\n"
                "<tool_call>tool_name<arg_key>param</arg_key><arg_value>value</arg_value></tool_call>\n\n"
                "AVAILABLE TOOLS:\n\n"
                "1. web_builder - Create/overwrite files\n"
                "   Parameters: filename, code\n"
                "   Example: <tool_call>web_builder<arg_key>filename</arg_key><arg_value>index.html</arg_value>"
                "<arg_key>code</arg_key><arg_value><!DOCTYPE html>...</arg_value></tool_call>\n\n"
                "2. file_reader - Read file contents\n"
                "   Parameters: filename\n"
                "   Example: <tool_call>file_reader<arg_key>filename</arg_key><arg_value>style.css</arg_value></tool_call>\n\n"
                "3. file_editor - Edit files with search/replace\n"
                "   Parameters: filename, search, replace\n"
                "   Example: <tool_call>file_editor<arg_key>filename</arg_key><arg_value>style.css</arg_value>"
                "<arg_key>search</arg_key><arg_value>old text</arg_value>"
                "<arg_key>replace</arg_key><arg_value>new text</arg_value></tool_call>\n\n"
                "4. file_list - List all project files\n"
                "   Example: <tool_call>file_list</tool_call>\n\n"
                "CRITICAL RULES:\n"
                "1. BEFORE creating/editing files, you MUST proposed a plan using `[PLAN] description [/PLAN]`.\n"
                "   - Wait for the user to click 'Proceed' (which sends you a confirmation message) before executing the plan with tools.\n"
                "   - Do NOT call `web_builder` or `file_editor` in the same response as the plan.\n"
                "2. ALWAYS use `file_reader` to read a file BEFORE using `file_editor` on it.\n"
                "3. The `search` parameter in `file_editor` must match the file content EXACTLY.\n"
                "4. Use `web_builder` to overwrite/create new files.\n"
                "5. Tool call tags will be hidden from user - just use them.\n"
            )
        })
        
        # Add history
        messages.extend(self.history)
        if not is_hidden:
            messages.append({'role': 'user', 'content': user_text})

        # --- RECURSIVE EXECUTION LOOP ---
        MAX_TURNS = 5
        turn = 0
        has_shown_initial_ui = False
        current_metadata = {}
        accumulated_ui_text = ""
        
        try:
            while turn < MAX_TURNS:
                turn += 1
                print(f"[DEBUG] Starting Turn {turn}")
                
                # Show spinner if not already showing text
                if not has_shown_initial_ui:
                    GLib.idle_add(self.show_spinner)

                full_content = ""
                pending_tool_calls = []
                last_update_time = 0
                
                try:
                    # Stream response
                    stream = client.stream_response(messages, tools=tools_def)
                    
                    for chunk in stream:
                        msg_chunk = chunk.get('message', {})
                        content_chunk = msg_chunk.get('content', '')
                        
                        if msg_chunk.get('tool_calls'):
                            pending_tool_calls.extend(msg_chunk['tool_calls'])

                        if content_chunk:
                            full_content += content_chunk
                            
                            # Real-time filter: hide tool call XML (streaming friendly)
                            # Remove complete tags and partial tags at end of string
                            streaming_display = re.sub(r'<tool_call>[^<]*(?:</tool_call>|$)', '', full_content, flags=re.DOTALL)
                            # Handle partial open tags like "<tool"
                            streaming_display = re.sub(r'<tool_call.*$', '', streaming_display, flags=re.DOTALL) 
                            
                            # Combine with history from previous turns
                            display_text = accumulated_ui_text + streaming_display
                            
                            if not has_shown_initial_ui:
                                if display_text.strip():
                                    GLib.idle_add(self.replace_spinner_with_msg, "assistant", display_text)
                                    has_shown_initial_ui = True
                                    
                                    # FLUSH BUFFERED SOURCES/ARTIFACTS from previous turns
                                    if current_metadata.get('sources'):
                                        GLib.idle_add(self.add_sources_to_ui, current_metadata['sources'])
                                    if current_metadata.get('artifacts'):
                                        GLib.idle_add(self.add_artifacts_to_ui, current_metadata['artifacts'])
                                    last_update_time = time.time()
                            else:
                                # Update existing bubble
                                current_time = time.time()
                                if current_time - last_update_time > 0.05:
                                    # Pre-parse markdown in background thread
                                    from src.ui.utils import markdown_to_pango
                                    parsed_display = markdown_to_pango(display_text)

                                    GLib.idle_add(self.update_last_message, display_text, parsed_display)
                                    last_update_time = current_time

                except Exception as e:
                    print(f"[DEBUG] Stream error: {e}")
                    import traceback
                    traceback.print_exc()

                # Parse & Clean final content for this turn
                clean_content, parsed_calls = ToolCallParser.parse_tool_calls(
                    full_content,
                    project_id=self.chat_data['id']
                )
                
                if clean_content.strip():
                    accumulated_ui_text += clean_content + "\n"
                    # Force update to ensure clean state is shown
                    if has_shown_initial_ui:
                        # Pre-parse for accumulated update
                        from src.ui.utils import markdown_to_pango
                        parsed_accumulated = markdown_to_pango(accumulated_ui_text)
                        GLib.idle_add(self.update_last_message, accumulated_ui_text, parsed_accumulated)
                
                if parsed_calls:
                    pending_tool_calls.extend(parsed_calls)
                
                # --- DECISION POINT ---
                
                if not pending_tool_calls:
                    # No tools -> We are done
                    print(f"[DEBUG] Turn {turn} finished with no tools. Exiting loop.")
                    break
                
                # We have tools -> Execute and Loop
                print(f"[DEBUG] Turn {turn}: Executing {len(pending_tool_calls)} tools")
                
                # Update UI to prevent empty bubble/spinner confusion
                if not has_shown_initial_ui:
                    # Show spinner with descriptive text
                    feature_name = "Executing tools..." # default
                    if pending_tool_calls:
                         # Get first tool name for status
                         first_tool = pending_tool_calls[0]['function']['name']
                         readable_tools = {
                             "web_builder": "Building web pages...",
                             "file_reader": "Reading files...",
                             "file_editor": "Editing files...", 
                             "file_list": "Scanning directory...",
                             "web_search": "Searching the web...",
                             "get_current_time": "Checking time..."
                         }
                         feature_name = readable_tools.get(first_tool, f"Running {first_tool}...")

                    GLib.idle_add(self.show_spinner, feature_name)
                
                # Add assistant message with tool calls to history
                assistant_msg = {
                    'role': 'assistant',
                    'content': clean_content if clean_content.strip() else None,
                    'tool_calls': pending_tool_calls
                }
                messages.append(assistant_msg)
                
                # Execute Tools
                all_sources = []
                all_artifacts = []
                
                for tool_call in pending_tool_calls:
                    fname = tool_call['function']['name']
                    args = tool_call['function']['arguments']
                    
                    if fname in ["web_builder", "file_reader", "file_editor", "file_list"]:
                        args["project_id"] = self.chat_data["id"]
                    
                    print(f"[DEBUG] Executing tool: {fname}")
                    result = tm.execute_tool(fname, **args)
                    
                    # Extract Sources/Artifacts
                    sources_matches = re.finditer(r'\[SOURCES\](.*?)\[/SOURCES\]', str(result), re.DOTALL)
                    for match in sources_matches:
                        try: all_sources.extend(json.loads(match.group(1).strip()))
                        except: pass

                    artifact_matches = re.finditer(r'\[ARTIFACT\](.*?)\[/ARTIFACT\]', str(result), re.DOTALL)
                    for match in artifact_matches:
                        try:
                            datum = json.loads(match.group(1).strip())
                            all_artifacts.append(datum)
                            if datum.get('language') == 'html':
                                root = self.get_native()
                                if hasattr(root, "artifacts_panel"):
                                    GLib.idle_add(root.artifacts_panel.load_project, datum['path'])
                                    GLib.idle_add(root.show_artifacts)
                        except: pass
                    
                    messages.append({
                        'role': 'tool',
                        'tool_call_id': tool_call.get('id', f"call_{fname}_{id(tool_call)}"),
                        'content': str(result)
                    })

                # Update Metadata
                if all_sources: current_metadata['sources'] = all_sources
                if all_artifacts: current_metadata['artifacts'] = all_artifacts
                
                # Handling UI Updates with correct ordering (Text -> Sources)
                if has_shown_initial_ui:
                     # Text bubble already exists, safe to append sources/artifacts below it
                    if current_metadata:
                        GLib.idle_add(self.update_last_message_metadata, current_metadata)
                    if all_sources: 
                        GLib.idle_add(self.add_sources_to_ui, all_sources)
                    if all_artifacts: 
                        GLib.idle_add(self.add_artifacts_to_ui, all_artifacts)
                else:
                    # Text bubble doesn't exist yet (spinning). 
                    # Buffer metadata/sources to flush LATER when the text bubble is created.
                    # This prevents sources from appearing above the text.
                    pass 

                # --- USER TURN LIMIT LOGIC ---
                # "use only one turn, use second turn ONLY in case the tool failed"
                # If we executed tools, we check if any failed.
                # If all succeeded, we break the loop so the AI doesn't perform a "summary" turn.
                any_error = False
                for msg in messages:
                    if msg.get('role') == 'tool':
                        content = str(msg.get('content', '')).lower()
                        if "error" in content or "failed" in content:
                            any_error = True
                            break
                
                if not any_error:
                    print(f"[DEBUG] Turn {turn} tool execution successful. Breaking loop as requested.")
                    # IMPORTANT: We break early here to satisfy the user request for "ONLY ONE TURN".
                    # This means the AI won't see the tool output to generate a text summary.
                    break
            # --- END OF LOOP ---
            
            # Handle Final UI State
            if not has_shown_initial_ui:
                # If we are here, we finished the loop but haven't shown the text bubble yet.
                # This happens if response was only tools, or if everything was buffered.
                
                final_text = accumulated_ui_text.strip()
                if not final_text and turn > 1:
                     final_text = "✓ Task completed"
                
                # Now we flush everything: Text -> Metadata -> Sources/Artifacts
                
                # 1. Create the text bubble (removes spinner)
                if final_text or current_metadata:
                     # Pre-parse final text
                     from src.ui.utils import markdown_to_pango
                     parsed_final = markdown_to_pango(final_text) if final_text else None
                     GLib.idle_add(self.replace_spinner_with_msg, "assistant", final_text, current_metadata, parsed_final)
                else:
                     GLib.idle_add(self.remove_spinner)
                
                # 2. Flush buffered sources/artifacts (will appear BELOW the new text bubble)
                if current_metadata.get('sources'):
                    GLib.idle_add(self.add_sources_to_ui, current_metadata['sources'])
                if current_metadata.get('artifacts'):
                    GLib.idle_add(self.add_artifacts_to_ui, current_metadata['artifacts'])

            elif current_metadata:
                  # If UI was already shown, just update metadata if pending
                  GLib.idle_add(self.update_last_message_metadata, current_metadata)

            # Robust Plan Detection
            plan_match = re.search(r'\[PLAN\](.*?)(?:\[/PLAN\]|$)', accumulated_ui_text + full_content, re.DOTALL)
            if plan_match:
                plan_text = plan_match.group(1).strip()
                if plan_text:
                    if 'plan' not in current_metadata:
                        current_metadata['plan'] = plan_text
                        GLib.idle_add(self.update_last_message_metadata, current_metadata)
                    GLib.idle_add(self._refresh_last_bubble_with_plan, plan_text)

        except Exception as e:
            GLib.idle_add(self.remove_spinner)
            GLib.idle_add(self._add_message_ui, "system", f"Error: {e}", False)
        finally:
            GLib.idle_add(self.enable_ui)

    def _refresh_last_bubble_with_plan(self, plan_text):
        """Append the Proceed button to the last bubble if it just got a plan."""
        # Find the last assistant bubble
        msg_row = self.chat_box.get_last_child()
        if not msg_row: return
        
        # Dig into message row -> bubble
        bubble = msg_row.get_first_child()
        if not bubble: return
        
        # Check if button already exists
        child = bubble.get_first_child()
        while child:
            if child.has_css_class("plan-button-box"):
                return
            child = child.get_next_sibling()
            
        # Add the button
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        btn_box.set_margin_top(8)
        btn_box.add_css_class("plan-button-box")
        
        proceed_btn = Gtk.Button(label="Proceed with Plan")
        proceed_btn.add_css_class("suggested-action")
        proceed_btn.add_css_class("plan-proceed-button")
        
        def on_click(btn):
            btn.set_sensitive(False)
            btn.set_label("Executing...")
            self.on_plan_proceed()
        
        proceed_btn.connect("clicked", on_click)
        btn_box.append(proceed_btn)
        bubble.append(btn_box)

    def on_plan_proceed(self):
        """Handle clicking the inline Proceed button."""
        # Send a confirmation to AI (no is_hidden parameter exists)
        self.add_message("user", "Proceed with the plan.")
        # Re-run AI to execute those tools
        import threading
        import traceback
        
        def run_with_exception_handler():
            try:
                self.run_ai("The user approved the plan. Please call the tools now.")
            except Exception as e:
                print(f"[DEBUG thread] EXCEPTION in run_ai: {e}")
                traceback.print_exc()
                GLib.idle_add(self.enable_ui)
        
        thread = threading.Thread(target=run_with_exception_handler)
        thread.daemon = True
        thread.start()


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, storage: ChatStorage, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.set_title("Gaia")
        self.set_default_size(800, 600)
        
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
        self.new_chat_button.set_tooltip_text("New Chat")
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
        self.artifacts_button.set_icon_name("document-open-recent-symbolic")
        self.artifacts_button.set_tooltip_text("Show Artifacts")
        self.artifacts_button.connect("toggled", self.on_artifacts_toggled)
        self.header_bar.pack_end(self.artifacts_button)

        # Tab Overview Button (4-squares icon, to the left of menu)
        self.tab_overview_button = Gtk.Button()
        self.tab_overview_button.set_icon_name("view-grid-symbolic")
        self.tab_overview_button.set_tooltip_text("View All Chats")
        self.tab_overview_button.set_action_name("overview.open")
        self.header_bar.pack_end(self.tab_overview_button)
        
        # Actions
        action = Gio.SimpleAction.new("preferences", None)
        action.connect("activate", self.on_preferences_action)
        self.add_action(action)
        menu.append("Settings", "win.preferences")
        
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
        print(f"[DEBUG] _create_initial_chat called, _creating_chat={self._creating_chat}")
        if not self._creating_chat:
            self._creating_chat = True
            # Create unsaved chat - will be persisted on first message
            chat = self.storage.create_chat(save=False)
            print(f"[DEBUG] Created initial chat: {chat['id']} (unsaved)")
            self._add_chat_tab(chat)
            self._creating_chat = False

    def _load_existing_chats(self):
        """Load existing chat data - create tabs for all but lazy-load only active one."""
        def load_in_thread():
            try:
                # Heavy IO: List all chats
                chats = self.storage.list_chats()
                print(f"[DEBUG] _load_existing_chats: found {len(chats)} chats")
                
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
            # print(f"[DEBUG] Creating tab for chat: {chat['id']}")
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
        tab_page.set_title(chat.get('title', 'New Chat'))
        tab_page.set_icon(Gio.ThemedIcon.new("user-available-symbolic"))
        
        return tab_page
    
    def create_new_chat(self) -> Adw.TabPage:
        """Create a new chat and add it as a tab."""
        print(f"[DEBUG] create_new_chat called, _creating_chat={self._creating_chat}")
        if self._creating_chat:
            print("[DEBUG] create_new_chat: blocked by flag")
            return None
        
        self._creating_chat = True
        try:
            # Create unsaved chat - will be persisted on first message
            chat = self.storage.create_chat(save=False)
            print(f"[DEBUG] create_new_chat: created {chat['id']} (unsaved)")
            tab_page = self._add_chat_tab(chat)
            self.tab_view.set_selected_page(tab_page)
            return tab_page
        finally:
            self._creating_chat = False

    def on_preferences_action(self, action, param):
        from src.ui.settings import SettingsWindow
        settings = SettingsWindow(parent=self)
        settings.present()
    
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
        print(f"[DEBUG] _create_chat_if_empty: pages={self.tab_view.get_n_pages()}, _creating_chat={self._creating_chat}")
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

