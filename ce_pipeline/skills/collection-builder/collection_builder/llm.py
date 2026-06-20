"""
llm.py — OpenAI integration for the collection builder. Two jobs:

  1. classify_batch(titles)  -> structured gate decisions (POI / activity / day-trip)
  2. embed(texts)            -> embedding vectors for cosine matching

DESIGN PRINCIPLE: FAIL LOUD. There is no TF-IDF fallback, no degraded mode. If
the API key is missing or a call fails, the program raises and stops. Silent
downgrades that make bad output look real are the exact trap we're removing.

Provider is OpenAI by default but isolated behind two functions so swapping to a
Headout-internal endpoint later is a localized change.

Env:
  OPENAI_API_KEY   (required)
  CB_EMBED_MODEL   (default text-embedding-3-small)
  CB_GATE_MODEL    (default gpt-4o-mini)
"""
import json
import os
import sys
import time

EMBED_MODEL = os.environ.get("CB_EMBED_MODEL", "text-embedding-3-small")
GATE_MODEL = os.environ.get("CB_GATE_MODEL", "gpt-4o-mini")

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        sys.exit("FATAL: OPENAI_API_KEY is not set. This engine requires a real "
                 "embedding/LLM backend and will not run without one. "
                 "Set OPENAI_API_KEY and retry.")
    try:
        from openai import OpenAI
    except ImportError:
        sys.exit("FATAL: openai package not installed. Run: pip install openai")
    _client = OpenAI(api_key=key)
    return _client


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------
def embed(texts, batch_size=256):
    """Return a list of embedding vectors (list[float]) for `texts`, in order.
    Raises on any API failure — no silent fallback."""
    client = _get_client()
    out = []
    for i in range(0, len(texts), batch_size):
        chunk = [t if t.strip() else " " for t in texts[i:i + batch_size]]
        for attempt in range(4):
            try:
                resp = client.embeddings.create(model=EMBED_MODEL, input=chunk)
                out.extend([d.embedding for d in resp.data])
                break
            except Exception as e:
                if attempt == 3:
                    sys.exit(f"FATAL: embedding call failed after retries: {e}")
                time.sleep(2 ** attempt)
    return out


# ---------------------------------------------------------------------------
# Gate classification
# ---------------------------------------------------------------------------
GATE_SYSTEM = """You classify travel-experience listings for an online marketplace \
(tours, attractions, cruises, activities). For each listing decide how it should be \
catalogued. Output STRICT JSON only.

Return one object per input with these fields:
{
  "i": <int index you were given>,
  "type": "POI" | "ACTIVITY" | "DAY_TRIP",
  "landmark": "<canonical landmark/attraction name>" | null,
  "activity": "<one of the activity keys below>" | null,
  "daytrip_kind": "city_tour" | "point_to_point" | "complex" | null,
  "origin": "<origin city>" | null,
  "destination": "<destination/region>" | null,
  "theme": "<short theme phrase for clustering, e.g. 'glowworm caves', 'whale watching'>",
  "city": "<primary city/region this is sold in>"
}

DECISION RULES (apply in order):

1) ACTIVITY VETO FIRST. If the product is fundamentally one of these activity \
classes, it is type=ACTIVITY with the matching `activity` key — EVEN IF a famous \
landmark appears in the title (a cruise on Milford Sound is ACTIVITY/cruise, not POI):
   cruise, ferry, food_tour, wine_tour, skydiving, ziplining, helicopter \
(scenic/aerial flights), bungee, jet_boat, rafting, kayaking, scuba, surfing, \
skiing, hot_air_balloon, water_sports (generic/multi water activities), \
speed_boat, hoho (hop-on hop-off bus), airport_transfer.

2) DAY_TRIP. If it is a day trip / multi-stop tour (not a single-venue visit):
   - city_tour: sightseeing within or immediately around ONE city (single base, \
no major point-to-point travel) -> daytrip_kind="city_tour".
   - point_to_point: travels from an origin city to a named destination/region \
and back (e.g. "Sydney to Blue Mountains") -> set origin + destination.
   - complex: several destinations / no single A->B structure -> set destination \
to the dominant region if any.

3) POI. Only if NONE of the above apply AND the experience centers on ONE \
specific, named landmark that is itself the attraction — a place you go to \
enter or see (e.g. Melbourne Skydeck, Hobbiton Movie Set, Philip Island Nature \
Park, a museum, an observation deck). Set `landmark` to the canonical name.

Always fill `theme` and `city`. Be consistent with landmark/theme names across \
listings so similar items cluster. Output a JSON array, nothing else."""


def classify_batch(titles, batch_size=40):
    """titles: list[str]. Returns list[dict] gate decisions aligned to input order.
    Raises on failure — no silent fallback."""
    client = _get_client()
    results = [None] * len(titles)
    for start in range(0, len(titles), batch_size):
        chunk = titles[start:start + batch_size]
        payload = [{"i": start + j, "title": t} for j, t in enumerate(chunk)]
        user = ("Classify these listings. Return a JSON array of objects as "
                "specified.\n\n" + json.dumps(payload, ensure_ascii=False))
        for attempt in range(4):
            try:
                kwargs = dict(
                    model=GATE_MODEL,
                    response_format={"type": "json_object"},
                )
                # Some models (e.g. gpt-5.5) don't support temperature=0
                if "5.5" not in GATE_MODEL:
                    kwargs["temperature"] = 0
                resp = client.chat.completions.create(**kwargs,
                    messages=[
                        {"role": "system", "content": GATE_SYSTEM},
                        {"role": "user", "content":
                            user + "\n\nWrap the array as {\"items\": [...]}."},
                    ],
                )
                raw = resp.choices[0].message.content
                data = json.loads(raw)
                items = data.get("items", data if isinstance(data, list) else [])
                for obj in items:
                    idx = obj.get("i")
                    if isinstance(idx, int) and 0 <= idx < len(titles):
                        results[idx] = obj
                break
            except Exception as e:
                if attempt == 3:
                    sys.exit(f"FATAL: gate classification failed after retries: {e}")
                time.sleep(2 ** attempt)
    # Any unfilled slot is a hard error — we do not guess.
    missing = [i for i, r in enumerate(results) if r is None]
    if missing:
        sys.exit(f"FATAL: gate returned no decision for {len(missing)} rows "
                 f"(indices {missing[:10]}...). Aborting rather than guessing.")
    return results
