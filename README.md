# Gaia - GNOME AI Assistant

**Your personal AI companion, built for GNOME.**

Gaia is a fast, beautiful, and private AI assistant that lives on your Linux desktop. It integrates seamlessly with your system, offering a native experience powered by local LLMs or top-tier cloud models.

<div align="center">
  <img src="demo.gif" width="100%" alt="Gaia Demo" />
  <br>
  <em>See Gaia in action</em>
</div>

## Why Gaia?

*   **🧠 Flexible AI Backend**: Use local models via **Ollama** for privacy, or connect to powerful cloud providers like **OpenAI, Anthropic (Claude), Google (Gemini), and Mistral**.
*   **🎨 Native Design**: Built with GTK4 and Libadwaita, Gaia looks and feels like it belongs on your desktop.
    *   **Deep Research Agent**: Unlike standard search, this agent performs an autonomous, multi-turn investigation. It generates a research plan, executes multiple targeted searches, scrapes and analyzes sources, reflects on findings, and finally synthesizes a comprehensive report with citations.
    *   **Asynchronous Processing**: Deep Research runs entirely in the background. You can start an investigation and continue your conversation or other tasks while Gaia works.
    *   **Desktop-Native Feedback**: Stay updated with native GNOME notifications showing real-time progress (0-100%). Each notification includes a "Stop" button for instant cancellation from your system tray.

## Getting Started

### 1. Prerequisites
You need a modern Linux distribution (Fedora/Ubuntu/Arch) with GNOME.
Ensure **[Ollama](https://ollama.ai/)** is installed and running:
```bash
ollama pull granite4:latest
```

### 2. Installation
Gaia relies on standard system libraries.

**Ubuntu / Debian:**
```bash
sudo apt install libgtk-4-dev libadwaita-1-dev python3-dev gobject-introspection libcairo2-dev
```

**Fedora:**
```bash
sudo dnf install gtk4-devel libadwaita-devel python3-devel gobject-introspection-devel cairo-gobject-devel
```

**Arch Linux:**
```bash
sudo pacman -S gtk4 libadwaita python python-gobject cairo
```

### 3. Setup Python Environment
Create a virtual environment and install dependencies:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Run Gaia
Launch it casually from the terminal:
```bash
./.venv/bin/python3 src/main.py
```

## Desktop Integration
Want to launch Gaia like a pro? Add it to your app grid.

The desktop file is already set up to work if Gaia is in your PATH, or you can copy it to your local applications folder:

```bash
cp data/com.example.gaia.desktop ~/.local/share/applications/
```
*Note: You may need to update the `Exec` path in the desktop file depending on where you extracted the project.*

## Pro Tip: Keyboard Shortcut
Bind `Super+Space` to open Gaia instantly!
1.  Go to **Settings** -> **Keyboard** -> **View and Customize Shortcuts** -> **Custom Shortcuts**.
2.  Add a shortcut:
    *   **Command**: `/path/to/gaia/src/main.py` (ensure you use the absolute path to the python interpreter in the venv)

## License

This project is licensed under the [GNU General Public License v3.0](LICENSE).
