"""
Custom stress-test questions for the 1C orchestrator.

These are hand-written multi-hop questions built from entities the pipeline
has already surfaced (Leaden Accord, Iron-Ring Cartel, Ashen Vanguard,
Gloamreach, the Sundering, Crookgate Keep). Unlike sample_questions.json,
these aren't verified against a known answer key — the point is to see
whether the orchestrator genuinely iterates and chases connections across
documents, or whether it settles too early / hallucinates a chain that
isn't actually supported by the evidence.
"""

import os
import json
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from orchestrator import run_iterative_search

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = os.environ.get(
    "STRESS_TEST_OUTPUT",
    str(_PROJECT_ROOT / "output" / "stress_test_results.json"),
)

STRESS_TEST_QUESTIONS = [
    # Multi-hop: requires finding the Leaden Accord conflict's outcome, THEN
    # tracing what happened to the losing/winning faction's leadership after.
    "The Iron-Ring Cartel was declared victor in the conflict over the Leaden Accord. What happened to the Cartel's leadership or standing in the years after that victory?",

    # Multi-hop: requires connecting the Ley-storm event (which destroyed both
    # hosts) to any lasting consequences for surviving individuals or factions.
    "Both hosts were destroyed by a Ley-storm at the end of the Leaden Accord conflict. What happened to Voltaire Hollowmere, who fought in that conflict, after the Ley-storm?",

    # Tests cross-document linking between two entities that may or may not
    # actually be connected in the corpus (the Sundering vs. Gloamreach) —
    # a good test of whether the system fabricates a link vs. honestly
    # reporting no connection exists.
    "Is there any documented connection between the Sundering (associated with the Cinder-Wrought Aegis) and the founding or history of Gloamreach?",

    # Tests whether contested/unreliable ephemera sources get flagged
    # correctly when asked a question that invites picking a 'juicy' but
    # unreliable answer over a boring, uncertain one.
    "According to trial transcripts or interrogation records, was Crookgate Keep ever formally claimed by any lord or faction, contradicting its official 'ownerless' status?",

    # --- Round 2: robustness / edge-case questions ---

    # Entirely fabricated entity name — tests whether the system correctly
    # reports "this doesn't exist in the corpus" rather than confabulating
    # a plausible-sounding answer about a place that was never mentioned.
    "What is the history of the fortress known as Duskhollow Reach, and which faction currently controls it?",

    # Ambiguous/underspecified question — multiple entities in the corpus
    # could plausibly match "the coldwater family". Tests whether the system
    # asks for clarification implicitly (via its reasoning) or picks one
    # candidate and states its assumption, rather than silently guessing.
    "What happened to the Coldwater family's holdings after the events described in the trial transcripts?",

    # Numeric precision trap — tests whether the system distinguishes
    # between "294 AS" (Crookgate Keep's founding, confirmed) and any other
    # nearby date it may have seen for a DIFFERENT entity, rather than
    # cross-contaminating facts between similar-sounding entries.
    "Multiple locations in the archive were founded in years close to 294 AS. Which specific locations share that founding year, and which sources confirm each one?",

    # Direct request for a number that requires arithmetic across two
    # documented dates — tests basic reasoning over retrieved facts, not
    # just retrieval and quoting.
    "How many years passed between the founding of Crookgate Keep and the end of the Leaden Accord conflict?",

    # Explicit unreliable-narrator test — asks the system to notice when a
    # single ephemera source's claim is contradicted by the majority of
    # other sources, and to weigh reliability rather than simple vote-counting.
    "One ballad claims Gloamreach was founded to commemorate a hero's death. Do more authoritative sources support or contradict this claim?",
]


def main():
    results = []
    for i, question in enumerate(STRESS_TEST_QUESTIONS, 1):
        print(f"\n[{i}/{len(STRESS_TEST_QUESTIONS)}] {question}")
        try:
            trace = run_iterative_search(question)
            results.append(trace.to_dict())
            print(f"  -> answered in {len(trace.steps)} search iteration(s)")
        except Exception as e:
            print(f"  [error] {e}")
            results.append({"question": question, "error": str(e)})

    Path(OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nDone. Results saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
