"""Unit tests for bin/crt-theme — the CRT theme picker.

These exercise our python logic against a TEMP sqlite DB that mirrors
cool-retro-term's real schema. The user's real DB is never read or written
(see conftest's no_real_db / no_side_effects guards).
"""

import json
import os
import re

import pytest


# --- find_db ---------------------------------------------------------------

def test_find_db_single_with_ini(crt, tmp_path):
    """One .sqlite with a coolretroterm1 .ini sidecar is found."""
    dbdir = tmp_path / "Databases"
    dbdir.mkdir()
    db = dbdir / "abc.sqlite"
    db.write_text("")
    (dbdir / "abc.ini").write_text("[General]\nName=coolretroterm1\n")
    found = crt.find_db(db_glob=str(dbdir / "*.sqlite"))
    assert found == str(db)


def test_find_db_multiple_picks_coolretroterm1(crt, tmp_path):
    """With several .sqlite files, the one whose .ini says coolretroterm1 wins."""
    dbdir = tmp_path / "Databases"
    dbdir.mkdir()
    # A decoy DB with a different app name.
    decoy = dbdir / "0000.sqlite"
    decoy.write_text("")
    (dbdir / "0000.ini").write_text("[General]\nName=someotherapp\n")
    # The real one.
    real = dbdir / "9999.sqlite"
    real.write_text("")
    (dbdir / "9999.ini").write_text("[General]\nName=coolretroterm1\n")
    found = crt.find_db(db_glob=str(dbdir / "*.sqlite"))
    assert found == str(real)


def test_find_db_none_when_empty(crt, tmp_path):
    """No matching files -> None (callers turn this into an actionable error)."""
    dbdir = tmp_path / "Databases"
    dbdir.mkdir()
    assert crt.find_db(db_glob=str(dbdir / "*.sqlite")) is None


def test_find_db_single_no_ini_fallback(crt, tmp_path):
    """A lone .sqlite with no readable .ini is still returned (fallback)."""
    dbdir = tmp_path / "Databases"
    dbdir.mkdir()
    db = dbdir / "solo.sqlite"
    db.write_text("")
    found = crt.find_db(db_glob=str(dbdir / "*.sqlite"))
    assert found == str(db)


def test_find_db_env_override(crt, make_db, monkeypatch):
    """CRT_THEME_DB pins an exact path, bypassing the glob entirely."""
    db = make_db()
    monkeypatch.setenv("CRT_THEME_DB", db)
    assert crt.find_db() == db


def test_find_db_env_override_missing_file(crt, monkeypatch):
    """A CRT_THEME_DB pointing at a nonexistent file resolves to None."""
    monkeypatch.setenv("CRT_THEME_DB", "/nope/does/not/exist.sqlite")
    assert crt.find_db() is None


# --- apply_theme / read_current_profile ------------------------------------

def test_apply_theme_writes_profile_roundtrip(crt, temp_db):
    """apply_theme writes the profile; read_current_profile reads it back equal."""
    prof = crt.load_theme("amber")
    crt.apply_theme(temp_db, prof, "Classic Amber")
    got = crt.read_current_profile(temp_db)
    assert got == prof


def test_apply_theme_written_json_equals_theme_file(crt, temp_db):
    """The persisted _CURRENT_PROFILE JSON equals the on-disk theme file."""
    with open(os.path.join(crt.THEMES_DIR, "cottoncandy.json")) as f:
        theme_on_disk = json.load(f)
    prof = crt.load_theme("cottoncandy")
    crt.apply_theme(temp_db, prof, "Cotton Candy")
    got = crt.read_current_profile(temp_db)
    assert got == theme_on_disk


def test_apply_theme_makes_backup(crt, temp_db):
    """apply_theme leaves a .crt-theme.bak copy next to the DB."""
    prof = crt.load_theme("green-p1")
    bak = crt.apply_theme(temp_db, prof, "P1 Phosphor Green")
    assert os.path.isfile(bak)
    assert bak == temp_db + ".crt-theme.bak"


