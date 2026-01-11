# Changelog

All notable changes to this project will be documented in this file.


## [0.3.3] - 2026-01-11

### Added
- **Gnome Desktop Suite**: A complete set of tools to integrate with your GNOME environment.
    - **Radio Tuner**: (`gnome_radio`) Search and play internet radio stations via radio-browser.info.
    - **Audio Control**: (`gnome_audio_control`) Manage system volume (get, set, mute, unmute).
    - **Wallpaper Search**: (`gnome_search_background`) Find high-quality wallpapers via Unsplash/Pexels.
    - **Wallpaper Set**: (`gnome_set_background`) Apply images as desktop background.
    - **Theme Manager**: (`gnome_theme`) Switch system-wide light/dark theme.
    - **File Opener**: (`gnome_opener`) Intelligent file and URL opener.

### Changed
- **Refactoring**:
    - Modularized the monolithic `gnome_tools` into dedicated subfolders (`background/`, `theme/`, `opener/`, `audio/`, `radio/`) for better maintainability.

## [0.3.2] - 2026-01-09

### Fixed
- **Web Preview Performance**: Eliminated an unnecessary 300ms delay when reopening chats with existing web artifacts. Project restoration is now practically instant.

## [0.3.1] - 2026-01-09

### Added
- **Global Concurrency Manager**: Implemented a centralized system to manage API limits across all tools.
    - Added strict default limits for **Z.ai** (2), **Ollama** (4), **Anthropic** (4), and others to prevent "429 Too Many Requests" errors.
    - Refactored `Web Builder` and `Deep Research` to use this shared system.
- **Provider-Specific Limits**: The app now automatically detects the active AI provider and applies the appropriate safety limit.

### Fixed
- **Chat UI Overlap**: Increased the bottom margin of the chat view to prevent the "Thinking..." status overlay from obscuring the latest messages.
- **Z.ai API Stability**: Resolved critical "Error 1302: High concurrency usage" issues by strictly throttling Z.ai requests to 2 concurrent calls.

## [0.3.0] - 2026-01-08

### Fixed
- **Web Builder Reliability**:
    - **Partial Failure Reporting**: The Web Builder now correctly reports "Finished with Errors" if some files failed to generate, instead of falsely claiming success.
    - **Blank Page in Packaged App**: Fixed a critical issue where the Web Preview displayed a blank page in Flatpak/Debian installs by properly disabling the WebKitGTK sandbox (`WEBKIT_DISABLE_SANDBOX=1`) to allow access to local artifacts.
- **Web Preview UI**:
    - Added a **Refresh Button** to the Artifacts Panel toolbar.
    - Improved artifact loading logic with smarter caching and debounce handling to prevent blank pages on initial load.
## [0.2.9] - 2026-01-08

### Fixed
- **Crash Fix**: Resolved a `TypeError` in `CodeBlock` rendering on systems with stricter GTK bindings (forcing explicit length parameter) which caused the app to crash when displaying code.

## [0.2.8] - 2026-01-08

### Added
- **Rich Chat Markup**:
    - Code blocks are now rendered with distinct styling and syntax coloring.
    - Added a **Copy Button** to every code block for one-click copying of commands and snippets.
    - Improved copy button behavior with visual feedback on click.

### Fixed
- **Chat Persistence**:
    - Fixed a critical issue where chat history was being truncated to the last 100 messages upon loading, causing permanent data loss for older conversations.
    - Resolved a lazy-loading bug where background tabs could overwrite valid chat files with empty data on application exit.
- **Status UI**:
    - Moved the "Thinking..." spinner to a floating overlay in the bottom-left corner, ensuring it remains visible without cluttering the chat flow.
    - Fixed a race condition where the status spinner could get stuck indefinitely if an error occurred or generation stopped unexpectedly.
- **Markdown Parsing**: Adjusted the parser to leniently handle code blocks with trailing spaces in the language identifier (e.g., `bash `).
- **History Rendering**: Existing chats now correctly load with rich formatting (code blocks and copy buttons) instead of loading as plain text.

