"""End-to-end orchestrator for the unmanaged-CE consolidation pipeline.

    CSV (a city's supplier listings)
      -> [1] categorize   collection-builder v4 (LLM POI-gate + embedding match)
      -> [2] group        experiences -> Combined Entities (CEs)
      -> [3] assort       assortment-builder skill per CE   (LLM)
      -> [4] route        confidence gate (auto-list vs review)
      -> [5] output       experienceos_upload.csv  (+ review_queue.csv)

collection-builder v4 requires OPENAI_API_KEY + network (no offline mode).
Set your key (and optionally CB_GATE_MODEL / CB_EMBED_MODEL) before running.
Assortment uses its own model config (LLM_PROVIDER / LLM_MODEL in pipeline.llm).

Examples:
    # categorize only (writes decisions.csv + grouping)
    python run.py --city "Hong Kong" --input feed.csv --ce-list skills/collection-builder/sample_data_ce_list_global.csv
    # full pipeline (categorize -> assort -> ExperienceOS CSV)
    python run.py --city "Hong Kong" --input feed.csv --assort --review-xlsx
"""
from __future__ import annotations
import argparse, csv, json, os, subprocess, sys
from collections import defaultdict

try:
    from dotenv import load_dotenv; load_dotenv()
except Exception:
    pass

from pipeline.stages import stages
from pipeline.stages.output import write_csv, write_review_xlsx
from pipeline.schema import CEAssortment, AUTO_LIST, REVIEW, SUPPRESS_MANAGED_OVERLAP

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.join(HERE, "skills", "collection-builder")
ENGINE = os.path.join(SKILL, "collection_builder", "run.py")
DEFAULT_CE_LIST = os.path.join(SKILL, "sample_data_ce_list_global.csv")


def _bool(v): return str(v).strip().lower() in ("true", "1", "yes", "y")
def _float(v):
    try: return float(v)
    except (TypeError, ValueError): return 0.0


def load_rows(path, city):
    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if city:
        rows = [r for r in rows if str(r.get("City", r.get("city", ""))).strip() == city]
    return rows


def categorize(rows, out_dir, ce_list, market):
    """Run collection-builder v4 -> per-experience decision records.
    Writes a feed CSV with the column names v4 expects, calls its CLI, and reads
    back decisions.csv (coercing bool/float)."""
    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("FATAL: collection-builder v4 needs OPENAI_API_KEY (LLM gate + "
                 "embeddings). Set it in your shell or .env and retry.")
    feed = os.path.join(out_dir, "_feed.csv")
    with open(feed, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["experience_id", "experience_name", "link"])
        w.writeheader()
        for r in rows:                       # map our Columbus columns -> v4 feed columns
            w.writerow({"experience_id": r.get("Product ID", r.get("experience_id", "")),
                        "experience_name": r.get("Name", r.get("experience_name", "")),
                        "link": r.get("Link", r.get("link", ""))})
    decisions = os.path.join(out_dir, "decisions.csv")
    cmd = [sys.executable, ENGINE, "--feed", feed, "--ce-list", ce_list, "--out", decisions]
    if market:
        cmd += ["--market", market]
    subprocess.run(cmd, check=True)
    with open(decisions, encoding="utf-8-sig") as f:
        records = list(csv.DictReader(f))
    for r in records:                        # normalize types for downstream use
        r["is_new"] = _bool(r.get("is_new"))
        r["needs_review"] = _bool(r.get("needs_review"))
        r["confidence"] = _float(r.get("confidence"))
    print(f"[categorize] {len(records)} decisions "
          f"({sum(r['needs_review'] for r in records)} need review)")
    return records


