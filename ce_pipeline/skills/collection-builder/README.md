# Collection Builder (v4 — POI-gated, embedding-matched)

Clusters raw experience feeds into Headout collections. Complete rewrite of the
keyword-rule engine. Uses an LLM to classify each experience and embeddings to
match it to existing collections.

## What changed from the old skill

- **POI gate.** Every experience is first classified: is it a single named
  landmark (POI), an activity with a subcategory home, or a day trip? The old
  engine treated everything as collectable — wrong.
- **Embeddings via API, not a local model.** No Hugging Face download, no RAM
  ceiling, no sandbox blocking. Runs the same everywhere.
- **Fails loud.** No TF-IDF fallback. If the API key is missing or a call fails,
  it stops. The numbers you see are always from the real model.
- **City is a hard filter** for POI matching, never part of the score — so
  "Sydney Harbour" and "Auckland Harbour" can't false-merge.
- **Assign vs create are separate jobs** with independent thresholds.
- **No subcategory dumping ground.** An experience either maps to a real
  category/subcategory bucket (`18 - Sydney`), assigns to an existing
  collection, or becomes a proposed new collection. Nothing falls into a
  generic guided-tours bucket as a last resort.

## Decision logic

```
experience
  → strip boilerplate
  → LLM GATE:
       ACTIVITY (cruise, ferry, skydive, zipline, heli, wine, food, jet boat…)
            → "<ID> - City"   (18 - Sydney, 1026 - Tokyo, 1049 - Queenstown…)
       DAY_TRIP city_tour
            → "1010 - City"   (Guided Tours)
       DAY_TRIP point_to_point / complex
            → NEW umbrella collection ("Sydney to Blue Mountains Tours",
              "Fiji Tours", "Uluru Tours") — review
       POI (one named landmark you enter/see)
            → JOB A: match existing collections in the SAME city by embedding
                 sim ≥ 0.82            → assign
                 0.65 ≤ sim < 0.82     → assign + review
                 sim < 0.65            → JOB B
            → JOB B: cluster unmatched POIs (same city + theme, any size)
                 → one proposed new collection each — review
```

ID conventions are in `taxonomy.py::ACTIVITY_TO_ID` (cruises resolve at the
category level = 18; everything else at subcategory level). Edit there.

## Setup (Replit or any machine with network)

```bash
pip install openai numpy openpyxl
export OPENAI_API_KEY=sk-...
```

## Run

```bash
python collection_builder/run.py \
    --feed feed.csv \
    --ce-list existing_ces.csv \
    --out decisions.csv \
    --xlsx decisions.xlsx \
    --limit 50            # optional: smoke-test on first 50 rows first
```

- `--feed`: incoming experiences. Recognised name columns: `experience_name`,
  `Product Name`, `name`, `title`. Optional `link`, `experience_id`.
- `--ce-list`: existing collections. Recognised columns: `name` /
  `Combined Entity Name`, and `city` / `Primary City` (or parsed from
  `"<...> - City"` names).

Start with `--limit 30` to confirm `OPENAI_API_KEY` works and the output looks
right before spending tokens on the full feed.

## The feedback loop (how to improve output)

The output CSV has two blank columns: **`correct_collection`** and **`notes`**.

1. Open `decisions.csv`. Leave correct rows blank.
2. For each WRONG row, put what it should be in `correct_collection`
   (and why in `notes`).
3. Send the file back. Each correction maps to one concrete lever:
   - wrong assign / missed assign → threshold change (`ASSIGN_HIGH`/`ASSIGN_LOW`)
   - POI that must always map a certain way → override entry
   - wrong activity→ID → fix `ACTIVITY_TO_ID`
   - bad new-collection name → naming rule
   - wrong POI/non-POI call → gate prompt tweak

This is the closest thing to "training": every correction becomes a regression
test. Re-run, diff against your labels, measure what the fix moved.

## Tuning

Thresholds live at the top of `engine.py`:
`ASSIGN_HIGH=0.82`, `ASSIGN_LOW=0.65`, `CLUSTER_SIM=0.80`.
Models via env: `CB_EMBED_MODEL` (default `text-embedding-3-small`),
`CB_GATE_MODEL` (default `gpt-4o-mini`).

## Cost

For ~850 experiences: a few cents of embeddings + a few cents of `gpt-4o-mini`
classification. Negligible. Scales linearly across markets.