### Changed
- **Styling**: Refined the appearance of the floating status indicator for a cleaner, more professional look consistent with GNOME Adwaita.

## [0.2.7] - 2026-01-06

### Added
- **Web Builder Settings**: New "Web Builder" configuration group in Settings > Tools.
    - **Max Files**: Configure the maximum number of files the AI can generate (Default: 5).
- **Native Plan Approval UI**: Web build plans are now displayed using native Adwaita widgets (`AdwPreferencesGroup`, `AdwActionRow`) for a polished, system-consistent look.

### Fixed
- **JavaScript Imports**: Fixed incorrect import paths in JS modules (e.g., `./js/utils.js` is now correctly `./utils.js` when inside the `js/` folder).
- **HTML Asset Linking**: `index.html` is now generated LAST, after all CSS/JS assets are confirmed, ensuring all `<link>` and `<script>` tags are complete and accurate.
- **Auto-Execution Bug**: Prevented the AI from automatically executing plans; it now reliably waits for user approval via the UI "Proceed" button.

### Changed
- **Concise AI Responses**: Significantly reduced AI verbosity during web builds. The AI now outputs a brief confirmation and calls the tool immediately.
- **Strict Import Rules**: Updated subagent prompts to enforce correct relative paths and provide the full project structure to each file writer.

## [0.2.6] - 2026-01-06

### Fixed
- **Large Project Generation**: Resolved a "Read operation timed out" error by increasing HTTP client timeouts to 20 minutes, allowing the AI to generate complex web projects without interruption.
- **Web Builder Feedback**: Fixed an issue where the "Thinking..." status persisted during file creation. The specific "Creating files..." status now correctly appears.

### Changed
- **System Prompts**: Overhauled the system prompt intro ("Operator Manual") in all supported languages (EN, IT, DE, ES, FR) to enforce modular file structures and stricter tool usage rules.

## [0.2.5] - 2026-01-06

### Fixed
- **Plan Execution**: Resolved a regression where the "Proceed" button was not visible for AI plans.
- **Chat Saving**: Implemented immediate saving for chat messages and AI responses, fixing data loss on application exit.
- **Startup Crash**: Fixed an `IndentationError` in `chat_storage.py` that prevented the app from launching.

### Changed
- **Performance**: Optimized UI streaming to reduce lag during long AI responses (increased update interval to 100ms).
- **Cleanup**: Deleting a chat now correctly removes its associated artifacts folder.

## [0.2.4] - 2026-01-05

### Fixed
- **Startup Errors**:
    - Fixed `IndentationError` in `file_list`, `web_search`, and `file_reader` tools.
    - Resolved `httpx-socks` dependency issue by ensuring it is included in the build.
    - Fixed `GtkSource` startup warning by adding `gir1.2-gtksource-5` to package dependencies.

## [0.2.3] - 2026-01-05

### Added
- **Internationalization (i18n)**:
    - Added full support for multiple languages: Italian (it), German (de), Spanish (es), and French (fr).
    - New `LanguageManager` and `prompts_*.json` system allows for translated GUI strings and AI prompts.
    - Updated `SettingsWindow` with a language selector (requires restart).
- **Tool Localization**:
    - AI tool descriptions in the Settings panel are now fully localized.

### Fixed
- **Web Scraping**: Fixed a configuration error in `trafilatura` extraction that prevented options like `min_duplcheck_size` from being applied correctly.
- **Language Detection**: Fixed `PromptManager` not respecting the user-selected language configuration on startup.

## [0.2.2] - 2026-01-04

### Added
- **Self-Healing Web Preview**:
    - **Web Console Tool**: New AI tool (`web_console`) allows Gaia to read browser logs and fix runtime errors in generated web applications.
    - **Silent Logging**: The Artifacts Panel now silently captures `window.onerror` and `console.error` events to a `console.json` file, enabling "agentic" debugging without cluttering the UI.
    - **Opaque Error Handling**: Improved handling of generic "Script error." messages caused by local file security policies.

