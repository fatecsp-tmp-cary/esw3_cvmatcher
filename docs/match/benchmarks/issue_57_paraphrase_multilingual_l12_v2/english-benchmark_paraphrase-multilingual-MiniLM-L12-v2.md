# Benchmark Report #57 (paraphrase-multilingual-MiniLM-L12-v2)

**Related issue:** [TASK] Evaluate a local PT/EN embedding model #25
**Subtask:** #57 — Benchmark sentence-transformers paraphrase-multilingual-MiniLM-L12-v2
**Project context:** CV-Match — resume × job matching API using text search + semantic similarity
**Script:** `scripts/benchmarks/embedding_benchmark.py` (PR #81), the same one used in tasks #56 and #57
**Input:** `embedding_benchmark_input.json` — 1 fictional resume + 100 jobs in Portuguese

## Test environment

- OS: Windows 11 (10.0.26200), VSCode editor (integrated PowerShell terminal)
- CPU: Intel64 Family 6 Model 140, 8 logical cores
- RAM: 7.7 GB
- Python 3.13.12, PyTorch 2.14.1 (CPU), sentence-transformers 6.1.0, NumPy 2.5.4, device cpu, batch size 32
- Python virtual environment (`venv`) created and activated before installing dependencies
- Installed libraries: `sentence-transformers`, `psutil`
- Command executed:

```
python embedding_benchmark.py --model sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 --input embedding_benchmark_input.json --runs 5 --output resultado_l12.json
```

- The command was executed twice. The first run downloaded the model (load time of 25.05 s, not representative). The values below are from the **second run**, with the model already cached (`cached_before_load: true`).
- Measurement conditions: laptop plugged in.
- Note: running via the Code Runner "Run" button may use the global Python instead of the `venv` — always run `python file.py` in the terminal with `(venv)` active.

## Key concepts learned

- **Embedding:** a numeric representation (vector) of the meaning of a text. Texts with similar meaning produce vectors that are close to each other.
- **Cosine similarity:** a metric (0 to 1, and it can be negative) that measures how close two vectors are. The closer to 1, the more similar the meaning.
- **An absolute score is not a "0-100% grade"**; what matters more is the relative ranking between options for the same reference text.
- **Warm-up:** the first `model.encode()` call is slower (PyTorch does internal preparation). Benchmarks should discard the first runs before measuring.
- **Median of several runs (`--runs`):** the median ignores isolated extreme values, so it is more reliable than a single measurement.
- **Batch processing is faster per item** than processing one by one — confirmed empirically in the previous benchmark (~36% faster in the test performed).
- **max_seq_length / token limit:** every model has a maximum number of tokens it processes at once. Longer texts are truncated **silently** (no visible error, only a log warning) — the rest of the text is ignored in the embedding.
- **Times and memory depend on the machine:** models should only be compared when measured on the same computer.

## Results — PT/EN support

| Comparison | Type | Similarity |
|---|---|---|
| "O gato está dormindo no sofá." (PT) vs. EN translation | equivalent | 0.9857 |
| "Qual é o horário de funcionamento da loja?" (PT) vs. EN translation | equivalent | 0.8644 |
| "Preciso cancelar meu pedido." (PT) vs. EN translation | equivalent | 0.9601 |
| "Desenvolvedora backend com experiência em Python e APIs REST." (PT) vs. EN translation | equivalent | 0.8837 |
| "Analista de suporte técnico com conhecimento em redes." (PT) vs. EN translation | equivalent | 0.9358 |
| "O gato está dormindo no sofá." vs. "I need to cancel my order." | unrelated | 0.0587 |
| "Qual é o horário de funcionamento da loja?" vs. "The weather is nice today." | unrelated | 0.2373 |
| "Desenvolvedora backend..." vs. "Chef preparing menus and managing a kitchen team." | unrelated | 0.0139 |

Mean of equivalent pairs: **0.9259**. Mean of unrelated pairs: **0.1033**. Difference (gap): **0.8226**.

**Conclusion:** the model shows robust and consistent PT/EN support, with a clear separation between equivalent sentences and semantically unrelated sentences. The lowest value among the equivalent pairs (0.8644) is well above the highest value among the unrelated pairs (0.2373).

## Results — Time and memory

| Metric | Observed value |
|---|---|
| Model load time (model cached) | 10.14 s |
| Process memory before loading | 381.7 MB (Python + PyTorch baseline cost) |
| Process memory after loading | 815.3 MB |
| Additional memory used by the model | 433.7 MB |
| Peak memory (RSS) | 925.6 MB |
| Resume, single encode (median of 5) | 77.58 ms (min 66.82 / max 119.41) |
| 100 jobs in one batch (median of 5) | 2396.48 ms (23.96 ms per job) |
| Embedding vector dimension | 384 |

**Note:** the single encode of the resume truncates the text at the model limit, so the cost of chunking is not included in this time.

**Variation between runs:** between the first and second run, the resume varied by about 10% (70.48 ms to 77.58 ms) and the 100 jobs by about 6% (2253.74 ms to 2396.48 ms). The earlier individual benchmark (same model, another machine) reported variation below 2%, so these timings are indicative only.

### Comparison with the previous benchmark (individual script)

| Metric | Previous benchmark | Shared script | Assessment |
|---|---|---|---|
| Load time (model cached) | ~6 to 11.5 s | 10.14 s | Within range |
| Additional model memory | ~825 to 939 MB | 433.7 MB (peak 925.6 MB) | **Large difference (about half)** |
| Process memory after loading | ~1216 to 1319 MB | 815.3 MB | **33% to 38% lower** |
| Truncated resume (single encode) | 70.7 ms | 77.58 ms | Similar |
| PT/EN, equivalent pairs | 0.9524 | 0.9259 (mean of 5) | Consistent (different pairs) |
| PT/EN, unrelated pairs | 0.1133 | 0.1033 (mean of 3) | Consistent |
| Resume: tokens and chunks | 398 tokens, 4 chunks | 366 tokens, 4 chunks | Different resumes, same result |

**Relevant memory difference:** the process memory before loading the model is practically the same in both measurements (~382 MB vs. ~390 MB), so the difference is in loading the model itself. The cause was not investigated. Hypotheses to check: Python version (3.11 in the previous benchmark, 3.13 now), library versions (torch 2.14.0 to 2.14.1; transformers 5.17 to 5.19), and a different computer.

## Resume × job matching test (realistic scenario)

Tested 1 fictional resume (backend profile, 366 tokens) against 100 fictional jobs in Portuguese from the shared input. Top 10 with chunking (score = highest similarity between the resume chunks and the job):

| Rank | Job | Score |
|---|---|---|
| 1 | [14] Desenvolvedor de Sistemas com PostgreSQL | 0.7357 |
| 2 | [4] Engenheiro de Software Backend Pleno | 0.7007 |
| 3 | [1] Desenvolvedor Backend Python | 0.6910 |
| 4 | [12] Desenvolvedor FastAPI | 0.6802 |
| 5 | [8] Desenvolvedor Full Stack Python | 0.6786 |
| 6 | [13] Engenheiro de Software (Python e Java) | 0.6456 |
| 7 | [10] Desenvolvedor de Integrações | 0.6439 |
| 8 | [18] Engenheiro de Dados | 0.6297 |
| 9 | [11] Desenvolvedor Spring Boot Sênior | 0.6279 |
| 10 | [71] Redator Técnico | 0.6143 |

**Result:**

- Backend development jobs take the top positions, with no manual keyword rules — purely through semantic similarity.
- The lowest scores belong to non-IT professions (Mecânico Automotivo 0.1510; Comissário de Bordo 0.1787; Corretor de Imóveis 0.2188), which is coherent.
- The middle of the ranking is mixed: "Pedreiro" (0.3957) and "Professor do Ensino Fundamental" (0.3947) rank above "Desenvolvedor Go" (0.3916).
- "Redator Técnico" (Technical Writer) appears at 10th place (0.6143), above several development jobs, which is a plausible but debatable result.
- The input has no relevance labels (ground truth), so **precision@k was not calculated**. The ranking looks plausible but is not validated.

**Architecture implication (measured in the previous benchmark, not redone with the shared script):** the performance bottleneck is generating embeddings, not comparing them (9 comparisons took 4.68 ms). In this benchmark, generating embeddings for 100 jobs took about 2.4 s. It is recommended to generate and index the job embeddings in advance (not on every search); at search time, generate only the resume embedding and compare it with the precomputed job embeddings.

## Critical finding — Token limit (128) and silent truncation

Tested with the resume from the shared input:

| Item | Value |
|---|---|
| Model limit (`model.max_seq_length`) | 128 tokens |
| Resume | 366 tokens, 4 chunks |
| Longest job | 114 tokens (89% of the limit) |
| Jobs that needed chunking | 0 of 100 |

- The resume has **366 tokens** (almost triple the limit).
- Without chunking, the model silently processes only the first 128 tokens, **discarding the rest of the resume with no visible error** — only a log warning (`Token indices sequence length is longer than...`).
- Embedding time for the truncated resume: 77.58 ms (median).
- No job needed chunking, but the longest one is close to the limit.

**Evidence of the impact:** comparing the top 10 without chunking (truncated resume) with the top 10 with chunking, only **5 of the 10 jobs** are in common (ids 4, 12, 1, 13 and 14). Job 14 (Desenvolvedor de Sistemas com PostgreSQL) rises from 9th place (score 0.5521) to 1st (0.7357), which indicates that it matches parts of the resume that truncation was discarding.

**Identified risk:** resumes where the most relevant information (e.g. technical projects, certifications, volunteering) is beyond the first ~128 tokens would have that information ignored in matching, producing unfair or incorrect comparisons with nobody noticing the cause. The jobs in this input are fictional and short; real postings from sites such as LinkedIn tend to be longer and may need chunking too.

## Tested solution — Chunking

The shared script splits the text into chunks using the model's own tokenizer (limit of 128 tokens minus the 2 special tokens, per the script code), with a **20-token overlap** between consecutive chunks. It generates an embedding for each chunk and uses the **highest score among the chunks** as the resume score (logic: if any part of the resume matches the job well, that counts in the candidate's favor).

