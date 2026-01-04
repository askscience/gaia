import os
import gi
try:
    gi.require_version('WebKit', '6.0')
    from gi.repository import WebKit
except ValueError:
    WebKit = None

from gi.repository import GObject, GLib

class PreviewManager(GObject.Object):
    """
    Manages the bridge between WebKit WebView and Gaia.
    Injects error listeners and receives messages from JS.
    """
    
    def __init__(self):
        super().__init__()
        self.log_file = None

    def start_logging(self, project_path):
        """Start logging to console.json in the project directory."""
        self.log_file = os.path.join(project_path, "console.json")
        # Clear existing log
        try:
            with open(self.log_file, "w") as f:
                f.write("")
        except Exception as e:
            print(f"[PreviewManager] Failed to init log file: {e}")

    def setup_bridge(self, web_view):
        """
        Configures the WebView to listen for Gaia messages.
        """
        if not WebKit: return

        # 1. Get Content Manager
        content_manager = web_view.get_user_content_manager()
        
        # 2. Register Script Message Handler "gaia"
        try:
             content_manager.register_script_message_handler("gaia")
        except:
             pass # Already registered

        # Connect signal (avoid duplicate connections if possible, but GObject handles generic usually)
        # Note: In a robust app we'd disconnect old handlers. For now, we assume 1 manager per view lifetime.
        content_manager.connect("script-message-received::gaia", self._on_message_received)
        
        # 3. Inject the JS Listener
        self._inject_listener(content_manager)

    def _inject_listener(self, content_manager):
        # Read the JS file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        js_path = os.path.join(current_dir, "injector.js")
        
        try:
            with open(js_path, "r") as f:
                js_code = f.read()
                
            script = WebKit.UserScript.new(
                js_code,
                WebKit.UserContentInjectedFrames.TOP_FRAME,
                WebKit.UserScriptInjectionTime.START,
                [], []
            )
            content_manager.add_script(script)
        except Exception as e:
            print(f"[PreviewManager] Failed to inject JS: {e}")

    def _on_message_received(self, content_manager, js_result):
        """Handle message from JS."""
        try:
            # Check if likely WebKit.JavascriptResult (has get_js_value)
            if hasattr(js_result, "get_js_value"):
                value = js_result.get_js_value()
            else:
                value = js_result
            
            try:
                json_str = value.to_json(0) 
            except AttributeError:
                return
            
            import json
            data = json.loads(json_str)
            
            # Filter generic "Script error."
            if data.get("message") == "Script error." and data.get("lineno") == 0:
                data["message"] = "Opaque Script Error (Browser hid details)"
            
            # Log to file if configured
            if self.log_file:
                try:
                    with open(self.log_file, "a") as f:
                        f.write(json.dumps(data) + "\n")
                except Exception as e:
                    print(f"[PreviewManager] Write failed: {e}")
                
        except Exception as e:
            print(f"[PreviewManager] Error parsing message: {e}")