## [0.2.1] - 2026-01-04

### Added
- **Advanced Tor Support**:
    - Integrated automated Tor Control Port configuration tool (using `HashedControlPassword`).
    - Added GUI dialog to automatically enable Tor control access with admin privileges (`pkexec`) if "Connection Refused" or "Auth Failed" is detected.
    - Implemented a "Refresh Identity" button in settings that appears when Tor is detected.
    - Added robust authentication fallback (Cookie -> Password -> Null) for Tor Control.
- **Network Resilience**:
    - Patched `Google`, `OpenAI`, and `Anthropic` providers to correctly handle SOCKS proxies (fixing `httpx` connection refused errors).
    - Added smart proxy scheme detection (auto-adds `socks5://` for Tor ports).

### Changed
- **UI Improvements**: moved Network settings to the bottom of the General page for better layout balance.

## [0.2.0] - 2026-01-04

### Added
- **Global Proxy Support**:
    - Users can now configure a system-wide proxy via the Settings panel.
    - Improved support for SOCKS5 proxies, ensuring robust connections for advanced network configurations.
    - Added auto-correction logic to handle common proxy URL formatting issues transparently.
- **Centralized Status Manager**:
    - Introduced a unified `StatusManager` to broadcast real-time tool execution status to the UI.
    - Improved developer experience with automatic status callback injection via `ToolManager`.

### Fixed
- **Connection Reliability**: Resolved connection errors by ensuring all dependencies for SOCKS proxies (PySocks, httpx-socks) are properly handled.

## [0.1.9] - 2026-01-03

### Added
- **Calendar Integration**:
    - **New Calendar Tool**: Integrated a full GDBus-based calendar toolset, allowing the AI to add, remove, and list events directly from the GNOME Calendar.
    - **Smart Event Listing**: The AI can now query events by date ranges and natural language descriptions.
    - **Time Awareness**: The AI is now explicitly aware of the current system time to ensure accurate event scheduling.

### Changed
- **Refactoring**:
    - **Chat Logic**: Massive refactor of `src/ui/chat/page.py` to externalize all hardcoded prompts into a centralized JSON file.
    - **Prompt Manager**: Introduced `src/core/prompt_manager.py` to handle dynamic prompt injection and tool-specific guidelines.
    - **Deep Research**: Externalized Deep Research prompts to `src/core/prompts/en.json`, unifying the prompt management system.


## [0.1.8] - 2026-01-03

### Changed
- **Deep Research Architecture**:
    - **Refactored Scraping**: Unified Deep Research and Web Search tools to use a shared, high-quality scraping module based on `trafilatura` (with `BeautifulSoup` fallback).
    - **Clean Data Pipeline**: Deep Research now consumes raw scraped data directly, ensuring it receives clean text without the chat-formatted `[SOURCES]` tags.
    - **Async Writing**: Parallelized the AI writing phase of Deep Research. Subagents now extract facts and draft sections concurrently, significantly speeding up report generation.


## [0.1.7] - 2026-01-03

### Added
- **Stop Generation**: Users can now instantly stop the AI generation by clicking the stop button (formerly the send button).
    - The chat history silently records `[stopped by user]` so the AI is aware of the interruption in future turns without cluttering the UI.

### Changed
- **UI Polish**: Updated the Artifacts Panel toggle button icon to the standard `sidebar-show-symbolic` for better visual consistency with GNOME.


## [0.1.6] - 2026-01-03

