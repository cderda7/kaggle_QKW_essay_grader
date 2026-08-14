# Decisions log — v1

Every judgment call made while building this system, in the order they came up. Reference this
instead of re-litigating a choice silently in a future delta — if you want something changed,
point at the entry number.

1. **Grading engine = Claude, invoked via parallel subagents in this session, not a standalone
   script hitting an external API.** This sandbox doesn't expose a usable `ANTHROPIC_API_KEY` to
   shell scripts. `grading/grade_essays.py` documents both real options for a headless v2 (wire up
   the Anthropic API, or keep using in-session subagent grading) in its module docstring. v1's
   actual predictions come from 10 parallel subagent calls made during this session.

2. **Rubric (`rubric_v1.md`) is a reconstructed proxy, not the verbatim official PERSUADE rubric.**
   I tried to fetch the actual rubric from the Kaggle dataset page, the competition overview page,
   and the PERSUADE 2.0 Zenodo record — none returned fetchable plain text (JS-rendered / PDF-only
   in this environment). I built the rubric from the standard analytic traits (Organization,
   Development/Elaboration, Conventions) this class of state argumentative-writing rubric is built
   from, calibrated to the score distribution observed in `personal_training_set.csv`. **This is
   the single biggest unverified assumption in the system** — if you have the real rubric document,
   share it and I'll replace this precisely.

3. **Zero-shot grading — no few-shot anchor essays pulled from `personal_training_set.csv`
   itself.** Avoids any evaluation leakage (using a training essay as a calibration example, then
   also scoring it for QWK) and keeps the full 100 essays in the eval set. Trade-off: less precise
   calibration to this dataset's specific scoring conventions than few-shot would give. Flagging
   as a natural v2 delta.

4. **Single grading pass per essay, no repeats/ensembling.** Keeps this run bounded. If you want to
   check the grader's own self-consistency (intra-rater reliability) — i.e. would it give the same
   essay the same score twice — that's a clean, cheap v2 delta (re-run the same 100 essays and QWK
   the two prediction sets against each other).

5. **Batch size = 10 essays per subagent call, 10 batches, 100/10 exactly.** Balances independence
   (smaller batches = less risk of one essay's context anchoring another) against overhead (fewer,
   larger batches = fewer calls). Each batch prompt explicitly instructs "grade each essay
   independently... do not compare essays to each other."

6. **Scope stayed to `personal_training_set.csv` only**, per your explicit instruction.
   `personal_testing_set_1.csv` (500 rows, includes score=6 examples this file doesn't have) and
   the official `train.csv`/`test.csv` were read only during initial data recon and are otherwise
   untouched — reserved for a future true-holdout validation delta.

7. **`personal_training_set.csv` is not duplicated into this folder.** All scripts read it from its
   original location so there's one source of truth on disk; only the generated
   rubric/prompts/predictions/results live under `aes_qwk_system/`.

8. **Essay text is read from disk by each grading subagent, not pasted into the orchestrator's
   prompt.** Keeps the orchestration simple and means every grading call sees the literal same CSV
   a re-run would use. Trade-off (documented in `grading/grading_prompt_template.md`): the grader
   technically has the `score` column in view in the same file, mitigated by an explicit
   "ignore/pretend it isn't there" instruction and validated post-hoc — a grader secretly reading
   the answer key would show suspiciously perfect agreement, which the results don't show (53%
   exact agreement, not ~100%).

9. **Grading subagents write their own batch result files directly (via the Write tool) rather than
   returning the full JSON in their response back to me.** Kept the main session's context light
   across 100 essays' worth of rationale text; I only see short confirmation lines plus whatever I
   choose to spot-check afterward.

10. **Confusion-matrix finding, surfaced rather than smoothed over:** the system never assigned a
    score of 1 anywhere in this run, even though 9 essays were human-rated 1 (see
    `evaluation/results_v1.md`). I'm reporting this as the main systematic disagreement pattern
    rather than treating the moderate QWK as an unexplained abstract number.

