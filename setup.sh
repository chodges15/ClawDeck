#!/bin/bash
# ClawDeck — Setup Script
# Run this once to install dependencies and configure hooks.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== ClawDeck Setup ==="
echo ""

# 1. System dependencies
echo "[1/4] Installing system dependencies via Homebrew..."
if ! command -v brew &> /dev/null; then
    echo "  ERROR: Homebrew not found. Install it from https://brew.sh"
    exit 1
fi

brew install hidapi 2>/dev/null || echo "  hidapi already installed"
brew install python@3.13 2>/dev/null || echo "  python@3.13 already installed"

# 2. Find a compatible Python (3.13 preferred, then 3.12)
PYTHON=""
for candidate in \
    /opt/homebrew/bin/python3.13 \
    /usr/local/bin/python3.13 \
    /opt/homebrew/bin/python3.12 \
    /usr/local/bin/python3.12; do
    if [ -x "$candidate" ]; then
        PYTHON="$candidate"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo "ERROR: Could not find Python 3.12 or 3.13."
    echo "Your system Python ($(python3 --version)) is too new for pyobjc."
    echo "Run: brew install python@3.13"
    exit 1
fi

echo "  Using: $($PYTHON --version)"

# 3. Virtual environment + packages
echo "[2/4] Creating virtual environment..."
rm -rf .venv
$PYTHON -m venv .venv
source .venv/bin/activate

echo "[3/4] Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# 4. Install Claude Code hooks
echo "[4/4] Configuring Claude Code hooks..."
python install_hooks.py

echo ""
echo "=== Setup Complete ==="
echo ""
echo "To run:"
echo "  cd $SCRIPT_DIR"
echo "  .venv/bin/python main.py"
