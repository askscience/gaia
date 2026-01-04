import gi
from gi.repository import GObject
from src.core.status.signals import TOOL_STATUS_UPDATE

class StatusManager(GObject.Object):
    """
    Singleton manager that handles status updates from tools and broadcasts them to the UI.
    """
    _instance = None
    
    # Define signals
    __gsignals__ = {
        TOOL_STATUS_UPDATE: (GObject.SignalFlags.RUN_FIRST, None, (str, str)),
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StatusManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        super().__init__()
        self._initialized = True

    def emit_status(self, project_id: str, message: str):
        """
        Emit a status update signal.
        This should be called by tools when they want to show what they are doing.
        """
        # Ensure we run this on the main thread if called from a background thread
        # accessing GObject signals is generally thread-safe in PyGObject if threads are init'd,
        # but emitting often needs to happen in main loop or be safe. 
        # Actually GObject signals are synchronous. If called from thread, slots run in thread.
        # We'll emit directly, UI usually handles idle_add on reception if needed.
        self.emit(TOOL_STATUS_UPDATE, project_id, message)
