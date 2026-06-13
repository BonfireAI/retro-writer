#!/usr/bin/env bash
# install.sh — install the retro-writer cockpit into the user's home.
#
#   - symlinks bin/blog, bin/blog-export and bin/crt-theme into ~/.local/bin/
#     (chmod +x in repo)
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

for cmd in blog blog-export crt-theme; do
	chmod +x "$BIN_SRC/$cmd"
	ln -sf "$BIN_SRC/$cmd" "$LOCAL_BIN/$cmd"
	printf 'linked: %s -> %s\n' "$LOCAL_BIN/$cmd" "$BIN_SRC/$cmd"
done

# Desktop entry: copy the shipped (path-free `Exec=blog`) file, then rewrite the
# INSTALLED copy's Exec to the absolute ~/.local/bin/blog symlink we just made.
# The absolute path makes the app-menu launcher robust even when the desktop
# environment's launch PATH omits ~/.local/bin (a common gotcha). We rewrite the
# installed copy only — the repo file stays portable and leak-free.
cp "$REPO_DIR/desktop/retro-writer.desktop" "$APPS_DIR/retro-writer.desktop"
sed -i "s|^Exec=.*|Exec=$LOCAL_BIN/blog|" "$APPS_DIR/retro-writer.desktop"
printf 'installed: %s\n' "$APPS_DIR/retro-writer.desktop"

update-desktop-database "$APPS_DIR" 2>/dev/null || true

printf 'drafts dir: %s\n' "$WRITING_DIR"
printf 'Done installing. (Reminder: ~/.local/bin must be on PATH.)\n'
