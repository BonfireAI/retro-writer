"""Behavior tests for bin/install.sh — the give-away's install entry point.

install.sh is the README's only documented install instruction (`./bin/install.sh`),
yet it was previously only static-checked with shellcheck. These tests RUN it.

install.sh derives every destination from $HOME ($HOME/.local/bin,
$HOME/.local/share/applications, $HOME/writing), so it is fully exercisable
against a pytest tmp_path used as a throwaway HOME — the real home is never
touched. We assert symlink + directory creation, and that the installed desktop
entry's Exec points at a launcher that ACTUALLY EXISTS for this user (the
"clicking 'Retro Writer' silently fails" guard — the Exec *string* itself is
pinned in tests/test_desktop_entry.py). We never require
update-desktop-database to succeed (install.sh guards it with `|| true`).
"""

import configparser
import os
import subprocess

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTALL_SH = os.path.join(REPO_ROOT, "bin", "install.sh")
BIN_SRC = os.path.join(REPO_ROOT, "bin")

# The three launchers install.sh symlinks into ~/.local/bin/.
LINKED_CMDS = ("blog", "blog-export", "crt-theme")


def run_install(home):
    """Run install.sh with HOME pinned to a throwaway dir; capture output.

    We pass a minimal env (PATH preserved so `bash`/`mkdir`/`ln` resolve) plus
    the temp HOME, so the script cannot reach the operator's real home.
    """
    env = dict(os.environ)
    env["HOME"] = str(home)
    return subprocess.run(
        ["bash", INSTALL_SH], env=env, capture_output=True, text=True
    )


def test_install_creates_symlinks_and_dirs(tmp_path):
    """A clean run exits 0 and lays down the symlinks, desktop entry, drafts dir."""
    res = run_install(tmp_path)
    assert res.returncode == 0, res.stderr

    local_bin = tmp_path / ".local" / "bin"
    # (a) each launcher exists as a symlink pointing back into the repo's bin/.
    for cmd in LINKED_CMDS:
        link = local_bin / cmd
        assert link.is_symlink(), f"{cmd} should be a symlink in ~/.local/bin"
        target = os.path.realpath(str(link))
        assert target == os.path.realpath(os.path.join(BIN_SRC, cmd)), (
            f"{cmd} should resolve to the repo's bin/{cmd}, got {target}"
        )

    # (b) the desktop entry was installed.
    desktop = tmp_path / ".local" / "share" / "applications" / "retro-writer.desktop"
    assert desktop.is_file(), "retro-writer.desktop should be installed"

    # (c) the drafts directory was created.
    assert (tmp_path / "writing").is_dir(), "~/writing drafts dir should be created"


def test_install_is_idempotent(tmp_path):
    """Running install.sh twice still exits 0 and leaves resolving symlinks."""
    first = run_install(tmp_path)
    assert first.returncode == 0, first.stderr

    second = run_install(tmp_path)
    assert second.returncode == 0, second.stderr

    local_bin = tmp_path / ".local" / "bin"
    for cmd in LINKED_CMDS:
        link = local_bin / cmd
        assert link.is_symlink(), f"{cmd} should still be a symlink after re-run"
        # The link must still resolve to a real file (not dangle after refresh).
        assert os.path.exists(os.path.realpath(str(link))), (
            f"{cmd} symlink should still resolve after a second install run"
        )

    # The desktop entry and drafts dir survive the re-run too.
    desktop = tmp_path / ".local" / "share" / "applications" / "retro-writer.desktop"
    assert desktop.is_file()
    assert (tmp_path / "writing").is_dir()


def test_installed_desktop_exec_target_is_a_real_clickable_file(tmp_path):
    """The installed Exec points at a launcher that EXISTS for this user.

    The hardcoded-home bug's user-visible symptom was: on any machine whose
    home is not the author's, clicking 'Retro Writer' in the app menu silently
    fails because the desktop entry's Exec aims at a nonexistent path. The
    string-equality of that Exec is pinned in tests/test_desktop_entry.py; this
    test closes the other half — that the target the launcher resolves to is a
    real file (here, the `blog` symlink install.sh just created under a
    throwaway HOME, never the author's /home).
    """
    home = tmp_path / "elsewhere"
    home.mkdir()

    res = run_install(home)
    assert res.returncode == 0, res.stderr

    installed = home / ".local" / "share" / "applications" / "retro-writer.desktop"
    assert installed.is_file(), "install.sh did not place the desktop entry"

    parser = configparser.ConfigParser(interpolation=None)
    parser.read(str(installed))
    exec_target = parser["Desktop Entry"]["Exec"]

    # Symptom guard: the launcher target must exist, or the menu item dies.
    assert os.path.exists(exec_target), (
        "installed Exec target does not exist — the app-menu launcher would "
        "silently fail: " + exec_target
    )
    # And it must be exactly the blog symlink install.sh laid down for THIS user.
    blog_link = home / ".local" / "bin" / "blog"
    assert os.path.realpath(exec_target) == os.path.realpath(str(blog_link))
    # Never leak the author's home onto another user's machine.
    assert "/home/ishtar/" not in exec_target
