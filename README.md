# retro-writer

A retro writing cockpit for Linux — WordGrinder running inside cool-retro-term,
themed for true '90s phosphor glow, outputting clean markdown.

The environment is the point. See `docs/superpowers/specs/` for the design.

## Layout

| Path | What |
|------|------|
| `bin/blog` | One-command launcher: cool-retro-term, fullscreen, in `~/writing`, running WordGrinder |
| `bin/blog-export` | Converts a WordGrinder draft (`.wg`) to clean Markdown (`.md`) |
| `bin/crt-theme` | CRT theme picker — browse/preview/apply the screen look (see below) |
| `themes/` | One full cool-retro-term profile per theme (`<key>.json`) + `manifest.json` (menu order) |
| `bin/install.sh` | Symlinks the commands into `~/.local/bin/` and installs the desktop entry |
| `desktop/retro-writer.desktop` | COSMIC-clickable launcher (points at `~/.local/bin/blog`) |
| `~/writing/` | Personal drafts (`.wg` + exported `.md`). **Kept out of this repo** (see `.gitignore`). |

## Install

```sh
bin/install.sh
```

This symlinks `blog`, `blog-export` and `crt-theme` into `~/.local/bin/`,
installs the `Retro Writer` desktop entry into `~/.local/share/applications/`,
and creates `~/writing/`. Ensure `~/.local/bin` is on your `PATH`.

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

## Choosing your look

The screen look — amber, phosphor green, WordPerfect blue, and more — is chosen
with **`crt-theme`**. cool-retro-term 1.2.0's `--profile` flag is broken, so the
look instead lives in cool-retro-term's own settings DB. `crt-theme` writes that
DB, and `blog` launches plain — so **whatever theme you last applied is the look
you get.**

```sh
crt-theme            # interactive picker: a numbered list with live color
                     #   swatches; pick a number to PREVIEW it (it applies the
                     #   theme and opens cool-retro-term so you can see it).
                     #   The theme you preview LAST stays as the default.
crt-theme list       # show the themes + swatches, no launching
crt-theme set <key>  # apply a theme as the default, without launching
crt-theme show <key> # apply a theme AND open a preview window
crt-theme current    # show the current colors + which theme they match
```

`set` is the quiet path: it makes a theme the default without popping a window,
so the next `blog` (or **Retro Writer** in COSMIC) opens straight into it.

### The themes

| Key | Look |
|-----|------|
| `amber` | Classic Amber — warm amber on black (the house look) |
| `green-p1` | P1 Phosphor Green — bright green on black |
| `green-soft` | Soft Green — gentler green on a faintly green-tinted black |
| `white-ibm` | IBM White — neutral white, low chroma |
| `wordperfect-blue` | WordPerfect Blue — pale text on the iconic DOS blue |
| `commodore-cyan` | Commodore Cyan — pale cyan on dark navy |
| `vintage-burn` | Heavy Vintage Amber — cranked burn-in, bloom and curve |
| `clean-amber` | Clean Amber — effects near zero, sharp for long sessions |
| `clean-green` | Clean Green — clean-amber but green |
| `cottoncandy` | CandyFactory Cotton Candy — pink on deep plum, playful |

Each theme is a full cool-retro-term profile under `themes/<key>.json`. Tweak the
numbers (effect intensities are ~0.0–1.0) and re-`set` to taste.

> First run only: launch cool-retro-term once (e.g. `blog`) so it creates its
> settings DB, then `crt-theme` can find and write it.
