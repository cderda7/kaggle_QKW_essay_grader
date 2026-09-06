# 05: Trait override, recompute, and persistence

**What to build:** The teacher disagreeing, and the system recording it. Trait scores become
editable; the holistic recomputes through the frozen aggregator; before and after are shown together;
and every correction is written to an append-only audit record that survives restart.

The teacher overrides **traits**, not the holistic. A direct holistic override cannot steer anything —
the aggregator is three fitted coefficients, not a promptable model — and it silently decouples the
displayed score from the evidence displayed beside it. What replaces it is a **dissent flag**: a way
to record "I disagree with the final score but not the traits", with a rationale and no number, which
is information about the aggregator and is stored as such.

Per decision D2, this ticket must handle the measured fact that most corrections are inert. Raising a
single trait by one point changes the displayed score on 2 of the 10 sampled essays; raising all four
changes it on 7. A teacher who edits a trait and sees nothing happen will conclude the control is
broken. So when a correction does not change the band, the score-formation panel expands on its own
and shows how far the continuous score sits from the nearest cut. The dead control becomes an
explanation.

**Blocked by:** 04.

**Status:** ready-for-agent

- [x] Any trait score can be changed, and the holistic recomputes through the frozen aggregator with no re-fitting
- [x] The original and recomputed holistic are shown together so the effect of a correction is explicit
- [x] When a correction does not change the band, the score-formation panel expands automatically and shows the distance to the nearest cut point
- [x] A dissent flag records disagreement with the final score, carrying a rationale and no number, distinct from any trait correction
- [x] A rationale can be attached to any correction
- [x] Records are appended, never mutated; earlier records are preserved and the latest is current
      state — *latest wins per section rather than wholesale, so a dissent does not silently
      discard an earlier trait correction; decisions_log.md ui_12 argues the departure*
- [x] Each record carries the original and corrected trait scores, the original and recomputed holistic, the rationale, a timestamp, whether the gold score had been revealed, and the trait-run and aggregator versions active
- [x] Override records are an input to the build rather than applied downstream of it
- [x] Corrections survive an application restart
- [x] A correction can be cleared, returning the essay to the AI's original, without erasing the record that it happened
- [x] The essay list distinguishes reviewed essays from untouched ones

## Closing note — what the validation run found

The design argument for this ticket lives in `decisions_log.md` (ui_6..ui_19) and the files-touched
picture in `architecture/05-trait-override-and-persistence.md`; neither is repeated here. This note
records what only the validation run knows.

**Ten review rounds, 31 findings fixed.** Most were narrow. Five were real defects a reader of the
finished code would not guess at, and each is a mistake a later ticket can make again:

- `OVERRIDES_FILE` was *from-imported*, creating a second binding of the ledger path — a narrower
  form of the very import-time-binding bug this ticket set out to close. Redirecting the ledger
  moved one binding and left the other pointing at the committed audit record.
- The trait guard accepted `5.9` and `True`, because `int()` raises on neither. A hand-edited
  ledger could therefore re-score an essay straight through the guard whose entire stated purpose
  is that a typo names itself. Non-whole values are now refused rather than truncated.
- Malformed POST bodies crashed on coercion before the guard ran, answering a 500 with no message,
  so the naming text reached the person editing the file by hand but never the person typing into
  the page.
- The ledger's read-modify-write could lose a record when one teacher saved from two tabs. Writes
  are now serialised behind a single lock spanning read and swap.
- Stopping `keydown` propagation on the new score selects swallowed Escape and broke ticket 03's
  Esc-to-release, which made the page's own hint text a false promise. Only Enter and Space are
  taken now.

**`score_line()` needed a redesign rather than another patch — the most transferable lesson
here.** Four consecutive rounds each fixed one narration branch and each produced the next round's
finding. The cause was not carelessness in any one fix: the branches did not cleanly cover the
state space, which is three independent questions — what the latest record was, whether *that
record* moved the score, and whether the standing correction has moved the score off the AI's —
and hand-written conditionals kept collapsing two of them into one. It was replaced with an
explicit state table driving the score head, the sentence and the panel's open state from one
derived state, with a test per row. When a third fix to the same conditional produces a fourth
finding, the conditional is the defect.

**244 tests** at the end of the run, up from 194 when the ticket's own work was first complete:
91 over the served page and the HTTP seam (including one per narration state), 78 over the build
and its guards, 23 over override record semantics and ledger durability under concurrent saves, 22
over segment rendering, 20 over quote anchoring, 10 over the gold-reveal ledger.

**Carried forward to ticket 06**, named so they are not silently dropped:

- `reason-revised-narrates-a-revision-that-did-not-happen` — saving a record identical to the one
  standing narrates "you revised the reason", which is false about both halves. Reachable in the
  two-tab race. The honest fix adds a state to the table, so it extends ui_18 rather than
  correcting it.
- `preflight-names-a-stale-copy-of-the-ledger-path` — the `OverrideError` banner names `app.py`'s
  import-time copy of the path rather than the file the failing records were actually read from.
- `record-override-handles-overrideerror-but-not-annotationerror` — a hand-edited annotation batch
  that no longer anchors surfaces as a 500 on Save instead of the guard text naming the essay.

**What this ticket does not prove.** Three of the ten sampled essays are annotated, and the draw
tops out at human score 4 — so nothing above describes how annotation or correction reads on a
strong essay. Those limits are the sample's, not this ticket's; `spec_ui_v1.md` ("Essay sample")
owns them, and they bound every claim in this note.
