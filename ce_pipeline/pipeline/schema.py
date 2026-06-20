"""Canonical data models for the unmanaged-CE consolidation pipeline.

The shapes here are the contract every stage reads/writes. They are built
backwards from the ExperienceOS output format (Exp-Variant_Assortment_output_format.xlsx):

    CE (Combined Entity)
      -> Experience (TGID, ranked)
           -> Variant (TID, ranked)
                -> SupplierRef[]  (multi-vendored: several SP SKUs per variant)

Kept dependency-free (stdlib dataclasses) so it runs anywhere in a hackathon.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional
import json


# ---------- INPUT: one normalized supplier listing pulled from Columbus ----------
@dataclass
class ListingRecord:
    listing_id: str                 # stable id for this raw listing
    sp_name: str                    # supplier / vendor name (e.g. "GlobalTix")
    sp_product_id: str              # supplier's own SKU id (e.g. "290941")
    title: str
    description: str = ""
    city: str = ""
    poi: Optional[str] = None       # primary point of interest, if detectable
    lat: Optional[float] = None
    lng: Optional[float] = None
    category_hint: Optional[str] = None
    duration_min: Optional[int] = None
    inclusions: list[str] = field(default_factory=list)
    pax_types: list[str] = field(default_factory=list)   # Adult/Child/Senior...
    price: Optional[float] = None
    currency: Optional[str] = None
    lang: Optional[str] = None
    url: Optional[str] = None
    raw: dict = field(default_factory=dict)              # untouched source payload


# ---------- INTERMEDIATE: a candidate cluster of near-identical listings ----------
@dataclass
class Cluster:
    cluster_id: str
    listing_ids: list[str]
    label: Optional[str] = None     # human-readable guess at what this cluster is
    signal: dict = field(default_factory=dict)  # debug: poi, embedding centroid, etc.


# ---------- OUTPUT building blocks (mirror the 3 sheets of the format file) ----------
@dataclass
class SupplierRef:
    """One supplier mapped to a variant. Several of these = multi-vendored."""
    sp_name: str
    product_ids: list[str] = field(default_factory=list)
    note: Optional[str] = None      # e.g. "single-sourced", "primary"


@dataclass
class Variant:                       # a TID / option on the booking page
    rank: int
    name: str
    content: str = ""               # the "Variant Content" description column
    product_name: str = ""          # primary supplier SKU reference (display)
    suppliers: list[SupplierRef] = field(default_factory=list)
    comments: str = ""              # rationale (kept for review + audit)
    confidence: Optional[float] = None
    is_new: bool = False            # "shaded gold = new vs previous version"


@dataclass
class Experience:                    # a TGID
    rank: int
    name: str
    variants: list[Variant] = field(default_factory=list)


@dataclass
class BenchItem:                     # "Cross-sell Bench" sheet row
    product: str
    indicative_price: str = ""
    where_it_would_sit: str = ""
    why_bench: str = ""


@dataclass
class CEAssortment:                  # the full result for ONE Combined Entity
    ce_name: str
    ce_id: Optional[str] = None      # existing CE id, or None if proposed-new
    ce_type: Optional[str] = None    # POI / DAY_TRIP / GENERIC
    is_new_ce: bool = False
    experiences: list[Experience] = field(default_factory=list)
    bench: list[BenchItem] = field(default_factory=list)
    notes: dict = field(default_factory=dict)   # Logic & Notes content
    confidence: Optional[float] = None           # CE-level confidence for gating

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)


# Routing buckets used by the confidence gate (see stages/route.py later)
AUTO_LIST = "auto_list"
REVIEW = "review_queue"
SUPPRESS_MANAGED_OVERLAP = "suppress_managed_overlap"
