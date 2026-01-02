# Changelog

All notable changes to this project will be documented in this file.

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