11. **Sanity-check finding on the largest single miss (`01267d1`, human=1 / system=5):** reading
    the essay directly, my working theory is that the rubric under-penalizes essays that are mostly
    strung-together quotations without original synthesis — a real gap in the proxy rubric (see
    decision #2), not a pipeline bug. Flagging as a concrete, testable candidate fix for `rubric_v2.md`
    rather than asserting it as certain — it's one data point.

12. **"Randomness" baseline added to `results_v1.json`/`.md`** (2,000 random re-pairings of the
    system's own scores against the human scores) so "is this real agreement or noise" has an
    empirical answer (actual QWK ≈ 6 SDs above the random-pairing mean) rather than relying on the
    kappa-band interpretation alone.

## v2 run (rubric edit — teacher persona, hypothesize-prompt instruction, new Argumentation
sub-score with a cap rule)

13. **You edited `rubric_v1.md` in place on disk rather than creating a new file.** To keep the
    versioned-and-diffable convention I set up intact (v1's predictions/results should stay
    reproducible against the rubric that actually produced them), I restored `rubric_v1.md` to its
    original content (unchanged in the cloud workspace, so no data was lost) and saved your edited
    version as `rubric_v2.md`. If you'd rather I edit rubrics in place going forward and not keep
    old versions around, say so and I'll drop the versioning scheme — right now I'm defaulting to
    "keep everything diffable" since that's what I told you the system was designed to do.

14. **Re-graded all 100 essays from scratch against `rubric_v2.md`**, rather than trying to patch
    v1's predictions. The rubric change added a whole new sub-score (Argumentation) and a
    persona/hypothesized-prompt framing — not a scoring-only tweak — so a partial patch wouldn't
    have been meaningful. Same 10 batches of 10 (`batches.json`, unchanged) so v1 and v2 essay-level
    results are directly comparable row-by-row.

15. **`grade_essays.py` and `compute_qwk.py` were both refactored to be version-aware** (`--version
    v1`/`v2`, separate `batch_results_v2/` dir, separate `predictions_v2.csv`/`results_v2.json`)
    instead of writing one-off v2-specific scripts. This is infrastructure for the delta workflow
    you described wanting going forward — a v3 rubric change should only need a new `rubric_v3.md`,
    a new batch_results dir, and two `--version v3` runs, not new scripts.

16. **Added a cap-rule validator** (in `grade_essays.py`'s assembly step): checks that no essay
    with `argumentation == 1` was scored `holistic_score > 3`, since that's a rule you gave the
    grader to self-enforce rather than something the assembly script computes independently.
    Zero violations found across all 100 v2 grades — the rule was applied correctly in every case
    it wasn't triggered incorrectly (though it also never triggered, since no essay in this run got
    an Argumentation score of 1 — see finding #17).

17. **New finding, surfaced rather than smoothed over:** the system still never assigned a holistic
    score of 1 anywhere in v2 (same as v1). This persists across both rubric versions, so it looks
    like a more structural reluctance (the model treating "1" as reserved for something more
    extreme than any essay in this set) rather than something the Argumentation addition would be
    expected to fix. Flagging as a separate, still-open issue from the Argumentation-dimension
    question — a candidate v3 change if you want to address it (e.g., explicit instruction that the
    full 1–6 range should be used, or revisiting the 1-band anchor description).

18. **The essay that motivated the rubric change (`01267d1`) improved but wasn't fully fixed** (v1:
    human=1/system=5, a 4-point miss; v2: human=1/system=4, a 3-point miss — Argumentation was
    scored 3, not 1, so the cap rule never triggered for it). Reporting this directly rather than
    treating "QWK went up overall" as proof the specific problem was solved — the aggregate metric
    improved for a mix of reasons (see `evaluation/results_v2.md`), and this particular essay is
    only partially better.

## Commit Tracker agent (`tracker/`) — turning commits into the Google Doc tracking table

19. **No GitHub API/connector is reachable from this cloud sandbox** (`api.github.com` calls are
    proxy-blocked; no GitHub MCP is installed or available in the registry). The agent reads commits
    from your actual local git clone via the device bridge instead — functionally equivalent as
    long as you've pushed, but it means a run only succeeds while your Mac + the Claude desktop app
    are connected. You already accepted this trade-off (chose "on-demand" over a background
    scheduled trigger) when I scoped this feature.

20. **There is no tool to edit an existing Google Doc's body content** — `update_file` only touches
    title/parent metadata, and no better-suited connector (Sheets, etc.) exists in this
    environment. So "populate the doc" can only mean fully regenerating it and replacing the file
    each run (trash old copy, create new copy, re-apply sharing) — you chose this ("recreate on
    each run") over a manual-paste-only fallback, accepting that the Doc's URL changes every sync.

21. **Plain text/markdown does not convert into a real Google Docs table on upload** — pipe
    characters render as literal text, not a formatted table. The agent builds a real `.docx` (via
    `docx`-js, per the `docx` skill) and lets Google Drive's docx→Google-Docs conversion produce a
    native table. Verified end-to-end: rendered the docx locally to a PDF/JPEG to confirm layout,
    then uploaded and re-read the live Doc's content to confirm Drive's conversion preserved the
    table structure and the exact cell values (see `tracker/README.md`).

22. **Version-mapping convention**: the Nth commit with a `; QWK:` segment (chronological, 1-indexed)
    is assumed to map to `evaluation/results_v<N>.json` in the CURRENT working tree — not a
    historical git-blob lookup at that commit's SHA. Simpler and matches this project's actual
    history exactly, but it's a real assumption that breaks if a version number is ever skipped or
    iteration commits are reordered relative to when their results file was produced. Flagged in
    `run_tracker.py`'s docstring, not just here.

23. **Commits without a `; QWK:` segment are silently skipped** (not given a blank row) — matches
    the template doc's own behavior (`syntax edit` and the v1-vs-v2-preservation commit aren't
    rows in your hand-built template either).

24. **`run_tracker.py` never auto-commits `tracker_log.json` to git**, and never writes to the
    `concerns` column — both are explicitly yours, consistent with how judgment calls have been
    handled all session (I write, you review and commit; per your own words, you'll document
    concerns yourself).

25. **First real run, against your actual repo**: `tracker_log.json` reproduced the hand-built
    template's values exactly (0.594 / blank / "verbosity bias"; 0.640 + both agreement-rate deltas
    / the prompt+rubric text / blank), and the uploaded Doc
    (`kaggle_QKW_essay_grader — Commit Tracker`,
    https://docs.google.com/document/d/1FkArThVoWQBWUEfb9wJq-SLgfKvZN9A3Fyg4yInvrqk/edit) renders
    as a real table, confirmed via `read_file_content` after upload, not just assumed from the
    local PDF preview.

26. **Relocated the agent to `projects/claude-agents/commit-tracker/` after you flagged that it
    should be reusable across projects, not scoped to this one.** Moving across the two separately
    mounted device folders meant `mv` couldn't delete the source files (only rename-within-a-mount
    is permitted here) — the old copies were moved to this project's `_to_delete/tracker/` instead
    of vanishing silently; you'll want to empty that yourself. Generalized `run_tracker.py` in the
    process: `--results-pattern` (default unchanged, so this project's behavior is identical) and
    `--no-results-lookup` for projects with no comparable results file, and changed the *default*
    log path (only relevant to NEW projects) from an aes_qwk_system-specific path to
    `<repo>/.commit_tracker/tracker_log.json`. This project keeps using its existing
    `aes_qwk_system/tracker_log.json` via an explicit `--log` flag — nothing about this project's
    own data moved or changed. Verified no regression (re-ran against this repo, diffed the output
    byte-for-byte against the pre-move file) and verified real generalization (ran against a
    throwaway scratch repo with an unrelated commit history and `--no-results-lookup`, confirmed it
    correctly parsed iteration commits and skipped the non-iteration one) before calling this done.
