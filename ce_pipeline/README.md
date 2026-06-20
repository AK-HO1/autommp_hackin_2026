# Unmanaged-CE Consolidation Pipeline

Input: a city's raw unmanaged supplier listings (Columbus export).
Output: `experienceos_upload.csv` — ranked CE → Experience (TGID) → Variant (TID)
→ Supplier(s), matching `Exp-Variant_Assortment_output_format.xlsx`.

It is a **deterministic DAG**, not an autonomous agent. The LLM is called only
inside the two judgment stages (categorize, assort), each a swappable "skill"
(prompt + strict JSON schema). Everything else is plain, testable code.

## Pipeline

| # | Stage | File | LLM? | Status |
|---|-------|------|------|--------|
| 1 | ingest / normalize | stages.py `normalize` | no | DONE (maps the export columns) |
| 2 | precluster | stages.py `precluster` | no | DONE v0 (token blocking; upgrade → embeddings) |
| 3 | categorize (CE assign, map-vs-new) | stages.py `categorize` | yes | TODO — needs your prompt |
| 4 | assort (entity resolution + variants + SP map) | stages.py `assort` | yes | TODO — needs your prompt |
| 5 | route (confidence gate + managed overlap) | stages.py `route` | no | TODO |
| 6 | output | output.py | no | DONE (CSV + reviewer xlsx) |

## Run

```bash
# today: ingest + cluster on a real export, one city
python run.py --city "Singapore" --input samples/columbus_export.csv --stop-after precluster

# once stages 3–5 are wired:
python run.py --city "Hong Kong" --input samples/columbus_export.csv --review-xlsx
```

## To wire the core (stages 3–5) we need

1. The **assortment prompt** (+ its input files & expected output) and the
   **categorization prompt** → become the `assort` / `categorize` skills.
2. An export **with the content columns** (Inclusions / Exclusions / Highlights /
   KBYG) joined per row — entity resolution depends on them.
3. A **denser, multi-supplier single-city** sample (this one is 1 RMS, spread
   over 54 cities) so dedup + multi-vendoring actually appear.
4. The **existing-CE master list** (CE id + name + category/subcat) for
   map-to-existing-vs-propose-new.
5. `ANTHROPIC_API_KEY` in the run environment.
