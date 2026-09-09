"""
Repeat-run check for 1c_000 (the Gloamreach founding-year question), to
measure how often the observed run-to-run variability recurs — see
docs/limitations.md 1c/1d. This is diagnostic evidence-gathering, not
part of the shipped pipeline: the finding it produced (1/4 runs let a
visible conflict get overridden by source-authority preference) is kept
as a disclosed, measured limitation. This question is deliberately NOT
used in the live demo (see docs/demo_script.md) given this finding.

This does NOT try to force deterministic behavior (e.g. pinning a
specific model instead of openrouter/free) — that would be a real
architecture change made under deadline pressure to chase a smoother
demo outcome, which is exactly the kind of late, high-risk change prior
review has consistently advised against. It only measures the
variability that already exists.
"""

import json
from pathlib import Path
from collections import Counter

from orchestrator import run_iterative_search

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = _PROJECT_ROOT / "output" / "1c_000_repeat_runs.json"

QUESTION = "State the precise year in the Age of Shadows that marks the true founding of Gloamreach."
NUM_RUNS = 4  # keep this small — each run costs real LLM calls against the free tier


def main():
    print(f"Running the same question {NUM_RUNS} times to measure variability:\n")
    print(f"  \"{QUESTION}\"\n")

    all_results = []
    iteration_counts = []

    for run_num in range(1, NUM_RUNS + 1):
        print(f"--- Run {run_num}/{NUM_RUNS} ---")
        trace = run_iterative_search(QUESTION)
        result = trace.to_dict()
        result["run_number"] = run_num
        all_results.append(result)

        num_iters = len(result["steps"])
        iteration_counts.append(num_iters)
        print(f"  iterations: {num_iters}")
        print(f"  final answer (first 200 chars): {result['final_answer'][:200]}...\n")

    Path(OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    counts = Counter(iteration_counts)
    print(f"Iteration counts across {NUM_RUNS} runs: {iteration_counts}")
    print(f"Distribution: {dict(counts)}")
    print("\nKnown finding as of last run (see docs/limitations.md 1c/1d):")
    print("  1/4 runs reached sufficient=true despite the LLM's own reasoning")
    print("  noting a visible conflict; the other 3/4 stopped via the")
    print("  independent near-duplicate check without ever reaching a")
    print("  confident verdict. Re-running may reproduce a different mix —")
    print("  compare against the saved 1c_000_repeat_runs.json history.")

    print(f"\nFull results saved to {OUTPUT_FILE}")
    print("Manually compare each run's final_answer for wording/framing differences")
    print("beyond iteration count alone.")


if __name__ == "__main__":
    main()
