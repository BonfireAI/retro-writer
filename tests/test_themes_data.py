"""Data-integrity tests for themes/*.json and themes/manifest.json.

These guard the theme assets: every profile parses, shares the same key set as
the cool-retro-term _CURRENT_PROFILE schema, has valid colors, and every theme
is wired into the manifest (and vice versa).
"""

import json
import os
import re

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THEMES_DIR = os.path.join(REPO_ROOT, "themes")
MANIFEST_PATH = os.path.join(THEMES_DIR, "manifest.json")

# The base profile whose 23-key set every theme must mirror.
BASE_PROFILE = "amber.json"

HEX6 = re.compile(r"^#[0-9a-fA-F]{6}$")


def _theme_json_files():
    return sorted(
        f for f in os.listdir(THEMES_DIR)
        if f.endswith(".json") and f != "manifest.json"
    )


def test_there_are_ten_themes():
    """Sanity: the gallery is the documented set of 10 themes."""
    assert len(_theme_json_files()) == 10


@pytest.mark.parametrize("fname", _theme_json_files())
def test_theme_parses(fname):
    """Every themes/*.json is valid JSON and an object."""
    with open(os.path.join(THEMES_DIR, fname)) as f:
        data = json.load(f)
    assert isinstance(data, dict)


@pytest.mark.parametrize("fname", _theme_json_files())
def test_theme_key_set_matches_base(fname):
    """Each theme has exactly the same 23 keys as the base profile."""
    with open(os.path.join(THEMES_DIR, BASE_PROFILE)) as f:
        base_keys = set(json.load(f).keys())
    assert len(base_keys) == 23
    with open(os.path.join(THEMES_DIR, fname)) as f:
        keys = set(json.load(f).keys())
    assert keys == base_keys, (
        "%s key set differs from %s: extra=%s missing=%s"
        % (fname, BASE_PROFILE, keys - base_keys, base_keys - keys)
    )


@pytest.mark.parametrize("fname", _theme_json_files())
def test_theme_colors_are_valid_hex(fname):
    """fontColor and backgroundColor are valid #rrggbb."""
    with open(os.path.join(THEMES_DIR, fname)) as f:
        data = json.load(f)
    assert HEX6.match(data["fontColor"]), "%s bad fontColor" % fname
    assert HEX6.match(data["backgroundColor"]), "%s bad backgroundColor" % fname


# --- manifest --------------------------------------------------------------

def _manifest():
    with open(MANIFEST_PATH) as f:
        return json.load(f)


def test_manifest_parses_and_nonempty():
    entries = _manifest()
    assert isinstance(entries, list) and entries


def test_manifest_entries_have_required_fields():
    for e in _manifest():
        for field in ("key", "label", "desc", "file"):
            assert field in e, "manifest entry missing %s: %r" % (field, e)


def test_manifest_keys_unique():
    keys = [e["key"] for e in _manifest()]
    assert len(keys) == len(set(keys)), "duplicate manifest keys: %s" % keys


def test_manifest_files_exist():
    for e in _manifest():
        path = os.path.join(THEMES_DIR, e["file"])
        assert os.path.isfile(path), "manifest references missing file: %s" % e["file"]


def test_every_theme_file_is_in_manifest():
    """No orphan theme files: every themes/*.json is covered by the manifest."""
    manifest_files = {e["file"] for e in _manifest()}
    on_disk = set(_theme_json_files())
    assert on_disk == manifest_files, (
        "manifest/disk mismatch: only-on-disk=%s only-in-manifest=%s"
        % (on_disk - manifest_files, manifest_files - on_disk)
    )
