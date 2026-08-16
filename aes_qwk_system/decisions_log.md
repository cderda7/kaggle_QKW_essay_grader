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

41. **Added a `SCORES` field to the v3 batch results, and made it a strictly post-hoc annotation
    rather than something the grader emits.** You asked for each object in
    `batch_results_v3/batch_NN.json` to lead with `"SCORES": "<teacher score> vs. <system score>"`
    so a reviewer reading a batch file sees the agreement or disagreement before reading the
    rationale, instead of cross-referencing `predictions_v3.csv`. The obvious implementation —
    ask the grader for that field in its output format — would have quietly destroyed the project's
    core premise: the grader is blind to the `score` column (decision #3, and the "IGNORE the score
    column" instruction in `grading_prompt_template.md`), and a grader that has to print
    "3 vs. 2" must first be handed the 3. QWK would then be measuring the model's willingness to
    copy a number it was given, and would be uninterpretable — worse, it would likely look *better*,
    which is the failure mode that doesn't announce itself. So the field is injected by
    `grade_essays.py --annotate-scores` after grading, from the same `personal_training_set.csv`
    the assembler already reads. The grader's prompt and output schema are unchanged.

    Because "we'll just remember not to ask for it" is not a real guarantee across future rubric
    versions, three mechanical guards back it up: (a) `_scores_annotation.json`, a manifest next to
    the batch files recording every essay_id the script annotated — a `SCORES` field it can't
    account for aborts `--assemble` as suspected leakage rather than being silently folded in;
    (b) `--strip-scores`, the inverse operation, for producing blind copies before showing prior
    batch output to any model (a v4 that compares itself against v3 is the realistic case);
    (c) `cross_check_predictions()`, which warns when the batch JSONs' holistic scores disagree with
    `predictions_<version>.csv`, since `SCORES` is computed from the former while every reported
    metric comes from the latter.

    Enabled for v3 only, per your call — v1/v2 batch results stay frozen as historical artifacts.
    Future versions opt in with `"annotate_scores": True` in `VERSION_CONFIG`.

42. **Found while verifying #41: `batch_results_v3/` and `predictions_v3.csv` have drifted apart,
    and the drift is not caused by anything in #41.** Guard (c) above fired on its first run.
    Re-assembling `predictions_v3.csv` from the current batch results changes 69 of 100 rows,
    including 38 holistic scores, and moves the metrics from QWK 0.6447 / 54% exact agreement (what
    the on-disk `predictions_v3.csv` and `results_v3.json` contain) to QWK 0.6382 / 43% (what the
    README headline and decision #40 report). In other words the two artifacts describe two
    different v3 generations, and the narrative written up in #38–40 matches the *batch files*,
    while `results_v3.json` matches the CSV. Relatedly, #39 describes reclassifying the non-severe
    threshold checks in `validate_v3_gate()` from hard violations to SOFT advisories, but the
    function in the working tree still emits them as hard violations (10 fire on the current batch
    data). Left both alone rather than picking a side: regenerating the CSV would overwrite reported
    results, and re-editing the validator would overwrite code, and which artifact is authoritative
    is a question about what actually happened in that run, not something to infer. Flagged for
    Carson to resolve; `--assemble` reproduces the batch-derived numbers whenever he wants them.

## Resolving #42, and the v4 trait weighting

43. **#42 is resolved in favour of `predictions_v3.csv`, which is the opposite of what #42's own
    framing implies.** #42 left open which of the two v3 generations was authoritative, noting only
    that the README/#38–40 narrative matches the batch files while `results_v3.json` matches the
    CSV. `tracker_log.json` settles it, and it wasn't consulted when #42 was written. Entry 4
    ("third iteration") records **QWK 0.6446754 — the CSV's exact number** — together with a real
    rubric delta: *"4-6 compensatory band now 3-6 compensatory band – a student with no individual
    score less than 3 is guaranteed at least a 3, not at least a 4 as previously, 2 traits = 1 →
    holistic = 1."* Both of those rules are present in `rubric_v3.md` and in `validate_v3_gate()`
    as they sit on disk. Entry 3 ("second iteration") records QWK 0.6381990 — the batch files'
    number. Corroborating: only **33 of 100 trait vectors and 4 of 100 rationales** match across
    the two artifacts, so the CSV is a *separate, later grading run*, not a recompute of the batch
    files under changed rules.

    So the ordering is: iteration 3 graded → `batch_results_v3/` saved → CSV built; then
    `rubric_v3.md` was edited and **iteration 4 re-graded, overwriting the CSV and
    `results_v3.json` but never saving its batch JSONs**. `batch_results_v3/` is the stale artifact
    and the CSV is current — the reverse of #42's reading. Re-assembling from the batch files, as
    #42 offered to do, would have silently rolled v3 back one iteration.

    Actions taken, none of them destructive: renamed `grading/batch_results_v3/` →
    `grading/batch_results_v3_iter3/` so the directory states which generation it holds (contents
    and its `_scores_annotation.json` untouched); repointed `VERSION_CONFIG["v3"]` at the new name
    with a comment that `--assemble --version v3` therefore regenerates *iteration-3* numbers, not
    the checked-in CSV; and added headers to `README.md` and `results_v3.md` marking which run each
    narrative describes. Nothing was regenerated and no graded output was overwritten.

44. **Consequence for #38–39, which are now historical rather than open.** The "all-3s dead zone"
    (#38) — trait profiles with no trait ≥4 being neither gated nor able to clear the old band-4
    threshold, leaving graders to resolve 14 essays two different ways — was a finding about
    *iteration 3*. Iteration 4's 3–6 compensatory band closed it by construction: clearing the gate
    now guarantees at least a 3, so there is no gap to fall into. Evidence that it is genuinely
    closed rather than merely restated: the fidelity check in #46 reproduces all 100 of iteration
    4's holistic scores mechanically, meaning zero essays were resolved by grader discretion.
    #39's unapplied SOFT reclassification of `validate_v3_gate()` is moot for the same reason —
    it was a patch for grader drift that iteration 4 does not exhibit. Both left in place as the
    record of what happened, with pointers added rather than edits to the original text.

45. **Weights enter as *weight mass*, not as a weighted average — the single most consequential
    choice in v4.** You asked for argumentation 0.35 / organization 0.25 / development 0.25 /
    conventions 0.15, keeping the established scoring rules. Those rules almost never average: they
    *count* ("at least 3 of the 4 traits at/above X"). Two translations were possible:

    - **Weight mass (chosen).** "≥3 of 4 traits" becomes "traits carrying ≥0.75 of total weight."
      Since 3 of 4 equally-weighted traits carry exactly 0.75, this is byte-for-byte v3's rule
      under the old weights — a strict generalisation, so the weights are provably the only thing
      that can move a score. Under the new weights exactly one subset behaves differently:
      {organization, development, conventions} carries 0.65 and no longer clears the bar, so the
      essays that move are those where argumentation is the sole trait below the threshold.
    - **Weighted mean as the placement engine inside each band (rejected).** Simulated: moves ~22
      essays and scores *worse* (QWK 0.630 vs v3's 0.645). It also reintroduces precisely the
      averaging behaviour #33 added the counting rule to block — a single strong trait carrying
      three middling ones. Rejecting a bigger visible effect in favour of a smaller correct one is
      the call here; flagging it as a call rather than an obvious choice.

    The gate's one genuine averaging step ("exactly one trait ==1 → average the four traits") does
    become a weighted mean, since it was already an aggregation.

46. **v4 was derived from v3's trait scores, not re-graded — and the derivation is gated on a
    fidelity check rather than on the assumption that it's safe.** Every prior version re-graded
    all 100 essays. A weight change doesn't touch what a grader does (read the essay, assign four
    trait scores), only how those four numbers combine, so `grade_essays.py --derive --version v4`
    recomputes holistic scores from `predictions_v3.csv` and carries the trait scores through
    untouched.

    The justification is empirical, not asserted: `check_v4_fidelity()` runs the v4 scoring
    function over all 100 v3 trait vectors with **equal** weights and compares against what the
    graders actually wrote. It reproduces **100/100 holistic scores and 100/100 `gate_applied`
    values**. So (a) the aggregation is fully mechanical, (b) iteration 4's grading was completely
    rule-compliant, and (c) the entire v3→v4 diff is attributable to the weights. The check raises
    rather than warns, and runs by default before every derivation, so a future edit that breaks
    the correspondence fails loudly instead of quietly producing a number.

    Cost, stated rather than glossed: v4 has no `batch_results_v4/` and no grader rationales of its
    own — `predictions_v4.csv` carries generated text describing which rule fired. And
    `rubric_v4.md` documents a rule no grader was ever run against. Whether *telling* a grader that
    argumentation is weighted 0.35 also shifts how it assigns trait scores is a real and separate
    question that this version does not answer; it needs a genuine re-grade and its own version.

47. **The one non-deterministic v3 rule had to be pinned down, and the pinning was verified not to
    change anything.** v3's "exactly one trait ==2 → holistic is 2 or 3, at grader discretion"
    cannot survive as-is in a derivation, which has no grader. v4 resolves it with the weighted
    mean, rounded half up, clamped to [2,3]. This reproduces what the graders did on **all 17** such
    essays in `predictions_v3.csv` under both the old and new weights — it is a formalisation of
    observed behaviour, not a new standard. (It is also inert by construction: the lowest possible
    weighted mean for a profile with one trait at 2 and nothing below 3 is 2.65, which rounds to 3
    either way.) Recording it because a reader comparing the rubrics will notice the discretion
    clause disappeared and should know it cost nothing.

48. **The gate stays unweighted, deliberately.** Any trait at ≤2 still gates the essay into the
    1–3 band, including conventions at its 0.15 weight, and the "2+ traits at 1 → 1" / "2+ traits
    ≤2 → 2" rules still count severe failures rather than weighing them. Weights govern how traits
    *aggregate*; they do not govern whether a severe weakness counts as severe. The official
    rubric's 1/2/3 language is disjunctive — "flawed by ONE OR MORE of the following weaknesses" —
    and draws no distinction between which dimension the weakness falls in (#27). The "no trait
    below 3 / below 4" floors on bands 4 and 5, and band 6's "all four ≥5," are unweighted for the
    same reason: they are membership tests, not aggregations.

    Checked rather than assumed, since this is the main thing blunting the weighting's effect: 49
    of 100 essays are decided by the gate before any weight is consulted. Making the gate
    weight-aware changes **zero** essays anyway, because band 4's "no trait below 3" floor catches
    the same essays and holds them at 3. Dropping the floors as well moves 2 more. Both are changes
    of standard rather than generalisations, and both need the disjunctive-language argument
    answered head-on — so neither belongs folded into a weighting change.

49. **Result, reported without inflation: one essay of 100 changes.** `0105e2e` (organization 4,
    development 4, conventions 4, argumentation 3) drops 4 → 3, because its three strong traits
    carry 0.65, below the 0.75 bar. Its human score is 2, so it moves toward the rater. QWK goes
    0.6447 → 0.6584, exact agreement stays at 54%, adjacent rises 93% → 94%, MAE falls 0.530 →
    0.520. **The QWK delta of +0.0137 is 0.14 random-baseline standard deviations — inside noise**,
    and should not be reported as a win; the case for v4 is that the rule now encodes the intended
    weighting, not that the metric moved. The small footprint is structural and was predictable
    (see #45 and #48): half the corpus is gated before weights apply, and the mass rule differs
    from the count rule for exactly one trait subset. Full breakdown in `evaluation/results_v4.md`.
