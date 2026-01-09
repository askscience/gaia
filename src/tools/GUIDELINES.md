# Tool Development Guidelines

This document outlines the best practices and requirements for creating and maintaining tools in the Gaia application.

## 1. User Facing Strings & Prompts (Mandatory)

All user-facing strings, error messages, status updates, and AI context prompts MUST be centralized in `src/core/prompts/en.json`. **Do NOT hardcode strings in your Python files.**

### How to Use PromptManager

1.  **Define Keys**: Add your strings to `src/core/prompts/en.json` under a section matching your tool name.
    ```json
    "my_tool": {
        "status_running": "Processing {item}...",
        "error_failed": "Failed to process {item}: {error}",
        "success": "Successfully processed {count} items."
    }
    ```

2.  **Import & Use**:
    ```python
    from src.core.prompt_manager import PromptManager

    class MyTool(BaseTool):
        def execute(self, item, status_callback=None, **kwargs):
            prompt_manager = PromptManager()

            if status_callback:
                # Use .get() with keyword arguments for variable interpolation
                msg = prompt_manager.get("my_tool.status_running", item=item)
                status_callback(msg)

            try:
                # ... do work ...
                return prompt_manager.get("my_tool.success", count=1)
            except Exception as e:
                return prompt_manager.get("my_tool.error_failed", item=item, error=str(e))
    ```

### Why?
- **Localization**: Easier to translate the app later.
- **Consistency**: Ensures tone and formatting consistency across tools.
- **Maintainability**: separating content from logic makes both easier to update.

## 2. Reporting Status

Tools should report their real-time status to the UI (e.g., the spinner next to the chat).

### Overview
The system consists of `StatusManager`, `ToolManager`, and the UI. You do not need to check for them manually.

### How to Implement
1.  **Add `status_callback` argument**: Modify your tool's `execute` method to accept `status_callback=None`.
2.  **Call the callback**: Call it with a string message (retrieved from `PromptManager`) whenever you want to update the UI.

```python
def execute(self, query: str, status_callback=None, **kwargs):
    prompt_manager = PromptManager()
    
    if status_callback:
        status_callback(prompt_manager.get("my_tool.status_start"))
    
    # ... work ...
```

## 3. Special Tool Guidelines

### Web Console (`web_console`)
- **Purpose**: Reads `console.json` logs from WebKit previews.
- **Usage**: Used to debug generated web projects.

## 4. Concurrency & Rate Limiting
To prevent "429 Too Many Requests" errors when using cloud AI providers (e.g., Z.ai, OpenAI), all tools MUST use the centralized **Concurrency Manager**.

**Do NOT use `asyncio.Semaphore` directly** for limiting LLM or API calls.

### How to Implement
1.  Import the manager:
    ```python
    from src.core.concurrency.manager import ConcurrencyManager
    ```
2.  Wrap your API calls:
    ```python
    manager = ConcurrencyManager()
    
    async def my_parallel_task(item):
        async with manager.get_async_semaphore():
             # Your API call here (e.g., AIClient.generate_response)
             result = await perform_api_call(item)
    ```

## 5. Adding New Tools
1.  Create a folder in `src/tools/`.
2.  Implement `tool.py` inheriting from `BaseTool`.
3.  Add prompts to `src/core/prompts/en.json`.
4.  Register the tool in `src/core/agent/tool_manager.py` (if manual registration is valid) or ensure it's discoverable.
