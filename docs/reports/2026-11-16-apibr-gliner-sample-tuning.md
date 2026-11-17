# GLiNER requirement extraction evaluation and tuning on the APiBR sample

This report evaluates the pinned local GLiNER detector and requirement projection
pipeline (`src/extraction/`) against the 23 manually labeled APiBR postings in
`sample_apibr_script.json`, using an improved evaluation methodology over the
previous analysis and comparing against the prototype script in
`tmp/gline/extract_requirements.py`.

## Method improvements (vs. previous analysis)

1. **Accent-folded, guarded matching**: Uses NFKD accent folding so Portuguese
   diacritics are preserved during normalization, requires exact match for short
   strings (`< 3` chars), enforces token-subset or length-ratio (`>= 0.65`)
   guards on substring containment, and pairs predictions to gold labels
   one-to-one on text similarity *before* checking `REQUIRED`/`PREFERRED` class
   agreement (preventing class labels from steering text pairing).
2. **Deduplicated per-job evaluation**: Deduplicates gold and predicted items by
   normalized text (`296` unique gold items across the 23 postings: `230`
   `REQUIRED` and `66` `PREFERRED`, from `299` raw entries).
3. **Out-of-fold + 70/30 stratified validation**: Evaluates both a deterministic
   stratified 70/30 split (`16` calibration postings with `217` gold labels and
   `7` heldout postings with `79` gold labels, seed `apibr-70-30-v1`) and 5-fold
   stratified cross-validation (`apibr-cv-v1`) with 2,000-iteration paired
   bootstrap confidence intervals.

## Comparison with `tmp/gline/extract_requirements.py`

On the same 23 postings at its default threshold `0.30`, the prototype script in
`tmp/gline/extract_requirements.py` predicted `301` items for `296` gold labels
and achieved good raw text overlap (`191` text matches, text F1 `0.640`),
because its `requirement_section()` filter only switched section scope on major
Markdown headings (`^#{1,3}\s+`) and was not derailed by bold subheadings or
colon-delimited bullets. However, its class F1 was only `0.184` (`55`
class-correct matches) because:
- `REQUIRED_CUES` matched singular `\brequisito\b` rather than plural
  `requisitos` / `requirements`, leaving most items under `## Requisitos` and
  `## Requirements` in `unclear_requirements`.
- `section_status()` reset section context on any colon-terminated bullet line.
- It lacked negation handling, span-wrapper trimming, and explicit taxonomy
  alias supplementation.

## Improvements evaluated: Cues, Tokenization/Spans, and Taxonomy

1. **Cues & section parsing (`src/extraction/context.py`, `src/extraction/classification.py`)**:
   - Added missing requirement headings (`obrigatorio`, `obrigatorios`,
     `requisitos mandatorios`, `requisitos desejaveis`, `experiencia e requisitos`,
     `o que precisa`, `o que precisa?`, `habilidades`, `habilidades desejadas`,
     `preferred experience`, `differential`, `differentials`) and corresponding
     `REQUIRED`/`PREFERRED` cues.
   - Prevented bullet items containing colons (e.g., `- Gestão de estado: Redux...`,
     `- Domínio de Figma: Auto Layout...`) from being misclassified as unknown
     inline section headings that flip a `requirements` section to `background`.
   - Stripped inline HTML formatting tags (`<p>`, `<strong>`, `&nbsp;`) when
     detecting section headings.
   - Guarded English `"no <mention>"` negation against the Portuguese contraction
     `no` (`em + o`, e.g., `Projetos no Github`).
2. **Tokenization & span wrapper trimming (`src/extraction/spans.py`, `src/extraction/classification.py`, `src/extraction/gliner.py`)**:
   - Extended `entity_bounds()` to strip Portuguese and English proficiency
     wrappers (`Conhecimento avançado em Power BI` -> `Power BI`,
     `Conhecimento em PHP` -> `PHP`, `English speaker` -> `English`) while
     preserving exact original Unicode offsets and quantities.
   - Added standalone generic wrapper nouns (`Conhecimento`, `Familiaridade`,
     `Proficiência`, `Domínio`, `sólida`, `Fluency`, `Knowledge`, etc.) to the
     cue-only stoplist so they are not selected as standalone requirements.
   - Reserved `SPECIAL_TOKENS = 2` (`[CLS]`, `[SEP]`) in `GlinerExtractor._fits()`
     so tokenized windows stay within `384` subtokens at inference time.
