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

import json
from pathlib import Path

from orchestrator import run_iterative_search

OUTPUT_FILE = r"D:\COMPETITIONS\SLIIT CodeFest\CodeFest AI Innovation\codefest-ai\output\stress_test_results.json"

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
