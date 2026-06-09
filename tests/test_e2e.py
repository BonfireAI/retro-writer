"""End-to-end, headless (no GUI) round-trip tests.

Two real round-trips, no display required:
  1. text -> wordgrinder --convert -> .wg -> blog-export -> .md, assert clean
     content (skipif no wordgrinder).
  2. crt-theme `set <key>` against a TEMP DB -> `current` reflects it.
"""

import os
import shutil
import subprocess

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLOG_EXPORT = os.path.join(REPO_ROOT, "bin", "blog-export")
CRT_THEME = os.path.join(REPO_ROOT, "bin", "crt-theme")

HAS_WG = shutil.which("wordgrinder") is not None
needs_wg = pytest.mark.skipif(not HAS_WG, reason="wordgrinder not installed")


@needs_wg
def test_e2e_draft_to_markdown(tmp_path):
    """Full draft->markdown: write text, make a .wg, export, verify content."""
    writing = tmp_path / "writing"
    writing.mkdir()

    body = "The Lighthouse\n\nIt was a clear night and the lamp turned slowly.\n"
    src_txt = writing / "story.txt"
    src_txt.write_text(body)

    # text -> .wg
    wg = writing / "story.wg"
    subprocess.run(
        ["wordgrinder", "--convert", str(src_txt), str(wg)],
        check=True, capture_output=True,
    )
    assert wg.is_file()

    # .wg -> .md via OUR exporter (no-arg picks newest in RETRO_WRITER_DIR)
    env = dict(os.environ)
    env["RETRO_WRITER_DIR"] = str(writing)
    res = subprocess.run(
        ["bash", BLOG_EXPORT], env=env, capture_output=True, text=True
    )
    assert res.returncode == 0, res.stderr

    md = writing / "story.md"
    assert md.is_file()
    text = md.read_text()
    assert "The Lighthouse" in text
    assert "the lamp turned slowly" in text


def test_e2e_set_then_current_via_cli(tmp_path):
    """crt-theme `set` then `current` against a temp DB round-trips the theme."""
    import json
    import sqlite3

    db = tmp_path / "crt.sqlite"
    con = sqlite3.connect(str(db))
    con.execute("CREATE TABLE settings(setting TEXT UNIQUE, value TEXT)")
    con.execute(
        "INSERT INTO settings(setting, value) VALUES ('_CURRENT_PROFILE', '{}')"
    )
    con.commit()
    con.close()

    env = dict(os.environ)
    env["CRT_THEME_DB"] = str(db)

    # Use a UNIQUELY-colored theme so `current`'s color-match is unambiguous.
    # (amber / clean-amber / vintage-burn share the same #ff8100/#000000.)
    key = "wordperfect-blue"
    set_res = subprocess.run(
        ["python3", CRT_THEME, "set", key],
        env=env, capture_output=True, text=True,
    )
    assert set_res.returncode == 0, set_res.stderr

    cur_res = subprocess.run(
        ["python3", CRT_THEME, "current"],
        env=env, capture_output=True, text=True,
    )
    assert cur_res.returncode == 0, cur_res.stderr
    assert key in cur_res.stdout

    # And the DB physically holds the wordperfect-blue profile.
    with open(os.path.join(REPO_ROOT, "themes", key + ".json")) as f:
        expected = json.load(f)
    con = sqlite3.connect(str(db))
    row = con.execute(
        "SELECT value FROM settings WHERE setting='_CURRENT_PROFILE'"
    ).fetchone()
    con.close()
    assert json.loads(row[0]) == expected
