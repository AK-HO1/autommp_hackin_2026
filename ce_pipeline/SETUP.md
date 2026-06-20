# Setup & Run (local)

Pipeline: a city's supplier-listings CSV -> **categorize** into Combined Entities
(collection-builder v4) -> **assort** each CE into ranked Experiences/Variants
-> ExperienceOS upload CSV.

> Note: collection-builder v4 uses an LLM gate + embeddings, so **categorization
> now requires `OPENAI_API_KEY` + network access** (no offline mode). Only the
> standalone assortment demo runs without a key.

## 0. Prerequisites
- Python 3.10+, git
- An OpenAI API key (used by both the categorizer and the assort step)

## 1. Get the code
Unzip `ce_pipeline.zip` so you have `ce_pipeline/` with `run.py` at its root.

## 2. Virtual env + dependencies
```bash
cd ce_pipeline
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt    # openai, numpy, openpyxl, python-dotenv
```

## 3. Configure keys (local only)
```bash
cp .env.example .env
# edit .env:
#   OPENAI_API_KEY=sk-...           (used by BOTH steps)
#   LLM_PROVIDER=openai             (assort)
#   LLM_MODEL=gpt-5.5               (assort model)
#   optional: CB_GATE_MODEL / CB_EMBED_MODEL  (categorization models)
```
`.env` is gitignored. (Or just `export` the vars in your shell.)

## 4. Smoke tests
**a) Assortment demo — NO key needed** (proves the assort + output path):
```bash
python demo_assort_peaktram.py     # -> out/peaktram_experienceos_upload.csv
```
**b) Categorizer smoke test — needs your key** (uses v4's bundled sample data):
```bash
python skills/collection-builder/collection_builder/run.py \
  --feed skills/collection-builder/sample_data_nz_feed.csv \
  --ce-list skills/collection-builder/sample_data_ce_list_global.csv \
  --market "Auckland,Queenstown,Rotorua,Christchurch,Wellington,Milford Sound,Te Anau,Taupo,Wanaka,Nelson" \
  --out out/decisions.csv --limit 30
```
Always `--limit 30` first to confirm the key works before spending tokens.

## 5. Full pipeline — needs your key
```bash
python run.py --city "Hong Kong" --input <your_feed.csv> \
              --assort --review-xlsx
# -> out/experienceos_upload.csv (+ review_queue.csv, assortment_review.xlsx)
```
- `--ce-list` defaults to the bundled `sample_data_ce_list_global.csv` (2,499 CEs);
  pass your own existing-collections CSV for real runs.
- `--market "City1,City2,..."` scopes matching to one market (defaults to `--city`).
- Drop `--assort` to stop after categorization (writes `decisions.csv` +
  `categorized_collections.csv`).
- Per-CE deep-research + keyword files go in `inputs/<collection_id>/` as
  `research.*` and `keywords.*` (see `samples/peaktram/` for the shape).

## 6. Feeds & existing-CE columns (what v4 recognizes)
- **Feed** name column: `experience_name` / `Product Name` / `name` / `title`
  (our `run.py` maps a Columbus `Name` + `Product ID` feed to these automatically);
  optional `link`, `experience_id`.
- **CE list** columns: `Combined Entity ID`, `Combined Entity Name`, `City`
  (aliases accepted). The ID is what lets the router reuse `<ID> - City` buckets.

## 7. Tuning collection-builder v4
- Thresholds: top of `skills/collection-builder/collection_builder/engine.py`
  (`ASSIGN_HIGH=0.82`, `ASSIGN_LOW=0.65`, `CROSS_CITY_HIGH=0.88`, `CLUSTER_SIM=0.80`).
- Activity -> subcategory IDs: `collection_builder/taxonomy.py` (`ACTIVITY_TO_ID`).
- POI/non-POI gate behaviour: the gate prompt in `collection_builder/llm.py`.
- Models: env `CB_GATE_MODEL` (default `gpt-4o-mini`), `CB_EMBED_MODEL`
  (default `text-embedding-3-small`).
- Feedback loop: `decisions.csv` has blank `correct_collection` + `notes` columns —
  label wrong rows; each correction maps to one of the levers above.

## 8. Push to git
```bash
git init && git add .
git status            # confirm .env and out/ are NOT listed
git commit -m "CE consolidation pipeline (collection-builder v4 + assortment-builder)"
git branch -M main && git remote add origin <your-repo-url> && git push -u origin main
```

## What runs today vs next
- DONE: categorization (collection-builder v4: LLM gate + embedding match),
  grouping into CEs, assortment per CE (assortment-builder), confidence-gate
  routing, ExperienceOS CSV + reviewer xlsx.
- NEXT: live Columbus API ingest (today: CSV export); auto-generating per-CE
  research + keyword inputs (today: provided files); assortment-rule tuning.

## Project map
```
run.py                       end-to-end orchestrator (drives v4 + assort)
demo_assort_peaktram.py      assortment demo (no key)
pipeline/
  schema.py                  data models (Listing -> CE -> Experience -> Variant -> Supplier)
  llm.py                     provider-agnostic model client for ASSORT (OpenAI / Anthropic)
  assort_llm.py              assortment via the assortment-builder skill
  stages/
    stages.py                ingest, normalize, assort (-> assort_llm), route
    output.py                ExperienceOS CSV + reviewer xlsx writers
skills/
  collection-builder/        v4 skill: collection_builder/ package (run/engine/llm/taxonomy)
                             + references + sample_data_*.csv
  assortment-builder/        assortment skill (prompt + output schema)
samples/                     columbus_export.csv + peaktram/ (research, keywords, supply)
inputs/                      per-CE research/keyword files: inputs/<collection_id>/
```
