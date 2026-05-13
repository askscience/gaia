#!/bin/bash
set -e

echo "======================================"
echo "  Gaia - GNOME AI Assistant Installer"
echo "  Rust Edition v0.5.0"
echo "======================================"
echo ""

GAIA_DIR="$HOME/.local/share/gaia_rust"
REPO_URL="https://github.com/askscience/gaia.git"
BRANCH="rust"

# ── Check Rust toolchain ──
if ! command -v cargo &> /dev/null; then
    echo "[1/4] Installing Rust toolchain..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
else
    echo "[1/4] Rust toolchain found: $(rustc --version)"
fi

# ── Install system dependencies ──
echo "[2/4] Checking system dependencies..."

install_deps() {
    if command -v apt &> /dev/null; then
        sudo apt update
        sudo apt install -y libgtk-4-dev libadwaita-1-dev libwebkitgtk-6.0-dev libgtksourceview-5-dev pkg-config
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y gtk4-devel libadwaita-devel webkitgtk6.0-devel gtksourceview5-devel pkg-config
    elif command -v pacman &> /dev/null; then
        sudo pacman -S --noconfirm gtk4 libadwaita webkitgtk-6.0 gtksourceview5 pkgconf
    else
        echo "⚠ Could not detect package manager. Install GTK4, Libadwaita, WebKitGTK 6.0, and GtkSourceView 5 manually."
        return 1
    fi
}

if ! pkg-config --exists gtk4 libadwaita-1 2>/dev/null; then
    install_deps
else
    echo "  System dependencies already installed."
fi

# ── Clone and build ──
echo "[3/4] Cloning Gaia ($BRANCH branch)..."
rm -rf "$GAIA_DIR"
git clone --branch "$BRANCH" --depth 1 "$REPO_URL" "$GAIA_DIR"

echo "[4/4] Building Gaia (release)..."
cd "$GAIA_DIR"
cargo build --release

BIN_PATH="$GAIA_DIR/target/release/gaia"

# ── Create desktop entry ──
DESKTOP_DIR="$HOME/.local/share/applications"
mkdir -p "$DESKTOP_DIR"

cat > "$DESKTOP_DIR/io.github.askscience.gaia.desktop" << EOF
[Desktop Entry]
Name=Gaia
Comment=GNOME AI Assistant
Exec=$BIN_PATH
Icon=$GAIA_DIR/icon.png
Terminal=false
Type=Application
Categories=Utility;Office;
Keywords=AI;Assistant;Chat;GPT;LLM;
StartupNotify=true
EOF

echo ""
echo "======================================"
echo "  Installation complete!"
echo ""
echo "  Binary: $BIN_PATH"
echo "  Desktop entry created."
echo ""
echo "  Run: $BIN_PATH"
echo "======================================"
