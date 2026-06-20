"""
engine.py — the decision pipeline.

Flow per experience:
  1. normalize title (strip boilerplate)
  2. LLM gate -> {type, landmark/activity/daytrip_kind, theme, city}
  3. route:
       ACTIVITY              -> "<ID> - City" bucket (taxonomy.ACTIVITY_TO_ID)
       DAY_TRIP city_tour    -> "1010 - City" (Guided Tours)
       DAY_TRIP point/complex-> named umbrella collection (new), review
       POI                   -> JOB A: match existing POI collections in-city
                                  hit  -> assign
                                  miss -> JOB B: cluster with other unmatched
                                          POIs (same city+theme), propose new
Outputs one record per experience + a blank `correct_collection` column so the
output file IS the labelling template for the feedback loop.

City is a HARD FILTER for POI matching (never part of the similarity score), so
"Sydney Harbour" and "Auckland Harbour" can't false-merge.
"""
import re
import unicodedata

import numpy as np

from . import taxonomy
from . import llm

# --- thresholds (tune against labelled data) -------------------------------
ASSIGN_HIGH = 0.82      # >= : confident same-city assign
ASSIGN_LOW = 0.65       # [LOW, HIGH): same-city assign but flag for review
CROSS_CITY_HIGH = 0.88  # stricter bar for a cross-city (fallback) assign
CLUSTER_SIM = 0.80      # Job B: titles >= this similar become one new collection


# --- text utils ------------------------------------------------------------
_BOILERPLATE = [
    r"^official ticket[s]?:\s*", r"^official tour:\s*", r"^certified by getyourguide:\s*",
    r"^skip[- ]the[- ]line:\s*", r"^new:\s*", r"^exclusive:\s*", r"^from\s+[\w' ]+:\s*",
]


def norm(s):
    s = "".join(c for c in unicodedata.normalize("NFKD", s or "")
                if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.lower()).strip()


def strip_boilerplate(title):
    t = title or ""
    t = re.sub(r"^[A-Za-zÀ-ÿ'’.\- ]{1,40}?:\s*", "", t, count=1)  # leading "City:"
    for pat in _BOILERPLATE:
        t = re.sub(pat, "", t, flags=re.I)
    return re.sub(r"\s+", " ", t).strip() or title


def cosine_matrix(a, b):
    """Rows of a vs rows of b -> similarity matrix. Inputs are L2-normalised first."""
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    a /= (np.linalg.norm(a, axis=1, keepdims=True) + 1e-9)
    b /= (np.linalg.norm(b, axis=1, keepdims=True) + 1e-9)
    return a @ b.T


# --- existing-collection memory --------------------------------------------
class CollectionMemory:
    """Existing collections to match against.

    Two kinds of entry, handled differently:
      - BUCKET collections whose ID is "<ID> - City" (e.g. "18 - Paris" =
        Cruises - Paris). Matched DETERMINISTICALLY by the activity router.
      - NAMED POI collections (Colosseum, Sky Tower). Matched SEMANTICALLY by
        embedding in Job A.

    City handling for POI matching is a PREFERENCE, not a hard wall:
      1. First try candidates whose city == the experience's city.
      2. If that city has no candidates (e.g. "Hobbiton" gate-city=Matamata but
         the CE is filed under Auckland), fall back to ALL named POIs in the
         loaded memory (which should be pre-scoped to one market/country via
         `market_cities`, so the fallback stays in-country and "Sky Tower
         Auckland" can't match "Sky Tower Bangkok").
    """

    def __init__(self, rows, market_cities=None):
        self.entries = []          # named POI collections (for embeddings)
        self.buckets = {}          # "<ID> - City" (normalised) -> canonical name
        mc = {norm(c) for c in market_cities} if market_cities else None
        for r in rows:
            if isinstance(r, dict):
                cid = str(r.get("id", r.get("collection_id", ""))).strip()
                name = r["name"]
                city = r.get("city", "")
            else:
                cid, name, city = "", r[0], (r[1] if len(r) > 1 else "")
            # If a market scope is given, skip collections outside it.
            if mc is not None and norm(city) not in mc:
                continue
            if re.match(r"^\d+\s*-\s*.+", cid):
                self.buckets[norm(cid)] = {"id": cid, "name": name, "city": city}
            else:
                self.entries.append({"id": cid, "name": name, "city": city})
        self._by_city = {}
        for idx, e in enumerate(self.entries):
            self._by_city.setdefault(norm(e["city"]), []).append(idx)
        self._emb = None
        self._all_idx = list(range(len(self.entries)))

    def embed_all(self):
        if self._emb is None and self.entries:
            self._emb = np.asarray(
                llm.embed([e["name"] for e in self.entries]), dtype=np.float32)
        return self._emb

    def candidates_in_city(self, city):
        """Prefer same-city candidates; fall back to the whole (market-scoped)
        memory when the city has none. Returns (indices, used_fallback)."""
        same = self._by_city.get(norm(city), [])
        if same:
            return same, False
        return self._all_idx, True

    def bucket_exists(self, collection_id):
        return norm(collection_id) in self.buckets


