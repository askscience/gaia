# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased] - 2026-01-02

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
