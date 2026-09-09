# Demo Video Script — Team Timesware, Sub-track 1C

Target length: 10 minutes max. Minimum 3-4 minutes must be genuine live,
unedited screen recording of the working system.

---

## Segment 1 - Intro (30-45 sec, narrated over slides or face-to-camera)

- "We're Team Timesware, and we built an iterative search assistant for
  Sub-track 1C over the Ashen Era Archive."
- One sentence on why 1C: "The corpus is deliberately unreliable and
  interconnected. A single retrieval pass can't catch conflicting sources
  or chase multi-step facts. Our system searches the way a human
  researcher would: look, evaluate, refine, repeat."
- Show the architecture diagram (docs/diagrams/architecture.png) for
  about 10 seconds while narrating the three stages: ingest, embed,
  orchestrate.

## Segment 2 - LIVE DEMO (aim for 4-5 minutes, unedited)

Run these on screen, live, in order. Do not pre-record and cut - the
requirement is a genuine live demonstration.

### Demo question 1 (show it works normally)
Run: "To which shadowed redoubt must one journey to examine the relic
long borne by Cerys Sablewood the Ashen since 356 AS?"

**Before it runs**, narrate: "First, watch it plan. It doesn't just fire
the raw question at the search engine."

**Immediately point out on screen**: the printed `[plan]` line showing
`key_entities` and the `initial_query` it constructed — this is the
`plan_initial_query()` step, logged directly into the trace
(`SearchTrace.plan` in the JSON output). Say: "This is a real, separate
step deciding where to start looking, before any retrieval happens."

While the loop runs, narrate: "Now watch it iterate. It's not just
grabbing one passage. It's checking whether it actually has enough to
answer."

Point out on screen: iteration 1 identifies the relic (The
Cinder-Wrought Aegis) and its bearer, but doesn't yet know where the
relic is housed; iteration 2's query pivots to chase that specific gap,
and the final answer correctly chains bearer -> relic -> location
(Gloamreach), citing both the codex and the wiki consistently.

Say out loud: "That second query wasn't scripted — it came from what
the system learned in the first search. That's the actual behavior
Sub-track 1C is asking for."

**Note (not shown live, kept for the report):** we also ran a question
requiring source-conflict resolution ("true founding year of
Gloamreach") and found it exposed a real gap — on 4 repeated runs, the
sufficiency check accepted a single source's claim without
cross-referencing a contradicting source already in evidence in 1 of 4
runs (see docs/limitations.md). We're not demoing it live given that
measured variability, but it's documented honestly as a known failure
case rather than hidden.

### Demo question 2 (show it resists fabrication - your strongest result)
Run: "What happened to Voltaire Hollowmere after the Ley-storm that ended
the Leaden Accord conflict?"

While it runs, narrate: "This one genuinely isn't answerable from the
corpus. Let's see what it does."

Point out: it runs the full 5 search iterations trying different angles,
then explicitly says the record doesn't preserve his fate. It doesn't
make something up.

Say out loud: "This is the behavior we're proudest of. Most retrieval
systems will confidently answer anyway. Ours won't."

### Demo question 3 (optional, if time allows - false-premise catch)
Run: "According to trial transcripts or interrogation records, was
Crookgate Keep ever formally claimed by any lord or faction, contradicting
its official 'ownerless' status?"

Point out: the system corrects the question's own false premise (the
record says "contested," never "ownerless") rather than accepting it.

## Segment 3 - Architecture walkthrough (2-3 min, can be narrated over
code/diagram, doesn't need to be live)

- Briefly show ingest.py, embed.py, orchestrator.py in the editor.
- Mention 1-2 concrete technical decisions from docs/decisions.md:
  - "We hit a rate-limit wall with the recommended embedding API without
    a payment card, so we switched to a fully local, free embedding
    model. No cost, no card, no limits."
  - "We also found that specific free LLM model IDs kept going stale
    mid-development, so we switched to OpenRouter's auto-router instead
    of hardcoding one."
- Show the SearchTrace JSON output briefly: "every search iteration is
  logged, so the whole reasoning process is auditable."

## Segment 4 - Limitations, honestly (30-45 sec)

- "We know this system is text-only, so it can't handle 1A-style image
  questions."
- "The free LLM router occasionally returns unexpected output. We added
  automatic retry, and it recovered every time in our testing, but it's
  worth naming as a known constraint of using free infrastructure."

## Segment 5 - Close (15-20 sec)

- "Full details are in our report and docs. Thanks for watching."

---

## Filming checklist

- [ ] Record in one take if possible for the live demo segment - natural
      pauses while the system runs are fine and expected (waiting for an
      LLM call is realistic, not dead air to cut).
- [ ] Make sure .env with your API key is NOT visible on screen at any
      point.
- [ ] Terminal font size large enough to read on a recording.
- [ ] Upload to YouTube as unlisted (not public, not private). Paste the
      link at the top of submission_report.docx/.pdf.
- [ ] Confirm total runtime is under 10 minutes before final export.
