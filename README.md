# AutoMMP — CE Consolidation Pipeline

Automated pipeline for consolidating unmanaged supplier listings into Combined Entities (CEs) with ranked assortments, ready for ExperienceOS upload.

**Pipeline:** Supplier CSV → categorize (LLM gate + embeddings) → group into CEs → assort per CE (LLM) → confidence-gate routing → ExperienceOS upload CSV

## Quick Start

```bash
# 1. Clone
git clone git@github.com:AK-HO1/autommp_hackin_2026.git
cd autommp_hackin_2026/ce_pipeline

# 2. Python env
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Set your OpenAI key (required for categorization + assortment)
export OPENAI_API_KEY="sk-..."
# or: cp .env.example .env  and fill in your key there

# 4. Smoke test — no API key needed
python demo_assort_peaktram.py
# -> out/peaktram_experienceos_upload.csv

# 5. Run the full pipeline on a city feed
python run.py --city "Kyoto" --input kyoto_feed.csv --assort --review-xlsx
# -> out/experienceos_upload.csv, out/review_queue.csv, out/assortment_review.xlsx
```

## What You Need

| Requirement | Notes |
|---|---|
| Python 3.10+ | Tested on 3.12 |
| `OPENAI_API_KEY` | Powers both collection-builder (embeddings + LLM gate) and assortment |
| A supplier feed CSV | Columns: `Product ID`, `Name`, `Link`, `City` (or equivalents) |

## CLI Options

```
python run.py --city "City Name" --input <feed.csv> [options]

Required:
  --input           Supplier listings CSV

Optional:
  --city            Filter feed to a single city
  --ce-list         Existing collections CSV (default: bundled global sample with 2,499 CEs)
  --market          Comma-separated cities to scope CE matching (defaults to --city)
  --assort          Run LLM assortment per CE (without this, stops after categorization)
  --review-xlsx     Generate reviewer Excel workbook
  --conf-threshold  Confidence cutoff for auto-list vs review (default: 0.7)
  --out             Output directory (default: out/)
  --inputs-dir      Per-CE research/keyword files at <dir>/<collection_id>/ (default: inputs/)
```

## Per-CE Research & Keyword Inputs

For better assortment quality, add research and keyword files per CE:

```
inputs/
  <collection_id>/
    research.md       # deep-dive research on the CE (attraction info, etc.)
    keywords.csv      # SEO/search keywords for ranking
```

See `inputs/` for Kyoto examples, and `samples/peaktram/` for the format reference.

## Output Files

| File | Description |
|---|---|
| `experienceos_upload.csv` | Auto-listed CEs, ready for ExperienceOS import |
| `review_queue.csv` | Low-confidence CEs that need human review |
| `assortment_review.xlsx` | Excel workbook with all CEs for manual review |
| `decisions.csv` | Per-experience categorization decisions from collection-builder |
| `categorized_collections.csv` | CE groupings (written when running without `--assort`) |

## Sample Output

See `kyoto-test/output/` for a complete Kyoto pipeline run output.

## Project Structure

```
ce_pipeline/
  run.py                        End-to-end orchestrator
  demo_assort_peaktram.py       Assortment demo (no API key needed)
  pipeline/
    schema.py                   Data models (Listing, CE, Experience, Variant, Supplier)
    llm.py                      Provider-agnostic LLM client for assortment
    assort_llm.py               Assortment via assortment-builder skill
    stages/
      stages.py                 Ingest, normalize, assort, route
      output.py                 CSV + xlsx writers
  skills/
    collection-builder/         v4 categorizer (LLM gate + embedding match)
    assortment-builder/         Assortment skill (prompt + output schema)
  samples/                      Sample data (Columbus export, Peak Tram research)
  inputs/                       Per-CE research/keyword files
kyoto-test/                     Kyoto test run (input data + output)
```
