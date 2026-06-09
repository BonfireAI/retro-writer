#!/usr/bin/env bash
# install.sh — install the retro-writer cockpit into the user's home.
#
#   - symlinks bin/blog and bin/blog-export into ~/.local/bin/ (chmod +x in repo)
#   - installs desktop/retro-writer.desktop into ~/.local/share/applications/
#   - creates the drafts dir ~/writing/
#
# Idempotent: re-running just refreshes the symlinks and desktop entry.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN_SRC="$REPO_DIR/bin"
LOCAL_BIN="$HOME/.local/bin"
APPS_DIR="$HOME/.local/share/applications"
WRITING_DIR="$HOME/writing"

mkdir -p "$LOCAL_BIN" "$APPS_DIR" "$WRITING_DIR"

for cmd in blog blog-export; do
	chmod +x "$BIN_SRC/$cmd"
	ln -sf "$BIN_SRC/$cmd" "$LOCAL_BIN/$cmd"
	printf 'linked: %s -> %s\n' "$LOCAL_BIN/$cmd" "$BIN_SRC/$cmd"
done

# Desktop entry: copy so its Exec points at the installed ~/.local/bin/blog.
cp "$REPO_DIR/desktop/retro-writer.desktop" "$APPS_DIR/retro-writer.desktop"
printf 'installed: %s\n' "$APPS_DIR/retro-writer.desktop"

update-desktop-database "$APPS_DIR" 2>/dev/null || true

printf 'drafts dir: %s\n' "$WRITING_DIR"
printf 'Done installing. (Reminder: ~/.local/bin must be on PATH.)\n'
