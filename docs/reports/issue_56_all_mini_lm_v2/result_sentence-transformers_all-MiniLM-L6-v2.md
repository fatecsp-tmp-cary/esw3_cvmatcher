# Learning Journey - Benchmark #56 (sentence-transformers all-MiniLM-L6-v2)

- **Parent Issue:** [TASK] Evaluate a local PT/EN embedding model #25
- **Sub-Issue:** [TASK] Benchmark sentence-transformers all-MiniLM-L6-v2 #56
- **Related PR:** [FEAT] add shared embedding benchmark script and input (#25) #81
- **Project Context:** CV-Match - REST API that receives an already structured CV as JSON and returns job openings ranked by compatibility.

**Note:** This report is about the benchmark results of the old 50-job dataset and the first version of the script. In this benchmark, IDs 1 through 12 were used as a reference (test rule).

## Test environment

- Script used: scripts/issue_56_all_minilm_l6_v2/embedding_benchmark.py
- Input used: scripts/issue_56_all_minilm_l6_v2/embedding_benchmark_input.json
- CPU: AMD64 Family 25 Model 80 Stepping 0, AuthenticAMD
- OS: Windows, VSCode editor (Powershell terminal)
- Python: 3.14.7
- PyTorch: 2.14.0
- NumPy: 2.5.3
- sentence-transformers: 6.1.0
- Model: sentence-transformer/all-MiniLM-L6-v2
- Vector dimension: 384
- Python Virtual Environment (`venv`) created and activated before installing dependencies
- Installed libraries: `sentence-transformers`, `psutil`, `numpy`

**Note:** Running via the Code Runner "Run" button might use the global Python instead of the `venv` — always run using `python file.py` in the terminal with `(venv)` active.

## Key concept learned

- **Embedding:** Numerical representation (vector) of a text's meaning. Texts with similar meanings generate vectors that are close to one another.
- **Cosine similarity:** A metric (ranging from 0 to 1, though it can be negative) that measures how close two vectors are. The closer to 1, the more similar the meaning.
- **Tokens:** A token is a unit of text processed by the model. It can correspond to a word, part of a word, or another text fragment.
- **Chunks:** Chunks are segments of text divided into smaller parts so that the AI ​​model can process texts that exceed its token limit.

## Results - Portuguese and English Support

| Sentence comparison                                                                   | Similarity   |
|---------------------------------------------------------------------------------------|--------------|
| "O gato está dormindo no sofá." (PT) vs. EN Translation                               | 0.1816       |
| "Desenvolvedora backend com experiência em Python e APIs REST." vs. EN Translation    | 0.6783       |
| Sentence above vs. Sentence with no semantic connection                               | 0.1353       |

| Pairs                                                                                 | Mean         |
| Equivalent                                                                            | 0.257        |
| Different                                                                             | 0.0977       |
| Gap Equivalent vs. Different                                                          | 0.1593       |

**Conclusion:** The model demonstrates a weak and inconsistent support for Portuguese and English sentences, the equivalent pairs without similar words (like Python, APIs REST) yielded some results showing low similarity, which should not have happened. 

## Results - Time and memory

| Metric                                           | Observed value                                 |
|--------------------------------------------------|------------------------------------------------|
| Model loading time                               | ~3.1 seconds                                   |
| Memory used by the process before loading        | ~413 megabytes                                 |
| Memory used by the process after  loading        | ~523 megabytes                                 |
| Memory used by the model                         | 110 megabytes                                  |
| Peak memory used during the process              | ~587 megabytes                                 |
| Runs to measure the embedding generation time    | 5 runs                                         |
| Median resume processing time for the resume     | ~21 milliseconds                               |
| Shortest time recorded for the resume            | ~19.7 milliseconds                             |
| Longest time recorded for the resume             | ~21.6 milliseconds                             |
| Jobs count                                       | 50 jobs                                        |
| Median time to process the batch                 | ~287.6 milliseconds                            |
| Shortest time recorded for the batch             | ~272.1 milliseconds                            |
| Longest time recorded for the batch              | ~317.6 milliseconds                            |
| Batch time divided by the number of jobs         | 5.75 milliseconds                              |

**Note:** These times measure the generation of embeddings, not the entire application workflow, which could include reading files, processing the resume, accessing the database, and presenting the results.

## Tokens - Text length

| Field                                            | Value                                          |
|--------------------------------------------------|------------------------------------------------|
| Max sequence length                              | 256                                            |
| Resume tokens                                    | 145                                            |
| Resume chunks                                    | 1                                              |
| Jobs chunked                                     | 0                                              |
| Max job tokens                                   | 67                                             |

**Note:** Since the resume contained 145 tokens and the job posting with the most tokens had 67, none of these texts needed to be chunked during this stage of the benchmark. However, longer resumes and job descriptions might require such treatment.

## Jobs ranking

| Position | Job ID | Job title                              | Score                                |
|----------|--------|----------------------------------------|--------------------------------------|
| 1        | 1      | "Desenvolvedor Backend Python"         | 0.7644                               |
| 2        | 2      | "Desenvolvedor Backend Java"           | 0.6651                               |
| 3        | 11     | "Engenheiro de Software em Nuvem"      | 0.6372                               |
| 4        | 9      | "Desenvolvedor Java Spring Boot"       | 0.6283                               |
| 5        | 6      | "Desenvolvedor de APIs"                | 0.6230                               |
| 6        | 7      | "Engenheiro DevOps"                    | 0.6083                               |
| 7        | 5      | "Engenheiro de Software Backend"       | 0.5938                               |
| 8        | 3      | "Desenvolvedor Full Stack"             | 0.5864                               |
| 9        | 4      | "Engenheiro de Software"               | 0.5676                               |
| 10       | 10     | "Engenheiro de Dados Python"           | 0.5398                               |
| 11       | 22     | "Engenheiro de Cloud"                  | 0.5390                               |
| 12       | 24     | "Analista de Suporte de TI"            | 0.4951                               |
| 13       | 20     | "Administrador de Redes"               | 0.4587                               |
| 14       | 18     | "Gerente de Projetos de Tecnologia"    | 0.4555                               |
| 15       | 25     | "Administrador de Sistemas"            | 0.4478                               |
| 16       | 23     | "Analista de Qualidade de Software"    | 0.4320                               |
| 17       | 12     | "Engenheiro de Automação de Testes"    | 0.4259                               |
| 18       | 28     | "Especialista em Suporte Técnico"      | 0.4093                               |
| 19       | 14     | "Desenvolvedor Frontend"               | 0.4070                               |
| 20       | 21     | "Analista de Sistemas"                 | 0.4026                               |
| 21       | 17     | "Analista de Cibersegurança"           | 0.4006                               |
| 22       | 8      | "Desenvolvedor de Banco de Dados"      | 0.3960                               |
| 23       | 29     | "Engenheiro de Segurança da Informação"| 0.3843                               |
| 24       | 48     | "Comissário de Bordo"                  | 0.3834                               |
| 25       | 13     | "Desenvolvedor de Aplicações Móveis"   | 0.3801                               |
| 26       | 26     | "Engenheiro de Dados"                  | 0.3714                               |
| 27       | 41     | "Eletricista"                          | 0.3274                               |
| 28       | 40     | "Garçom"                               | 0.3225                               |
| 29       | 35     | "Assistente de Recursos Humanos"       | 0.3210                               |
| 30       | 27     | "Consultor de Sistemas ERP"            | 0.3191                               |
| 31       | 15     | "Analista de Dados"                    | 0.3084                               |
| 32       | 37     | "Advogado"                             | 0.3061                               |
| 33       | 16     | "Engenheiro de Machine Learning"       | 0.3045                               |
| 34       | 31     | "Engenheiro Mecânico"                  | 0.3003                               |
| 35       | 34     | "Analista de Marketing"                | 0.2896                               |
| 36       | 44     | "Corretor de Imóveis"                  | 0.2867                               |
| 37       | 19     | "Designer de UI e UX"                  | 0.2852                               |
| 38       | 45     | "Farmacêutico"                         | 0.2842                               |
| 39       | 50     | "Técnico Agrícola"                     | 0.2717                               |
| 40       | 30     | "Coordenador de Projetos de TI"        | 0.2532                               |
| 41       | 39     | "Chef de Cozinha"                      | 0.2217                               |
| 42       | 42     | "Mecânico Automotivo"                  | 0.2100                               |
| 43       | 32     | "Engenheiro Civil"                     | 0.2013                               |
| 44       | 43     | "Professor do Ensino Fundamental"      | 0.1919                               |
| 45       | 47     | "Cabeleireiro"                         | 0.1877                               |
| 46       | 46     | "Pedreiro"                             | 0.1775                               |
| 47       | 38     | "Designer Gráfico"                     | 0.1731                               |
| 48       | 33     | "Enfermeiro"                           | 0.1726                               |
| 49       | 36     | "Contador"                             | 0.1483                               |
| 50       | 49     | "Personal Trainer"                     | 0.0837                               |

**Conclusion:** The results show that backend development and software engineering roles occupied the top positions, while professions not directly related to IT appeared lower in the rankings. This suggests that the model successfully identified relevant relationships between the resume and the job roles.

## Relevant IDs

This field contains the IDs considered relevant for evaluating the classification. In this benchmark, IDs 1 through 12 were used as a reference, corresponding to the software development and software engineering positions defined by the dataset itself.

**Note:** This reference is a test rule (IDs 1 through 12 were used as a reference), not a conclusion produced by the model. A job outside these IDs could still be suitable for a real candidate.

| Precision at          | Value               |
|-----------------------|---------------------|
| 5                     | 1,0                 |
| 10                    | 1,0                 |

The first ten jobs in the ranking were relevant according to the defined reference (ID 1 - 12). This does not mean that 100% of the 50 jobs were classified correctly, nor that the model found all the suitable vacancies.

## Preliminary conclusion

The model `sentence-transformers/all-MiniLM-L6-v2`:
- ✅ Ranked the job openings in alignment with the professional profile used in the test. Opportunities related to backend development and software engineering appeared in the top positions, and precision for the first five and ten openings was 100%, based on the IDs defined as relevant.
- ✅It took approximately 21 milliseconds to process the resume and 288 milliseconds to process the batch of 50 job openings, with a memory increase of approximately 110 MB after loading. This demonstrates promising performance for a CPU-based resume-to-job matching scenario, although it is not sufficient on its own to establish production requirements.
- ⚠️ Demonstrated inconsistency when comparing sentences in Portuguese and English.
- It is recommended to benchmark using larger resumes and job postings to test memory usage and processing time with chunking.