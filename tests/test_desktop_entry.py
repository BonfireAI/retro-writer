"""Tests for the desktop launcher entry and how install.sh deploys it.

Two contracts:

1. The SHIPPED desktop/retro-writer.desktop must be portable and leak-free:
   its Exec line carries no absolute path (so it never hardcodes any one
   user's home), and the file contains no `/home/` reference at all.

2. install.sh must rewrite the INSTALLED copy's Exec line to the absolute
   ~/.local/bin/blog symlink it creates, so the app-menu entry launches even
   when the desktop environment's PATH omits ~/.local/bin.

The install test overrides HOME to a tmp dir, so it never touches the real
~/.local. install.sh is `set -euo pipefail` and guards update-desktop-database
with `|| true`, so it runs cleanly under a throwaway HOME with no display.
"""

import os
import subprocess

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESKTOP_FILE = os.path.join(REPO_ROOT, "desktop", "retro-writer.desktop")
INSTALL_SH = os.path.join(REPO_ROOT, "bin", "install.sh")


def _exec_value(text):
    """Return the value of the single Exec= line in a .desktop file body."""
    lines = [ln for ln in text.splitlines() if ln.startswith("Exec=")]
    assert len(lines) == 1, "expected exactly one Exec= line, got %r" % lines
    return lines[0][len("Exec=") :]


def test_shipped_desktop_has_no_internal_path():
    """The shipped .desktop leaks no `/home/` username path anywhere."""
    with open(DESKTOP_FILE) as f:
        text = f.read()
    assert "/home/" not in text, "shipped .desktop must not hardcode a /home/ path"


def test_shipped_desktop_exec_is_relative():
    """The shipped Exec line is path-free (no leading directory)."""
    with open(DESKTOP_FILE) as f:
        text = f.read()
    value = _exec_value(text)
    assert not value.startswith("/"), (
        "shipped Exec must be path-free (e.g. `Exec=blog`), got %r" % value
    )
    assert "/" not in value, (
        "shipped Exec must carry no directory component, got %r" % value
    )


def test_install_rewrites_exec_to_absolute_local_bin(tmp_path):
    """After install under a temp HOME, the installed Exec is the absolute symlink."""
    home = tmp_path / "home"
    home.mkdir()
    env = dict(os.environ)
    env["HOME"] = str(home)

    res = subprocess.run(
        ["bash", INSTALL_SH],
        env=env,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, "install.sh failed: %s\n%s" % (res.stdout, res.stderr)

    installed = home / ".local" / "share" / "applications" / "retro-writer.desktop"
    assert installed.exists(), "install.sh did not place the desktop entry"

    text = installed.read_text()
    value = _exec_value(text)
    expected = str(home / ".local" / "bin" / "blog")
    assert value == expected, "installed Exec %r != expected %r" % (value, expected)
