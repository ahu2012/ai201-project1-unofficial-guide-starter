"""Milestone 5 — Query interface.

A small Gradio app over the full RAG pipeline: it takes a question, runs
retrieval + grounded generation via generate.answer(), and shows the answer
alongside the sources it was drawn from.

Run:
    python app.py
then open the local URL it prints (default http://127.0.0.1:7860).
"""

from __future__ import annotations

import gradio as gr

from embed_retrieve import DEFAULT_TOP_K
from generate import answer

EXAMPLES = [
    "Where should I get Indian food for an authentic experience?",
    "Where is the best pizza in New Haven?",
    "What kind of seafood is New Haven known for?",
    "What's a restaurant with a great cocktail menu?",
]


def handle_query(question: str, top_k: int):
    """Run one question through the pipeline; return (answer, sources markdown)."""
    question = (question or "").strip()
    if not question:
        return "Ask a question about off-campus dining near Yale.", ""

    result = answer(question, top_k=int(top_k))
    if result["sources"]:
        sources = "\n".join(f"- {s}" for s in result["sources"])
    else:
        sources = "_No sufficiently relevant sources were found._"
    return result["answer"], sources


with gr.Blocks(title="The Unofficial Guide — New Haven Dining") as demo:
    gr.Markdown(
        "# 🍕 The Unofficial Guide — New Haven Dining\n"
        "Ask about off-campus restaurants near Yale. Answers are grounded only "
        "in scraped Reddit threads, blogs, and local guides — with their sources shown."
    )
    with gr.Row():
        inp = gr.Textbox(label="Your question", scale=4, placeholder="e.g. Where's the best pizza?")
        top_k = gr.Slider(1, 10, value=DEFAULT_TOP_K, step=1, label="Chunks retrieved (top-k)", scale=1)
    btn = gr.Button("Ask", variant="primary")
    answer_box = gr.Textbox(label="Answer", lines=8)
    sources_box = gr.Markdown(label="Sources")

    gr.Examples(examples=EXAMPLES, inputs=inp)

    btn.click(handle_query, inputs=[inp, top_k], outputs=[answer_box, sources_box])
    inp.submit(handle_query, inputs=[inp, top_k], outputs=[answer_box, sources_box])


if __name__ == "__main__":
    demo.launch()
