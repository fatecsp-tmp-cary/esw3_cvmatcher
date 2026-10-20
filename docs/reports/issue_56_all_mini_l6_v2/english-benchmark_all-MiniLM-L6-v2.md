# Benchmark Report #56 (all-MiniLM-L6-v2)

**Related issue:** [TASK] Evaluate a local PT/EN embedding model #25
**Subtask:** #56 — Benchmark sentence-transformers all-MiniLM-L6-v2
**Project context:** CV-Match — resume × job matching API using text search + semantic similarity
**Script:** `scripts/benchmarks/embedding_benchmark.py` (PR #81), the same one used in tasks #56 and #57
**Input:** `embedding_benchmark_input.json` — 1 fictional resume + 100 jobs in Portuguese

## Test environment

- OS: Windows-11-10.0.26200-SP0, VSCode editor (integrated PowerShell terminal)
- CPU: AMD64 Family 25 Model 80 Stepping 0, AuthenticAMD
- RAM: 15.3 GB
- Python 3.14.7, PyTorch 2.14.0 (CPU), sentence-transformers 6.1.0, NumPy 2.5.3, device cpu, batch size 32
- Python virtual environment (`venv`) created and activated before installing dependencies
- Installed libraries: `sentence-transformers`, `psutil`
- Command executed:

```
python embedding_benchmark.py --model sentence-transformers/all-MiniLM-L6-v2 --input embedding_benchmark_input.json --runs 5 --output resultado_l6.json
```

- The command was executed twice. The first run is not reported. The values below are from the **second run**, with the model already cached (`cached_before_load: true`).
- Note: running via the Code Runner "Run" button may use the global Python instead of the `venv` — always run `python file.py` in the terminal with `(venv)` active.

## Key concepts learned

- **Embedding:** a numeric representation (vector) of the meaning of a text. Texts with similar meaning produce vectors that are close to each other.
- **Cosine similarity:** a metric (0 to 1, and it can be negative) that measures how close two vectors are. The closer to 1, the more similar the meaning.
- **An absolute score is not a "0-100% grade"**; what matters more is the relative ranking between options for the same reference text.
- **Warm-up:** the first `model.encode()` call is slower (PyTorch does internal preparation). Benchmarks should discard the first runs before measuring.
- **Median of several runs (`--runs`):** the median ignores isolated extreme values, so it is more reliable than a single measurement.
- **max_seq_length / token limit:** every model has a maximum number of tokens it processes at once. Longer texts are truncated **silently** (no visible error, only a log warning) — the rest of the text is ignored in the embedding.
- **Times and memory depend on the machine:** models should only be compared when measured on the same computer.

## Results — PT/EN support

| Comparison | Type | Similarity |
|---|---|---|
| "O gato está dormindo no sofá." (PT) vs. EN translation | equivalent | 0.1816 |
| "Qual é o horário de funcionamento da loja?" (PT) vs. EN translation | equivalent | 0.0623 |
| "Preciso cancelar meu pedido." (PT) vs. EN translation | equivalent | 0.3122 |
| "Desenvolvedora backend com experiência em Python e APIs REST." (PT) vs. EN translation | equivalent | 0.6783 |
| "Analista de suporte técnico com conhecimento em redes." (PT) vs. EN translation | equivalent | 0.0508 |
| "O gato está dormindo no sofá." vs. "I need to cancel my order." | unrelated | 0.0810 |
| "Qual é o horário de funcionamento da loja?" vs. "The weather is nice today." | unrelated | 0.0769 |
| "Desenvolvedora backend..." vs. "Chef preparing menus and managing a kitchen team." | unrelated | 0.1353 |

Mean of equivalent pairs: **0.2570**. Mean of unrelated pairs: **0.0977**. Difference (gap): **0.1593**.

**Conclusion:** The model demonstrates a weak and inconsistent support for Portuguese and English sentences, the equivalent pairs without similar words (like Python, APIs REST) yielded some results showing low similarity. 

## Results — Time and memory

| Metric | Observed value |
|---|---|
| Model load time (model cached) | 3.064 s |
| Process memory before loading | 412.2 MB (Python + PyTorch baseline cost) |
| Process memory after loading | 522.0 MB |
| Additional memory used by the model | 109.8 MB |
| Peak memory (RSS) | 606.7 MB |
| Resume, single encode (median of 5) | 28.46 ms (min 25.18 ms / max 29.84 ms) |
| 100 jobs in one batch (median of 5) | 814.76 ms (8.15 ms per job) |
| Embedding vector dimension | 384 |

**Note:** the single encode of the resume truncates the text at the model limit, so the cost of chunking is not included in this time.

### Comparison with the previous benchmark (individual script)

| Metric | Previous benchmark | Shared script | Assessment |
|---|---|---|---|
| Load time (model cached) | ~3.1 s | 3.064 s | Similar |
| Additional model memory | 110 MB | 109.8 MB | Similar |
| Process memory after loading | ~523 MB | 522.0 MB | Similar |
| Resume: tokens and chunks | 145 tokens, 1 chunk | 470 tokens, 2 chunks | Different resumes, different results |
| Resume, single encode | ~21 ms | 28.46 ms | **Not comparable:** before, a 145-token resume fit in the limit; now a 470-token resume is truncated to 256 tokens |
| PT/EN, equivalent pairs | 0.2570 | 0.2570 (mean of 5) | Same |
| PT/EN, unrelated pairs | 0.0977 | 0.0977 (mean of 3) | Same |

**Note:** time and memory measured on the same machine. The shared script does not measure chunking time.

**Memory difference:** the process memory before (~413 MB vs. 412.2 MB) and after (~523 MB vs. 522 MB) loading the model is practically the same in both measurements.

## Resume × job matching test (realistic scenario)

Tested 1 fictional resume (backend profile, 470 tokens) against 100 fictional jobs in Portuguese from the shared input. Top 10 with chunking (score = highest similarity between the resume chunks and the job):

| Rank | Job | Score |
|---|---|---|
| 1 | [4] Engenheiro de Software Backend Pleno | 0.7249 |
| 2 | [13] Engenheiro de Software (Python e Java) | 0.7195 |
| 3 | [1] Desenvolvedor Backend Python | 0.6929 |
| 4 | [10] Desenvolvedor de Integrações | 0.6588 |
| 5 | [16] Engenheiro DevOps | 0.6437 |
| 6 | [15] Desenvolvedor Backend de E-commerce | 0.6394 |
| 7 | [14] Desenvolvedor de Sistemas com PostgreSQL | 0.6300 |
| 8 | [2] Desenvolvedor Backend Java | 0.6235 |
| 9 | [11] Desenvolvedor Spring Boot Sênior | 0.6178 |
| 10 | [46] Analista de Suporte de TI | 0.6126 |

**Result:**

- Backend development jobs take the top positions, with no manual keyword rules — purely through semantic similarity.
- The lowest scores include a mix of both IT and non-IT professions. (100th Personal Trainer (0.1831); 99th Pentester (0.2420); 98th Motorista de Entregas (0.2855); 82nd Analista de BI (0.3790)), which is inconsistent.
- The middle of the ranking is mixed: "Comissário de Bordo" (0.5026) and "Advogado" (0.4704) rank above "Desenvolvedor Mobile Android" (0.4523).
- "Analista de Suporte de TI" (IT Support Analyst) appears at 10th place (0.6126), above several development jobs, which is a plausible but debatable result.
- "Comissário de Bordo" (Flight Attendant) appears at 36th place (0.5026), above several development and IT jobs, which is an unexpected result.
- The input has no relevance labels (ground truth), so **precision@k was not calculated**. The top of the ranking seems plausible, but the rest is inconsistent and often incoherent.

## Critical finding — Token limit (256) and silent truncation

Tested with the resume from the shared input:

| Item | Value |
|---|---|
| Model limit (`model.max_seq_length`) | 256 tokens |
| Resume | 470 tokens, 2 chunks |
| Longest job | 168 tokens (~65.6% of the limit) |
| Jobs that needed chunking | 0 of 100 |

- The resume has **470 tokens** (almost double the limit).
- Without chunking, the model silently processes only the first 256 tokens, **discarding the rest of the resume with no visible error** — only a log warning (`Token indices sequence length is longer than...`).
- Embedding time for the truncated resume: 28.46 ms (median).
- No job needed chunking. The longest job (168 tokens) is approximately 65.6% of the stated 256-token limit.
- The shared script does not measure chunking time.

## Preliminary conclusion

The model `all-MiniLM-L6-v2`:

- ✅ Has relatively low additional memory usage (109.8 MB), with a peak memory usage of 606.7 MB in this benchmark.
- ✅ Runs on CPU with no paid API
- ⚠️ Shows weak and inconsistent PT/EN support, with a similarity gap of only 0.1593 between equivalent and unrelated sentence pairs.
- ⚠️ Produces plausible top results in Portuguese resume-to-job matching, ranking several relevant backend development positions highly, but the middle and lower rankings contain inconsistent results.
- ⚠️ Has a 256-token limit. The 470-token resume exceeds this limit, requiring chunking to avoid silently discarding relevant information. The shared script does not measure chunking time.
- ⚠️ Only 1 resume and no ground truth: the ranking results are indicative, not conclusive

**Recommendation:** `all-MiniLM-L6-v2` is not recommended for CV-Match, because its PT/EN support is weak (gap of 0.1593) and the resume and jobs are in Portuguese. It is light and fast, so it remains useful as a baseline. The model decision belongs to #26; `multilingual-e5-small` was compared with L12 on 5 resumes in PR #87 (`docs/reports/benchmark-l12-chunking.md`).

**Reference with the model from #57 (data from the report of PR #91, measured on another machine, not redone here):**

- `paraphrase-multilingual-MiniLM-L12-v2`: PT↔EN gap of 0.8226 (vs. 0.1593 for L6), meaning L12 relates PT sentences to their EN equivalents well, while L6 does not
- 128-token limit for L12 (366 tokens in 4 chunks) vs. 256-token limit for L6 (470-token resume in 2 chunks)
- In the ranking with a Portuguese resume and jobs, the top 3 of the two models share 2 jobs (ids 4 and 1): L12's advantage in PT↔EN does not always show when everything is in the same language
- Memory and time should only be compared between models measured on the same machine

## Files used

- `scripts/benchmarks/embedding_benchmark.py` — shared script (PR #81)
- `embedding_benchmark_input.json` — shared input (1 resume + 100 jobs; PR #81)
- `resultado_l6.json` — raw result of this run
