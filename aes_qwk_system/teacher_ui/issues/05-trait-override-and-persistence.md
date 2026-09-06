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