# --- main entry ------------------------------------------------------------
def run(experiences, memory):
    """experiences: list[dict] with keys 'experience_id','experience_name',
                    and optionally 'link'.
       memory: CollectionMemory of existing collections (optionally pre-scoped
               to one market via market_cities when constructed).
       Returns list[dict] decision records.
    """
    titles = [e["experience_name"] for e in experiences]
    clean = [strip_boilerplate(t) for t in titles]

    # 1) GATE (LLM) — classify everything in one pass.
    gates = llm.classify_batch(clean)

    # Pre-embed memory once (only needed if there are POIs).
    mem_emb = memory.embed_all()

    records = []
    poi_pending = []      # POIs that missed Job A -> go to Job B
    poi_pending_meta = []

    for exp, title, g in zip(experiences, clean, gates):
        city = g.get("city") or "Unknown"
        theme = g.get("theme") or ""
        typ = g.get("type")

        # 2) ROUTE
        if typ == "ACTIVITY":
            act = g.get("activity")
            cid = taxonomy.activity_collection_id(act, city)
            cname = taxonomy.activity_collection_name(act, city)
            if cid is None:
                # unknown activity key -> treat as new theme collection, review
                records.append(_rec(exp, "create_new", _slug(theme or title), False,
                                    f"{(theme or title).title()} - {city}", city, theme,
                                    0.5, f"ACTIVITY '{act}' has no ID mapping; review", True))
            elif memory.bucket_exists(cid):
                # the "<ID> - City" bucket already exists -> assign to it
                records.append(_rec(exp, "assign_subcategory", cid, False, cname, city,
                                    theme, 0.92,
                                    f"activity={act} -> existing bucket {cid}", False))
            else:
                # bucket doesn't exist yet -> still route by ID, flag as new bucket
                records.append(_rec(exp, "assign_subcategory", cid, True, cname, city,
                                    theme, 0.85,
                                    f"activity={act} -> new bucket {cid}", False))
            continue

        if typ == "DAY_TRIP":
            kind = g.get("daytrip_kind")
            if kind == "city_tour":
                cid = f"1010 - {city}"
                exists = memory.bucket_exists(cid)
                records.append(_rec(exp, "assign_subcategory", cid, not exists,
                                    f"Guided Tours - {city}", city, theme,
                                    0.88 if exists else 0.82,
                                    f"day trip = city tour -> {cid}"
                                    + ("" if exists else " (new bucket)"), False))
            else:
                # point_to_point / complex -> NEW named umbrella collection
                name = _daytrip_name(g)
                records.append(_rec(exp, "create_new", _slug(name), True, name, city,
                                    theme, 0.7,
                                    f"day trip ({kind}) -> new umbrella collection", True))
            continue

        # typ == "POI"  -> JOB A
        landmark = g.get("landmark") or clean_or_title(title)
        decided = _job_a(exp, landmark, city, theme, memory, mem_emb, records)
        if not decided:
            poi_pending.append(landmark)
            poi_pending_meta.append((exp, city, theme, landmark))

    # 3) JOB B — cluster the POIs that found no existing home.
    if poi_pending:
        _job_b(poi_pending, poi_pending_meta, records)

    return records


