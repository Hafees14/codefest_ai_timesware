# Limitations

Honest account of what doesn't work, based on actual testing.

## 1. openrouter/free occasionally returns non-JSON responses
Observed: 3 of 4 stress-test questions triggered at least one non-JSON
response (a stray safety-classifier-style string) on the first attempt.
Root cause: the router randomly selects among live free models, some of
which don't reliably follow "respond only in JSON." Mitigated with
automatic retry (succeeded in every observed case) — a workaround, not a
fix; the underlying unpredictability remains.

## 1b. Sufficiency judgment is still a single LLM call, checked but not replaced

An independent code-level check now overrides the LLM's sufficiency
self-report specifically when a reformulated query retrieves
near-duplicate evidence to a prior search (see decisions.md #8). This
closes one real gap, but the core sufficiency decision — "is this enough
to answer" — is still made by a single, unstructured LLM JSON response
with no evidence-coverage checklist, entity tracking, or independent
confidence score behind it. A skeptical reviewer asking "what code
decides you have enough evidence" should be told exactly this, not given
an inflated description of the mechanism.

## 1c. Measured, n=4: judge_sufficiency can accept a contested claim as settled while acknowledging the conflict, then synthesis hedges rather than fully refusing

A 4-run repeat test of `1c_000` (Gloamreach's founding year — see
`output/1c_000_repeat_runs.json`) found: **1 of 4 runs (25%)** had
`judge_sufficiency` return `"sufficient": true` at iteration 2 despite
its own reasoning for that call explicitly noting *"the main Gloamreach
article indicates general controversy"* — it saw the conflict and chose
to treat the codex as authoritative anyway. The other 3 of 4 runs never
reached `sufficient: true` at all; they were stopped by the independent
near-duplicate-retrieval check (decisions.md #8) after iteration 2, still
undecided.

**This was verified as a reasoning/weighting difference, not a retrieval
miss**: the wiki's "contested, no year should be assigned" language was
present in the accumulated evidence context by iteration 1 in every run,
including the one that later returned `sufficient: true` — the evidence
was there; the model chose to prioritize one source over an
already-visible conflict.

**The resulting final answer was not silent about the conflict**, which
somewhat softens the finding: it led with a direct, bolded "246 AS"
answer, then still appended *"There is a conflict: `wiki\gloamreach.md`
says Gloamreach's founding is contested..."* in the same response. So
`synthesize_answer` did not fully fail to surface the disagreement — but
it also did not refuse to commit to a number the way the other 3 runs
effectively did (by never reaching a confident answer at all). The
practical failure mode observed is a **hedge**, not a fully silent wrong
answer: a confident-sounding lead claim followed by a caveat, rather
than either a clean refusal or a clean single answer. Whether a
skimming reader would notice the caveat below a bolded number is a real
concern even though the information is technically present.

This converts what was previously a general, unbenchmarked concern
(entry 1b) into a measured one: **1/4 observed**, on a small n, with the
exact mechanism identified (a sufficiency judgment that acknowledges a
conflict but resolves it by source-authority preference, not by
declining to answer).

## 1d. The same question behaves differently across repeated runs, confirmed at n=4

A 4-run repeat of `1c_000` under identical input found: 3 of 4 runs
stopped after 2 iterations via the independent near-duplicate check,
never reaching a confident sufficiency verdict; 1 of 4 reached
`sufficient: true` at iteration 2 with the hedged-answer behavior
described in 1c above. This is the `openrouter/free` per-call model
rotation (documented since decisions.md #2) manifesting as measured
behavioral variance on identical input, not a hypothetical risk.
Practically: a live demo re-run of this specific question has an
observed roughly 1-in-4 chance of producing the more confident, hedged
answer rather than the fully-refusing one — plan the demo accordingly
(see demo_script.md's failure-prevention checklist; a recorded
known-good run is a reasonable, disclosed fallback given this is a
documented property of the free-tier infrastructure, not something the
team is hiding).

## 2. Single-iteration answers rely on retrieval luck
One test question resolved in a single iteration because the first
retrieval happened to surface everything needed. Manually verified as
accurate, but the system has no mechanism to force a second
cross-verifying search — a single-iteration stop is not an independently
guaranteed property.

## 3. Text-only (out of scope for 1A-style questions)
Cannot answer questions requiring diagram/image reading. A 1A-tagged
question run against this pipeline during early development (before
sample-question filtering was added) produced a text-based attempt rather
than recognizing the question was out of scope.

## 4. Dependent on the LLM's honesty about "no answer" being genuine
The system's strongest observed behavior — refusing to fabricate when
evidence is insufficient — is a property of the specific free models the
router happened to use during testing, not independently enforced by the
orchestrator's code.

## 5. No automated evaluation against a ground-truth answer key
Testing has been manual: running questions and verifying outputs against
raw corpus files by hand. No automated scoring pipeline exists.

## 6. Deduplication assumes cross-format documents are truly identical
Not verified for every deduped file pair — only spot-checked for a few.
If any pair has meaningfully different content between formats, that
content would be silently missing from the index.

## 7. Query planning is still LLM-driven, not symbolic

`plan_initial_query()` (added after external review) answers "how do you
decide where to look" with a real, separately-inspectable step — but it
is still one LLM call proposing entities and a focused query, not a
deterministic entity-extraction pipeline. Its quality is only as good as
that single call's output for a given question, and it has not been
benchmarked against the previous "raw question as first query" behavior
across a range of questions to confirm it reliably improves first-search
relevance rather than just changing it. A fallback to the raw question on
any planning failure exists specifically so this addition cannot make
the pipeline strictly worse than before.

**Observed, not just designed**: during priority testing of `1c_003`
("Gauntlet of Sorrowfell" forging year), `plan_initial_query()` genuinely
failed with a JSON parse error on that run, and the fallback correctly
substituted the raw question as the first search — this is the first
real execution of that fallback path, not just a code review confirming
it exists. The question still resolved correctly in one iteration
because both conflicting sources happened to be present in that first
retrieval regardless of which query (planned or raw) triggered it — a
convenient outcome that does not by itself confirm the fallback always
recovers gracefully when retrieval quality genuinely depends on the
planning step succeeding.

## 8. Hybrid retrieval fusion weight is unvalidated

The new BM25 + dense fusion in `embed.py` uses simple reciprocal-rank
summing with no tuned weighting between the two signals, and has not
been tested against the real corpus to confirm it retrieves better
evidence than dense-only search did. It is a reasonable, low-risk
addition given the corpus's known OCR/mixed-reliability profile, but its
actual effect on answer quality is currently unverified — the same
honesty standard applied to the near-duplicate-retrieval check (see
entry 1b) applies here: this should be described as "a principled
addition," not as a benchmarked improvement, until it is tested.

## 8b. Near-duplicate overlap threshold (0.6) is unvalidated against a real repeat-loop case

`chunks_are_near_duplicate()` uses a hardcoded 0.6 overlap threshold to
decide when a reformulated query has stopped surfacing new evidence.
This value was chosen as a reasonable default, not derived from testing
against an actual case where the LLM's `next_query` looped back to
semantically-similar-but-differently-worded territory. `src/
before_after_comparison.py` (added after the third review) can surface
whether this fires during real stress-test runs — check its output for
`[independent check]` log lines and confirm at least once that the
threshold triggers on a genuine repeat and does not false-positive on a
legitimately different follow-up query.

## 9. Commit history: acknowledged, not retroactively fixable

An external review correctly identified a thin commit history relative
to the amount of iterative work reflected in this documentation and
codebase. This cannot be fixed retroactively without fabricating a false
history, which would be worse than an honest short one if discovered.
Going forward from this point, remaining work is committed in smaller,
real increments to at least partially reflect the iteration that has
genuinely occurred.

## 10. Hybrid search's "score" field is not a single comparable metric

`embed.py`'s `search()` originally crashed when a chunk was found only by
the BM25 pass and never appeared in the widened dense top-k (a real bug,
caught during pre-demo testing, not by static review — the BM25-sourced
chunk had no `"score"` key at all). Fixed by ensuring every returned
chunk always has a `"score"` field. However, that field's *meaning*
still differs depending on origin: a dense-only or dense-and-BM25 chunk
carries a cosine distance, a BM25-only chunk carries `None` for `score`
and its raw BM25 value only in the separate `"fusion_score"` field.
Callers that log or display `"score"` should be aware it is not one
consistent scale across all returned chunks — `"fusion_score"` is the
actual value used to rank results in hybrid mode.
