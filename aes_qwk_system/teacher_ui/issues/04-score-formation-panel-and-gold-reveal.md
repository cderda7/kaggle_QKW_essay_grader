# 04: Score-formation panel and gold-score reveal

**What to build:** Two pieces of honesty the review page needs before anyone is asked to trust it.

First, a way to see how the holistic score was actually formed. Four trait cards next to a `4/6`
assert that the traits produced the 4, and they did not: a substantial part of every score is essay
length. Measured on the sampled essays, doubling the word count moves the underlying continuous score
further than raising all four traits by a full point. A collapsed panel exposes the weighted trait
mean, the length term, the continuous score, the band it fell into and the distance to the nearest
cut point — so a teacher can locate which step they disagree with instead of being handed a number.

Second, the human rater's gold score is withheld by default and revealed only deliberately, with the
reveal recorded. This is a leakage control: overrides are meant to feed a steering bank later, and a
correction formed while looking at the answer key would launder gold labels into the grading prompt
through a route the existing blindness guards do not watch. It is a flag rather than a ban — reading
the source data directly is still possible and unrecorded — and it should be described that way.

**Blocked by:** 03.

**Status:** ready-for-agent

- [x] A score-formation panel is collapsed by default and preserves the page's ordinary reading experience
- [x] Expanded, it shows the weighted trait mean, the word count and its length term, the continuous score, the band, and the distance to the nearest cut point
- [x] Those values are read from the build artifact rather than recomputed in the page
- [x] The panel makes the length contribution explicit rather than leaving it to be inferred
- [x] The gold score is not present in the served page at all until it is deliberately revealed
- [x] Revealing the gold score for an essay is recorded
- [ ] Override records created for that essay after a reveal carry the flag — *the seam is
      built and tested (`gold.was_revealed()` flips on reveal and survives restart), but no
      override record exists to carry it until 05, which stamps from it*
- [x] The reveal control states plainly that it is recorded and why