3. **Taxonomy (`src/extraction/taxonomy.py`)**:
   - Added hyphen and URL boundary guards to `alias_spans()` so exact aliases do
     not match inside hyphenated package names (`react-table`,
     `material-react-table`) or URL slugs.
   - Expanded `_ALIASES` with recurring technologies (`Google Cloud Platform`/
     `GCP`, `Cloud Run`, `HTML`/`HTML5`, `CSS`/`CSS3`, `SCSS`, `CI/CD`,
     `REST API`/`RESTful`, `Scrum`, `Kanban`, `Linux`, `MySQL`, `SQL Server`,
     `Laravel`, `Flutter`, `Dart`, `Next.js`, `Vue.js`, `jQuery`, `Redux`,
     `Tailwind CSS`, `Figma`, `Power BI`, `Tableau`, `Looker`, `ETL`, `Oracle`,
     `GitHub`, `GitLab CI`, `NestJS`).

## Ablation & validation results (`sample_apibr_script.json`)

| Stage / Configuration | All Jobs Pred / Gold | All Text Matches | All Class Matches | All Class P / R / F1 | 70% Cal Class F1 (Pred/Gold) | 30% Heldout Class P / R / F1 (Pred/Gold) | 5-Fold CV OOF Class F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `tmp/gline` prototype (@0.30) | 301 / 296 | 191 | 55 | 0.183 / 0.186 / 0.184 | 0.165 (206/217) | 0.228 / 0.253 / 0.240 (95/79) | — |
| Previous pipeline (@0.30 baseline) | 155 / 296 | 111 | 105 | 0.677 / 0.355 / 0.466 | 0.423 (100/217) | 0.691 / 0.481 / 0.567 (55/79) | — |
| Previous pipeline (@0.20 tuned) | 201 / 296 | 123 | 118 | 0.587 / 0.399 / 0.475 | 0.447 (132/217) | 0.580 / 0.506 / 0.541 (69/79) | 0.450 |
| 1. +Cues & section parsing (@0.25) | 326 / 296 | 213 | 200 | 0.613 / 0.676 / 0.643 | 0.626 (221/217) | 0.600 / 0.797 / 0.685 (105/79) | 0.602 |
| 2. +Tokenization & span trimming (@0.25) | 289 / 296 | 213 | 200 | 0.692 / 0.676 / 0.684 | 0.654 (202/217) | 0.724 / 0.797 / 0.759 (87/79) | 0.647 |
| **3. +Taxonomy & guards (@0.25 selected)** | **304 / 296** | **228** | **212** | **0.697 / 0.716 / 0.707** | **0.674 (213/217)** | **0.736 / 0.848 / 0.788 (91/79)** | **0.661** |
| 3. +Taxonomy & guards (@0.30) | 277 / 296 | 217 | 201 | 0.726 / 0.679 / 0.702 | 0.662 (191/217) | 0.767 / 0.835 / 0.800 (86/79) | 0.661 |

## Decision and limits

The provisional threshold is now set to `0.25`, which maximizes calibration class
F1 (`0.674`) on the 70/30 split, yields a near 1:1 element count ratio (`213/217`
on calibration, `91/79` on heldout, `304/296` overall), and raises heldout class
F1 from `0.541` to `0.788` (`67/79` class-correct matches). `EXTRACTION_VERSION`
changes because the threshold, context, classification, span, and taxonomy
versions are part of the extraction policy. Stop workers, prepare a fresh
artifact directory, reprocess unchanged jobs, and restart workers before serving.
Hard exclusions remain disabled; independent reviewed PT/EN acceptance remains
pending. Full measurements are recorded in
[2026-11-16-apibr-gliner-sample-tuning.json](2026-11-16-apibr-gliner-sample-tuning.json).
