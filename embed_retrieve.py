"""Milestone 4 — Embedding + retrieval.

Implements the middle of the pipeline from planning.md:

    Chunking (chunks.json) -> Embedding (all-MiniLM-L6-v2) + Vector Store (ChromaDB)
                           -> Retrieval (ChromaDB, top-k)

Two responsibilities:
  * ``build_index`` — load the chunks produced by ``chunk_documents.py``, embed
    them with all-MiniLM-L6-v2, and store the vectors + source metadata in a
    persistent ChromaDB collection.
  * ``retrieve`` — embed a query with the *same* model and return the top-k most
    similar chunks, each with its source attribution. This is the seam the
    Milestone 5 (Groq) generation step will call.

Design notes (per planning.md → Retrieval Approach):
  * Embedding model: all-MiniLM-L6-v2 (sentence-transformers), top-k = 5.
  * We embed documents *and* queries ourselves and hand the vectors to Chroma,
    rather than relying on Chroma's bundled embedder, so the two always live in
    the same vector space.
  * Embeddings are L2-normalized and the collection uses cosine distance.

Usage:
    python embed_retrieve.py build
    python embed_retrieve.py query "Where should I get Indian food?"
    python embed_retrieve.py query "best pizza" --top-k 3
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# --- Spec config (planning.md → Retrieval Approach) --------------------------
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_TOP_K = 5
CHUNKS_PATH = Path("chunks.json")
PERSIST_DIR = Path("chroma_db")
COLLECTION_NAME = "newhaven_dining"

# Module-level singletons so the model/DB load once per process.
_embedder = None
_client = None


# --- Embedding ---------------------------------------------------------------
def get_embedder():
    """Load (once) the all-MiniLM-L6-v2 sentence-transformers model."""
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer

        _embedder = SentenceTransformer(EMBEDDING_MODEL)
    return _embedder


def embed_texts(texts: list[str], *, show_progress: bool = False) -> list[list[float]]:
    """Embed texts into L2-normalized vectors (suitable for cosine distance)."""
    model = get_embedder()
    vectors = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=show_progress,
        batch_size=64,
    )
    return vectors.tolist()


# --- Vector store ------------------------------------------------------------
def get_client():
    """Load (once) a persistent ChromaDB client backed by PERSIST_DIR."""
    global _client
    if _client is None:
        import chromadb

        _client = chromadb.PersistentClient(path=str(PERSIST_DIR))
    return _client


def get_collection(*, reset: bool = False):
    """Return the dining collection, optionally recreating it from scratch.

    Cosine space matches our normalized embeddings; ``reset`` is used by
    ``build_index`` so re-running produces a clean index instead of duplicates.
    """
    client = get_client()
    if reset:
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass  # collection didn't exist yet
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def load_chunks(path: Path = CHUNKS_PATH) -> list[dict]:
    """Load the chunk records written by chunk_documents.py."""
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found — run chunk_documents.py first to produce it."
        )
    return json.loads(path.read_text(encoding="utf-8"))


# --- Build (embedding step) --------------------------------------------------
def build_index(chunks_path: Path = CHUNKS_PATH) -> int:
    """Embed every chunk and store it (with source metadata) in ChromaDB.

    Returns the number of chunks indexed.
    """
    chunks = load_chunks(chunks_path)
    if not chunks:
        print("No chunks to index.", file=sys.stderr)
        return 0

    print(f"Embedding {len(chunks)} chunks with {EMBEDDING_MODEL} ...")
    texts = [c["text"] for c in chunks]
    embeddings = embed_texts(texts, show_progress=True)

    print(f"Writing to ChromaDB collection '{COLLECTION_NAME}' at {PERSIST_DIR}/ ...")
    collection = get_collection(reset=True)
    collection.add(
        ids=[c["id"] for c in chunks],
        embeddings=embeddings,
        documents=texts,
        metadatas=[
            {
                "source": c["source"],
                "chunk_index": c["chunk_index"],
                "n_tokens": c["n_tokens"],
            }
            for c in chunks
        ],
    )
    print(f"Indexed {collection.count()} chunks from "
          f"{len({c['source'] for c in chunks})} sources.")
    return collection.count()


# --- Retrieval ---------------------------------------------------------------
def retrieve(query: str, top_k: int = DEFAULT_TOP_K) -> list[dict]:
    """Return the top-k chunks most relevant to ``query``.

    Each result: {rank, source, chunk_index, distance, similarity, text}.
    ``similarity`` = 1 - cosine distance (1.0 = identical, higher is better).
    """
    collection = get_collection()
    if collection.count() == 0:
        raise RuntimeError("Index is empty — run build_index() first.")

    query_embedding = embed_texts([query])
    res = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    results: list[dict] = []
    for rank, (doc, meta, dist) in enumerate(
        zip(res["documents"][0], res["metadatas"][0], res["distances"][0]), start=1
    ):
        results.append(
            {
                "rank": rank,
                "source": meta["source"],
                "chunk_index": meta["chunk_index"],
                "distance": dist,
                "similarity": 1 - dist,
                "text": doc,
            }
        )
    return results


# --- CLI ---------------------------------------------------------------------
def _cmd_build(args) -> int:
    return 0 if build_index(args.chunks) else 1


def _cmd_query(args) -> int:
    results = retrieve(args.query, top_k=args.top_k)
    print(f"\nTop {len(results)} chunks for: {args.query!r}\n")
    for r in results:
        print(f"[{r['rank']}] {r['source']} (chunk {r['chunk_index']})  "
              f"similarity={r['similarity']:.3f}")
        print(f"    {r['text'][:300]}{'...' if len(r['text']) > 300 else ''}\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_build = sub.add_parser("build", help="embed chunks.json and store in ChromaDB")
    p_build.add_argument("--chunks", type=Path, default=CHUNKS_PATH)
    p_build.set_defaults(func=_cmd_build)

    p_query = sub.add_parser("query", help="retrieve top-k chunks for a query")
    p_query.add_argument("query", type=str)
    p_query.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    p_query.set_defaults(func=_cmd_query)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