def _job_a(exp, landmark, city, theme, memory, mem_emb, records):
    """Try to assign a POI to an existing collection. Prefer same-city
    candidates; if the city has none, fall back to the whole market but require
    a HIGHER similarity (a cross-city match must be near-certain to be the same
    POI, e.g. 'Hobbiton' filed under Auckland vs gate-city Matamata).
    Returns True if assigned, False if it should fall to Job B."""
    cand_idx, used_fallback = memory.candidates_in_city(city)
    if not cand_idx or mem_emb is None:
        return False
    q = np.asarray(llm.embed([landmark]), dtype=np.float32)
    sims = cosine_matrix(q, mem_emb[cand_idx])[0]
    best_local = int(np.argmax(sims))
    best_idx = cand_idx[best_local]
    score = float(sims[best_local])
    name = memory.entries[best_idx]["name"]
    matched_city = memory.entries[best_idx]["city"]

    # Cross-city (fallback) matches must clear a stricter bar so we don't merge
    # a POI into a same-named collection in a different city by mistake.
    high = ASSIGN_HIGH if not used_fallback else CROSS_CITY_HIGH

    if score >= high:
        note = (f"POI match (high) sim={score:.2f}"
                + (f"; cross-city -> filed under {matched_city}" if used_fallback else ""))
        records.append(_rec(exp, "assign_existing", _slug(name), False, name, city,
                            theme, round(score, 3), note,
                            used_fallback))  # review any cross-city assignment
        return True
    if not used_fallback and score >= ASSIGN_LOW:
        records.append(_rec(exp, "assign_existing", _slug(name), False, name, city,
                            theme, round(score, 3),
                            f"POI match (mid, review) sim={score:.2f}", True))
        return True
    return False


def _job_b(landmarks, meta, records):
    """Cluster unmatched POIs by city+theme similarity; propose one new
    collection per cluster (any size, including 1). All review-flagged."""
    embs = np.asarray(llm.embed(landmarks), dtype=np.float32)
    n = len(landmarks)
    assigned = [-1] * n
    clusters = []  # list of (rep_name, [member indices])

    for i in range(n):
        if assigned[i] != -1:
            continue
        exp_i, city_i, theme_i, lm_i = meta[i]
        members = [i]
        assigned[i] = len(clusters)
        for j in range(i + 1, n):
            if assigned[j] != -1:
                continue
            _, city_j, _, _ = meta[j]
            if norm(city_j) != norm(city_i):      # city is a hard boundary
                continue
            sim = float(cosine_matrix(embs[i:i + 1], embs[j:j + 1])[0][0])
            if sim >= CLUSTER_SIM:
                assigned[j] = len(clusters)
                members.append(j)
        clusters.append((lm_i, members))

    for rep_name, members in clusters:
        exp0, city0, theme0, lm0 = meta[members[0]]
        coll_name = _propose_poi_name(rep_name, city0)
        for m in members:
            exp_m, city_m, theme_m, lm_m = meta[m]
            records.append(_rec(exp_m, "create_new", _slug(coll_name), True, coll_name,
                                city_m, theme_m, 0.6,
                                f"JOB B: new POI collection (cluster of {len(members)})",
                                True))


# --- naming helpers --------------------------------------------------------
def _daytrip_name(g):
    """Name a day-trip umbrella per the GM's conventions:
       single origin -> '<Origin> to <Destination> Tours'
       multi-origin / famous destination -> '<Destination> Tours'."""
    origin = (g.get("origin") or "").strip()
    dest = (g.get("destination") or g.get("theme") or "").strip()
    dest = dest.title() if dest else "Day Trip"
    if origin:
        return f"{origin.title()} to {dest} Tours"
    return f"{dest} Tours"


def _propose_poi_name(landmark, city):
    """A clean proposed collection name for a new POI cluster."""
    lm = (landmark or "").strip().title()
    if not lm:
        return f"{city} Attractions"
    # Mirror existing CE style: many are just the landmark, some add 'Tickets'/'Tours'.
    return lm


def clean_or_title(title):
    return re.sub(r"\s+", " ", (title or "").strip()).title()


def _slug(name):
    return norm(name)


def _rec(exp, decision, collection_id, is_new, collection_name, city, theme,
         confidence, reason, needs_review):
    return {
        "experience_id": exp.get("experience_id", ""),
        "experience_name": exp.get("experience_name", ""),
        "primary_city": city,
        "theme": theme,
        "decision": decision,
        "collection_id": collection_id,
        "collection_name": collection_name,
        "is_new": is_new,
        "confidence": confidence,
        "needs_review": needs_review,
        "reason": reason,
        "link": exp.get("link", ""),
        "correct_collection": "",   # <- blank: fill this to give feedback
        "notes": "",                # <- blank: free-text feedback
    }
