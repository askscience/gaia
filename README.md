# Gaia Assistant

**Your personal AI companion, built for GNOME.**

Gaia is a fast, beautiful, and private AI assistant that lives on your Linux desktop. It integrates seamlessly with your system, offering a native experience powered by local LLMs.

<div align="center">
  <video src="demo.webm" width="100%" controls autoplay loop muted></video>
  <br>
  <em>See Gaia in action</em>
</div>

## Why Gaia?

*   **🔒 Private & Local**: Powered by [Ollama](https://ollama.ai/), your data never leaves your device.
*   **🎨 Native Design**: Built with GTK4 and Libadwaita, Gaia looks and feels like it belongs on your desktop.
*   **🛠️ Powerful Tools**:
    *   **Web Builder**: Create and edit HTML/CSS/JS projects instantly.
    *   **File Manager**: Read, write, and organize files.
    *   **Web Search**: Access the internet for up-to-date information.
    *   **System Awareness**: Check the time and understand your environment.

## Getting Started

### 1. Prerequisites
You need a modern Linux distribution (Fedora/Ubuntu/Arch) with GNOME.
Ensure **[Ollama](https://ollama.ai/)** is installed and running:
```bash
ollama pull granite4:latest
```

### 2. Installation
Gaia relies on standard system libraries.

**Fedora:**
```bash
sudo dnf install gtk4-devel libadwaita-devel python3-devel gobject-introspection-devel cairo-gobject-devel
```

**Install Python Dependencies:**
```bash
./.venv/bin/pip install -r requirements.txt
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
    *   **Shortcut**: `Super+Space`
