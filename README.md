# The Unofficial Guide — Project 1

> **How to use this template:**
> Complete each section *after* you've built and tested the corresponding part of your system.
> Do not write placeholder text — if a section isn't done yet, leave it blank and come back.
> Every section below is required for submission. One-liners will not receive full credit.

---

## Domain

<!-- What topic or category of knowledge does your system cover?
     Why is this knowledge valuable, and why is it hard to find through official channels?
     Example: "Student reviews of CS professors at [university] — useful because official
     course descriptions don't reflect teaching style, exam difficulty, or workload." -->

Off-campus dining near Yale's campus. The information is poorly reviewed and disaggregated. Student's have not traditionally gone there due to higher cost and good on-campus options.

---

## Document Sources

<!-- List every source you collected documents from.
     Be specific: include URLs, subreddit names, forum thread titles, or file names.
     Aim for variety — sources that together cover different subtopics or perspectives. -->

| # | Source | Description | URL or location |
|---|--------|-------------|-----------------|
| 1 | Reddit post| High quality restaurants with focus on cocktails| https://www.reddit.com/r/newhaven/comments/1n9mjbn/back_in_new_haven_recommend_me_a_new_high_quality/|
| 2 | Blog | Best restaurants | https://www.theadventuristmagazine.com/city-guides/northeast/connecticut/new-haven-best-restaurants|
| 3 | Blog | Best restaurants curated by Yalie| https://admissions.yale.edu/posts/2020-10-20-a-new-haven-eating-guide-certified-by-an-aspiring-foodie|
| 4 | Newspaper | Top restaurants list| https://www.infonewhaven.com/who-knew-blog/new-haven-restaurants-lead-connecticut-magazines-top-new-restaurants-for-2026-list/|
| 5 | Reddit post  | Restaurant list | https://www.reddit.com/r/newhaven/comments/1q12va0/ive_compiled_a_list_of_food_places_in_new_haven/|
| 6 | Reddit post | local restaurants | https://www.reddit.com/r/newhaven/comments/16h68pe/new_haven_locals_where_should_i_eat_tonight/|
| 7 | Blog | hungry onion restaurants | manual |
| 8 | BLog | forno bravo | manual |
| 9 | Blog | alumni | manual |
| 10 | School site | yale school site | manual |
---

## Chunking Strategy

<!-- Describe your chunking approach with enough specificity that someone else could reproduce it.
     Include:
     - Chunk size (characters or tokens) and why that size fits your documents
     - Overlap size and why (or why not) you used overlap
     - Any preprocessing you did before chunking (e.g., stripping HTML, removing headers)
     - What your final chunk count was across all documents -->

**Chunk size:**
100 tokens 

**Overlap:**
10 tokens

**Reasoning:**
Most of the sources are sound-bite sized pieces/reddit posts that are shorter in length. Keeping a shorter chunk size with small overlap will allow us to maintain the meaning while maintaing simplicity in the chunking mechanism.

**Final chunk count:**
202 chunks across all 10 documents.

**Sample**

Chunk 1 — 01_reddit_back_in_new_haven_high_quality.txt (chunk 0, 100 tokens)

back in new haven! recommend me a new high quality restaurant i haven ' t been back to ct in over a year and i haven ' t been out to eat in new haven other than pizza in a few years. i remember loving places like zinc and pacifico and miya ' s sushi ( rip ). what are some newer spots that are making great dishes? bonus points for a good cocktail menu upvote 34 downvote 38 go to comments share u / washingtonpost avatar washington

Chunk 2 — 02_theadventuristmagazine_new_haven_best_restaurants.txt (chunk 0, 100 tokens)

0 fair haven oyster co. city guides | new england new haven ' s best restaurants : old favorites, icons, and a few cheap obsessions by maria rodriguez | feb. 1, 2026 author bio : with a day job that requires constant travel, maria rodriguez is likely a regular at your favorite restaurant. she ' s reviewed restaurants since 2007 in magazines from barcelona to bakersfield...

