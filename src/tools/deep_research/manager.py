import os
import json
import threading
import asyncio
import time
import gi
gi.require_version('Notify', '0.7')
from gi.repository import Notify, GLib, Gio
from src.tools.deep_research.graph import DeepResearchGraph
from src.core.config import get_artifacts_dir

class BackgroundResearchManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BackgroundResearchManager, cls).__new__(cls)
            Notify.init("com.example.gaia")
            cls._instance.active_tasks = {} # chat_id -> {graph, notification, query}
        return cls._instance

    def start_research(self, query: str, chat_id: str, project_id: str):
        """Starts a background research task."""
        if chat_id in self.active_tasks:
            return "A deep research task is already running for this chat."

        graph = DeepResearchGraph()
        notification = Notify.Notification.new(
            "Deep Research Started",
            f"Topic: {query}",
            "system-search-symbolic" 
        )
        notification.set_hint("desktop-entry", GLib.Variant.new_string("com.example.gaia"))
        notification.set_urgency(Notify.Urgency.NORMAL)
        
        # Add Stop action
        notification.add_action(
            "stop",
            "Stop Research",
            self._on_stop_clicked,
            chat_id
        )

        self.active_tasks[chat_id] = {
            "graph": graph,
            "notification": notification,
            "query": query,
            "project_id": project_id,
            "last_show_time": time.time(),
            "loop": None,
            "task": None
        }

        def status_callback(message, percentage=None):
            GLib.idle_add(self._update_notification, chat_id, message, percentage)

        def run_in_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.active_tasks[chat_id]["loop"] = loop
            
            # Create a task for graph.run
            task = loop.create_task(graph.run(query, status_callback=status_callback))
            self.active_tasks[chat_id]["task"] = task
            
            try:
                final_state = loop.run_until_complete(task)
                loop.close()
                GLib.idle_add(self._on_research_finished, chat_id, final_state)
            except asyncio.CancelledError:
                print(f"Research task for {chat_id} was cancelled.")
                # We still want to call finished to clean up, but with a cancelled state
                GLib.idle_add(self._on_research_finished, chat_id, {"report": "Research cancelled by user."})
            except Exception as e:
                print(f"Error in background research: {e}")
                import traceback
                traceback.print_exc()
                GLib.idle_add(self._on_research_failed, chat_id, str(e))

        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()
        
        # Show initial notification to the user
        notification.show()
        
        return f"Deep Research for '{query}' has started in the background. You'll be notified when the report is ready."

    def stop_research(self, chat_id):
        """Stops a running research task."""
        if chat_id in self.active_tasks:
            task_info = self.active_tasks[chat_id]
            task_info["graph"].cancel() # Set flag just in case
            
            # Directly cancel the asyncio task if it's running
            if task_info["loop"] and task_info["task"]:
                task_info["loop"].call_soon_threadsafe(task_info["task"].cancel)
                print(f"Cancellation command sent to task for {chat_id}")
            return True
        return False

    def _update_notification(self, chat_id, message, percentage):
        if chat_id not in self.active_tasks:
            return False
            
        task = self.active_tasks[chat_id]
        notification = task["notification"]
        
        title = f"Researching: {percentage}%" if percentage is not None else "Research Progress"
        notification.update(title, f"{task['query']}\n{message}", "system-search-symbolic")
        
        # We don't call show() every time to avoid excessive 'toast' animations in GNOME
        # But we show it if it's been a while to keep it relevant if it was dismissed
        now = time.time()
        if now - task.get("last_show_time", 0) > 10: # Refresh toast every 10s
            try:
                notification.show()
                task["last_show_time"] = now
            except: pass
        return False

    def _on_stop_clicked(self, notification, action_name, chat_id):
        self.stop_research(chat_id)
        notification.close()

    def _on_research_finished(self, chat_id, final_state):
        if chat_id not in self.active_tasks:
            return
            
        task = self.active_tasks[chat_id]
        query = task["query"]
        project_id = task["project_id"]
        
        # If cancelled, show cancellation notification
        if final_state.get("report") == "Research cancelled by user.":
            n = Notify.Notification.new("Research Cancelled", f"Task for '{query}' was stopped.", "process-stop-symbolic")
            n.show()
            del self.active_tasks[chat_id]
            return

        # Success!
        # Generate the HTML file (we need to duplicate some logic from tool.py unfortunately, or factor it out)
        from src.tools.deep_research.tool_utils import save_report_artifact
        
        report_md = final_state.get("report", "Error: No report generated.")
        artifact_data = save_report_artifact(
            report_md, 
            query, 
            project_id, 
            final_state.get("notes", []),
            images=final_state.get("images", [])
        )
        
        # Cleanup
        task["notification"].close()
        
        # Auto-open in Gaia UI (now also handles the success notification for perfect sync)
        GLib.idle_add(self._trigger_ui_open, artifact_data, query, chat_id)
        
        del self.active_tasks[chat_id]

    def _trigger_ui_open(self, artifact_data, query, chat_id):
        """Find the main window and tell it to show the artifact."""
        try:
            # Calculate relative path for the AI (make it easier to file_editor)
            # path is: ~/.gaia/artifacts/{project_id}/...
            # We want relative to artifact root for that project
            import os
            from src.core.config import get_artifacts_dir
            project_artifacts = os.path.join(get_artifacts_dir(), chat_id)
            try:
                rel_path = os.path.relpath(artifact_data['path'], project_artifacts)
            except:
                 rel_path = artifact_data['filename'] # Fallback
            
            # 1. Notify user of completion exactly when we open the artifact
            success_notification = Notify.Notification.new(
                "Deep Research Complete!",
                f"Report on '{query}' is ready in the Artifact Panel.\nPath: {rel_path}",
                "emblem-documents-symbolic" # Documentation icon
            )
            success_notification.set_hint("desktop-entry", GLib.Variant.new_string("com.example.gaia"))
            success_notification.show()

            # 2. Open the artifact in the UI
            app = Gio.Application.get_default()
            if not app: return
            
            # 2. Open the artifact in the UI
            app = Gio.Application.get_default()
            if not app: return
            
            win = app.get_active_window()
            if win:
                # Update Artifacts Panel
                if hasattr(win, "artifacts_panel"):
                    win.artifacts_panel.load_artifact(artifact_data['path'], artifact_data['language'])
                    win.show_artifacts()
                
                # Update Chat Persistence
                if hasattr(win, "chat_pages") and chat_id in win.chat_pages:
                    chat_page = win.chat_pages[chat_id]
                    # Save persistence
                    chat_page.update_last_message_metadata({'artifacts': [artifact_data]})
                    # Update Live UI
                    chat_page.add_artifacts_to_ui([artifact_data])
                    
        except Exception as e:
            print(f"Error auto-opening artifact: {e}")

    def _on_research_failed(self, chat_id, error_msg):
        if chat_id not in self.active_tasks:
            return
            
        task = self.active_tasks[chat_id]
        n = Notify.Notification.new("Research Failed", f"Task for '{task['query']}' failed: {error_msg}", "dialog-error-symbolic")
        n.show()
        
        task["notification"].close()
        del self.active_tasks[chat_id]
