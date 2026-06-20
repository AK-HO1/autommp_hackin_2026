"""Assortment step. For ONE CE: assemble the assortment-builder prompt + the CE's
inputs (listings, deep research, keyword clusters), call the configured model, and
map the returned JSON into a CEAssortment (which output.py renders to the
ExperienceOS CSV).

Provider/model are config (pipeline.llm): set LLM_PROVIDER/LLM_MODEL + key, e.g.
    export LLM_PROVIDER=openai
    export LLM_MODEL=<your openai model id>
    export OPENAI_API_KEY=...        # set in your shell, never in code
"""
from __future__ import annotations
import os
from .llm import complete
from .schema import (CEAssortment, Experience, Variant, SupplierRef, BenchItem,
                     ListingRecord)

SKILL_DIR = os.path.join(os.path.dirname(__file__), "..", "skills", "assortment-builder")


def load_assort_prompt() -> str:
    return open(os.path.join(SKILL_DIR, "SKILL.md"), encoding="utf-8").read()


def _listing_line(l: ListingRecord) -> str:
    incl = f" | inclusions: {'; '.join(l.inclusions[:6])}" if l.inclusions else ""
    return (f"- {l.title} | supplier: {l.sp_name} | product_id: {l.sp_product_id} "
            f"| price: {l.price} {l.currency or ''}{incl}")


def assort_ce(ce_name: str, listings: list[ListingRecord],
              research_text: str = "", keyword_text: str = "") -> CEAssortment:
    """Run the assortment model for one CE and return a populated CEAssortment."""
    system = load_assort_prompt()
    user = (
        f"CE: {ce_name}\n\n"
        f"=== LISTINGS (the supply to assort) ===\n"
        + "\n".join(_listing_line(l) for l in listings)
        + f"\n\n=== DEEP RESEARCH ===\n{research_text[:12000]}\n"
        + f"\n=== KEYWORD CLUSTERS ===\n{keyword_text[:4000]}\n"
        + "\nReturn ONLY the JSON object specified in the skill."
    )
    data = complete(system, user, as_json=True)
    return map_to_assortment(data, ce_name)


def map_to_assortment(data: dict, ce_name_fallback: str = "") -> CEAssortment:
    """Deterministically map the model JSON into the dataclass schema."""
    def sup(s):
        return SupplierRef(sp_name=s.get("sp_name", ""),
                           product_ids=[str(x) for x in s.get("product_ids", [])],
                           note=s.get("note"))

    def var(v):
        return Variant(
            rank=int(v.get("rank", 0)), name=v.get("name", ""),
            content=v.get("content", ""), product_name=v.get("product_name", ""),
            suppliers=[sup(s) for s in v.get("suppliers", [])],
            comments=v.get("comments", ""),
            confidence=v.get("confidence"))

    exps = [Experience(rank=int(e.get("rank", 0)), name=e.get("name", ""),
                       variants=[var(v) for v in e.get("variants", [])])
            for e in data.get("experiences", [])]
    bench = [BenchItem(product=b.get("product", ""),
                       indicative_price=b.get("indicative_price", ""),
                       where_it_would_sit=b.get("where_it_would_sit", ""),
                       why_bench=b.get("why_bench", ""))
             for b in data.get("bench", [])]
    return CEAssortment(ce_name=data.get("ce_name") or ce_name_fallback,
                        experiences=exps, bench=bench, notes=data.get("notes", {}))
