"""
Iterative Agentic Search Orchestrator — Sub-track 1C
SLIIT Codefest 2026 AI Competition

Core idea:
  query -> retrieve -> judge sufficiency -> (insufficient) refine query -> retrieve again -> ...
  -> synthesize final answer from all accumulated evidence

Embedding/retrieval calls (via embed.py) and the LLM client (OpenRouter) are live.
"""

import os
import re
import time
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # reads .env in the current working directory (or nearest parent)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MAX_ITERATIONS = 5          # hard cap so it never loops forever
TOP_K = 5                   # chunks retrieved per search step

# openrouter/free is OpenRouter's built-in router — it automatically picks a
# live free model for each request, so this never goes stale the way a
# hardcoded model slug does (free model availability rotates frequently).
# If you want more control/consistency later, you can pin a specific model
# from https://openrouter.ai/models?max_price=0 instead.
LLM_MODEL_FALLBACKS = [
    "openrouter/free",
]

_client = None


def get_openrouter_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY environment variable not set. "
                "Run: $env:OPENROUTER_API_KEY='your-key-here' (PowerShell) before running this script."
            )
        _client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    return _client


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
@dataclass
class SearchStep:
    iteration: int
    query: str
    retrieved_chunks: List[Dict[str, Any]]
    reasoning: str            # why this query, what the model learned
    sufficient: bool


@dataclass
class SearchTrace:
    original_question: str
    steps: List[SearchStep] = field(default_factory=list)
    final_answer: str = ""
    plan: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return {
            "question": self.original_question,
            "plan": self.plan,
            "steps": [
                {
                    "iteration": s.iteration,
                    "query": s.query,
                    "reasoning": s.reasoning,
                    "sufficient": s.sufficient,
                    "num_chunks": len(s.retrieved_chunks),
                }
                for s in self.steps
            ],
            "final_answer": self.final_answer,
        }


# ---------------------------------------------------------------------------
# Placeholder integrations — replace with real implementations
# ---------------------------------------------------------------------------
def embed_query(text: str) -> List[float]:
    """Not used directly — kept for interface compatibility.
    See vector_search(), which calls embed.search() end-to-end
    (local sentence-transformers embedding + Chroma retrieval)."""
    raise NotImplementedError("Use vector_search() directly — it handles embedding internally via embed.py")


def vector_search(query_text: str, top_k: int = TOP_K) -> List[Dict[str, Any]]:
    """Query the Chroma vector store (see embed.py). Returns chunk dicts:
    [{"text": ..., "source": ..., "doc_id": ..., "doc_type": ..., "is_ocr": ...,
      "score": ..., "fusion_score": ...}, ...]
    "score" is on a different scale depending on whether a chunk came from
    dense search, BM25, or both (and may be None for a BM25-only match) —
    "fusion_score" is the comparable, rank-consistent value if you need to
    reason about relative relevance across the returned set.
    """
    from embed import search
    return search(query_text, top_k=top_k)


def call_llm(prompt: str, retries: int = 3) -> str:
    """Call OpenRouter, trying each model in LLM_MODEL_FALLBACKS in order.
    Retries with backoff on rate limits; moves to the next model immediately
    on a 404/unavailable error (no point retrying a dead model slug)."""
    client = get_openrouter_client()
    last_error = None

    for model in LLM_MODEL_FALLBACKS:
        delay = 2
        for attempt in range(retries):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.choices[0].message.content
            except Exception as e:
                err_str = str(e)
                if "404" in err_str or "not a valid model" in err_str.lower():
                    print(f"  [model unavailable] '{model}' — trying next fallback...")
                    last_error = e
                    break  # stop retrying this model, move to next in the list
                is_rate_limit = "429" in err_str or "rate" in err_str.lower()
                if is_rate_limit and attempt < retries - 1:
                    print(f"  [retry] '{model}' rate-limited; waiting {delay}s...")
                    time.sleep(delay)
                    delay *= 2
                    continue
                last_error = e
                break  # exhausted retries or non-recoverable error — try next model

    raise RuntimeError(f"All fallback models failed. Last error: {last_error}")