def run(city, input_path, out_dir, ce_list, market, managed_path, do_assort,
        inputs_dir, review_xlsx, conf_threshold):
    os.makedirs(out_dir, exist_ok=True)
    rows = load_rows(input_path, city)
    listings = stages.normalize(rows)
    by_id = {l.listing_id: l for l in listings}
    print(f"[ingest] {len(listings)} listings" + (f" in {city}" if city else ""))

    records = categorize(rows, out_dir, ce_list, market or city)   # [1]

    groups = defaultdict(list)                                     # [2] group -> CEs
    for r in records:
        groups[(str(r.get("collection_id")), r.get("collection_name", ""))].append(r)
    print(f"[group] {len(groups)} combined entities")

    managed = set(json.load(open(managed_path))) if managed_path and os.path.exists(managed_path) else set()
    auto, review = [], []
    for (cid, cname), recs in groups.items():
        ce = CEAssortment(ce_name=cname, ce_id=cid,
                          is_new_ce=any(r["is_new"] for r in recs),
                          confidence=min(r["confidence"] for r in recs))
        members = [by_id[r["experience_id"]] for r in recs if r.get("experience_id") in by_id]
        if do_assort:                                              # [3] assort (LLM)
            research, keyword = _load_ce_inputs(inputs_dir, cid)
            ce = stages.assort(ce, members, research, keyword)
            ce.ce_id, ce.is_new_ce = cid, any(r["is_new"] for r in recs)
        decision = stages.route(ce, managed, conf_threshold)       # [4] route
        if decision == AUTO_LIST: auto.append(ce)
        elif decision == REVIEW: review.append(ce)

    if do_assort:                                                  # [5] output
        n = write_csv(auto, os.path.join(out_dir, "experienceos_upload.csv"))
        print(f"[output] {len(auto)} CEs auto-listed -> experienceos_upload.csv ({n} rows)")
        if review:
            write_csv(review, os.path.join(out_dir, "review_queue.csv"))
            print(f"[output] {len(review)} CEs -> review_queue.csv")
        if review_xlsx:
            write_review_xlsx(auto + review, os.path.join(out_dir, "assortment_review.xlsx"))
    else:
        _write_grouping(groups, os.path.join(out_dir, "categorized_collections.csv"))
        print("[output] grouping -> categorized_collections.csv "
              "(decisions.csv has the full per-experience detail; add --assort for the upload)")


def _load_ce_inputs(inputs_dir, cid):
    research = keyword = ""
    if inputs_dir:
        d = os.path.join(inputs_dir, str(cid))
        for fn in (os.listdir(d) if os.path.isdir(d) else []):
            p = os.path.join(d, fn)
            if fn.lower().startswith("research"):
                research = open(p, encoding="utf-8", errors="ignore").read()
            elif fn.lower().startswith("keyword"):
                keyword = open(p, encoding="utf-8", errors="ignore").read()
    return research, keyword


def _write_grouping(groups, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["collection_id", "collection_name", "n_experiences", "is_new", "min_confidence"])
        for (cid, cname), recs in sorted(groups.items(), key=lambda x: -len(x[1])):
            w.writerow([cid, cname, len(recs), any(r["is_new"] for r in recs),
                        round(min(r["confidence"] for r in recs), 2)])


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--city")
    p.add_argument("--input", required=True, help="supplier-listings CSV")
    p.add_argument("--ce-list", default=DEFAULT_CE_LIST,
                   help="existing collections CSV (default: bundled global sample)")
    p.add_argument("--market", help="comma-separated cities to scope the CE list "
                                     "(defaults to --city if given)")
    p.add_argument("--out", default="out")
    p.add_argument("--managed", help="JSON list of Managed/Lite CE ids to suppress")
    p.add_argument("--inputs-dir", default="inputs",
                   help="per-CE research/keyword files at <dir>/<collection_id>/")
    p.add_argument("--assort", action="store_true", help="run assortment per CE (LLM)")
    p.add_argument("--review-xlsx", action="store_true")
    p.add_argument("--conf-threshold", type=float, default=0.7)
    a = p.parse_args()
    run(a.city, a.input, a.out, a.ce_list, a.market, a.managed, a.assort,
        a.inputs_dir, a.review_xlsx, a.conf_threshold)
