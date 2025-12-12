#!/bin/bash
# FILE: ~/.vim/bundle/headerize-vim/install.sh

# Target directory for executable scripts
TARGET_BIN_DIR="$HOME/.local/bin"
SCRIPT_NAME="headerize.py"

echo "Running headerize-vim installation script..."

# 1. Create the target bin directory if it doesn't exist
if [ ! -d "$TARGET_BIN_DIR" ]; then
    echo "Creating $TARGET_BIN_DIR..."
    mkdir -p "$TARGET_BIN_DIR"
fi

# 2. Copy the Python script to the target directory
echo "Copying $SCRIPT_NAME to $TARGET_BIN_DIR/"
cp "$(dirname "$0")/$SCRIPT_NAME" "$TARGET_BIN_DIR/$SCRIPT_NAME"

# 3. Ensure the script is executable
echo "Making $SCRIPT_NAME executable."
chmod +x "$TARGET_BIN_DIR/$SCRIPT_NAME"

echo "Installation complete. Ensure $TARGET_BIN_DIR is in your system \$PATH."

# Exit successfully
exit 0
