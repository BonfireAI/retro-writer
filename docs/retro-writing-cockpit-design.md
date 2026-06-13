# Retro Writing Cockpit — Design

- **Date:** 2026-06-09
- **Status:** Approved (design); awaiting spec review before implementation planning
- **Owner:** Anta

## Goal

A retro writing environment on Linux that captures the feel of WordStar / WordPerfect
from the early '90s — phosphor-glow CRT screen, distraction-free full-screen word
processor — for drafting blog posts. The environment is the deliverable. Publishing is
deliberately out of scope for this iteration.

## Decisions (the forks we settled)

1. **Retro depth → Modernized retro word processor.** Not the genuine DOS software
   (rejected: the `.wpd`/`.ws` file-conversion tax fights the actual goal of writing),
   and not merely a skinned modern editor. We keep the '90s soul but export clean text.
2. **The tool → WordGrinder** (`wordgrinder-ncurses`). One `apt install`, zero gamble.
   Full-screen ncurses word processor: menu bar, status line, live word count,
   distraction-free. WordTsar (true WordStar control-diamond) was the romantic choice but
   is unpackaged (source build / AppImage) — deferred, not chosen.
3. **Publish target → Just the writing cockpit first (YAGNI).** Build the writing
   experience, output clean markdown, and wire "where it publishes" as a deliberate later
   step once the tool has been lived in.

## Out of scope (this iteration)

- Any publishing pipeline (into a CandyFactory blog pipeline or a new static site).
- WordTsar / the genuine DOS software.
- The optional retro HTML output preview is **opt-in**, not built by default (see below).

## Architecture — three pieces, each with one job

### 1. The screen — `cool-retro-term`
A CRT *simulator* (phosphor glow, scanlines, screen curvature, burn-in, subtle flicker),
not just a color palette. We save one dedicated **CandyFactory profile** so the look is a
single reproducible config rather than hand-tuned each launch.

- Config lives in `~/.config/cool-retro-term/`.
- cool-retro-term's strength is monochrome phosphor, so the two authentic, gorgeous looks
  are **amber-on-black** and **green-on-black**. A **WordPerfect-blue** screen is possible
  but works against the phosphor engine.

### 2. The word processor — `wordgrinder` (`wordgrinder-ncurses`)
Distraction-free full-screen writing. Native save format is `.wg`; Markdown is an **export**
format. A small helper, **`blog-export`**, converts the latest/target draft `.wg → .md`
(exact mechanism — File→Export vs `wordgrinder --convert` CLI — to be confirmed during
implementation; both are candidates).

### 3. The ritual — a `blog` launcher
A single command **`blog`** (in `~/.local/bin/`) *and* a clickable COSMIC desktop entry
(`.desktop`). Either one opens cool-retro-term with the CandyFactory profile, full-screen,
running WordGrinder in the drafts folder. One action → you're in the glow, writing.

## Where things live

| What | Path | Why |
|------|------|-----|
| Drafts (`.wg` + exported `.md`) | `~/writing/` | Personal; kept out of the CandyFactory repos |
| Cockpit: launcher, cool-retro-term profile, WordGrinder config, README, this spec | `~/Projects/retro-writer/` (git repo) | Reproducible; portable to any Linux box |
| cool-retro-term profile | `~/.config/cool-retro-term/` (sourced from repo) | Where the app reads it |
| `blog` command | `~/.local/bin/blog` | On PATH |

## Data flow

```
you type → WordGrinder (.wg in ~/writing/) → blog-export → clean .md
```

That `.md` is the seam we wire to a blog later, when the publish target is decided.

## The look — shown, not described

Once built, launch **amber**, **green**, and (as an experiment) **WordPerfect-blue** on the
real screen so the choice is made from actual glow, not from words. The chosen look becomes
the default in the CandyFactory cool-retro-term profile.

## Optional bolt-on (opt-in only)

A `pandoc` recipe that renders a draft `.md` into a retro-styled HTML *preview* — a
green/amber "published-looking" page — to taste the output aesthetic while real publishing
is deferred. Not built unless requested.

## Verification (evidence, not vibes)

1. Install → confirm `cool-retro-term` and `wordgrinder` binaries run.
2. Launch the cockpit (the `blog` command and the desktop entry both work).
3. Write a throwaway line, export it via `blog-export`.
4. Confirm a clean `.md` exists on disk with the expected content.

## Alternatives considered and set aside

- **(B) Bare tools** — install the two packages, hand over raw commands. Rejected: loses the
  saved profile + one-action launch; re-assembled every time.
- **(C) Cockpit + retro HTML preview baked in** — Approach A with the bolt-on always on.
  Rejected as default: the preview should be opt-in, not assumed.

## Open items carried into implementation

- Exact WordGrinder → Markdown export mechanism (menu export vs `--convert`), confirmed live.
- cool-retro-term CLI flags for profile + workdir + execute, confirmed live.
- Final default CRT look (amber / green / blue), chosen by Anta from the live demo.