Chunk 3 — 03_admissions_2020_10_20_a_new_haven_eating_guide_certified_by_.txt (chunk 0, 100 tokens)

skip to main content show all breadcrumbshome a new haven eating guide ( certified by an aspiring foodie ) gianna tuesday, october 20, 2020 coming from new york... my move to new haven worried me ~ food wise ~. my mom is probably the best cook i know, but when i wasn ' t eating her soul - filling dominican meals...

Chunk 4 — 04_infonewhaven_top_new_restaurants_2026.txt (chunk 0, 100 tokens)

connecticut magazine ' s top new restaurants for 2026 has been released. the list features 27 restaurants statewide... six are in new haven... 116 crown by hachiroku 116 crown street chef yuta kamori ' s precise japanese cuisine and ambitious cocktail menu earned recognition. casanova 278 park street chef joseph iannaccone brings refined

Chunk 5 — 05_reddit_compiled_list_fod_places.txt (chunk 0, 100 tokens)

i ' ve compiled a list of food places in new haven for my family ' s trip, does this look good enough? i looked through the posts here, and made this list. we ' ll be visiting in late february... below is the list : gui

---

## Embedding Model

<!-- Name the embedding model you used and explain your choice.
     Then answer: if you were deploying this system for real users and cost wasn't a constraint,
     what tradeoffs would you weigh in choosing a different model?
     Consider: context length limits, multilingual support, accuracy on domain-specific text,
     latency, and local vs. API-hosted. -->

**Embedding model:**
all-MiniLM-L6-v2

**Top-k:**
5

**Retrieval Examples**
Query 1: "Where should I get Indian food for an authentic experience?" - relevant because it specifically references Indian food
Top match: 05_reddit_compiled_list_fod_places.txt (chunk 36) — similarity 0.652

...the new haven area has some really great indian places too. i would highly recommend trying at least one of them. some of my favorites are tandoor in new haven and indian hot breads in hamden. happy eating! upvote

Query 2: "Where is the best pizza in New Haven?" - not as great because naya is not pizza
Top match: 07_hungry_onion (chunk 10) — similarity 0.789

##a is good, but not as great as the sit - down location of naya... atticus market has really unique new haven ( ish ) style pizzas on thursday, friday and saturday nights... some examples : seacoast mushroom and potato pie, white bean and ramps,

Query 3: "What kind of seafood is New Haven known for?" -- relevant because it references seafood
Top match: 05_reddit_compiled_list_fod_places.txt (chunk 35) — similarity 0.747

...there are a few good seafood places but those are a bit out of the new haven area... shell and bones in new haven and union league also have great seafood options.

**Production tradeoff reflection:**
For real users, I would start proto-typing with a cheap model like the one above. As the prototyping concluded, I would probably look at more domain-specific embedders to the culinary scene and allow for multilingual support at the expense of cost.

---

## Grounded Generation

<!-- Explain how your system enforces grounding — how does it prevent the LLM from answering
     beyond the retrieved documents?
     Describe both your system prompt (what instruction you gave the model) and any structural
     choices (e.g., how you formatted the context, whether you filtered low-relevance chunks).
     Do not just say "I told it to use the documents" — show the actual instruction or explain
     the mechanism. -->

**System prompt grounding instruction:**
The system prompt (in `generate.py`) tells the model it is a New Haven dining guide and must answer using *only* the numbered context passages it is given. The explicit rules are: (1) use only facts found in the context — do not add restaurants, dishes, or details from outside knowledge; (2) if the context doesn't contain the answer, say so plainly (e.g. "The sources I have don't cover that.") instead of guessing; (3) cite the passages used by number, like [1] or [2][3]; (4) the context is scraped text that may contain typos or odd spacing, so interpret it sensibly but never invent missing information. Generation runs at `temperature=0.2` to favor faithful summarization over creativity.

