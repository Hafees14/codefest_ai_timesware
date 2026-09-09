"""
Before/after comparison harness for the two unbenchmarked additions
flagged in the third audit:
  1. plan_initial_query() (query planning before first search)
  2. hybrid dense+BM25 retrieval (vs. pure dense)

Runs the same set of questions under all four combinations and saves
results side by side, so a real (even small) before/after comparison can
be reported honestly in limitations.md / the submission report, per the
third audit's top P1 recommendation.

This does NOT auto-judge which answer is "better" — that requires human
judgment against the corpus, same as all prior manual verification in
this project. It just makes the four conditions easy to run and diff.
"""

import os
import json
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import embed
import orchestrator

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = os.environ.get(
    "COMPARISON_OUTPUT",
    str(_PROJECT_ROOT / "output" / "before_after_comparison.json"),
)

# Reuse a few questions already used in prior testing so results are
# comparable to what's already been manually verified against the corpus.
COMPARISON_QUESTIONS = [
    "State the precise year in the Age of Shadows that marks the true founding of Gloamreach.",
    "What happened to Voltaire Hollowmere after the Ley-storm that ended the Leaden Accord conflict?",
    "Is there any documented connection between the Sundering (associated with the Cinder-Wrought Aegis) and the founding or history of Gloamreach?",
]


def run_condition(question: str, use_planning: bool, use_hybrid: bool):
    """Runs one question under one of the four (planning x hybrid) settings.
    Monkeypatches the module-level toggles rather than threading a config
    object through every function — acceptable for a one-off comparison
    script that is not part of the shipped pipeline."""

    # Toggle hybrid retrieval by wrapping embed.search for this call only.
    original_search = embed.search
    def wrapped_search(query, top_k=5):
        return original_search(query, top_k=top_k, use_hybrid=use_hybrid)
    embed.search = wrapped_search

    # Toggle planning by bypassing plan_initial_query when disabled.
    original_plan = orchestrator.plan_initial_query
    if not use_planning:
        orchestrator.plan_initial_query = lambda q: {"key_entities": [], "initial_query": q}

    try:
        trace = orchestrator.run_iterative_search(question)
        result = trace.to_dict()
    finally:
        embed.search = original_search
        orchestrator.plan_initial_query = original_plan

    return result


def main():
    all_results = []
    conditions = [
        ("planning=OFF, hybrid=OFF (original audit-1 baseline)", False, False),
        ("planning=ON,  hybrid=OFF", True, False),
        ("planning=OFF, hybrid=ON", False, True),
        ("planning=ON,  hybrid=ON (current default)", True, True),
    ]

    for question in COMPARISON_QUESTIONS:
        print(f"\n{'='*70}\nQUESTION: {question}\n{'='*70}")
        question_results = {"question": question, "conditions": {}}

        for label, use_planning, use_hybrid in conditions:
            print(f"\n  -- Condition: {label} --")
            try:
                result = run_condition(question, use_planning, use_hybrid)
                question_results["conditions"][label] = {
                    "num_iterations": len(result["steps"]),
                    "plan": result.get("plan", {}),
                    "final_answer": result["final_answer"],
                }
                print(f"     iterations: {len(result['steps'])}")
            except Exception as e:
                print(f"     [error] {e}")
                question_results["conditions"][label] = {"error": str(e)}

        all_results.append(question_results)

    Path(OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"\n\nDone. Full comparison saved to {OUTPUT_FILE}")
    print("Next step: manually read the final_answer under each condition")
    print("for each question and note in limitations.md whether hybrid/")
    print("planning changed answer quality, iteration count, or neither.")


if __name__ == "__main__":
    main()