# ---------------------------------------------------------------------------
# Core orchestration steps
# ---------------------------------------------------------------------------
def sanitize_json_escapes(text: str) -> str:
    """LLMs sometimes echo Windows-style paths (e.g. 'ephemera\\contract...')
    inside JSON string values. A lone backslash before a non-JSON-escape
    character (like \\c, \\g, \\t-as-in-'the') is invalid JSON and breaks
    json.loads. Double any backslash that isn't already part of a valid
    JSON escape sequence (\\\", \\\\, \\/, \\b, \\f, \\n, \\r, \\t, \\uXXXX)."""
    return re.sub(r'\\(?!["\\/bfnrt]|u[0-9a-fA-F]{4})', r'\\\\', text)


def extract_json(raw: str) -> Dict[str, Any]:
    """Strip markdown code fences some models wrap JSON in, then parse.
    Handles ```json ... ``` and bare ``` ... ``` wrappers, and falls back
    to finding the first {...} block if the model added stray preamble text."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]  # drop opening fence (``` or ```json)
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]  # drop closing fence
        text = "\n".join(lines).strip()
    text = sanitize_json_escapes(text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # last resort: grab the substring between the first { and last }
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1:
            return json.loads(text[start:end + 1])
        raise


def plan_initial_query(question: str) -> Dict[str, Any]:
    """
    Explicit query-planning step, run once before the first retrieval.

    This is a deliberately minimal answer to "how do you decide where to
    look": rather than sending the raw question verbatim as the first
    search (the previous behavior), an LLM call first extracts the key
    named entities/concepts the question depends on and proposes a
    focused initial search query built from them. This is a real,
    separately-inspectable step distinct from judge_sufficiency — but it
    is still LLM-driven, not a symbolic entity-extraction pipeline, so it
    should not be oversold as full query planning (see limitations.md).

    Returns {"key_entities": [...], "initial_query": str}. Falls back to
    the raw question if planning fails for any reason (network error,
    unparseable response) — this step is an enhancement, not a
    single point of failure for the pipeline.
    """
    prompt = f"""A user wants to search a large document archive to answer this question:

Question: {question}

Before searching, identify the key named entities, places, events, or concepts this
question depends on, and propose a focused initial search query.

Respond ONLY with JSON:
{{
  "key_entities": ["entity1", "entity2"],
  "initial_query": "a focused search query covering the entities above"
}}"""
    try:
        raw = call_llm(prompt)
        result = extract_json(raw)
        if "initial_query" in result and result["initial_query"]:
            return result
    except Exception as e:
        print(f"  [warn] Query planning failed ({e}); falling back to raw question as initial query.")
    return {"key_entities": [], "initial_query": question}


def judge_sufficiency(question: str, accumulated_evidence: str, max_attempts: int = 3) -> Dict[str, Any]:
    """
    Ask the LLM: given what we've gathered so far, can we answer the question?
    Returns dict: {"sufficient": bool, "reasoning": str, "next_query": str or None}
    Must return STRICT JSON — enforce this in the prompt.

    Retries the call (not just the parse) if the response doesn't look like an
    attempt at JSON at all — this happens occasionally because openrouter/free
    can route to a different, less instruction-following model each call
    (observed: a safety classifier verdict like 'User Safety: safe' leaking
    through instead of an actual answer). A genuine JSON syntax error is
    still handled by extract_json's sanitization/fallback; this catches the
    case where the response isn't JSON-shaped at all.
    """
    prompt = f"""You are evaluating whether enough evidence has been gathered to answer a question.

Question: {question}

Evidence gathered so far:
{accumulated_evidence}

Respond ONLY with JSON (no markdown, no preamble):
{{
  "sufficient": true or false,
  "reasoning": "brief explanation of what is known and what, if anything, is missing",
  "next_query": "a specific follow-up search query targeting the gap, or null if sufficient"
}}"""

    last_error = None
    for attempt in range(max_attempts):
        raw = call_llm(prompt)
        if "{" not in raw:
            print(f"  [warn] Response doesn't look like JSON, retrying ({attempt + 1}/{max_attempts}): {raw!r}")
            last_error = ValueError(f"No JSON-like content in response: {raw!r}")
            continue
        try:
            return extract_json(raw)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"  [debug] Raw LLM response that failed to parse: {raw!r}")
            last_error = e

    raise last_error


def synthesize_answer(question: str, accumulated_evidence: str) -> str:
    """Final answer generation from all accumulated evidence."""
    prompt = f"""Answer the question using ONLY the evidence below. Cite which source(s) support each claim.
If sources conflict, note the conflict explicitly rather than picking one silently.

