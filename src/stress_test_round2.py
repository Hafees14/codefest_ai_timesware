"""
Round 2 adversarial stress-test questions.

Broader than stress_test.py — targets different failure categories:
1. A question about an entity that likely doesn't exist in the corpus at all
   (tests: does it hallucinate an entity into existence, or correctly say
   "not found"?)
2. An ambiguous question with two plausible referents (tests: does it pick
   one silently, or notice the ambiguity?)
3. A question with a subtly wrong fact embedded in it (tests: does it
   correct the premise, or answer around the error uncritically?)
4. A very broad, vague question (tests: does it ask a reasonable narrower
   question via its search queries, or spin uselessly?)
5. A question phrased to sound like it needs a number/date but the corpus
   may only have qualitative info (tests graceful degradation)

Run this the same way as stress_test.py. Results are NOT pre-verified —
they must be manually checked against the corpus, same as before.
"""

import os
import json
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from orchestrator import run_iterative_search

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = os.environ.get(
    "STRESS_TEST_ROUND2_OUTPUT",
    str(_PROJECT_ROOT / "output" / "stress_test_round2_results.json"),
)

ROUND2_QUESTIONS = [
    # Entity that (as far as we know from exploration so far) may not exist —
    # tests whether the system invents details for a plausible-sounding but
    # fictional-within-the-fiction name rather than reporting "not found."
    "What role did the mercenary captain 'Dread Varlen Ashcroft' play in the fall of Crookgate Keep?",

    # Ambiguous: 'the Cartel' could mean the Iron-Ring Cartel specifically,
    # or be read as a generic reference — tests whether the system
    # disambiguates explicitly rather than silently assuming one meaning.
    "What territory does the Cartel control?",

    # Embeds a subtly wrong premise: earlier testing established Gloamreach's
    # founding year is CONTESTED (246 AS per codex, 286 AS per an ephemera
    # contract) — this question asserts 250 AS as if settled, a year that
    # doesn't match either documented candidate.
    "Since Gloamreach was founded in 250 AS, what other settlements were established in the same decade?",

    # Deliberately broad/vague — tests whether the iterative search narrows
    # productively or thrashes without converging.
    "Tell me about conflict in the Ashen Era.",

    # Looks like it wants a number but the underlying fact may only be
    # qualitative/contested — tests graceful degradation instead of
    # inventing a precise-sounding but fabricated figure.
    "How many soldiers did the Ashen Vanguard lose in the Leaden Accord conflict?",
]


def main():
    results = []
    for i, question in enumerate(ROUND2_QUESTIONS, 1):
        print(f"\n[{i}/{len(ROUND2_QUESTIONS)}] {question}")
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
