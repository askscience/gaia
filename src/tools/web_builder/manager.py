import asyncio
import threading
import time
import json
import gi
gi.require_version('Notify', '0.7')
from gi.repository import Notify, GLib, Gio
from src.tools.web_builder.graph import WebBuilderGraph
from src.core.config import get_artifacts_dir
from src.core.status.manager import StatusManager

class BackgroundWebBuilderManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BackgroundWebBuilderManager, cls).__new__(cls)
            Notify.init("io.github.askscience.gaia")
            cls._instance.active_tasks = {} # project_id -> {graph, notification, description, ...}
        return cls._instance

    def create_plan(self, description: str, project_id: str):
        """
        Creates a plan synchronously (from the caller's perspective) but runs async internally.
        Stores the plan in pending state.
        """
        graph = WebBuilderGraph()
        
        # Run planning synchronously (this blocks the tool thread, not UI)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Status update
        StatusManager().emit_status(project_id, "Web Builder: Planning architecture...")
        
        try:
            state = loop.run_until_complete(graph.plan(description, project_id))
        except Exception as e:
            loop.close()
            return {"error": str(e)}
        loop.close()
        
        if state.get("error"):
            return {"error": state["error"]}
            
        # Store pending task
        self.active_tasks[project_id] = {
            "graph": graph,
            "state": state,
            "description": description,
            "project_id": project_id,
            "status": "pending_approval"
        }
        
        return state.get("files_plan", [])

    def execute_pending_plan(self, project_id: str):
        """Starts background execution of the pending plan."""
        if project_id not in self.active_tasks:
            return "Error: No pending plan found for this project."
            
        task_info = self.active_tasks[project_id]
        if task_info.get("status") != "pending_approval":
            return "Error: Task is not in pending approval state."
            
        graph = task_info["graph"]
        state = task_info["state"]
        description = task_info.get("description", "Project")

        # Setup Notification
        notification = Notify.Notification.new(
            "Web Builder Started",
            f"Building project: {description[:30]}...",
            "applications-development-symbolic" 
        )
        notification.set_hint("desktop-entry", GLib.Variant.new_string("io.github.askscience.gaia"))
        notification.set_urgency(Notify.Urgency.NORMAL)
        notification.add_action("stop", "Cancel Build", self._on_stop_clicked, project_id)

        task_info["notification"] = notification
        task_info["last_show_time"] = time.time()
        task_info["status"] = "running"

        def status_callback(message, percentage=None):
            GLib.idle_add(self._update_notification, project_id, message, percentage)

        def run_in_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            task_info["loop"] = loop
            
            task = loop.create_task(graph.execute_from_plan(state, status_callback=status_callback))
            task_info["task"] = task
            
            try:
                final_state = loop.run_until_complete(task)
                loop.close()
                GLib.idle_add(self._on_build_finished, project_id, final_state)
            except asyncio.CancelledError:
                GLib.idle_add(self._on_build_finished, project_id, {"error": "Build cancelled by user."})
            except Exception as e:
                import traceback
                traceback.print_exc()
                GLib.idle_add(self._on_build_failed, project_id, str(e))

        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()
        
        notification.show()
        
        return "Web Builder started in background. Please inform the user that the website creation is IN PROGRESS and you will notify them when it is complete. Do not say you have finished effectively."

    def stop_building(self, project_id):
        if project_id in self.active_tasks:
            task_info = self.active_tasks[project_id]
            task_info["graph"].cancel()
            
            if task_info.get("loop") and task_info.get("task"):
                task_info["loop"].call_soon_threadsafe(task_info["task"].cancel)
            return True
        return False

    def _update_notification(self, project_id, message, percentage):
        if project_id not in self.active_tasks:
            return False
            
        task = self.active_tasks[project_id]
        notification = task.get("notification")
        if not notification: return False
        
        title = f"Building: {percentage}%" if percentage is not None else "Building Progress"
        notification.update(title, f"{message}", "applications-development-symbolic")
        
        now = time.time()
        if now - task.get("last_show_time", 0) > 10: 
            try:
                notification.show()
                task["last_show_time"] = now
            except: pass
            
        StatusManager().emit_status(project_id, f"Web Builder: {message}")
        return False

    def _on_stop_clicked(self, notification, action_name, project_id):
        self.stop_building(project_id)
        notification.close()

    def _on_build_finished(self, project_id, final_state):
        if project_id not in self.active_tasks:
            return
            
        task = self.active_tasks[project_id]
        notification = task.get("notification")
        
        if final_state.get("error"):
            msg = final_state["error"]
            if msg == "Cancelled by user.":
                n = Notify.Notification.new("Build Cancelled", "Web build was stopped.", "process-stop-symbolic")
                n.show()
            else:
                self._on_build_failed(project_id, msg)
            if project_id in self.active_tasks:
                del self.active_tasks[project_id]
            if notification: notification.close()
            return

        # Check for partial failures
        artifacts = final_state.get("artifacts", [])
        files_plan = final_state.get("files_plan", [])
        
        success_count = len(artifacts)
        total_count = len(files_plan)
        
        if success_count < total_count and total_count > 0:
            # Partial Failure
            title = "Web Build Finished with Errors"
            summary = f"Created {success_count}/{total_count} files. Some files failed."
            icon = "dialog-warning-symbolic" 
        else:
            # Full Success
            title = "Web Build Complete!"
            summary = f"Created {success_count} files for project."
            icon = "emblem-documents-symbolic"
        
        final_notification = Notify.Notification.new(title, summary, icon)
        final_notification.set_hint("desktop-entry", GLib.Variant.new_string("io.github.askscience.gaia"))
        final_notification.show()
        
        if notification: notification.close()
        
        GLib.idle_add(self._trigger_ui_update, project_id, artifacts)
        StatusManager().emit_status(project_id, "Web Builder: Complete!")
        
        del self.active_tasks[project_id]

    def _trigger_ui_update(self, project_id, artifacts):
        try:
            app = Gio.Application.get_default()
            if not app: return
            
            win = app.get_active_window()
            if win:
                if hasattr(win, "chat_pages") and project_id in win.chat_pages:
                    chat_page = win.chat_pages[project_id]
                    chat_page.update_last_message_metadata({'artifacts': artifacts})
                    chat_page.add_artifacts_to_ui(artifacts)
                    
                index_artifact = next((a for a in artifacts if "index.html" in a["filename"]), None)
                if index_artifact and hasattr(win, "artifacts_panel"):
                    # Web Builder Complete: Force Window Visibility (for Voice Mode)
                    win.set_visible(True)
                    win.present()
                    
                    win.artifacts_panel.load_artifact(index_artifact['path'], "html")
                    win.show_artifacts()
                    
                    # Ensure Fullscreen (Hide Chat)
                    if hasattr(win, "tab_overview") and win.tab_overview.get_visible():
                        win.toggle_artifact_fullscreen()
                    
        except Exception as e:
            print(f"Error auto-opening artifact: {e}")

    def _on_build_failed(self, project_id, error_msg):
        if project_id not in self.active_tasks:
            return
        task = self.active_tasks[project_id]
        n = Notify.Notification.new("Build Failed", f"Error: {error_msg}", "dialog-error-symbolic")
        n.show()
        if task.get("notification"): task["notification"].close()
        del self.active_tasks[project_id]
