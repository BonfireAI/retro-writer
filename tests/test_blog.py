"""Tests for bin/blog — the launcher's --print-cmd no-launch seam.

We never actually launch cool-retro-term (no display in CI). `blog --print-cmd`
prints the exact command it WOULD exec and exits 0, so we can assert its shape.
"""

import os
import subprocess

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLOG = os.path.join(REPO_ROOT, "bin", "blog")


def run_blog(args=(), env_extra=None, writing_dir=None):
    env = dict(os.environ)
    if writing_dir is not None:
        env["RETRO_WRITER_DIR"] = str(writing_dir)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", BLOG, *args], env=env, capture_output=True, text=True
    )


def test_bash_syntax_clean():
    """bash -n on blog is clean."""
    assert subprocess.run(["bash", "-n", BLOG]).returncode == 0


def test_print_cmd_shape(tmp_path):
    """`blog --print-cmd` prints the cool-retro-term command and exits 0."""
    res = run_blog(["--print-cmd"], writing_dir=tmp_path)
    assert res.returncode == 0
    cmd = res.stdout.strip()
    assert "cool-retro-term" in cmd
    assert "--fullscreen" in cmd
    assert "--workdir" in cmd
    # The workdir is honored from RETRO_WRITER_DIR.
    assert str(tmp_path) in cmd
    # `-e wordgrinder` MUST be LAST (it catches all following args).
    assert cmd.endswith("-e wordgrinder")
    # The broken --profile flag must NOT be used.
    assert "--profile" not in cmd


def test_dry_run_env_var(tmp_path):
    """RETRO_WRITER_DRY_RUN=1 also prints the command without launching."""
    res = run_blog([], env_extra={"RETRO_WRITER_DRY_RUN": "1"}, writing_dir=tmp_path)
    assert res.returncode == 0
    assert "cool-retro-term" in res.stdout
    assert res.stdout.strip().endswith("-e wordgrinder")


def test_print_cmd_does_not_create_writing_dir(tmp_path):
    """--print-cmd is side-effect free: it must NOT mkdir the drafts dir."""
    wdir = tmp_path / "would_be_created"
    res = run_blog(["--print-cmd"], writing_dir=wdir)
    assert res.returncode == 0
    assert not wdir.exists(), "--print-cmd should not create the writing dir"
