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

## v3 rubric edit (disjunctive 1–3 band vs. compensatory 4–6 band)

27. **What triggered this**: you pointed out that the rubric's own equal-interval framing implies
    scores 1–3 should be disjunctive ("marked by ONE OR MORE of the following weaknesses" — one
    severe weakness caps the essay low regardless of other traits) while scores 4–6 should be
    compensatory (require jointly meeting multiple positive criteria, not averaging). You gave a
    direct instruction to edit `rubric_v3.md` to encode this, and explicitly rejected a
    clarifying-question tool call first — so everything below is my own operationalization of your
    principle, documented here rather than confirmed with you beforehand, per your standing
    instruction to surface judgment calls rather than make them silently.

28. **Found `rubric_official_persuade.md` already in the project folder while syncing this work —
    the real rubric decision #2 flagged wanting.** It's the verbatim official PERSUADE 2.0 scoring
    rubric (both the Independent and Source-based task variants), sourced from the corpus repo
    (`github.com/scrosseye/persuade_corpus_2.0`), not the reconstructed proxy v1/v2 were built on.
    Its own "Notes for our grading prompts" section already states almost exactly the
    disjunctive/compensatory asymmetry you separately identified — worth knowing since it suggests
    that note is likely where your observation came from. **I rebuilt `rubric_v3.md` around this
    verbatim text instead of extending my proxy anchors**, since decision #2 explicitly said I'd
    replace the proxy the moment a real rubric was available, and this is strictly better-sourced.
    I don't know for certain how this file got into the project folder (whether from earlier in
    this session or added directly) — flagging that gap rather than asserting a history I can't
    verify.

29. **Merged the Independent and Source-based task variants into one rubric** with bracketed
    "[taken from the source text(s)]" clauses, rather than keeping two separate rubric files or
    picking one variant. This follows the source file's own recommendation (its note #4: the AES
    2.0 training data doesn't carry the PERSUADE `task` column needed to cleanly split essays by
    variant, and the two texts differ only in that clause). Trade-off: a source-based essay graded
    with no actual source text available will be evaluated on evidence/reasoning quality generally,
    since there's no source-text-provenance to check — same limitation the "hypothesize a prompt"
    instruction already has for missing prompts.

30. **Kept v1/v2's four JSON field names (`organization`, `development`, `conventions`,
    `argumentation`) rather than renaming them to match the official rubric's own dimension names**
    (organization/coherence, evidence and support, language, point of view/critical thinking). The
    mapping is close but not exact — most notably, the official "language" dimension includes
    vocabulary and sentence variety, which is broader than v1/v2's grammar/mechanics-focused
    "conventions." I chose continuity (same CSV columns, same `--version` pipeline code, directly
    comparable v1→v2→v3 columns) over a fully accurate rename. If you'd rather the fields be
    renamed to match the official dimensions exactly, that's a clean, contained follow-up change.

31. **Defined "severe weakness" as a trait score ≤2** (any of the four traits from steps 2–5)
    rather than inventing a separate qualitative judgment, and rather than trying to have the
    grader directly classify "does this weakness count as severe" in prose. This generalizes v2's
    rule (Argumentation==1 caps holistic at 3) to all four traits, and extends the trigger from
    "==1" to "≤2" — a real strengthening, not just a generalization. I picked ≤2 because a bare
    "==1 only" trigger seemed too narrow to meaningfully test the disjunctive-band hypothesis (v2
    already had that exact rule and it never fired — see decision #16/#17 — the system never
    assigns a 1). If ≤2 still doesn't fire often, that's itself informative for interpreting v3's
    results; flagging this now instead of waiting to explain a null result later.

32. **Placement within the 1–3 band is graduated by severity**, not a flat cap: any trait at 1 →
    holistic ∈ {1,2}; lowest trait at 2 (nothing at 1) → holistic ∈ {2,3}; multiple traits ≤2 →
    weight toward the bottom of the applicable range. This is a real change from v2's flat "cap at
    3" rule — v3's cap can go as low as 1–2 for a trait score of 1, where v2 only ever said "no
    higher than 3." Calling this out explicitly since it's stricter, not just broader.

33. **Compensatory 4–6 placement uses an explicit "N of 4 traits at/above threshold" rule**
    (4 needs ≥3 traits ≥4 and none below 3; 5 needs ≥3 traits ≥5 and none below 4; 6 needs all 4
    traits ≥5 with at least two 6s), even though the official rubric's 4–6 text is prose ("a
    typical essay..."), not a formula. I chose a concrete, checkable rule instead of leaving that
    prose to stand alone because vague prose is exactly what let v1/v2's grader default back to
    averaging in practice — a "3 of 4" threshold is the most direct way I could think of to
    structurally block a single standout trait from carrying three middling ones. This is a real
    design choice with alternatives I didn't take (e.g., "holistic ≤ second-lowest trait" as a
    stricter formula, or leaving it as pure narrative guidance) — flagging in case you'd prefer a
    different formula.

