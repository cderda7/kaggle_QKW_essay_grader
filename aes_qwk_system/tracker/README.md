# Commit Tracker agent

Turns your structured commit messages into the "Commit Tracker" Google Doc — the QWK / ∆ /
rationale / concerns table you built by hand in `Template GitHub Commit Tracker`. Built and scoped
in a Cowork session on 2026-08-14; see `decisions_log.md` (entries 19+) for the design rationale
and constraints this works around.

## How it works (two steps, different machines)

1. **`run_tracker.py`** — runs on *your Mac* (stdlib only, no dependencies). Reads your local git
   history, finds commits shaped like `<label> ; QWK: <value> ; Delta: <text> ; rationale: <text>`,
   cross-references the matching `evaluation/results_vN.json` for the real QWK and agreement rates
   (not just whatever the commit message says — see the version-mapping convention in the script's
   docstring), and writes/updates `../tracker_log.json`.
2. **`build_tracker_doc.js`** — runs in Claude's cloud workspace (needs Node + the `docx` package),
   turns `tracker_log.json` into a `.docx` matching the template's table layout, which Claude then
   uploads to Google Drive (auto-converts to a native Google Doc with a real table — plain
   text/markdown does NOT convert into a real table, only a real document format does).

Only step 1 is something you could run yourself. Step 2 needs Claude (or another agent with Google
Drive MCP access) — there's no tool available in this project to edit an existing Google Doc's
table in place, so the doc gets **fully regenerated and replaced** each run (see below).

## Running a sync (on-demand only — see decisions_log.md #20)

Ask Claude to "run the commit tracker" (or similar). Each run:
1. `python3 aes_qwk_system/tracker/run_tracker.py` against your repo, via the device bridge.
2. Regenerates `tracker_table.docx` from the full, updated `tracker_log.json`.
3. Reads the current tracker Doc's sharing permissions (if one already exists from a prior run),
   trashes it (recoverable — Drive trash, not permanent delete), creates a fresh Doc from the new
   `.docx`, and re-applies the same sharing.
4. Reports the new Doc URL — **it changes on every run**, since there's no in-place edit available.
   Re-share the link if you've sent it to anyone; consider bookmarking your Drive folder instead of
   the direct doc link if that's disruptive.

`tracker_log.json` is NOT auto-committed to git — review and commit it yourself (or ask Claude to)
like any other change.

## What the agent will never touch

The `concerns` column. That's always left blank in the generated table — it's explicitly yours to
fill in by hand in the Doc, and any hand-edits to it will be lost on the next sync (full
regeneration), so keep concerns tracked wherever you'd naturally keep them long-term, and treat the
live Doc's concerns column as a working/current snapshot rather than permanent storage.

## Starting a brand-new project

There's no separate "init" script — running `run_tracker.py` for the first time in a new repo (no
existing `tracker_log.json`) IS the init step: it processes all historical iteration commits found
and the first Drive upload creates the project's first tracker Doc.
