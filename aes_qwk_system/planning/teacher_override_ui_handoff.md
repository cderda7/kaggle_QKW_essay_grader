# Teacher Override -> Few-Shot Steering: Session Handoff

Written 2026-09-03 by Claude (Cowork), after exploring the current repo state so the next
session doesn't have to rediscover it. Paste the "Kickoff prompt" section at the bottom into a
new session to start building.

## What's actually in this repo today

- `aes_qwk_system/` is a batch/offline research pipeline: rubric text (`rubric_v1.md` ...
  `rubric_v9.md`) plus a Python orchestrator (`grading/grade_essays.py`) that assembles and
  validates JSON grading output into `predictions_v*.csv`, scored by `evaluation/compute_qwk.py`
  against QWK.
- Grading itself is NOT automated. `grade_essays.py`'s own docstring says it does not call an LLM
  API (no ANTHROPIC_API_KEY was available when it was built) -- every version so far was graded by
  a Claude subagent reading the rubric and CSV by hand, batch by batch.
- From v5 on, the grader only produces the 4 trait scores + evidence_notes; the holistic score is
  computed in code (`v4_holistic()` through v8) or by a fitted regression + cut points
  (`aggregator_v9.json`, v9). So "the AI's grade" is really two different things: (a) a trait-level
  judgment a model makes against a rubric, and (b) a small fitted numeric model that turns 4 traits
  + word count into a 1-6 holistic score. That split matters for what "few-shot steering" even
  means -- see Open Question 1 below.
- There is no web app, no database, no auth anywhere in this repo -- it's scripts + CSVs +
  markdown. A teacher UI is a genuinely new subsystem, not a UI bolted onto an existing app.
- `aes_qwk_system/decisions_log.md` and `aes_qwk_system/tracker_log.json` already fill the roles
  your global instructions describe as `DECISION_LOG.md` and the "progress-tracker doc" -- 77
  dated, numbered decision entries, and a structured commit log in the
  `<label> ; QWK: ... ; Delta: ... ; rationale: ...` shape your `commit-message-generator` skill
  produces. Keep using these; don't create a second, competing root-level `DECISION_LOG.md`.
- Git: repo is on branch `multiple-graders`, with uncommitted changes to `README.md` and
  `decisions_log.md`, and an untracked `evaluation/results_v9_test500.json`. Resolve that before
  starting a clean feature branch (Step 0).
- The connected-folder bridge can't see `~/.claude/skills` (it's outside the connected
  `QWK_essay_grader` folder), so I could not confirm whether `grilling`, `codebase-design`, or
  `domain-modeling` -- the missing companions your own skill notes flagged for `grill-me`, `tdd`,
  and `improve-codebase-architecture` -- have since been installed. Check before relying on those
  three.

## Decisions already made (this session)

1. **Audience / hosting**: just you, running locally. No auth, no multi-tenant concerns for v1.
2. **Live vs. batch**: v1 works against essays that are already graded (`predictions_v9.csv` etc.)
   -- reviewing and correcting existing AI grades, not live-grading a brand-new essay on demand.
   That sidesteps the missing-API-key problem entirely for now.
3. **Tracking**: stay in local markdown/JSON files, not a configured issue tracker. Skip
   `/setup-matt-pocock-skills`.

## Open questions grill-me should nail down (don't skip this)

1. **What exactly does a teacher override?** Just the final holistic score, or the 4 trait scores
   too? If a teacher only disagrees with the holistic number, that alone can't become a good
   few-shot example for the trait-grading prompt (which is what actually needs steering -- the
   aggregator is 3 fitted coefficients, not something few-shot examples can steer at all). The
   override UI likely needs to capture corrected trait scores (or at least a corrected trait plus a
   reason), not just a corrected 1-6 number.
2. **Where do few-shot examples live relative to the existing version system?** This project treats
   every rubric/scoring change as a new numbered version with its own directory and decision-log
   entries. A few-shot bank is exactly that kind of change -- probably wants to be `rubric_v10.md`
   (or a new `VERSION_CONFIG` entry) rather than a side mechanism bolted onto v9.
3. **Selection strategy**: do ALL overrides go into the prompt (grows unbounded, costs tokens,
   risks drift), a capped/curated set, or similarity-matched examples per new essay? Real modeling
   decision -- give it a decision-log entry with alternatives once chosen.
4. **Does an override retroactively re-grade anything**, or does it only affect future runs? Given
   the project's LOO / frozen-aggregator discipline about never refitting on eval data, retroactive
   re-scoring needs the same care.
5. **Storage**: "just me, local" -- a JSON or SQLite file next to `tracker_log.json` is probably
   enough. No need for a database server. Worth confirming rather than assuming.
6. **Audit trail**: original AI trait scores + holistic, teacher's corrected version, rationale,
   timestamp, and which rubric/aggregator version was active. This project's whole culture is
   "every score is auditable" -- the override UI should inherit that, not lose it.

