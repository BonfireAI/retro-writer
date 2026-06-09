"""Shared pytest fixtures for the retro-writer test suite.

The cockpit is glue around two external programs; these tests cover OUR code:
the `crt-theme` python tool, the bash launchers, and the theme data. Tests
NEVER touch the user's real cool-retro-term database — every DB lives in a
pytest tmp_path and is wired in via the CRT_THEME_DB env override.
"""

import importlib.util
import json
import os
import sqlite3
import sys

import pytest

# --- paths -----------------------------------------------------------------

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN_DIR = os.path.join(REPO_ROOT, "bin")
THEMES_DIR = os.path.join(REPO_ROOT, "themes")
MANIFEST_PATH = os.path.join(THEMES_DIR, "manifest.json")

CRT_THEME_PATH = os.path.join(BIN_DIR, "crt-theme")
BLOG_PATH = os.path.join(BIN_DIR, "blog")
BLOG_EXPORT_PATH = os.path.join(BIN_DIR, "blog-export")


def _import_crt_theme():
    """Import the hyphenated, extensionless `crt-theme` script as a module.

    The file is a plain executable named `crt-theme` (no .py), so it cannot be
    imported by name. We load it from its path under a clean module name and
    cache it: every fixture and test must share ONE module object, or
    monkeypatches applied by one wouldn't be seen by another.
    """
    cached = sys.modules.get("crt_theme")
    if cached is not None:
        return cached
    spec = importlib.util.spec_from_loader(
        "crt_theme", importlib.machinery.SourceFileLoader("crt_theme", CRT_THEME_PATH)
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["crt_theme"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def crt():
    """The imported crt-theme module (its `__main__` block does not run)."""
    return _import_crt_theme()


@pytest.fixture
def theme_files():
    """List of absolute paths to every themes/*.json (excluding the manifest)."""
    out = []
    for name in sorted(os.listdir(THEMES_DIR)):
        if name.endswith(".json") and name != "manifest.json":
            out.append(os.path.join(THEMES_DIR, name))
    return out


@pytest.fixture
def manifest():
    """The parsed themes/manifest.json (list of entry dicts)."""
    with open(MANIFEST_PATH) as f:
        return json.load(f)


def _make_db(path, profile=None):
    """Create a temp sqlite DB mirroring cool-retro-term's real schema.

    Schema is exactly `settings(setting TEXT UNIQUE, value TEXT)` and the
    `_CURRENT_PROFILE` row holds a JSON profile — same as the real app.
    """
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE settings(setting TEXT UNIQUE, value TEXT)")
    if profile is not None:
        con.execute(
            "INSERT INTO settings(setting, value) VALUES (?, ?)",
            ("_CURRENT_PROFILE", json.dumps(profile)),
        )
    else:
        # Real DBs always have the row present; default to an empty placeholder
        # so UPDATE has a row to hit.
        con.execute(
            "INSERT INTO settings(setting, value) VALUES (?, ?)",
            ("_CURRENT_PROFILE", "{}"),
        )
    con.commit()
    con.close()
    return path


@pytest.fixture
def temp_db(tmp_path):
    """A fresh temp DB with a placeholder _CURRENT_PROFILE row.

    Returns the path; callers seed it with a profile via `seed_profile`.
    """
    db = tmp_path / "coolretroterm.sqlite"
    _make_db(str(db))
    return str(db)


@pytest.fixture
def make_db(tmp_path):
    """Factory: make_db(profile=..., name=...) -> path to a temp DB."""
    counter = {"n": 0}

    def _factory(profile=None, name=None):
        counter["n"] += 1
        fname = name or ("db%d.sqlite" % counter["n"])
        path = tmp_path / fname
        _make_db(str(path), profile)
        return str(path)

    return _factory


@pytest.fixture
def use_db(monkeypatch):
    """Point crt-theme at a given DB path via the CRT_THEME_DB override."""

    def _use(path):
        monkeypatch.setenv("CRT_THEME_DB", str(path))

    return _use


@pytest.fixture(autouse=True)
def no_real_db(monkeypatch):
    """Safety net: ensure tests can never glob the user's real DB.

    Point the glob at a path inside /nonexistent so an accidentally-unset
    CRT_THEME_DB still cannot reach the real cool-retro-term database.
    """
    # Imported lazily so this runs before any test that needs the module.
    crt = _import_crt_theme()
    monkeypatch.setattr(
        crt, "DB_GLOB", "/nonexistent-retro-writer-test/Databases/*.sqlite"
    )


class _FakeSubprocess:
    """Stand-in for crt-theme's `subprocess` ref: stubs run/Popen, no GUIs.

    We replace the module *reference* inside crt-theme rather than mutating the
    real `subprocess` module, so the test files' own subprocess calls (which
    invoke the real bash scripts) are completely unaffected.
    """

    # Mirror the stdlib constants crt-theme references in its run() call.
    DEVNULL = -3
    PIPE = -1

    def __init__(self):
        self.run_calls = []
        self.popen_calls = []

    def run(self, *a, **k):
        self.run_calls.append((a, k))
        return None

    def Popen(self, *a, **k):
        self.popen_calls.append((a, k))
        return None


class _FakeTime:
    """Stand-in for crt-theme's `time` ref: no real sleeping in tests."""

    def sleep(self, *a, **k):
        return None


@pytest.fixture(autouse=True)
def no_side_effects(monkeypatch):
    """Neutralize the real-world side effects in apply_theme/launch.

    - pkill / Popen must never run during tests (they'd kill or spawn GUIs).
    - time.sleep(1) in apply_theme would make the suite needlessly slow.
    Tests that assert command shape do so via the bash `--print-cmd` seam,
    not by letting the python tool spawn anything.
    """
    crt = _import_crt_theme()
    monkeypatch.setattr(crt, "subprocess", _FakeSubprocess())
    monkeypatch.setattr(crt, "time", _FakeTime())