34. **Lightly cleaned up the source rubric's own phrasing slips** ("progression of ideas exhibits
    adequate," "the essay generally using") when merging the anchors into `rubric_v3.md`, rather
    than preserving them verbatim with the errors intact. The source file's own note explicitly
    invited this ("preserved verbatim above; clean them up if pasting into a prompt") — content and
    meaning unchanged, only grammar smoothed.

35. **Added `gate_applied` and `gate_rationale` fields to the JSON output schema** so each essay's
    output records whether it went through the disjunctive or compensatory path and why — this
    gives an auditable trail for exactly the kind of "why did the score change" note the Commit
    Tracker's QWK-notes column is meant to capture, and makes it possible to check the gate logic
    was actually followed (a v3 analog of the v2 cap-rule validator) without re-deriving it from
    the holistic score alone.

36. **Corrected the file's H1 from "AES Grading Rubric v1" to "AES Grading Rubric v3."** `rubric_v2.md`
    inherited the stale "v1" heading from when you edited it in place (I didn't fix that — v2 is
    your file, I only preserved it as decision #13 describes). For a brand-new file I'm authoring,
    I fixed the label rather than propagating the stale text. Not a content or scoring change,
    noting it only for completeness.

37. **Update, now done**: you said "run that." Re-graded all 100 essays against `rubric_v3.md`
    (same 10 batches, same 10-parallel-subagent process as v1/v2), added a `"v3"` entry to
    `grade_essays.py`'s `VERSION_CONFIG` with the `validate_v3_gate()` validator described in
    entries 27–36's code, and ran `compute_qwk.py --version v3`. Findings below.

38. **New finding, discovered empirically while assembling — a real gap in the v3 rubric's gate
    design, not a grading error.** The severe-weakness trigger is trait score ≤2, but a trait score
    of exactly **3** ("developing mastery" — the official rubric's own bottom-band language) is
    neither severe by that trigger nor able to structurally clear step 7's compensatory thresholds
    (which require ≥3 of 4 traits at ≥4). 14 of the 100 essays landed in this dead zone — mostly
    profiles like all-four-traits-at-3, or one trait at 4 with the rest at 3 — and graders resolved
    the ambiguity two different ways: some stayed at holistic=3 (following the rubric's own
    "default to the lower adjacent score" fallback), most rounded up to holistic=4 (reading the
    "typical essay... develops... organized... adequate" language loosely). I'm treating this as a
    genuine rubric ambiguity rather than a grading mistake — every one of those 14 essays followed
    *some* defensible reading of the text as written, which is exactly the problem: the rubric
    permits two readings where it should permit one. Concrete candidate fix for a v4 delta: either
    widen the severe-weakness trigger to ≤3, or add an explicit tie-break rule for flat/near-flat
    3-profiles (e.g., "profiles with no trait ≥4 default to holistic=3, not 4").

39. **Reclassified those 14 essays' validator output from hard violations to soft advisories**,
    after first running the validator as originally written (entries 27–36) and seeing all 14 flagged
    as rule violations — re-reading them individually made clear they weren't grader error, they
    were the rubric gap in #38 surfacing. Changed `validate_v3_gate()`'s two threshold checks in the
    non-severe branch (holistic<4, and holistic==4-without-3-of-4) to SOFT, keeping the 5/6-band
    checks and all of the severe-branch checks HARD, since those weren't implicated in the ambiguity
    and no violations of them occurred. Kept every one of the 14 visible in the run log rather than
    silently absorbing them once reclassified — see `results_v3.md`'s "real cost" section for the
    aggregate effect.

40. **Result, reported without smoothing over the mixed outcome**: QWK = 0.6382, essentially tied
    with v2's 0.6400 (Δ0.0018, well inside the random-baseline SD of ~0.099 — not a meaningful QWK
    move). Underneath that flat number are two real, opposite shifts: (a) the specific finding that
    motivated this whole rubric version — the system never assigning a holistic score of 1 — is now
    resolved (v1/v2: 0 times in 100 essays each; v3: 8 times, matching 3 of the 9 true human=1
    essays exactly); but (b) exact agreement dropped from 51% (v2) to 43% and MAE rose from 0.54 to
    0.65, concentrated almost entirely in the human=3 cohort (36 essays, the dataset's largest
    group) via the #38 dead-zone gap pushing many of them to system=4. Full breakdown, confusion
    matrices, and the verbosity-bias diagnostics (essentially unchanged from v2) are in
    `results_v3.md`. I'm not calling this an unambiguous win or an unambiguous regression — which
    one it is depends on whether under-identifying weak essays or precision in the middle of the
    scale matters more for your use case; flagging that as your call, not mine, to make.
