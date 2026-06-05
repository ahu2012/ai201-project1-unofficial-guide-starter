"""Milestone 3 — Document ingestion + chunking.

Loads raw documents from the ``documents/`` folder, cleans them, and splits
them into fixed-size token chunks that match the spec in planning.md:

    Chunk size: 100 tokens
    Overlap:    10 tokens

Token counts are measured with the *same* tokenizer the embedding model
(all-MiniLM-L6-v2) uses, so "100 tokens" here means 100 tokens as the embedder
will see them — not 100 words or 100 characters.

Output is written to ``chunks.json``: a list of records, each carrying the
chunk text plus source attribution that the embedding/retrieval stage
(ChromaDB) can store as metadata.

Usage:
    python chunk_documents.py
    python chunk_documents.py --input documents --output chunks.json
    python chunk_documents.py --chunk-size 100 --overlap 10
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import unicodedata
from pathlib import Path

# --- Spec defaults (see planning.md → Chunking Strategy) ---------------------
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_CHUNK_SIZE = 100  # tokens
DEFAULT_OVERLAP = 10  # tokens
SUPPORTED_SUFFIXES = {".txt", ".md", ".markdown", ".pdf"}


# --- Stage 1: ingestion ------------------------------------------------------
def read_file(path: Path) -> str:
    """Read a single document to raw text. Supports .txt/.md and (optionally) .pdf."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        try:
            import pdfplumber  # optional dependency, see requirements.txt
        except ImportError:
            print(
                f"  ! skipping {path.name}: install pdfplumber to read PDFs "
                "(uncomment it in requirements.txt)",
                file=sys.stderr,
            )
            return ""
        with pdfplumber.open(path) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    return path.read_text(encoding="utf-8", errors="replace")


def load_documents(input_dir: Path) -> list[tuple[str, str]]:
    """Return [(source_name, raw_text), ...] for every supported file in input_dir."""
    if not input_dir.is_dir():
        raise NotADirectoryError(f"Input directory not found: {input_dir}")

    docs: list[tuple[str, str]] = []
    for path in sorted(input_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        raw = read_file(path)
        if raw.strip():
            docs.append((path.name, raw))
            print(f"  loaded {path.name} ({len(raw):,} chars)")
        else:
            print(f"  ! {path.name} is empty after reading — skipped")
    return docs


# --- Stage 2: cleaning -------------------------------------------------------
def clean_text(text: str) -> str:
    """Normalize scraped/copied text into clean prose before chunking.

    The sources are Reddit posts, blogs, and news pages copied or scraped to
    text, so they carry HTML fragments, entities, smart quotes, and ragged
    whitespace. We strip those so chunk boundaries fall on real content.
    """
    text = unicodedata.normalize("NFKC", text)
    text = html.unescape(text)  # &amp; -> &, &#39; -> ', etc.
    text = re.sub(r"<[^>]+>", " ", text)  # drop any leftover HTML tags
    # Collapse runs of blank lines to a single blank line (keep paragraph breaks).
    text = re.sub(r"\n\s*\n\s*", "\n\n", text)
    # Collapse spaces/tabs within a line.
    text = re.sub(r"[ \t]+", " ", text)
    # Trim trailing spaces on each line.
    text = re.sub(r" *\n", "\n", text)
    return text.strip()


# --- Stage 3: chunking -------------------------------------------------------
def chunk_text(
    text: str,
    tokenizer,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[str]:
    """Split text into fixed-size token windows with overlap.

    A window of ``chunk_size`` tokens slides forward by ``chunk_size - overlap``
    tokens each step, so adjacent chunks share ``overlap`` tokens of context.
    Tokens are decoded back to readable text using the embedding model's
    tokenizer, so the counts line up with what the embedder ingests.
    """
    if overlap >= chunk_size:
        raise ValueError(f"overlap ({overlap}) must be smaller than chunk_size ({chunk_size})")

    # Encode without special tokens — those belong to embedding, not chunking.
    token_ids = tokenizer.encode(text, add_special_tokens=False)
    if not token_ids:
        return []

    step = chunk_size - overlap
    chunks: list[str] = []
    for start in range(0, len(token_ids), step):
        window = token_ids[start : start + chunk_size]
        chunk = tokenizer.decode(window, skip_special_tokens=True).strip()
        if chunk:
            chunks.append(chunk)
        if start + chunk_size >= len(token_ids):
            break  # last window already reached the end
    return chunks


def load_tokenizer():
    """Load the all-MiniLM-L6-v2 tokenizer (tokenizer files only, no model weights)."""
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(EMBEDDING_MODEL)


# --- Driver ------------------------------------------------------------------
def build_chunks(
    input_dir: Path,
    chunk_size: int,
    overlap: int,
) -> list[dict]:
    print(f"Loading documents from {input_dir}/ ...")
    documents = load_documents(input_dir)
    if not documents:
        print(
            f"\nNo readable documents found in {input_dir}/. "
            "Drop your .txt/.md/.pdf sources there and rerun.",
            file=sys.stderr,
        )
        return []

    print(f"\nLoading tokenizer for {EMBEDDING_MODEL} ...")
    tokenizer = load_tokenizer()

    print(f"\nChunking (size={chunk_size} tokens, overlap={overlap} tokens) ...")
    records: list[dict] = []
    for source, raw in documents:
        cleaned = clean_text(raw)
        chunks = chunk_text(cleaned, tokenizer, chunk_size, overlap)
        for i, chunk in enumerate(chunks):
            records.append(
                {
                    "id": f"{source}::chunk_{i}",
                    "source": source,
                    "chunk_index": i,
                    "n_tokens": len(tokenizer.encode(chunk, add_special_tokens=False)),
                    "text": chunk,
                }
            )
        print(f"  {source}: {len(chunks)} chunks")
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=Path("documents"), help="folder of source documents")
    parser.add_argument("--output", type=Path, default=Path("chunks.json"), help="where to write chunks JSON")
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE, help="chunk size in tokens")
    parser.add_argument("--overlap", type=int, default=DEFAULT_OVERLAP, help="overlap in tokens")
    args = parser.parse_args()

    records = build_chunks(args.input, args.chunk_size, args.overlap)
    if not records:
        return 1

    args.output.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {len(records)} chunks from {len({r['source'] for r in records})} documents to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
