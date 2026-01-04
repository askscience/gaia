# Centralized Tool Status Guidelines

This module provides a unified system for tools to report their real-time status to the UI (e.g., the spinner next to the chat).

## Overview

The system consists of:
1.  **`StatusManager`** (`src/core/status/manager.py`): A singleton that broadcasts status updates.
2.  **`ToolManager`** (`src/tools/manager.py`): Automatically injects a `status_callback` into any tool that accepts it.
3.  **UI** (`src/ui/chat/page.py`): Listens for status events and updates the spinner.

## How to Make a Tool Report Status

You do **not** need to manually import `StatusManager` in your tool. The `ToolManager` handles the wiring.

### Step 1: Add `status_callback` to `execute`

Modify your tool's `execute` method to accept `status_callback=None` as an argument.

```python
def execute(self, query: str, status_callback=None, **kwargs):
    # ...
```

### Step 2: Call the Callback

Simply call the function with a string message whenever you want to update the UI.

```python
    if status_callback:
        status_callback(f"Surfing web: {query}...")
    
    # Do some work...
    
    if status_callback:
        status_callback("Processing results...")
```

## How It Works Under the Hood

1.  **Injection**: When `ToolManager.execute_tool` is called, it checks if `status_callback` is in the tool's signature.
2.  **Wrapping**: If present, it creates a wrapper function `report_status(msg)` that:
    *   Emits a `tool-status-update` signal via `StatusManager`.
    *   Calls any legacy callbacks (if provided).
3.  **Broadcasting**: `StatusManager` emits the GObject signal.
4.  **Listening**: The active `ChatPage` receives the signal. If the `project_id` matches, it updates the spinner text.

## Adding New Tools

Just follow the pattern above. No UI definition changes are needed.