Beyond the prompt, grounding is enforced structurally:
- **Numbered, source-labeled context.** Each retrieved chunk is injected as `[n] (source: filename, similarity X.XX)` so the model can cite specific passages and attribution is auditable.
- **Low-relevance filtering.** Chunks below 0.15 cosine similarity are dropped before the prompt is built. If *no* chunk clears the bar, the system returns a grounded "don't cover that" answer **without calling the LLM at all** — so an empty retrieval can never produce a hallucinated answer.

**How source attribution is surfaced in the response:**
Two ways. In the generated text, the model cites passage numbers (e.g. "Star of India on Boston Post Road [2]"). Separately, `answer()` returns a de-duplicated list of the source filenames behind the chunks that were actually used, and the interface prints them under a **Sources:** heading — so the user can trace any claim back to the originating document (Reddit thread, blog, or guide).

---

## Evaluation Report

<!-- Run your 5 test questions from planning.md through your system and record the results.
     Be honest — a partially accurate or inaccurate result that you explain well is more
     valuable than a suspiciously perfect result. -->

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | Where should I get Indian food for an authentic experience? | Star of India on the Post Road | Named **Star of India on Boston Post Road**, plus Coromandel, Tandoor, Indian Hot Breads, and Sherkaan; cited sources [1][2][5] | Relevant | Accurate |
| 2 | What's a restaurant offering a stellar cocktail menu? | 116 focuses on cocktails | Described a Japanese/yuzu cocktail bar and a lychee-cucumber-mojito spot but **stated the restaurant name wasn't in the passages** — did not name 116 | Partially relevant | Partially accurate |
| 3 | What are some options for casual spots that are newly opened? | Tacos Los Gordos, Munchies, Atticus Market | Declined: "the sources I have don't cover that" — none of the expected spots were retrieved | Off-target | Inaccurate |
| 4 | Where is the best pizza in New Haven? | Modern, Pepe's, Sally's, Bar | Surfaced **Pepe's, Sally's, Modern** (and Atticus), noted the Pepe's-vs-Sally's debate; missed "Bar"; cited [1][3][4][5] | Relevant | Accurate |
| 5 | What kind of seafood is New Haven known for? | Clams, oysters, and especially lobster rolls | Mentioned lobster and shellfish from the context but not clams/oysters/lobster rolls specifically | Partially relevant | Partially accurate |

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

<!-- Identify at least one question where retrieval or generation did not work as expected.
     Write a specific explanation of *why* it failed, tied to a part of the pipeline.

     "The answer was wrong" is not an explanation.

     "The relevant information was split across a chunk boundary, so retrieval returned
     only half the context — the model didn't have enough to answer correctly" is an explanation.

     "The embedding model treated the professor's nickname as out-of-vocabulary and returned
     results from an unrelated review" is an explanation. -->

**Question that failed:**
"What are some options for casual spots that are newly opened?" (expected: Tacos Los Gordos, Munchies, Atticus Market).

**What the system returned:**
The system declined — "The sources I have don't cover that" — and surfaced only generic chunks about "new high-quality restaurants" and the diversity of cuisines in New Haven. None of the expected spots appeared in the top-5.

**Root cause (tied to a specific pipeline stage):**
This is a **retrieval (embedding)** failure, not a generation one. The expected answers *are* in the corpus — Atticus Market, for instance, was retrieved as the top hit for the pizza query — but the query "casual spots that are newly opened" embeds around the abstract concepts of *casualness* and *recency*, while the chunks that actually name these places describe them concretely (a taco spot, a market) without using those framing words. The all-MiniLM-L6-v2 embedding put the query and those chunks far apart in vector space, so they never entered the top-5 and the grounded prompt correctly refused rather than guessing. The 100-token chunks also fragment any list of "new openings," scattering the relevant names across several low-scoring chunks instead of concentrating them in one strong match.

