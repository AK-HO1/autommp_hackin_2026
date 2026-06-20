"""Pipeline stages. Each is a pure function with a typed signature, so it can be
built and tested in isolation, then chained by run.py.

Status:
  output.py        DONE (matches ExperienceOS format)
  ingest           TODO  -- needs a Columbus JSON sample to map real fields
  precluster       TODO  -- cheap embeddings/blocking, no LLM
  categorize       TODO  -- wraps your EXISTING categorization prompt (CE assignment)
  assort           TODO  -- wraps your EXISTING entity-resolution/assortment prompt
  route            TODO  -- confidence gate + Managed/Lite overlap check
"""
from __future__ import annotations
from ..schema import ListingRecord, Cluster, CEAssortment


# ---------------------------------------------------------------- 1. INGEST
def fetch_columbus(city: str) -> list[dict]:
    """Call the Columbus API for all unmanaged supplier listings in `city`.
    Returns raw payloads. (Swap for a local JSON loader while developing.)"""
    raise NotImplementedError("Wire Columbus API / local JSON loader here")


def _split_bullets(text: str) -> list[str]:
    if not text:
        return []
    import re
    parts = re.split(r"\n|(?:^|\s)-\s", text)
    return [p.strip(" -\u2022\t") for p in parts if p and p.strip(" -\u2022\t")]


def normalize(raw_listings: list[dict]) -> list[ListingRecord]:
    """Map raw export rows -> ListingRecord. INPUT CONTRACT for the export
    (Name, Product ID, Supplier, City, Retail Price, Currency, RMS) plus the
    content columns from the screenshot (Inclusions/Exclusions/Highlights/KBYG)
    when present. Unknown columns are preserved in .raw."""
    out = []
    for r in raw_listings:
        g = lambda *keys: next((str(r[k]).strip() for k in keys
                                if k in r and str(r[k]).strip()), "")
        price = g("Retail Price", "retail_price")
        out.append(ListingRecord(
            listing_id=g("Product ID", "product_id") or g("Name"),
            sp_name=g("Supplier") or g("RMS") or "UNKNOWN",   # Supplier blank -> RMS
            sp_product_id=g("Product ID", "product_id"),
            title=g("Name", "name"),
            description=g("Highlights", "Description", "description"),
            city=g("City", "city"),
            category_hint=g("Category", "Subcategory"),
            inclusions=_split_bullets(g("Inclusions")),
            price=float(price) if price.replace(".", "", 1).isdigit() else None,
            currency=g("Currency") or None,
            raw={**r, "rms": g("RMS"),
                 "exclusions": _split_bullets(g("Exclusions")),
                 "kbyg": _split_bullets(g("Know before your go", "Know Before You Go"))},
        ))
    return out


# ------------------------------------------------------------- 2. PRE-CLUSTER
_GENERIC = {"ticket", "tickets", "tour", "tours", "pass", "combo", "city",
            "entry", "admission", "the", "of", "in", "to", "and", "with",
            "save", "guided", "english", "hop", "on", "off", "experience"}


def _key_tokens(title: str) -> set[str]:
    import re
    toks = re.findall(r"[A-Za-z][A-Za-z'&]+", title.lower())
    return {t for t in toks if t not in _GENERIC and len(t) > 2}


def precluster(listings: list[ListingRecord]) -> list[Cluster]:
    """v0 candidate clustering: blocking by city, then union-find merge of
    listings that share a significant (non-generic) title token. Dependency-free
    so it runs offline today. UPGRADE PATH: replace the token-overlap test with
    embedding cosine-similarity + geo proximity; keep the union-find structure.
    Produces candidate sets only -- no same/variant/distinct decisions (that's assort).
    """
    parent: dict[str, str] = {l.listing_id: l.listing_id for l in listings}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        parent[find(a)] = find(b)

    # block by city, then connect within a city by shared key token
    from collections import defaultdict
    by_city = defaultdict(list)
    for l in listings:
        by_city[l.city].append(l)
    for city_name, city_listings in by_city.items():
        stop = _GENERIC | set(city_name.lower().split())
        tok_index = defaultdict(list)
        for l in city_listings:
            for t in (_key_tokens(l.title) - stop):
                tok_index[t].append(l.listing_id)
        for ids in tok_index.values():
            for other in ids[1:]:
                union(ids[0], other)

    groups = defaultdict(list)
    for l in listings:
        groups[find(l.listing_id)].append(l)

    clusters = []
    for i, (root, members) in enumerate(sorted(groups.items())):
        from collections import Counter
        toks = Counter(t for m in members for t in _key_tokens(m.title))
        label = " ".join(w for w, _ in toks.most_common(2)) or members[0].title
        clusters.append(Cluster(
            cluster_id=f"cl_{i:04d}",
            listing_ids=[m.listing_id for m in members],
            label=label,
            signal={"city": members[0].city, "size": len(members)},
        ))
    return clusters


# -------------------------------------------------------------- 3. CATEGORIZE
def categorize(cluster: Cluster, listings: list[ListingRecord]) -> CEAssortment:
    """Assign a cluster to a Combined Entity.
    >>> PLUG IN your existing categorization prompt here. <<<
    Responsibilities:
      - map to an EXISTING CE (collection / '<subcat> - <city>') when confident
      - else propose a NEW CE (set is_new_ce=True), with ce_type POI/DAY_TRIP/GENERIC
      - return a CEAssortment shell (no experiences/variants yet) + ce-level confidence
    Implementation: Anthropic API call, strict JSON output, few-shot seeded from
    the Japan/Klook golden output. (See skills/categorize.md for the contract.)
    """
    raise NotImplementedError("Wrap existing categorization prompt")


# ------------------------------------------------------------------ 4. ASSORT
def assort(ce: CEAssortment, listings: list[ListingRecord],
           research_text: str = "", keyword_text: str = "") -> CEAssortment:
    """Entity resolution + assortment via the assortment-builder skill.
    Calls the configured model (pipeline.llm) and returns a populated CEAssortment.
    research_text / keyword_text are this CE's deep-research + keyword-cluster inputs."""
    from pipeline.assort_llm import assort_ce
    return assort_ce(ce.ce_name, listings, research_text, keyword_text)


# ------------------------------------------------------------------- 5. ROUTE
def route(ce: CEAssortment, managed_ce_index: set[str],
          conf_threshold: float = 0.7) -> str:
    """Confidence gate + boundary check. Returns AUTO_LIST / REVIEW /
    SUPPRESS_MANAGED_OVERLAP."""
    from ..schema import AUTO_LIST, REVIEW, SUPPRESS_MANAGED_OVERLAP
    key = str(ce.ce_id or ce.ce_name).lower()
    if key in {k.lower() for k in managed_ce_index}:
        return SUPPRESS_MANAGED_OVERLAP
    conf = ce.confidence if ce.confidence is not None else (
        min((v.confidence or 0) for e in ce.experiences for v in e.variants)
        if any(e.variants for e in ce.experiences) else 0)
    if ce.is_new_ce or conf < conf_threshold or not ce.experiences:
        return REVIEW
    return AUTO_LIST
