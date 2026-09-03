# 07: Remaining seven essays, end-to-end pass, and the `ui_v1` report

**What to build:** Completion and judgment. The remaining seven essays of the frozen sample are
annotated so all ten are reviewable, the whole flow is exercised in a browser the way a teacher would
use it, and the run is written up.

The write-up matters more than it sounds. Nothing in this subsystem is measurable by QWK — no score
moves — so the only way to find out whether the annotation is any good is to read it. Span acceptance
rate is the closest thing to a metric available, and it comes out of the override records for free.
It is not this ladder's headline number by decision, but it should be reported with `n` attached,
because at ten essays it will be extremely noisy and quoting it bare would overstate it.

Two known limits of this sample belong in the write-up rather than being discovered later: it tops
out at human score 4 with no 5s or 6s, so nothing here describes annotation on a strong essay; and
its word counts run 159–507, a narrow low range that limits what these essays can show about the
length coupling the score-formation panel exists to expose.

**Blocked by:** 06.

**Status:** ready-for-agent

- [ ] All ten essays in the frozen sample are annotated and present in the artifact
- [ ] The full flow is exercised in a browser: open an essay, read it, hover cards and spans, expand the formation panel, correct a trait, reject a span, edit a comment, reload and find everything still there
- [ ] Any bug found is reproduced through the browser first, the way a teacher would hit it, before being diagnosed
- [ ] Visual defects noticed during the pass are fixed, including ones unrelated to the ticket at hand
- [ ] The anchoring failure rate across all ten essays is recorded, alongside the single-essay figure from ticket 01, so the trend across instrument revisions is visible
- [ ] Span acceptance rate is computed from the override records and reported with `n` attached
- [ ] A results write-up records what the ten essays showed about annotation quality, including whether acceptance rate differs between essays the system scored well and essays it scored badly
- [ ] The write-up names the sample's two limits explicitly: no essays above human score 4, and a narrow low word-count range
- [ ] A tracker row for `ui_v1` is written in the ladder's own format, with no metric segment