**Result in this benchmark:**

- The 366-token resume was split into **4 chunks**.
- The shared script does not measure chunking time. In the previous benchmark, processing 4 chunks of a 398-token resume took 204.7 ms (no overlap) and 271.3 ms (with a 20-token overlap), against ~70 ms for the truncated resume. These are single-run measurements.

**Trade-off identified (previous benchmark):** the overlap avoids cutting sentences or words in half at chunk boundaries, but it may dilute information that was previously concentrated in a single chunk (in the previous test, the best score dropped from 0.650 without overlap to 0.611 with overlap). Neither approach is strictly "better" — it is a product decision to be validated with more data.

## Model alternatives identified (for future investigation)

The two e5 models have a 512-token limit; the mpnet keeps 128 and does not avoid chunking.

| Model | Token limit | Notes |
|---|---|---|
| `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (tested) | 128 | Lightweight, requires chunking for long texts |
| `intfloat/multilingual-e5-small` | 512 | Same weight/size (118M parameters, 384 dimensions) |
| `intfloat/multilingual-e5-base` | 512 | Medium weight |
| `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` | 128 | Heavier than MiniLM |

**On quality (not only token limit):** `multilingual-e5-small` has the same size (118M parameters, 384 dimensions) and a 512-token limit, and requires prefixing texts with `"query: "` / `"passage: "`, a particularity of its training. It was **not measured in this report**, but it was measured in the multi-resume benchmark of PR #87 (`docs/match/benchmarks/benchmark-l12-chunking.md`: 5 fictional resumes, 100 jobs, human gabarito, chunking and pgvector). There, the mean nDCG@10 with the mean of the top 3 chunks was 0.698 for `multilingual-e5-small` against 0.634 for L12, and the whole resume without chunking scored 0.621 against 0.629 (truncated). With only 5 resumes, differences below about 0.05 are not reliable, so the two models are close and e5-small does not lose quality here.

**Recommendation:** the comparison with `multilingual-e5-small` suggested here was done in #87; the final model decision belongs to #26. For L12 alone, chunking is mandatory for real resumes (see the finding above).

## Preliminary conclusion

The model `paraphrase-multilingual-MiniLM-L12-v2`:

- ✅ Meets the PT/EN support requirement well (gap of 0.8226; all equivalent pairs above 0.86)
- ✅ Runs on CPU with no paid API
- ⚠️ Uses ~434 MB of additional RAM (peak of ~926 MB) on this machine — about half of what was measured in the previous benchmark (~825-939 MB), a difference whose cause has not been investigated; a point of attention for deployment on a low-memory free tier
- ⚠️ The 128-token limit requires chunking for real resumes, and chunking changed half of the top 10 in this test — it is not an optional detail
- ⚠️ Only 1 resume and no ground truth: the ranking results are indicative, not conclusive
- `intfloat/multilingual-e5-small` was compared in PR #87 (512-token limit, same weight, mean nDCG@10 0.698 against 0.634 for L12 with chunking); the final decision is up to #26

**Reference with the model from #56 (data from PR #81, measured by the author on another machine, Linux, not redone here):**

- `all-MiniLM-L6-v2`: PT↔EN gap of 0.1593 (vs. 0.8226 for L12), meaning it does not relate PT sentences to their EN equivalents well
- 256-token limit (470-token resume in 2 chunks), vs. 128 for L12 (366 tokens in 4 chunks)
- In the ranking with a Portuguese resume and jobs, the top 3 of the two models share 2 jobs (ids 4 and 1): L12's advantage in PT↔EN does not always show when everything is in the same language
- Memory and time should only be compared between models measured on the same machine

## Files used

- `scripts/benchmarks/embedding_benchmark.py` — shared script (PR #81)
- `embedding_benchmark_input.json` — shared input (1 resume + 100 jobs; PR #81)
- `resultado_l12.json` — raw result of this run