### Fixed
- **Settings UI**: Improved "Tools" section with nicely formatted names (e.g., "File Editor" instead of `file_editor`) and full, untruncated descriptions.
- **Deep Research Citations**: Resolved an issue where redundant citation numbers (e.g., `[1] [2]...`) appeared before the references section.
- **Deep Research Logging**: Fixed a double-print issue in the Global Planning debug output.
- **AI File Discoverability**:
    - Updated `file_list` tool to search recursively, allowing the AI to see artifacts in subfolders.
    - Improved Deep Research notifications to provide relative file paths, enabling the AI to correct edit reports.

## [0.1.5] - 2026-01-02

### Fixed
- **Deep Research Report Formatting**: Fixed broken markdown citations and multi-line links that caused rendering issues.
- **Citation Numbering**: Implemented global citation normalization to ensure citation numbers in the text match the reference list exactly.
- **Section Titles**: Removed "Step X" prefixes from section headers for a cleaner, more professional look.
- **Duplicate Sources**: Removed redundant "Sources" sections from both the generated text and the HTML template.

## [0.1.4] - 2026-01-02

### Fixed
- **Deep Research Persistence**: Fixed a critical issue where Deep Research reports were not saved to chat history, causing them to fail to load when reopening chats.
- **Deep Research Auto-Loading**: Improved detection logic to ensure reports automatically open in the Artifacts Panel regardless of how they are loaded.

## [0.1.3] - 2026-01-02

### Added
- **Artifacts Panel Refactor**:
    - Centralized project controls (Export, Create App, Fullscreen) in the header toolbar.
    - Replaced the "Code" tab with a native file selector dropdown.
    - Added a **Fullscreen** toggle to expand artifacts to the entire window.
    - Integrated specialized **Research Mode** for Deep Research reports with **PDF Export** support.
- **UX Improvements**:
    - Web projects now default to the rendered **Web Preview**.
    - Removed redundant completion cards from the chat for a cleaner, unified flow.
    - Updated icons to native GNOME symbolic set (`globe-symbolic`, `view-app-grid-symbolic`).

### Fixed
- **Artifact Loading**: Resolved race conditions and bytecode caching issues that caused incorrect view states.
- **Dependency Handling**: Split WebKit and GtkSource imports to ensure the preview works even if coding tools are missing.
- **State Management**: Implemented `clear()` to prevent data leakage between chats.


## [0.1.2] - 2026-01-02

### Added
- **Tool Selection Settings**: Users can now enable or disable specific AI tools (like web search or file editing) from the General settings tab.

### Fixed
- **Disabled Tool Hallucination**: AI is now explicitly instructed when tools are disabled, preventing it from attempting to call them via text and ensuring it provides helpful feedback to the user.

## [0.1.1] - 2026-01-02

### Added
- **Native Source Cards**: Refactored source display to use compact, native GNOME list rows instead of large cards.
- **Rich Metadata**: Integrated OpenGraph extraction to display high-quality thumbnails, titles, and descriptions for sources.

### Changed
- **Web Search UX**: Enforced strict single-search workflow with discursive AI answers appearing *before* source references.
- **UI Polish**: Removed solid borders and accent colors from source lists for a cleaner, native Libadwaita appearance.

## [0.1.0] - 2026-01-01

### Added
- **Inline Image Integration** in Deep Research reports.
    - Images from Unsplash and Pexels are now placed contextually within the report sections.
    - Built-in automatic attribution links below each image.
    - Professional CSS styling for centered, responsive images and caption-style credits.
- **Unique Image Distribution**: Ensures each report section receives a unique subset of the image pool, preventing repetition.
- **Asynchronous Deep Research**: Research tasks run in the background with native GNOME notification progress and cancellation.

### Fixed
- Fixed `NameError: name 'Dict' is not defined` in `state.py`.
- Resolved `IndentationError` in `nodes.py` due to rogue triple quotes.
- Eliminated redundant section titles and "Sources" headers in the research report output.
- Optimized image search keywords to use shorter, more relevant terms (1-3 words).

### Changed
- Improved Deep Research synthesizer to delegate "Sources" header management to the HTML template.
- Refined section subagent prompts to strictly prevent repeating introductory fillers and titles.
