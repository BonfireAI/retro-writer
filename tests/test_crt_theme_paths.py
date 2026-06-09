"""Coverage of crt-theme's error branches, the interactive menu, and helpers.

These drive the failure paths (bad manifest/theme JSON, DB read/write errors,
missing cool-retro-term) and the interactive `cmd_menu` loop — all our code —
against temp fixtures and monkeypatched I/O. The real DB is never touched.
"""

import builtins
import json
import sqlite3

import pytest


# --- load_manifest error branches ------------------------------------------

def test_load_manifest_missing_exits(crt, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(crt, "MANIFEST_PATH", str(tmp_path / "nope.json"))
    with pytest.raises(SystemExit):
        crt.load_manifest()
    assert "manifest not found" in capsys.readouterr().err


def test_load_manifest_bad_json_exits(crt, monkeypatch, tmp_path, capsys):
    bad = tmp_path / "manifest.json"
    bad.write_text("{ not json")
    monkeypatch.setattr(crt, "MANIFEST_PATH", str(bad))
    with pytest.raises(SystemExit):
        crt.load_manifest()
    assert "could not read theme manifest" in capsys.readouterr().err


def test_load_manifest_empty_exits(crt, monkeypatch, tmp_path, capsys):
    empty = tmp_path / "manifest.json"
    empty.write_text("[]")
    monkeypatch.setattr(crt, "MANIFEST_PATH", str(empty))
    with pytest.raises(SystemExit):
        crt.load_manifest()
    assert "empty or malformed" in capsys.readouterr().err


# --- load_theme_json error branches ----------------------------------------

def test_load_theme_json_missing_file_exits(crt, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(crt, "THEMES_DIR", str(tmp_path))
    with pytest.raises(SystemExit):
        crt.load_theme_json({"key": "x", "file": "ghost.json"})
    assert "theme file missing" in capsys.readouterr().err


def test_load_theme_json_bad_json_exits(crt, monkeypatch, tmp_path, capsys):
    (tmp_path / "broken.json").write_text("{ nope")
    monkeypatch.setattr(crt, "THEMES_DIR", str(tmp_path))
    with pytest.raises(SystemExit):
        crt.load_theme_json({"key": "x", "file": "broken.json"})
    assert "bad theme JSON" in capsys.readouterr().err


def test_load_theme_json_not_a_profile_exits(crt, monkeypatch, tmp_path, capsys):
    (tmp_path / "notprofile.json").write_text('{"hello": "world"}')
    monkeypatch.setattr(crt, "THEMES_DIR", str(tmp_path))
    with pytest.raises(SystemExit):
        crt.load_theme_json({"key": "x", "file": "notprofile.json"})
    assert "not a valid _CURRENT_PROFILE" in capsys.readouterr().err


# --- read_current_profile DB error -----------------------------------------

def test_read_current_profile_db_error_exits(crt, tmp_path, capsys):
    # A path that exists but is not a valid sqlite db triggers sqlite3.Error.
    notdb = tmp_path / "garbage.sqlite"
    notdb.write_text("this is definitely not sqlite")
    with pytest.raises(SystemExit):
        crt.read_current_profile(str(notdb))
    assert "could not read settings DB" in capsys.readouterr().err


# --- apply_theme error branches --------------------------------------------

def test_apply_theme_backup_failure_exits(crt, temp_db, monkeypatch, capsys):
    def boom(*a, **k):
        raise OSError("disk full")
    monkeypatch.setattr(crt.shutil, "copy2", boom)
    prof = crt.load_theme("amber")
    with pytest.raises(SystemExit):
        crt.apply_theme(temp_db, prof, "Classic Amber")
    assert "could not back up DB" in capsys.readouterr().err


def test_apply_theme_write_failure_exits(crt, temp_db, monkeypatch, capsys):
    """A sqlite error during the UPDATE write exits with a clear message."""
    real_connect = crt.sqlite3.connect

    class FailingConnection:
        """Wraps a real connection but raises on the UPDATE write."""

        def __init__(self, con):
            self._con = con

        def execute(self, sql, *args, **kwargs):
            if sql.strip().upper().startswith("UPDATE"):
                raise sqlite3.OperationalError("database is locked")
            return self._con.execute(sql, *args, **kwargs)

        def __getattr__(self, name):
            return getattr(self._con, name)

    def fail_on_update(path, *a, **k):
        return FailingConnection(real_connect(path, *a, **k))

    monkeypatch.setattr(crt.sqlite3, "connect", fail_on_update)
    prof = crt.load_theme("amber")
    with pytest.raises(SystemExit):
        crt.apply_theme(temp_db, prof, "Classic Amber")
    assert "could not write theme to DB" in capsys.readouterr().err


# --- launch error branch ---------------------------------------------------

def test_launch_missing_binary_exits(crt, monkeypatch, capsys):
    def no_binary(*a, **k):
        raise FileNotFoundError("cool-retro-term")
    # crt.subprocess is the fake; give it a Popen that raises.
    monkeypatch.setattr(crt.subprocess, "Popen", no_binary)
    with pytest.raises(SystemExit):
        crt.launch("Some Theme")
    assert "not found on PATH" in capsys.readouterr().err


def test_launch_calls_popen_when_present(crt, monkeypatch):
    seen = {}
    monkeypatch.setattr(
        crt.subprocess, "Popen", lambda args, **k: seen.setdefault("args", args)
    )
    crt.launch("Classic Amber")
    assert seen["args"][0] == "cool-retro-term"
    assert "Classic Amber" in seen["args"]


# --- print_theme_line idx=None branch --------------------------------------

def test_print_theme_line_index_vs_none(crt, capsys):
    """With an index the line is numbered; with None it is not."""
    entry = {"key": "amber", "label": "Classic Amber", "desc": "warm"}
    prof = crt.load_theme("amber")

    crt.print_theme_line(7, entry, prof)
    numbered = capsys.readouterr().out
    assert numbered.lstrip().startswith("7."), numbered

    crt.print_theme_line(None, entry, prof)
    unnumbered = capsys.readouterr().out
    assert "Classic Amber" in unnumbered
    # The unindexed first line starts straight into the swatch escape, not a
    # "<n>." number prefix.
    first_line = unnumbered.splitlines()[0]
    assert not first_line.lstrip().startswith(("0.", "1.", "7."))


# --- cmd_menu interactive loop ---------------------------------------------

def _feed_inputs(monkeypatch, answers):
    """Make builtins.input() return the queued answers in order."""
    it = iter(answers)
    monkeypatch.setattr(builtins, "input", lambda *a, **k: next(it))


def test_menu_quit_immediately(crt, temp_db, use_db, monkeypatch, capsys):
    use_db(temp_db)
    _feed_inputs(monkeypatch, ["q"])
    crt.main([])  # no command -> menu
    assert "last-previewed theme remains the default" in capsys.readouterr().out


def test_menu_invalid_then_quit(crt, temp_db, use_db, monkeypatch, capsys):
    use_db(temp_db)
    _feed_inputs(monkeypatch, ["banana", "99", "q"])
    crt.main([])
    out = capsys.readouterr().out
    assert "please enter a number" in out


def test_menu_pick_applies_and_launches(crt, temp_db, use_db, monkeypatch, capsys):
    use_db(temp_db)
    popened = []
    monkeypatch.setattr(crt.subprocess, "Popen", lambda *a, **k: popened.append(a))
    # Pick item 1 (amber), then quit.
    _feed_inputs(monkeypatch, ["1", "q"])
    crt.main([])
    out = capsys.readouterr().out
    assert "applied 'Classic Amber'" in out
    assert popened, "menu pick should launch a preview"
    # The DB now holds the picked theme.
    assert crt.read_current_profile(temp_db) == crt.load_theme("amber")


def test_menu_eof_returns(crt, temp_db, use_db, monkeypatch):
    """Ctrl-D / EOF on the prompt exits the menu cleanly."""
    use_db(temp_db)

    def raise_eof(*a, **k):
        raise EOFError()

    monkeypatch.setattr(builtins, "input", raise_eof)
    crt.main([])  # must return without raising


def test_menu_empty_input_quits(crt, temp_db, use_db, monkeypatch, capsys):
    use_db(temp_db)
    _feed_inputs(monkeypatch, [""])
    crt.main([])
    assert "last-previewed theme remains" in capsys.readouterr().out


# --- explicit-entries paths of load_theme / match_theme --------------------

def test_load_theme_with_explicit_entries(crt):
    """Passing entries explicitly skips the load_manifest fallback."""
    entries = crt.load_manifest()
    prof = crt.load_theme("amber", entries=entries)
    assert prof["fontColor"] == "#ff8100"


def test_match_theme_with_explicit_entries(crt):
    """match_theme accepts a caller-supplied manifest."""
    entries = crt.load_manifest()
    prof = crt.load_theme("commodore-cyan", entries=entries)
    got = crt.match_theme(prof, entries=entries)
    assert got["key"] == "commodore-cyan"
