# Limitations

Honest account of what doesn't work, based on actual testing (not
speculation) against the official 1C sample questions and hand-written
stress-test questions.

## 1. `openrouter/free` occasionally returns non-JSON responses

**Observed**: In stress testing, 3 of 4 hand-written questions triggered at
least one non-JSON response from the LLM on the first attempt — in every
observed case, the response was the literal string `"User Safety: safe"`,
which looks like a content-moderation classifier's verdict leaking through
rather than an actual answer to the prompt.

**Root cause**: `openrouter/free` randomly routes each request to a
different currently-live free model. Some of these models don't reliably
follow the "respond only in JSON" instruction.

**Mitigation in place**: `judge_sufficiency` retries the call (up to 3
attempts) if a response doesn't contain anything JSON-shaped. In every
observed case so far, a retry succeeded — implying the router landed on
a more compliant model on the next attempt. This is a workaround, not a
fix: the underlying unpredictability remains.

**If this recurs at scale**: pin a single specific free model (e.g. via
`openrouter.ai/models?max_price=0`) instead of the auto-router, trading
resilience-to-model-rotation for more consistent instruction-following.

## 2. Single-iteration answers are not automatically less trustworthy, but warrant scrutiny

**Observed**: One stress-test question (about Crookgate Keep's ownership
status) resolved in a single search iteration, because the first
retrieval happened to surface all the relevant conflicting sources
together. The answer was manually verified against the raw source file
and found accurate.

**Risk**: this is a matter of retrieval luck, not a guaranteed property.
A single-iteration stop means the sufficiency judgment saw enough in the
first retrieval — it does not independently confirm that a *second*,
differently-worded search wouldn't have surfaced a contradicting source
the first search missed. The system has no mechanism to force a minimum
number of iterations for cross-verification.

## 3. No image/diagram handling (out of scope for 1C, relevant if judges probe boundaries)

This system is text-only. It cannot answer questions that require reading
a diagram, plate, or figure directly (that's sub-track 1A's requirement).
When a 1A-style question was accidentally run against this pipeline during
development (before sample question filtering was added), the system
attempted a text-based answer rather than recognizing the question was
out of scope for it. The `run_sample_questions.py` script now filters to
1C-tagged questions specifically to avoid this, but the underlying
orchestrator itself has no explicit check for "this question needs an
image."

## 4. Dependent on the LLM's honesty about "no answer" being genuine

The system's strongest observed behavior is refusing to fabricate an
answer when the evidence doesn't support one (see decisions.md and the
stress-test results). This is a property of the specific free models
`openrouter/free` happened to route to during testing — it is not
independently enforced by the orchestrator's code. A different or future
model could behave less conservatively (i.e., more willing to guess) and
the system would not detect or prevent that; `synthesize_answer`'s prompt
asks the model to only use provided evidence and flag conflicts, but
compliance is not verified programmatically.

## 5. No automatic evaluation against a ground-truth answer key

Testing so far has been manual: running questions and reading the outputs
to judge whether they're accurate and well-reasoned. There is no automated
scoring against `sample_questions.json` (which does not ship with answers)
or any other ground truth. Quality assessment in this submission relies on
manual verification against the corpus source files (as done for the
Crookgate Keep and Gauntlet of Sorrowfell test cases).

## 6. Deduplication assumes cross-format documents are truly identical

The pipeline assumes that when the same document exists as both `.docx`
and `.pdf` with the same base filename, the content is identical and
skips the non-preferred format. This was not verified for every one of
the ~15 deduped file pairs — only spot-checked for a couple. If any pair
turns out to have meaningfully different content between formats (e.g. an
abridged PDF vs. a full DOCX), that content would be silently missing
from the index.