## Step by step

### Step 0 -- Clean up git state (you run these yourself -- I never run git for you)
Decide what to do with the uncommitted `README.md` / `decisions_log.md` changes and the untracked
`results_v9_test500.json` on `multiple-graders` -- commit them (message sourced from the relevant
`tracker_log.json` row, via `commit-message-generator`) or stash them, so they don't tangle with
the new feature. Then branch, e.g. `git checkout -b teacher-override-ui`, once `multiple-graders`
is clean.

### Step 1 -- /grill-me to pressure-test the concept
Companion skill `grilling` may or may not be installed -- check `~/.claude/skills` first. Paste the
kickoff prompt below and make sure the six open questions above get answered before moving on.

### Step 2 -- /to-spec to formalize it
Tell it explicitly to write the spec to a local markdown file (e.g.
`aes_qwk_system/planning/teacher_override_spec.md`) instead of publishing to a tracker.

### Step 3 -- /to-tickets to break it into shippable pieces
Same local-file instruction. Expect tickets roughly like: override data model + storage;
trait-level override form UI; essay list/filter view reusing `predictions_v9.csv`; few-shot bank
assembly logic; wiring the bank into the grading prompt (new rubric version); decision-log entries
for the modeling choices; tests for each.

### Step 4 -- Build each ticket test-first (tdd skill)
Companion skill `codebase-design` may be missing too -- same caveat as Step 1. Once there's enough
code to have an architecture, `improve-codebase-architecture` is worth a pass -- not on day one.

### Step 5 -- Treat this as a real E2E product, per standing instructions
This is a UI a human clicks through: reproduce any bug the way a teacher actually would (open the
app, click through it), not just by calling a function directly. Be picky about anything that looks
visually off along the way, even if unrelated to the ticket at hand.

### Step 6 -- no-mistakes before calling it done
Check whether `no-mistakes init` has run in THIS repo specifically (only a global `~/.no-mistakes`
was found, nothing project-level) -- init it here first if not. Needs work committed on a
non-default branch, so this runs after Steps 0/4, not before.

### Step 7 -- Commit messages and decision log, throughout
For every significant technical call (override storage shape, few-shot selection strategy,
whether/how it plugs into the version system) add a numbered entry to
`aes_qwk_system/decisions_log.md` in its existing style, right when the call is made -- not
retroactively. Source commit messages from `tracker_log.json` via `commit-message-generator`.

## Kickoff prompt -- paste this to start the next session

```
I'm continuing work on QWK_essay_grader (aes_qwk_system/). I want to add a teacher UI where I can
review already-graded essays (starting from predictions_v9.csv), override the AI's grade, and have
accepted overrides build up a few-shot example bank that steers future grading -- as a local,
single-user tool (no auth, no live model API call needed yet).

Before writing any code, run /grill-me on this concept. Make sure it resolves: (1) whether
overrides capture trait-level scores or just the holistic number -- the holistic score is currently
DERIVED from traits via aggregator_v9.json, a fitted regression, not something few-shot examples
can steer, so trait-level correction is probably required; (2) whether the few-shot mechanism
becomes a new rubric version (e.g. v10) in the existing VERSION_CONFIG system in
grading/grade_essays.py, consistent with how every other scoring change in this project is
versioned; (3) example selection strategy (all vs. capped vs. matched) with tradeoffs; (4) whether
an override retroactively re-scores anything or only affects future grading runs; (5) storage (a
local JSON or SQLite file is probably enough for a single-user tool -- don't over-build); (6) the
audit trail an override needs (original AI trait+holistic scores, teacher's corrected scores,
rationale, timestamp, rubric/aggregator version active at the time).

Then /to-spec -- write the spec to a local markdown file under aes_qwk_system/planning/, not to an
issue tracker (this project doesn't use one; it tracks progress in tracker_log.json and
decisions_log.md).

Then /to-tickets, same local-file instruction, broken into independently shippable pieces.

Build each ticket test-first using the tdd skill. First check whether the grilling and
codebase-design companion skills are actually installed (~/.claude/skills), since grill-me and tdd
depend on them and may have been degraded the last time this was checked.

Repo state as of the last session: on branch multiple-graders with uncommitted changes to
README.md/decisions_log.md and an untracked results_v9_test500.json -- clean that up and branch off
before starting. aes_qwk_system/decisions_log.md is the existing decision log (add entries there,
don't create a new root DECISION_LOG.md); aes_qwk_system/tracker_log.json is the existing progress
tracker (source commit messages from it via commit-message-generator). Run no-mistakes init in this
repo if it hasn't been (only a global ~/.no-mistakes was found, nothing project-level) before
relying on the no-mistakes validation pipeline, and only once work is committed on a non-default
branch.
```
