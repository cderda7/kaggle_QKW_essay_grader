# Teacher Review UI — decisions log

Judgment calls for the `ui_` version ladder, numbered independently of `../decisions_log.md` (the
QWK ladder's log). Entries are prefixed `ui_` wherever they are cited from outside this file, so
`ui_3` is never confused with `#3` over there.

**Cross-reference:** `../decisions_log.md` **#78** — *the span/feedback annotation is produced by a
separate additive pass over frozen trait scores* — is the decision this entire subsystem rests on. It
lives in the QWK log deliberately: it is a decision about the grading pipeline, and a reader checking
why v9's validated numbers survive this feature needs to find it there, not here.

Entries `ui_1`–`ui_7` were settled in the `/grill-me` session of 2026-09-03 and are specified in full
in `spec_ui_v1.md`.

---

## ui_v1

1. **The teacher UI gets its own version ladder, prefixed `ui_`.** The `v1`–`v9` ladder means "a
   scoring change with a QWK attached". This subsystem changes no score and produces no QWK, so a
   number in that ladder would be uncomparable to its neighbours — and `results_v9.md` §4–5 has
   already reserved v10 for constraining β₂, a real scoring change that would collide with it.

   *Alternatives:* fold it in as `v10` (collides, and puts a metric-less rung in a metric-ladder);
   tag it `v9-annotated` as a variant (implies it is a variant of v9's *scoring*, which it is not).

   *Tradeoffs:* two ladders, two logs and two trackers to keep straight, and the `ui_` prefix is ugly
   in filenames and commit messages. Accepted because without it `v1` means two different things
   permanently, and version collisions are unrecoverable once they are in commit history.

   *Defense:* the two ladders answer genuinely different questions — QWK asks whether the number was
   right, `ui_` asks whether the stated reasoning was right and whether a teacher can correct it —
   and no single metric orders both. Annotation artefacts are keyed to the *trait run* they explain
   (`annotation_v6_runB/`) rather than to a `ui_` version, since those trait scores are shared by v7,
   v8 and v9 alike.

2. **The teacher overrides trait scores; the holistic recomputes through the frozen aggregator. Direct
   holistic override is not offered.** The holistic is `1 + #{ s ≥ cᵢ }` over a fitted `s` — it is not
   a model output and there is nothing in it a correction could teach.

   *Alternatives:* override the holistic directly (simplest UI, and what a marker expects); allow
   both independently.

   *Tradeoffs:* a teacher who is certain the essay is a 5 cannot type 5. Their trait correction may
   be absorbed by the cut points and move nothing, which is a worse first-use experience than a text
   box. Mitigated by surfacing the no-op explicitly and by the score-formation panel (ui_5), and by
   the dissent flag below.

   *Defense:* a direct holistic override decouples the displayed score from the evidence displayed
   beside it, and cannot steer any future model behaviour because the aggregator is three fitted
   coefficients rather than a promptable instrument. Allowing both independently would produce rows
   where the traits imply 3.2 and the teacher asserts 5 with nothing recording why. Instead a distinct
   **score dissent flag** records "I disagree with the final score but not the traits" with a
   rationale and *no number* — that is information about the aggregator, and it is stored as such
   rather than disguised as a trait correction it isn't. This closes Open Question 1 of the
   superseded `../planning/teacher_override_ui_handoff.md`.

3. **Spans anchor by verbatim quote plus occurrence index, re-located to offsets at build time.**

   *Alternatives:* have the model emit character offsets directly; have it emit sentence or paragraph
   indices and highlight whole sentences.

   *Tradeoffs:* quoting costs output tokens proportional to the highlighted text, and a quote the
   model mis-transcribes fails the build rather than degrading gracefully — annotation batches will
   need re-running more often than offset-based ones would appear to.

   *Defense:* models cannot count characters, so emitted offsets are silently wrong, and a
   silently-misplaced highlight is the worst failure available here because it looks authoritative to
   the teacher whose trust the feature exists to earn. Sentence indices are robust but discard the
   sub-sentence precision the design needs. Quote-matching is the only option that is *mechanically
   verifiable*: it either matches the essay exactly or it fails loudly, which is the same stance
   `load_triage()` and the `SCORES` manifest already take. Matching runs on a whitespace-normalised
   projection because student text has irregular spacing a model will not reproduce when quoting.

4. **The human gold score is withheld from the review surface by default; revealing it stamps
   subsequent override records `gold_revealed: true`.**

   *Alternatives:* always visible (it is the researcher's own tool and comparison is the point); never
   available in the UI at all.

   *Tradeoffs:* an extra click before the comparison a researcher will often want, and a flag that has
   to be threaded through every override record.

   *Defense:* the reviewable essays come from `personal_training_set.csv`, which carries the rater's
   score, and overrides are intended to feed a few-shot bank later. An override formed while looking
   at the answer key would launder gold labels into the grading prompt through a door that neither the
   `SCORES` annotation manifest nor `--strip-scores` watches — the same leakage those guards exist to
   prevent, re-entering by a route they do not cover. Always-visible makes every override permanently
   unusable for steering with no way to tell which; never-available is over-strict, since the
   comparison is genuinely useful *after* the reviewer has committed to a view. Flagging preserves
   both and costs one boolean.

5. **The holistic score is never displayed without access to its derivation.** A collapsed
   score-formation panel exposes the weighted trait mean, the `log₁₀(word_count)` term, the continuous
   score, the band and the distance to the nearest cut point.

   *Alternatives:* show only `N/6`, matching the reference mock exactly; show no holistic at all in the
   review pane and display traits only.

   *Tradeoffs:* additional UI surface on a page whose value depends on being clean, and it exposes an
   uncomfortable fact to a teacher who may not want it.

   *Defense:* `corr(word_count, system_score) = 0.820` against the human raters' 0.688 — a substantial
   part of every holistic score is essay length, and four trait cards next to a bare `4/6` assert
   otherwise. Showing only the number would be the first place in this project where a score appears
   without its audit trail, in the one artefact built specifically for auditing. It is also
   load-bearing for ui_2: a teacher whose trait correction does not move the score needs to see the
   cut points to understand why. Collapsed by default keeps the everyday reading experience intact.

6. **Override records are an *input* to `build_review`, not a mutation applied to its output.** The
   build takes predictions, annotation batches, essay text and override records and returns the review
   state implied by all four.

   *Alternatives:* build the AI's view, then apply overrides as a separate transformation at read
   time; apply them in the request handler.

   *Tradeoffs:* every override triggers a rebuild rather than a patch, which is wasteful at larger
   corpus sizes and will need revisiting well before this reaches hundreds of essays.

   *Defense:* it collapses what would otherwise be two seams into one. With overrides as an input,
   span anchoring, batch validation, the join, holistic recomputation and override application all sit
   below a single pure function boundary, and the HTTP layer holds no logic worth testing. At ten
   essays the rebuild cost is irrelevant and the testability is worth more than the efficiency. This
   boundary is the design's main source of leverage and should be defended during implementation — if
   override application drifts into the request handler, the test suite loses most of its value.

7. **Overrides are stored append-only in a single JSON file.** One record per correction event, never
   mutated; current state is the latest record per essay.

   *Alternatives:* SQLite; one JSON file per essay; mutate a single current-state record in place.

   *Tradeoffs:* the file grows without bound as a teacher revises, and reading current state is a scan
   rather than a lookup. Both are irrelevant at this scale and both would matter at a larger one.

   *Defense:* one local user over ten essays needs neither concurrency nor indexing, and SQLite would
   make the correction history invisible to `git diff` — in a repository where every other artefact is
   a diffable text file and the project's whole discipline is that judgment calls stay inspectable.
   Append-only rather than in-place so that a reviewer who changes their mind twice leaves a trail;
   the *history of the teacher's own judgment* is data, not noise, and is the raw material for any
   future steering work.

8. **A trait with nothing citable reports the absence rather than failing the batch** (decision D1,
   taken 2026-09-03 while breaking `spec_ui_v1.md` into tickets). Guard 6 requires at least one
   anchored span per criterion. On a very short or very weak response there may be genuinely nothing
   to quote for a trait — most obviously Argumentation on an essay that never states a position — and
   the frozen sample deliberately contains a 159-word bottom-band essay, so this was going to fire on
   the first run.

   *Alternatives:* keep the hard ≥1 requirement and let the annotator stretch for a quote; drop the
   minimum entirely.

   *Tradeoffs:* it is an escape hatch, and an annotator that finds a trait hard will be tempted to
   use it instead of looking harder. Mitigated by requiring a written reason, by instrument language
   restricting it to genuine absence, and by the fact that the reason renders on the card where a
   teacher will see whether it was honest.

   *Defense:* forcing a citation where none exists makes the annotator fabricate one to satisfy a
   guard — precisely the failure the guards exist to prevent, arrived at by the guards themselves.
   Dropping the minimum instead permits silent absence, which is worse than either: on a bottom-band
   essay, *"there is no argument here to point at"* is the single most informative thing the
   annotator can say, and it should be recorded as a finding rather than shrugged off as an empty
   list. The absence becomes evidence.

9. **An inert trait correction expands the score-formation panel instead of silently doing nothing**
   (decision D2, same session). The override feature's dominant experience is that it does not visibly
   work, and this was measured rather than assumed. Against `aggregator_v9.json` and the ten sampled
   essays:

   | correction | move in `s` | essays whose displayed score changes |
   |---|---|---|
   | +1 on argumentation alone (heaviest trait, w=0.35) | 0.239 | **2 / 10** |
   | +1 on all four traits | 0.683 | 7 / 10 |
   | doubling the word count | 0.868 | — |

   Cut-point gaps are 0.781, 0.832, 0.844, 0.389. So the single-trait correction a teacher is most
   likely to make is inert four times in five — and **doubling the essay's length moves the
   continuous score further than raising every trait by a full point.**

   *Alternatives:* accept it and report "no change" in text; reopen ui_2 and allow direct holistic
   override after all.

   *Tradeoffs:* auto-expanding overrides the teacher's own choice to collapse the panel, and it puts
   the system's least flattering property in front of them at the moment they are most likely to be
   frustrated by it.

   *Defense:* the alternative is a control that appears broken, and a review surface whose first
   interaction appears broken does not get a second use. The expansion is also true rather than
   merely placating — the teacher is being shown a real fact about the instrument they are auditing,
   which is the entire purpose of the panel. Reopening ui_2 would trade an honest limitation for a
   dishonest one: a directly-typed holistic would *look* responsive while decoupling the score from
   the evidence beside it. This decision is why the panel is not optional polish.

10. **The panel's arithmetic lives in the build artifact, not in the page** (decision D3, taken
    2026-09-05 while building ticket 04). `_score_formation` gained the additive terms
    (`intercept`, `trait_term`, `length_term`, and a `terms` map keyed by the aggregator's own
    feature names) and two sensitivities (`s_per_trait_point`, `s_per_length_doubling`), each
    measured by running the frozen aggregator again rather than by multiplying coefficients. The
    renderer formats these numbers and derives none of them.

    *Alternatives:* store only the raw features and `beta` — which the artifact already did — and
    let the page multiply them out; compute the sensitivities once by hand and hard-code the two
    constants in the copy.

    *Tradeoffs:* a wider artifact, four more stored fields per essay, and two extra aggregator
    calls per essay per build. Some of the stored values are trivially derivable from the ones
    beside them, which reads as redundancy in the JSON.

    *Defense:* a page that multiplies β by a feature is a second implementation of the aggregator,
    and the ticket's own acceptance criterion — values read from the build artifact rather than
    recomputed in the page — is a statement about exactly that. Two implementations of a fitted map
    eventually disagree, and the one place that disagreement would surface is the panel built to be
    checked. Hard-coding the sensitivities is worse still: they are properties of
    `aggregator_v9.json`, so a v10 with a smaller β₂ would leave the page asserting v9's numbers in
    prose. Building the terms by zipping the aggregator's own `features` list rather than by
    position means a future feature set cannot silently relabel a coefficient — it would produce a
    term under a new name instead of mislabelling an old one. The cost is measured: the build is
    still under a tenth of a second over the sample.

    A consequence worth recording: the panel prints every term to three decimals so the column adds
    up on screen (+2.048 + 7.364 − 6.783 = 2.629). Two-decimal addends under a three-decimal total
    read as an arithmetic error, and this is the one panel whose whole purpose is being checked.

11. **A reveal is recorded once per essay, in its own ledger, not once per look** (decision D4,
    same session). `gold_reveals.json` holds one record per essay — essay id, timestamp, ladder
    version and trait run — written on the first reveal. Re-revealing returns the original record
    and its original timestamp. It is a separate file from `overrides.json`, and `gold.py` is the
    only module that reads the corpus `score` column at all.

    *Alternatives:* append an event per click, giving a full viewing history; store the flag inside
    the override records only, with no ledger of its own; keep a per-session flag in memory.

    *Tradeoffs:* the ledger cannot answer "how often was this looked at", and a reveal made and
    then regretted cannot be taken back — the essay is marked from that moment on.

    *Defense:* the question the flag has to answer is "was this correction formed with the answer
    key in view", and that is a property of the essay from the first reveal onward, not of any
    individual click. Once revealed, the score renders with the page on every subsequent load, so a
    second look takes no action that could be recorded — an event log would therefore undercount by
    construction while looking authoritative. The first timestamp is the one that bounds the
    corrections, which is why it survives. A separate file rather than a field inside overrides
    because a reveal precedes any correction and often produces none: storing it inside the record
    it is meant to qualify would mean the flag only exists once it is too late to be informative,
    and ticket 05 needs to read it before it writes. In-memory was rejected outright: a leakage
    control that a restart clears is not a control.

    The reveal is a **POST**, and `find()` runs before the ledger is touched, so the endpoint
    cannot be used to read the answer key of an essay outside the review set. The control says what
    it is: the CSV is on disk and reading it there is neither prevented nor logged. A control that
    overstates its own reach teaches the reviewer to trust a boundary that is not there.

12. **Current state is a fold over an essay's records, latest-wins *per section* rather than
    wholesale** (decision D5, taken 2026-09-05 while building ticket 05). `override_state()` walks
    an essay's records in order: a `trait_correction` sets the corrected traits, a `cleared`
    withdraws them, a `dissent` sets the dissent. Each kind overwrites only its own section. The
    artifact then distinguishes **`overridden`** (the trait scores as they now stand differ from
    the AI's) from **`reviewed`** (a teacher has been here at all).

    *Alternatives:* the spec's literal reading — the single most recent record is the whole current
    state; or require every record to restate the full state, so latest-wins is true by
    construction.

    *Tradeoffs:* "the latest record" is no longer a complete description of what the UI shows, so a
    reader of `overrides.json` has to know the fold rule to predict the page. Two of the three
    kinds are also silent about the sections they do not touch, which only reads correctly once
    you know that silence means "unchanged" rather than "cleared".

    *Defense:* a dissent and a trait correction answer different questions — "the aggregator is
    wrong" and "the traits are wrong" — and a teacher will often record both. Under wholesale
    latest-wins, recording a dissent after a correction would silently discard the correction, and
    the teacher's second deliberate action would undo their first with no indication. Requiring
    every record to restate the full state avoids that but makes each record a snapshot rather than
    an event, which destroys exactly what the steering bank needs: what the teacher *changed* and
    why. The fold keeps the ledger a list of events and still yields one unambiguous current state.
    Ticket 06 inherits the same rule for span verdicts and feedback edits, which is the second
    reason to settle it here rather than there.

    The `overridden`/`reviewed` split falls out of the same argument: a cleared correction and a
    dissent both leave every trait exactly as the AI wrote it, and an essay list that called those
    untouched would lose the two cases most worth looking at again.

13. **A record's recomputed holistic is obtained by building the artifact that would result from
    storing it** (decision D6, same session). `record_correction` runs `build_review` twice — once
    over the existing records, once with the prospective record appended — and stores what the
    second build produced. The page never previews a score either: saving posts, the server writes,
    and the page reloads server-rendered.

    *Alternatives:* call `apply_aggregator` directly in the writer, which is two lines; recompute in
    the browser so the teacher sees the new score without a round trip.

    *Tradeoffs:* two full builds per correction, each re-anchoring every span — measured at well
    under a tenth of a second over the sample, but linear in essay count and wasteful in principle.
    The reload also costs a round trip on every save and rebuilds a page that has mostly not
    changed.

    *Defense:* this is the same argument as ui_10, applied to the write path. Override records are
    an input to the build (ui_6), so the only number that is true is the one the build produces
    from them; anything else is a second implementation of a fitted map, and a record that
    disagreed with the page it came from would be worse than one with no number at all. A browser
    preview is the same mistake with a shorter half-life — and it would have to predict the
    *cut point* a continuous score lands in, which is precisely where a correction most often does
    nothing (ui_9). Letting the page guess "4" and then reload to "3" would discredit the
    instrument at the exact moment it is being audited. The reload is also what makes the panel's
    automatic expansion honest: it opens because the build said the band did not move, not because
    the page assumed it would not.

14. **An override record states what *it* did, against the score it was made against, and keeps
    the AI baseline as a separate field** (decision D7, review of ticket 05). `original_holistic`
    is the holistic standing at the instant the record was written and `score_unchanged` compares
    the rebuilt holistic to that same standing score; the AI's own number stays reachable as
    `ai_holistic`, alongside `original_traits`, which remains the AI's traits because
    `corrected_traits` is expressed relative to them.

    *Alternatives:* keep both fields on the AI baseline, which is what the first cut did; make
    every field relative to the standing state, including `original_traits`; store only the delta
    and let a reader recover the baseline by replaying the ledger.

    *Tradeoffs:* one record now carries two reference points, which a hand reader has to keep
    apart, and the field names have to earn that distinction. Replaying the ledger would need no
    baseline at all, but only for a reader willing to run the build.

    *Defense:* on the AI baseline, a dissent recorded after a correction stored
    `score_unchanged: false` and a 4 → 2 move that the *earlier correction* had caused, and a
    withdrawal that moved the displayed score 2 → 4 stored `score_unchanged: true`. Both are false
    statements in an append-only audit record that exists to be read by hand and is the evidence
    the ladder is judged on; a record misattributing another record's movement is worse than one
    carrying no claim. Keeping `original_traits` on the AI baseline is not an inconsistency but the
    same principle: it is the companion to `corrected_traits`, which lists only the traits that
    differ from the AI's, so any other baseline would make the pair unreadable.

    The same reasoning governs the rationale on a withdrawal. Clearing a correction no longer
    inherits the reason the page was rendered with — that text argues *for* the correction being
    withdrawn — so only a reason the teacher typed for the withdrawal travels with the `cleared`
    record.

15. **A trait correction can be withdrawn; a dissent can only be superseded** (decision D8, review
    of ticket 05). `cleared` withdraws a trait correction and restores the AI's scores. There is
    no kind that withdraws a dissent: a teacher who recorded one in error or with a typo writes a
    new dissent over it, and the latest-wins fold in `override_state` makes the newest one
    current. The dissent textarea is therefore rendered even once a dissent stands, prefilled with
    the standing reason and beside the record it would replace.

    *Alternatives:* a fourth kind (`dissent_cleared`) so both halves of the form are symmetrical;
    leave the dissent unrevisable, which is where the first cut of ticket 05 landed.

    *Tradeoffs:* the asymmetry has to be explained rather than inferred, and a dissent recorded
    against the wrong essay stays in the trail forever, answerable only by a later dissent saying
    so. A fourth kind would close that, at the cost of a persisted-schema change and a second
    withdrawal concept to keep coherent with `cleared`.

    *Defense:* the two disagreements are not the same shape, so a symmetrical form would be a
    false symmetry. A trait correction *changes a number the aggregator consumes*, so withdrawing
    it has to restore the AI's input and there is a definite state to return to. A dissent changes
    nothing and asserts something — that the fitted map is wrong here — and the honest way to
    retract an assertion in an append-only record is to make a better one, not to delete it. That
    is also what the ledger is for: a dissent, a correction of it, and the reasoning between them
    is exactly the material a later steering bank would want, and a withdrawal would erase it from
    the readback while leaving it in the trail, which is the worst of both. Superseding needs no
    new kind, no schema change, and no second meaning for "withdrawn", so ui_v1 stops here.

    The same principle settles where a rationale lives (ui_14, mirrored). A reason travels with
    the record kind it was typed for and no further: withdrawing a correction takes the reason
    with it rather than offering it back as the justification for whatever the teacher does next.
    Without that, clearing a correction with "on reflection the AI had it right" left that
    sentence in the correction textarea, and the teacher's next correction was stored against a
    reason arguing it should not have been made.

16. **The page narrates the save the teacher just made, against the score that save was made
    against** (decision D9, review of ticket 05). The artifact carries two separately named facts:
    `score_unchanged_vs_ai`, whether the corrections as they now stand leave the AI's score
    untouched, and `score_unchanged_by_latest_record`, whether the most recent record moved
    anything, measured against `holistic_before_latest_record`. The score head, the sentence under
    it and the score-formation panel's open state are all driven by the second.

    *Alternatives:* keep one flag on the AI baseline, which is where ui_14 left it and where this
    was found; narrate the net state instead of the last action, and drop the "did not move the
    score" sentence for anything after the first correction.

    *Tradeoffs:* two fields where there was one, and a reader of the artifact now has to notice
    which baseline a name refers to. The before/arrow/after head no longer always shows the AI's
    original either — on a second correction it shows the score being corrected away from, and the
    AI's number is carried by the trait cards and the formation panel instead.

    *Defense:* one flag could not answer both questions, and the page was asking the one it did
    not hold. Against the frozen aggregator, traits {4,3,3,2} at 60 words score 1; correcting to
    all 6 gives 2; a second correction to {4,3,3,3} gives 1 again. The old flag reported that
    second save as *unchanged* — the page said "did not move the score" and opened the panel while
    the record it had just written said the score went 2 → 1. The mirror case is worse: from all 6,
    correcting conventions to 5 leaves the score at 2, and the page said "moved this from 1 to 2"
    with the panel shut. That is precisely the "this control appears not to work" experience
    ui_9/D2 exists to explain, unexplained for every save after the first. A teacher reads that
    sentence in the second after clicking Save, so it is about that click; ui_14 already settled
    the same question for the ledger, and the page and the record now say the same thing.

    The same decision removes a contradiction in the unchanged render. `.score.corrected
    .score-was` is struck through, so the dominant case — a single trait moves the score on 2 of
    10 sampled essays — drew a struck-through 3, an arrow and an identical 3 directly above the
    words "did not move the score". A strikethrough asserts the value was superseded. When the
    save moved nothing there is no before to show, so the single number stands alone and the
    sentence and the self-opened panel carry the fact that a correction is recorded.

17. **Each kind of record is narrated as itself, and only a trait correction that landed in the
    same band opens the panel** (decision D10, review of ticket 05). `latest_save()` reads
    `latest_record_kind` first and answers with one of `moved`, `same_band`, `cleared`, `dissent`
    or nothing at all; the score head, the sentence beneath it and the score-formation panel's
    open state are all driven by that single value, as ui_16 requires.

    *Alternatives:* keep one boolean ("did the score move since the last record") and accept that
    a dissent reads as a correction that did nothing; suppress the sentence entirely for anything
    that is not a trait correction.

    *Tradeoffs:* four narrations to keep true instead of two, and the dissent case shows the
    standing correction's own before/after head rather than the last record's — the one place the
    head is not the last save's baseline, because a dissent has no baseline to speak of.

    *Defense:* on the synthetic fixture a trait correction to all 6 (1 → 2) followed by a dissent
    left `score_unchanged_by_latest_record` true, so the page said "Your latest correction did not
    move the score" and opened the panel. Three separate false statements: the teacher's last
    action was a dissent, not a correction; the panel offered a distance to the nearest cut for a
    record kind that cannot approach one; and the 1 → 2 the correction did cause vanished from the
    essay page while the index still showed "corrected 1 → 2 · dissent". A dissent moves no trait
    and no score by design — that is the whole of decision ui_2 — so reporting it as a correction
    that failed to move one tells a teacher their deliberate act was a broken trait edit. The
    panel stays shut for it because "how far is this essay from the nearest cut" answers why a
    TRAIT edit moved nothing, which is not the question a dissent raises. A withdrawal gets its
    own sentence for the same reason: it restores the AI's scores on purpose.

    Two guards moved with it. `essay_id` is now type-checked like `corrected_traits`, `rationale`
    and every trait value already were: ids in this corpus are numeric-looking strings, so the
    natural slip in a diffable hand-edited ledger is dropping the quotes, and `"essay_id": 79938`
    passed every guard while matching no essay — a correction that is in the file and invisible on
    every page, which is the exact outcome the collect-all guards exist to prevent. A record
    naming an essay outside the review set is still ignored silently; only the type is checked.
    And `record_correction` re-folds the trail once the record is complete, because the build that
    produces the recomputed holistic must read the record before it carries one: the POST response
    was handing back a trail entry whose `recomputed_holistic` was null where a later GET of the
    same essay returned the real number.

18. **The score narration is one table of states, not a chain of conditionals** (decision D11,
    review of ticket 05). `SCORE_NARRATION` has one row per state the essay page can be in, and
    each row decides all three outputs together: which holistic the head contrasts the current one
    against (or none, drawing a single number), whether the score-formation panel opens itself,
    and the sentence beneath. `narration_state()` picks the row; nothing else branches.

    *This supersedes the approach of ui_16 and ui_17, not their conclusions.* Both are still
    right about what the page should say. What was wrong was fixing it one branch at a time:
    ui_14 moved the ledger's baseline, ui_16 moved the page's to match, ui_17 added the record
    kind, and each round's review found the next uncovered corner of the same function. Three more
    arrived after ui_17 — a struck-through AI score above the words "every trait still reads as it
    was scored"; a second correction that added nothing printing a bare number and hiding the AI's
    holistic from the page entirely, which the ticket requires be shown; and a save that only
    rewrote a reason being told its correction failed to move the score. Those were one defect
    reported four times. The head, the sentence and the panel were computed by separate
    conditionals over overlapping questions, so any state the branches did not jointly cover
    produced a page contradicting itself.

    *Alternatives:* keep patching the branch each round exposes; drop the sentence for every case
    except the first correction, which is the smallest change and the least useful page.

    *Tradeoffs:* ten rows where there were four branches, and adding a state means writing the row
    rather than an `if`. That is the point — a missing row is a `KeyError` at the seam, where a
    missing branch was a plausible-looking sentence.

    *Defense:* the dimensions are genuinely independent and the old code conflated two of them.
    Whether the LATEST record moved the score and whether the corrections now STANDING have moved
    it off the AI's are different questions: a second correction can add nothing to a first that
    already moved the band. Separating them is what lets `corrected_inert_off_ai` say both things
    at once — the corrections moved this 1 → 2, and the latest one added nothing — where the old
    single branch could only say one and chose the one that hid the AI's number.

    Three rules are asserted over the table itself rather than trusted per row: a contrast is only
    drawn between two different holistics, because a strikethrough beside an identical number
    asserts a falsehood; "every trait still reads as it was scored" appears only where no trait
    differs from the AI's; and only a trait correction that edited traits and did not move the
    band opens the panel, because the distance to the nearest cut answers a question neither a
    dissent nor a withdrawal asks. Every state also has a test asserting head, sentence and panel
    together, which is the coverage that would have caught all three rounds in one pass.

    A reason-only save is now its own state. The page sends every trait that differs from the
    AI's, so rewriting just the reason re-posts the standing traits: a real record, because the
    reason did change, but one that edited no trait. `latest_record_changed_traits` is read off
    the two folds `override_state` already computes, so the ledger format is untouched.
