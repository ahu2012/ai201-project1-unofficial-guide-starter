"""Milestone 5 — Grounded generation (Groq) + query interface.

Final stage of the pipeline from planning.md:

    Retrieval (ChromaDB, top-k) -> Generation (Groq)

``answer()`` retrieves the top-k chunks for a question (via embed_retrieve),
formats them into a grounded prompt, and asks a Groq-hosted Llama model to
answer using *only* that retrieved context — then surfaces which sources it
drew from.

Grounding mechanism (see README → Grounded Generation):
  * System prompt instructs the model to answer only from the numbered context
    and to say so when the answer isn't there — no outside knowledge.
  * Each chunk is injected with a ``[n] (source: filename)`` label so the model
    can cite, and so attribution is auditable.
  * Low-similarity chunks are filtered out before prompting; if nothing clears
    the bar, we don't even call the LLM — we return a grounded "not found".

Usage:
    python generate.py ask "Where should I get Indian food?"
    python generate.py ask "best pizza" --top-k 5
    python generate.py chat            # interactive loop
"""

from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv

from embed_retrieve import DEFAULT_TOP_K, retrieve

# --- Config (planning.md → Architecture: Generation = Groq) ------------------
GROQ_MODEL = "llama-3.3-70b-versatile"
# Drop chunks below this cosine similarity before prompting — keeps clearly
# off-topic retrievals out of the context window.
MIN_SIMILARITY = 0.15

SYSTEM_PROMPT = (
    "You are a local guide to off-campus dining near Yale in New Haven. "
    "Answer the user's question using ONLY the numbered context passages "
    "provided below, which are excerpts from Reddit threads, blogs, and local "
    "guides.\n"
    "Rules:\n"
    "1. Use only facts found in the context. Do not add restaurants, dishes, or "
    "details from your own knowledge.\n"
    "2. If the context does not contain the answer, say so plainly (e.g. "
    "\"The sources I have don't cover that.\") instead of guessing.\n"
    "3. Cite the passages you used by their number, like [1] or [2][3].\n"
    "4. The context is scraped text and may contain typos or odd spacing; "
    "interpret it sensibly but never invent missing information."
)

_client = None


def get_client():
    """Load (once) a Groq client, reading GROQ_API_KEY from .env / environment."""
    global _client
    if _client is None:
        from groq import Groq

        load_dotenv()
        key = os.getenv("GROQ_API_KEY")
        if not key or key == "your_key_here":
            raise RuntimeError(
                "GROQ_API_KEY is not set. Copy .env.example to .env and add your "
                "key from https://console.groq.com"
            )
        _client = Groq(api_key=key)
    return _client


def format_context(results: list[dict]) -> str:
    """Render retrieved chunks as a numbered, source-labeled context block."""
    blocks = []
    for r in results:
        blocks.append(
            f"[{r['rank']}] (source: {r['source']}, similarity {r['similarity']:.2f})\n"
            f"{r['text']}"
        )
    return "\n\n".join(blocks)


def build_messages(query: str, results: list[dict]) -> list[dict]:
    """Assemble the chat messages for the grounded generation call."""
    user_content = (
        f"Context passages:\n\n{format_context(results)}\n\n"
        f"Question: {query}\n\n"
        "Answer using only the context above, and cite the passage numbers you used."
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def answer(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    *,
    model: str = GROQ_MODEL,
    min_similarity: float = MIN_SIMILARITY,
) -> dict:
    """Retrieve, ground, and generate. Returns {answer, sources, used_chunks}.

    If no retrieved chunk clears ``min_similarity``, returns a grounded refusal
    without calling the LLM.
    """
    retrieved = retrieve(query, top_k=top_k)
    used = [r for r in retrieved if r["similarity"] >= min_similarity]

    if not used:
        return {
            "answer": "The sources I have don't cover that.",
            "sources": [],
            "used_chunks": [],
        }

    completion = get_client().chat.completions.create(
        model=model,
        messages=build_messages(query, used),
        temperature=0.2,  # low — we want faithful summarization, not creativity
    )
    text = completion.choices[0].message.content

    # De-duplicate sources, preserving retrieval order.
    sources: list[str] = []
    for r in used:
        if r["source"] not in sources:
            sources.append(r["source"])

    return {"answer": text, "sources": sources, "used_chunks": used}


# --- CLI ---------------------------------------------------------------------
def _print_result(result: dict) -> None:
    print(f"\n{result['answer']}\n")
    if result["sources"]:
        print("Sources:")
        for s in result["sources"]:
            print(f"  - {s}")
    print()


def _cmd_ask(args) -> int:
    _print_result(answer(args.query, top_k=args.top_k))
    return 0


def _cmd_chat(args) -> int:
    print("New Haven dining guide — ask a question (Ctrl-C or 'quit' to exit).\n")
    try:
        while True:
            query = input("> ").strip()
            if query.lower() in {"quit", "exit"}:
                break
            if query:
                _print_result(answer(query, top_k=args.top_k))
    except (KeyboardInterrupt, EOFError):
        print()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_ask = sub.add_parser("ask", help="answer a single question")
    p_ask.add_argument("query", type=str)
    p_ask.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    p_ask.set_defaults(func=_cmd_ask)

    p_chat = sub.add_parser("chat", help="interactive question loop")
    p_chat.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    p_chat.set_defaults(func=_cmd_chat)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
