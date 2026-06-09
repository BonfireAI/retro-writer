# retro-writer

A retro writing cockpit for Linux — WordGrinder running inside cool-retro-term,
themed for true '90s phosphor glow, outputting clean markdown.

The environment is the point. See `docs/superpowers/specs/` for the design.

## Layout

| Path | What |
|------|------|
| `bin/blog` | One-command launcher: cool-retro-term, fullscreen, in `~/writing`, running WordGrinder |
| `bin/blog-export` | Converts a WordGrinder draft (`.wg`) to clean Markdown (`.md`) |
| `bin/install.sh` | Symlinks the two commands into `~/.local/bin/` and installs the desktop entry |
| `desktop/retro-writer.desktop` | COSMIC-clickable launcher (points at `~/.local/bin/blog`) |
| `~/writing/` | Personal drafts (`.wg` + exported `.md`). **Kept out of this repo** (see `.gitignore`). |

## Install

```sh
bin/install.sh
```

This symlinks `blog` and `blog-export` into `~/.local/bin/`, installs the
`Retro Writer` desktop entry into `~/.local/share/applications/`, and creates
`~/writing/`. Ensure `~/.local/bin` is on your `PATH`.

## Usage

- **`blog`** — open the cockpit and write. Launches cool-retro-term fullscreen
  in `~/writing/`, running WordGrinder. (Or click **Retro Writer** in COSMIC.)
- **`blog-export [file.wg]`** — export a draft to clean Markdown.
  - With an argument: convert that file.
  - With no argument: convert the most-recently-modified `*.wg` in `~/writing/`.
  - Output: a `.md` of the same basename, next to the source.

Data flow:

```
you type → WordGrinder (.wg in ~/writing/) → blog-export → clean .md
```

### Markdown export

`blog-export` uses `wordgrinder --convert`. Verified on **WordGrinder 0.8**:
`.md` is a supported export extension and yields clean Markdown — no fallback
to `.txt` was needed.

## The CRT profile

The default cool-retro-term profile is **provisional**. The real default is set
*post-install* via the live look-pick (amber / green / WordPerfect-blue, chosen
from actual glow on the real screen). Override the profile at any time with the
`RETRO_WRITER_PROFILE` env var, e.g.:

```sh
RETRO_WRITER_PROFILE="CandyFactory Amber" blog
```