def test_read_current_profile_none_when_empty(crt, make_db):
    """A DB with no _CURRENT_PROFILE row reads back as None, not a crash."""
    # Build a DB with the table but NO row.
    import sqlite3
    db = make_db()
    con = sqlite3.connect(db)
    con.execute("DELETE FROM settings")
    con.commit()
    con.close()
    assert crt.read_current_profile(db) is None


def test_read_current_profile_none_on_garbage(crt, make_db):
    """A non-JSON value in the row reads back as None (tolerant)."""
    import sqlite3
    db = make_db()
    con = sqlite3.connect(db)
    con.execute(
        "UPDATE settings SET value=? WHERE setting='_CURRENT_PROFILE'",
        ("not json {{",),
    )
    con.commit()
    con.close()
    assert crt.read_current_profile(db) is None


# --- match_theme / current -------------------------------------------------

def test_match_theme_identifies_set_theme(crt, make_db):
    """A DB set to a known theme's colors is matched back to that theme."""
    prof = crt.load_theme("wordperfect-blue")
    db = make_db(profile=prof)
    got = crt.read_current_profile(db)
    entry = crt.match_theme(got)
    assert entry is not None
    assert entry["key"] == "wordperfect-blue"


def test_match_theme_none_for_custom_colors(crt):
    """Hand-edited colors that match no theme return None."""
    custom = {"fontColor": "#123456", "backgroundColor": "#abcdef"}
    assert crt.match_theme(custom) is None


def test_match_theme_key_case_insensitive(crt, manifest):
    """match_theme_key normalizes case and the leading '#'."""
    prof = crt.load_theme("amber")
    entry = crt.match_theme_key(
        manifest, prof["fontColor"].upper(), prof["backgroundColor"].upper()
    )
    assert entry["key"] == "amber"


# --- load_theme / load_manifest --------------------------------------------

def test_load_theme_unknown_key_exits(crt):
    """An unknown theme key exits nonzero with an actionable message."""
    with pytest.raises(SystemExit) as exc:
        crt.load_theme("does-not-exist")
    assert exc.value.code == 2


def test_load_manifest_returns_entries(crt):
    """load_manifest returns the 10-theme list."""
    entries = crt.load_manifest()
    assert isinstance(entries, list)
    keys = [e["key"] for e in entries]
    assert "amber" in keys and "cottoncandy" in keys


# --- render_swatch / swatch ------------------------------------------------

def test_render_swatch_is_truecolor_ansi(crt):
    """render_swatch emits a well-formed ANSI 24-bit color sequence."""
    prof = crt.load_theme("amber")  # font #ff8100 on bg #000000
    s = crt.render_swatch(prof)
    # Background = bg rgb, then foreground = font rgb, then reset.
    assert "\033[48;2;0;0;0;38;2;255;129;0m" in s
    assert s.endswith("\033[0m")


def test_swatch_truecolor_shape_regex(crt):
    """The swatch matches the truecolor SGR grammar exactly."""
    s = crt.swatch("#3399ff", "#101010")
    m = re.match(
        r"^\033\[48;2;(\d+);(\d+);(\d+);38;2;(\d+);(\d+);(\d+)m.*\033\[0m$", s
    )
    assert m, "swatch is not a valid truecolor SGR sequence"
    br, bgc, bb, fr, fg, fb = map(int, m.groups())
    assert (br, bgc, bb) == (0x10, 0x10, 0x10)
    assert (fr, fg, fb) == (0x33, 0x99, 0xFF)


def test_hex_to_rgb_variants(crt):
    """hex_to_rgb handles #rrggbb, short #rgb, and bad input gracefully."""
    assert crt.hex_to_rgb("#ff8100") == (255, 129, 0)
    assert crt.hex_to_rgb("f80") == (255, 136, 0)
    assert crt.hex_to_rgb("garbage") == (128, 128, 128)
    assert crt.hex_to_rgb("#zzzzzz") == (128, 128, 128)


