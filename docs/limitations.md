# Limitations

Honest account of what doesn't work, based on actual testing.

## 1. openrouter/free occasionally returns non-JSON responses
Observed: 3 of 4 stress-test questions triggered at least one non-JSON
response (a stray safety-classifier-style string) on the first attempt.
Root cause: the router randomly selects among live free models, some of
which don't reliably follow "respond only in JSON." Mitigated with
automatic retry (succeeded in every observed case) — a workaround, not a
fix; the underlying unpredictability remains.

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