**What you would change to fix it:**
Three options, roughly in order of effort: (1) raise top-k or add a fetch-then-rerank step so more candidates are considered before filtering; (2) add lightweight query expansion (e.g. expand "newly opened casual spots" into "new restaurant openings, recent, taco, market, casual") so the query embedding overlaps more with concrete chunk vocabulary; (3) switch to a larger/instruction-tuned embedding model that handles abstract-to-concrete matching better. A larger chunk size would also help keep "new openings" lists intact rather than fragmented.

---

## Spec Reflection

<!-- Reflect on how planning.md shaped your implementation.
     Answer both questions with at least 2–3 sentences each. -->

**One way the spec helped you during implementation:**
Writing the Chunking Strategy and Retrieval Approach sections first meant every implementation step had concrete numbers to hit — 100-token chunks, 10-token overlap, all-MiniLM-L6-v2, top-k 5, ChromaDB, Groq. When I prompted the AI to generate each stage, I could point it directly at those values instead of negotiating defaults, and the architecture diagram made the boundaries between stages obvious: ingestion writes `chunks.json`, embedding reads it and writes to ChromaDB, generation reads from retrieval. That clean hand-off kept each script independent and easy to test on its own.

**One way your implementation diverged from the spec, and why:**
The spec described chunk size "in tokens" without specifying *which* tokenizer. During implementation I decided to measure tokens with the all-MiniLM-L6-v2 tokenizer itself rather than a generic word/whitespace count, so that "100 tokens" matches exactly what the embedding model ingests. A side effect I didn't anticipate in the spec: that tokenizer is WordPiece, so it lowercases text and occasionally splits a word across a chunk boundary (e.g. `apizza` → `ap` / `##izza`), which shows up in retrieved context. It doesn't hurt retrieval, but it's a divergence from the "clean prose chunks" I imagined when writing the plan.

---

## AI Usage

<!-- Describe at least 2 specific instances where you used an AI tool during this project.
     For each: what did you give the AI as input, what did it produce, and what did you
     change, override, or direct differently?

     "I used Claude to help me code" is not sufficient.
     "I gave Claude my Chunking Strategy section from planning.md and asked it to implement
     chunk_text(). It returned a function using a fixed character split. I overrode the
     chunk size from 500 to 200 because my documents are short reviews, not long guides." -->

**Instance 1**

- *What I gave the AI:* My Documents section (the table of 10 source URLs) and asked it to write a scraper that saves each source into `documents/`.
- *What it produced:* `scrape_documents.py`, which uses Reddit's `.json` endpoint for Reddit threads and a standard-library HTML parser (no BeautifulSoup) for blogs. When several sources turned out to be bot-protected (Reddit 403s, a Sucuri WAF JS challenge on infonewhaven), it added an Internet Archive (Wayback) fallback that transparently recovers a snapshot when the live site blocks the request.
- *What I changed or overrode:* I decided **not** to add a Reddit OAuth path or a WAF-challenge solver for the 3 sources that stayed blocked. Instead I manually copied those (plus a few extra) into `documents/` as plain text — which is why sources 7–10 are marked "manual." I also had to fix that the manual files were saved without a `.txt` extension, so the chunker was updated to accept extensionless text files.

**Instance 2**

- *What I gave the AI:* My Chunking Strategy section (100 tokens / 10 overlap) and asked it to implement the load → clean → chunk pipeline.
- *What it produced:* `chunk_documents.py` with a `chunk_text()` that slides a fixed token window with overlap, plus a `clean_text()` preprocessing step. It defaulted to using the all-MiniLM-L6-v2 tokenizer so token counts line up with the embedder.
- *What I changed or overrode:* I kept the tokenizer-based counting (rather than a simpler character split) because it makes the "100 tokens" in my spec literally true for the embedding model. I verified the overlap behavior on a small sample before running it on all 10 documents, which produced 202 chunks.
