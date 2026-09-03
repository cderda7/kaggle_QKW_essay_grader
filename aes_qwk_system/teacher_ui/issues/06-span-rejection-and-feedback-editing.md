# 06: Span rejection and feedback editing

**What to build:** The other half of disagreement — correcting how the AI *explained* itself, as
opposed to what it scored. A teacher can reject an individual highlight as unsupported, and can edit
a trait's feedback text or the overview paragraph.

These are stored in their own sections of the override record, separate from score corrections,
because they answer a different question. "The AI scored this wrong" and "the AI explained this
badly" must stay distinguishable — conflating them would make both unusable as evidence, and span
rejections are the raw material for the span acceptance rate that later versions of this ladder will
be judged on.

One edge the earlier tickets leave open: the build guarantees every trait card has at least one span
or a stated reason for having none, but a teacher rejecting every span on a card recreates the empty
state through the sanctioned path. That state needs to render as what it is — evidence that was
offered and refused — rather than looking like a card that never had any.

**Blocked by:** 05.

**Status:** ready-for-agent

- [ ] Any individual span can be rejected as unsupported, and the rejection is visible on the page afterwards
- [ ] A trait's feedback comment can be edited without discarding the rest of the assessment
- [ ] The overview paragraph can be edited
- [ ] Span verdicts and text edits are stored in their own sections of the record, distinct from score overrides
- [ ] A card whose spans have all been rejected renders so the absence reads as refused evidence, not as a trait that never had any
- [ ] Rejections and edits survive reload and a rebuild of the artifact
- [ ] An edit can be reverted to the AI's original text without erasing the record that it was edited
- [ ] Rejecting a span does not alter any trait score or the holistic
