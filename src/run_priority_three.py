"""
Priority three-question check:
  1c_000, 1c_003 — the only two officially 1C-tagged sample questions,
  both phrased as "the precise/true/actually" year — strongly suggesting
  a conflicting-source design (a popular/ballad account vs. an official
  codex/record giving a different date). These are the most important
  test cases in the entire sample set for this sub-track specifically.
  Note: 1c_000 is kept here for evidence-gathering (see
  docs/limitations.md 1c/1d for the measured variability finding) but is
  deliberately NOT used in the live demo script given that finding.
  1b_003 — a continuity/consistency check: Cerys Sablewood also surfaced
  in earlier ad-hoc testing ("wielded since 356 AS"), so this checks
  whether the system finds the same fact consistently across a
  differently-phrased question about the same entity. This is the
  question actually used for the live demo instead.

What this specifically checks that prior testing hasn't yet verified:
whether judge_sufficiency's "reasoning" field, when sources conflict,
explicitly names both conflicting values ("Source A says X, Source B
says Y") or silently picks one.
"""

import json
from pathlib import Path

from orchestrator import run_iterative_search

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = _PROJECT_ROOT / "output" / "priority_three_results.json"

PRIORITY_QUESTIONS = [
    {"qid": "1c_000", "question": "State the precise year in the Age of Shadows that marks the true founding of Gloamreach."},
    {"qid": "1c_003", "question": "In which year was the 'Gauntlet of Sorrowfell' actually forged?"},
    {"qid": "1b_003", "question": "To which shadowed redoubt must one journey to examine the relic long borne by Cerys Sablewood the Ashen since 356 AS?"},
]


def main():
    results = []
    for item in PRIORITY_QUESTIONS:
        print(f"\n{'='*70}\n[{item['qid']}] {item['question']}\n{'='*70}")
        trace = run_iterative_search(item["question"])
        result = trace.to_dict()
        result["qid"] = item["qid"]
        results.append(result)

        print(f"\nCompleted in {len(result['steps'])} iteration(s).")
        for step in result["steps"]:
            conflict_signal = any(
                kw in step["reasoning"].lower()
                for kw in ["conflict", "disagree", "contradict", "differ", "one source", "another source", "however,"]
            )
            flag = "  <-- possible conflict language" if conflict_signal else ""
            print(f"  iter {step['iteration']}: sufficient={step['sufficient']}{flag}")
        print(f"\nFINAL ANSWER:\n{result['final_answer']}\n")

    Path(OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved full results to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
