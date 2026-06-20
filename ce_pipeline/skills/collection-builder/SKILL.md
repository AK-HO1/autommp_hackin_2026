---
name: collection-builder
description: >-
  Clusters a raw experience/tour/activity feed (GetYourGuide, Viator, Klook,
  Bokun, or Columbus export) into Headout collections. For each experience it
  runs an LLM POI-gate then embedding match to decide: assign to an EXISTING
  collection, map to a category/subcategory bucket ("18 - Sydney" for cruises,
  "1010 - Auckland" for city tours), or propose a NEW collection (a POI landmark
  or a day-trip/destination umbrella like "Sydney to Blue Mountains Tours").
  Use whenever someone wants to categorize, classify, assign, route, bucket,
  cluster, or de-duplicate an experience feed into collections; auto-create
  collections for new POIs/themes; map an export to a collection taxonomy; or
  answer "which collection does this experience go in." Trigger on "cluster
  these experiences," "assign this feed to collections," "build collections from
  this list," "categorize this export," or an uploaded CSV of attraction/tour
  products — don't wait for the exact word "collection." Requires OPENAI_API_KEY
  and network access; runs on Replit or Headout infra, NOT inside a restricted
  sandbox.
---

# Collection Builder (v4)

POI-gated, embedding-matched engine that turns a raw experience feed into
Headout collection decisions. This is a rewrite of the old keyword-rule engine.

## When to use

A feed of experiences arrives (CSV) and each one must be placed:
- **assign_existing** — matches a collection that already exists, reuse it
- **assign_subcategory** — non-POI activity -> `"<ID> - City"` bucket
- **create_new** — a new POI collection or a day-trip/destination umbrella

Low-confidence cases are flagged `needs_review=true`, never silently guessed.

## Decision logic (what the engine does)

```
experience
  → strip boilerplate ("City:", "Official ticket:", etc.)
  → LLM GATE classifies into one of three:
       ACTIVITY  (cruise, ferry, skydiving, ziplining, helicopter, wine, food,
                  jet boat, bungee, rafting, kayaking, scuba, surfing, skiing…)
                 → "<ID> - City"   e.g. 18 - Sydney (cruises),
                                        1026 - Tokyo (food), 1049 - Queenstown
       DAY_TRIP  city_tour          → "1010 - City"  (Guided Tours)
                 point_to_point /
                 complex            → NEW umbrella collection, review
                                       ("Sydney to Blue Mountains Tours",
                                        "Fiji Tours", "Uluru Tours")
       POI       (one named landmark you enter/see; NOT a veto'd activity)
                 → JOB A: embedding match vs existing collections IN THE SAME
                          CITY (city is a hard filter, never part of the score)
                            sim ≥ 0.82          → assign
                            0.65 ≤ sim < 0.82   → assign + review
                            sim < 0.65          → JOB B
                 → JOB B: cluster unmatched POIs (same city + theme, any size)
                          → propose one new collection each, review
```

The activity→ID table and naming conventions are in
`collection_builder/taxonomy.py` (`ACTIVITY_TO_ID`). Cruises resolve at the
CATEGORY level (18); everything else at the subcategory level. Edit there, not
in code.

## How to run it

This engine calls OpenAI for the gate (classification) and embeddings (match).
It **fails loud** — no API key or a failed call aborts; there is no offline
fallback, so the output is always from the real model.

### Step 1 — check the environment
Confirm `OPENAI_API_KEY` is set and the host has network access.
- **If yes** (Headout infra, a configured Replit, a dev machine): run directly,
  Step 2.
- **If no** (restricted sandbox, no key): do NOT try to run it here. Tell the
  user to run it on Replit/their infra and walk them through Step 2 there. Do
  not fabricate output.

### Step 2 — install and run
```bash
pip install -r requirements.txt          # openai, numpy, openpyxl
export OPENAI_API_KEY=sk-...

python collection_builder/run.py \
    --feed FEED.csv \
    --ce-list EXISTING_CES.csv \
    --market "Auckland,Queenstown,Rotorua,Christchurch,Wellington,Milford Sound,Te Anau,Taupo,Dunedin,Kaikoura,Franz Josef,Tauranga,Waitomo,Matamata,Wanaka,Lake Tekapo,Nelson,Napier,Paihia,Blenheim,Picton,Hamilton" \
    --out decisions.csv \
    --xlsx decisions.xlsx \
    --limit 30        # smoke-test first; drop --limit for the full run
```

Inputs:
- `--feed`: incoming experiences. Name column may be `experience_name`,
  `Product Name`, `name`, or `title`; optional `link`, `experience_id`.
- `--ce-list`: existing collections. Columns `name` /
  `Combined Entity Name`, `city` / `City`, and `Combined Entity ID` (the ID is
  what lets the router match `<ID> - City` buckets like "18 - Sydney").
- `--market` (optional but recommended for the global CE list): comma-separated
  cities to scope matching to one market, e.g. all NZ cities. This (a) speeds up
  matching against a 2,499-row global list and (b) keeps the cross-city fallback
  in-country so "Sky Tower" (Auckland) can't match "Sky Tower" (Bangkok).

### City matching is a preference, not a wall
POI matching prefers same-city candidates, but if a POI's gate-city has no
existing collection (e.g. a GYG title says "Matamata: Hobbiton Tour" while the
"Hobbiton Movie Set Tours" collection is filed under Auckland), it falls back to
the whole market with a stricter similarity bar (`CROSS_CITY_HIGH=0.88`) and
flags the result for review. This stops both duplicate-creation AND wrong
cross-city merges.

Always run `--limit 30` first to confirm the key works and the output looks
right before spending tokens on the whole feed.

Sample data ships for a first run: `sample_data_nz_feed.csv` (845 NZ
experiences) and `sample_data_ce_list_global.csv` (2,499 global Headout
collections, with real IDs + cities, including the `<ID> - City` buckets).

## Reading and improving the output

The output CSV is also the **feedback template** — it has two blank columns,
`correct_collection` and `notes`. To tune the engine:

1. Open `decisions.csv`; leave correct rows blank.
2. For each WRONG row, put the right answer in `correct_collection` (why in
   `notes`).
3. Each correction maps to one lever:
   - wrong / missed assign → thresholds `ASSIGN_HIGH` / `ASSIGN_LOW` in `engine.py`
   - POI that must always map a certain way → add an override
   - wrong activity → ID → fix `ACTIVITY_TO_ID` in `taxonomy.py`
   - bad new-collection name → naming rule in `engine.py`
   - wrong POI/non-POI call → adjust the gate prompt (`GATE_SYSTEM` in `llm.py`)

Re-run, diff against the labels, report what each fix moved. Every correction is
a regression test — that is the tuning loop.

## Tuning knobs

- Thresholds (top of `engine.py`): `ASSIGN_HIGH=0.82`, `ASSIGN_LOW=0.65`,
  `CROSS_CITY_HIGH=0.88` (stricter bar for cross-city fallback matches),
  `CLUSTER_SIM=0.80`.
- Models (env): `CB_EMBED_MODEL` (default `text-embedding-3-small`),
  `CB_GATE_MODEL` (default `gpt-4o-mini`).

## Cost

~850 experiences ≈ a few cents total (embeddings + gpt-4o-mini). Scales linearly
across markets.

## Files

- `collection_builder/run.py` — CLI entry point
- `collection_builder/engine.py` — pipeline, routing, Job A / Job B
- `collection_builder/llm.py` — OpenAI gate + embeddings (fails loud)
- `collection_builder/taxonomy.py` — category/subcategory IDs + routing table
- `references/` — naming conventions, taxonomy notes (read for context)
