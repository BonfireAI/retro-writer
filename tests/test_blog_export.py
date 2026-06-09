"""Tests for bin/blog-export — the .wg -> .md exporter.

We invoke the real bash script via subprocess. The drafts dir is always a
temp dir (via RETRO_WRITER_DIR), never the user's ~/writing. The conversion
step needs wordgrinder; those assertions are skipif-gated (wordgrinder IS
installed here and in CI).
"""

import os
import shutil
import subprocess

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLOG_EXPORT = os.path.join(REPO_ROOT, "bin", "blog-export")

HAS_WG = shutil.which("wordgrinder") is not None
needs_wg = pytest.mark.skipif(not HAS_WG, reason="wordgrinder not installed")


def run_export(args, writing_dir):
    """Run blog-export with a temp RETRO_WRITER_DIR; return CompletedProcess."""
    env = dict(os.environ)
    env["RETRO_WRITER_DIR"] = str(writing_dir)
    return subprocess.run(
        ["bash", BLOG_EXPORT, *args],
        env=env,
        capture_output=True,
        text=True,
    )


def make_wg(writing_dir, name, text):
    """Create a real .wg draft by converting text via wordgrinder."""
    txt = writing_dir / (name + ".txt")
    txt.write_text(text)
    wg = writing_dir / (name + ".wg")
    subprocess.run(
        ["wordgrinder", "--convert", str(txt), str(wg)],
        check=True, capture_output=True,
    )
    return wg


# --- static / syntax -------------------------------------------------------

def test_bash_syntax_clean():
    """bash -n on blog-export is clean."""
    rc = subprocess.run(["bash", "-n", BLOG_EXPORT]).returncode
    assert rc == 0


# --- argument handling (no wordgrinder needed for error paths) -------------

def test_too_many_args_errors(tmp_path):
    res = run_export(["a.wg", "b.wg"], tmp_path)
    assert res.returncode != 0
    assert "too many arguments" in res.stderr


def test_missing_file_errors(tmp_path):
    res = run_export([str(tmp_path / "nope.wg")], tmp_path)
    assert res.returncode != 0
    assert "file not found" in res.stderr


def test_non_wg_arg_errors(tmp_path):
    """An existing non-.wg file is rejected."""
    other = tmp_path / "notes.txt"
    other.write_text("hello")
    res = run_export([str(other)], tmp_path)
    assert res.returncode != 0
    assert "expected a .wg file" in res.stderr


def test_no_drafts_errors(tmp_path):
    """No-arg with an empty drafts dir errors that there are no drafts."""
    res = run_export([], tmp_path)
    assert res.returncode != 0
    assert "no *.wg drafts found" in res.stderr


def test_missing_drafts_dir_errors(tmp_path):
    """No-arg with a nonexistent drafts dir errors clearly."""
    missing = tmp_path / "no_such_dir"
    res = run_export([], missing)
    assert res.returncode != 0
    assert "drafts dir not found" in res.stderr


# --- conversion (needs wordgrinder) ----------------------------------------

@needs_wg
def test_explicit_arg_converts(tmp_path):
    """An explicit .wg path is converted to <basename>.md beside it."""
    wg = make_wg(tmp_path, "post", "Hello world.")
    res = run_export([str(wg)], tmp_path)
    assert res.returncode == 0, res.stderr
    md = tmp_path / "post.md"
    assert md.is_file()
    assert "Exported:" in res.stdout
    assert str(md) in res.stdout
    assert "Hello world." in md.read_text()


@needs_wg
def test_no_arg_picks_newest(tmp_path):
    """No-arg converts the most-recently-modified *.wg in the drafts dir."""
    old = make_wg(tmp_path, "old", "Old draft.")
    new = make_wg(tmp_path, "new", "New draft.")
    # Force a clearly newer mtime on `new`.
    os.utime(old, (1_000_000, 1_000_000))
    os.utime(new, (2_000_000, 2_000_000))
    res = run_export([], tmp_path)
    assert res.returncode == 0, res.stderr
    assert (tmp_path / "new.md").is_file()
    assert "new.md" in res.stdout
    # The older draft should NOT have been the one exported.
    assert "New draft." in (tmp_path / "new.md").read_text()


@needs_wg
def test_output_basename_next_to_source(tmp_path):
    """Output .md sits next to the source, same basename."""
    sub = tmp_path / "drafts"
    sub.mkdir()
    wg = make_wg(sub, "essay", "Body text.")
    res = run_export([str(wg)], tmp_path)
    assert res.returncode == 0, res.stderr
    assert (sub / "essay.md").is_file()


# --- error surfacing (Elegance Law) ----------------------------------------

def test_blog_export_surfaces_wordgrinder_error_on_failure(tmp_path):
    """blog-export must surface wordgrinder's real stderr, not swallow it.

    Uses a fake wordgrinder that prints a unique marker to stderr and exits 1.
    The marker must appear in blog-export's stderr so the caller learns WHY the
    conversion failed (Elegance Law: failure is how machinery communicates).
    """
    # Create a fake wordgrinder that emits a unique marker and exits nonzero.
    fake_bin = tmp_path / "fakebin"
    fake_bin.mkdir()
    fake_wg = fake_bin / "wordgrinder"
    fake_wg.write_text("#!/usr/bin/env bash\necho 'WORDGRINDER_REAL_ERROR_MARKER_42' >&2\nexit 1\n")
    fake_wg.chmod(0o755)

    # Create a valid-looking .wg source file (blog-export only checks existence + .wg).
    src = tmp_path / "draft.wg"
    src.write_text("")

    env = dict(os.environ)
    env["RETRO_WRITER_DIR"] = str(tmp_path)
    # Prepend the fake bin dir so our fake wordgrinder is found first.
    env["PATH"] = str(fake_bin) + os.pathsep + env.get("PATH", "")

    res = subprocess.run(
        ["bash", BLOG_EXPORT, str(src)],
        env=env,
        capture_output=True,
        text=True,
    )

    assert res.returncode != 0, "expected nonzero exit when wordgrinder fails"
    assert "WORDGRINDER_REAL_ERROR_MARKER_42" in res.stderr, (
        f"wordgrinder error marker not found in blog-export stderr.\n"
        f"stderr was: {res.stderr!r}\n"
        f"stdout was: {res.stdout!r}"
    )