# --- CLI: main / list / set / current / errors -----------------------------

def test_cli_list_includes_every_label(crt, capsys):
    """`crt-theme list` prints every theme label from the manifest."""
    rc = crt.main(["list"])
    assert rc == 0
    out = capsys.readouterr().out
    for entry in crt.load_manifest():
        assert entry["label"] in out


def test_cli_set_writes_and_is_default(crt, make_db, monkeypatch, capsys):
    """`crt-theme set <key>` applies the theme to the (temp) DB."""
    db = make_db()
    monkeypatch.setenv("CRT_THEME_DB", db)
    rc = crt.main(["set", "green-soft"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Applied theme" in out and "green-soft" in out
    got = crt.read_current_profile(db)
    assert got == crt.load_theme("green-soft")


def test_cli_set_then_current_reports_it(crt, make_db, monkeypatch, capsys):
    """After `set X`, `current` reports theme X."""
    db = make_db()
    monkeypatch.setenv("CRT_THEME_DB", db)
    crt.main(["set", "commodore-cyan"])
    capsys.readouterr()  # discard set output
    rc = crt.main(["current"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "commodore-cyan" in out
    assert "Commodore Cyan" in out


def test_cli_show_applies_and_launches(crt, make_db, monkeypatch, capsys):
    """`crt-theme show <key>` applies AND triggers a launch (Popen stubbed)."""
    db = make_db()
    monkeypatch.setenv("CRT_THEME_DB", db)
    calls = []
    monkeypatch.setattr(crt.subprocess, "Popen", lambda *a, **k: calls.append(a))
    rc = crt.main(["show", "clean-amber"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Launching cool-retro-term" in out
    assert calls, "show should attempt to launch cool-retro-term"


def test_cli_set_unknown_key_exits_nonzero(crt, make_db, monkeypatch, capsys):
    """`set` with a bad key exits nonzero with a helpful message."""
    db = make_db()
    monkeypatch.setenv("CRT_THEME_DB", db)
    with pytest.raises(SystemExit) as exc:
        crt.main(["set", "bogus"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "unknown theme key" in err


def test_cli_set_missing_db_exits_actionable(crt, monkeypatch, capsys):
    """`set` with no findable DB exits nonzero with an actionable message."""
    # CRT_THEME_DB unset + glob points nowhere (autouse fixture) -> no DB.
    monkeypatch.delenv("CRT_THEME_DB", raising=False)
    with pytest.raises(SystemExit) as exc:
        crt.main(["set", "amber"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "settings DB not found" in err
    assert "Launch cool-retro-term once" in err


def test_cli_current_no_profile_exits(crt, make_db, monkeypatch, capsys):
    """`current` against a DB with no profile row exits nonzero."""
    import sqlite3
    db = make_db()
    con = sqlite3.connect(db)
    con.execute("DELETE FROM settings")
    con.commit()
    con.close()
    monkeypatch.setenv("CRT_THEME_DB", db)
    with pytest.raises(SystemExit) as exc:
        crt.main(["current"])
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "could not read current profile" in err


def test_cli_current_custom_colors_reports_none(crt, make_db, monkeypatch, capsys):
    """`current` with non-theme colors reports 'none'."""
    db = make_db(profile={"fontColor": "#abcdef", "backgroundColor": "#012345"})
    monkeypatch.setenv("CRT_THEME_DB", db)
    rc = crt.main(["current"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "none" in out.lower()


def test_apply_theme_no_row_to_update_exits(crt, make_db, monkeypatch):
    """If the table has no _CURRENT_PROFILE row, apply_theme exits nonzero."""
    import sqlite3
    db = make_db()
    con = sqlite3.connect(db)
    con.execute("DELETE FROM settings")
    con.commit()
    con.close()
    prof = crt.load_theme("amber")
    with pytest.raises(SystemExit):
        crt.apply_theme(db, prof, "Classic Amber")