Question: {question}

Evidence:
{accumulated_evidence}

Answer:"""
    return call_llm(prompt)


def format_chunks(chunks: List[Dict[str, Any]]) -> str:
    return "\n\n".join(
        f"[Source: {c.get('source', 'unknown')} | doc_id: {c.get('doc_id', '?')}]\n{c['text']}"
        for c in chunks
    )


# ---------------------------------------------------------------------------
# Independent stopping signal (not just the LLM's self-report)
# ---------------------------------------------------------------------------
def chunks_are_near_duplicate(chunks_a: List[Dict[str, Any]], chunks_b: List[Dict[str, Any]],
                                overlap_threshold: float = 0.6) -> bool:
    """Code-level (not LLM-judged) check: if the new query's top-k retrieval
    overlaps heavily with a previous iteration's retrieval (by chunk id/text),
    the reformulated query isn't actually surfacing new evidence — the LLM's
    "insufficient, search again" self-report can be overridden by this
    independent signal rather than trusted blindly, preventing the system
    from silently looping on semantically-similar rephrasings of the same
    query. This directly answers "what decides you need another search"
    with something other than a single LLM prompt."""
    if not chunks_a or not chunks_b:
        return False
    ids_a = {c.get("doc_id", c.get("text", ""))[:120] for c in chunks_a}
    ids_b = {c.get("doc_id", c.get("text", ""))[:120] for c in chunks_b}
    overlap = len(ids_a & ids_b) / max(1, min(len(ids_a), len(ids_b)))
    return overlap >= overlap_threshold


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
def run_iterative_search(question: str) -> SearchTrace:
    trace = SearchTrace(original_question=question)
    accumulated_evidence = ""

    plan = plan_initial_query(question)
    trace.plan = plan
    current_query = plan["initial_query"]
    if plan.get("key_entities"):
        print(f"  [plan] Key entities identified: {plan['key_entities']}")
        print(f"  [plan] Initial query: '{current_query}'")

    previous_chunk_sets: List[List[Dict[str, Any]]] = []

    for i in range(1, MAX_ITERATIONS + 1):
        chunks = vector_search(current_query, top_k=TOP_K)
        accumulated_evidence += f"\n\n--- Search {i}: '{current_query}' ---\n"
        accumulated_evidence += format_chunks(chunks)

        try:
            judgment = judge_sufficiency(question, accumulated_evidence)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"  [warn] Could not parse sufficiency judgment ({e}); treating as insufficient, stopping search.")
            judgment = {"sufficient": False, "reasoning": f"LLM response unparseable: {e}", "next_query": None}

        # Independent check: has this exact evidence set already been seen?
        # If so, override the LLM's judgment and stop — a repeated retrieval
        # means the reformulated query isn't actually finding anything new,
        # regardless of what the LLM's self-report claims.
        is_repeat_retrieval = any(chunks_are_near_duplicate(chunks, prev) for prev in previous_chunk_sets)
        if is_repeat_retrieval and not judgment["sufficient"]:
            print(f"  [independent check] Iteration {i} retrieved near-duplicate evidence to a "
                  f"prior search; overriding LLM's 'insufficient' self-report and stopping "
                  f"(this query angle is exhausted, not genuinely unresolved).")
            judgment["reasoning"] += " [Overridden: retrieval repeated a prior search's evidence set — stopping to avoid an unproductive loop.]"
        previous_chunk_sets.append(chunks)

        step = SearchStep(
            iteration=i,
            query=current_query,
            retrieved_chunks=chunks,
            reasoning=judgment["reasoning"],
            sufficient=judgment["sufficient"],
        )
        trace.steps.append(step)

        if judgment["sufficient"] or not judgment.get("next_query") or is_repeat_retrieval:
            break

        current_query = judgment["next_query"]

    trace.final_answer = synthesize_answer(question, accumulated_evidence)
    return trace


# ---------------------------------------------------------------------------
# Entry point / example usage
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    # Usage: python orchestrator.py "your question here"
    # Falls back to a default test question if none is given.
    if len(sys.argv) > 1:
        q = " ".join(sys.argv[1:])
    else:
        q = "Which other equipment or factions are affected if the artifact known as X is destroyed?"
    trace = run_iterative_search(q)
    print(json.dumps(trace.to_dict(), indent=2))
    print("\n=== FINAL ANSWER ===")
    print(trace.final_answer)
