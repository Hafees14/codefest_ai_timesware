"""
Batch test runner — runs every question in sample_questions.json through the
orchestrator and saves full traces + answers to output/ for review.
"""

import os
import json
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from orchestrator import run_iterative_search

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_QUESTIONS_FILE = os.environ.get(
    "SAMPLE_QUESTIONS_FILE",
    str(_PROJECT_ROOT / "corpus" / "Ashen_Era_Archive" / "Ashen_Era_Archive" / "sample_questions.json"),
)
OUTPUT_FILE = os.environ.get(
    "SAMPLE_RESULTS_OUTPUT",
    str(_PROJECT_ROOT / "output" / "sample_question_results.json"),
)


TARGET_TRACK_KEYWORD = "1C"  # only run questions belonging to your chosen sub-track


def load_questions(path: str):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Filter to only this track's questions — sample_questions.json covers all
    # three sub-tracks (1A/1B/1C), and running 1A/1B questions through a 1C
    # pipeline tests capabilities (like image embedding) this system doesn't have.
    filtered = [q for q in data if TARGET_TRACK_KEYWORD in q.get("track", "")]
    print(f"Filtered to {len(filtered)}/{len(data)} questions tagged for track '{TARGET_TRACK_KEYWORD}'.")
    return filtered


def main():
    questions = load_questions(SAMPLE_QUESTIONS_FILE)
    print(f"Loaded {len(questions)} sample questions.")

    results = []
    for i, q in enumerate(questions, 1):
        # handle both plain-string and dict-shaped question entries
        question_text = q if isinstance(q, str) else q.get("question", str(q))
        print(f"\n[{i}/{len(questions)}] {question_text}")

        try:
            trace = run_iterative_search(question_text)
            results.append(trace.to_dict())
            print(f"  -> answered in {len(trace.steps)} search iteration(s)")
        except Exception as e:
            print(f"  [error] {e}")
            results.append({"question": question_text, "error": str(e)})

    Path(OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nDone. Results saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
