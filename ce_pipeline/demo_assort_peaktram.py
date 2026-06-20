"""Peak Tram (CE 2067) assortment — produced in-session by applying the
assortment-builder skill to the Trip.com supply + deep research. This is the
SAME JSON shape pipeline.assort_llm would get back from OpenAI; here it's filled
by Claude-in-session so you get a real output with no key. Maps -> CEAssortment
-> ExperienceOS CSV + reviewer xlsx.
"""
from pipeline.assort_llm import map_to_assortment
from pipeline.stages.output import write_csv, write_review_xlsx

TRIP = "Trip.com"; PID = ["113164"]

assortment = {
  "ce_name": "Hong Kong Peak Tram & Sky Terrace 428 Tickets",
  "experiences": [
    {"rank": 1, "name": "Hong Kong Peak Tram & Sky Terrace 428 Tickets",
     "variants": [
       {"rank": 1, "name": "Round-Trip Peak Tram + Sky Terrace 428",
        "content": "Round-trip ride on the historic Peak Tram plus admission to Sky Terrace 428, Hong Kong's highest open-air viewing deck. Valid on your chosen date.",
        "product_name": "Trip.com - Round-trip Peak Tram + Sky Terrace 428 (from JPY 3,170)",
        "suppliers": [{"sp_name": TRIP, "product_ids": PID, "note": "lowest of Specified/Flex date"}],
        "comments": "RANK 1 = core, highest-demand product and the top search term ('Hong Kong Peak Tram tickets'). Specified-date (JPY 3,273) and Flex-date (JPY 3,170) are practically identical to the guest, so collapsed into one variant showing the lower price instead of splitting the decision. Pax = Adult/Child/Senior; the '2 people' fare (JPY 6,586) is exactly 2x adult, not cheaper, so excluded.",
        "confidence": 0.9},
       {"rank": 2, "name": "Skip-the-Line Round-Trip + Sky Terrace 428 (Ruby Express)",
        "content": "The same round-trip tram + Sky Terrace 428, with Ruby Pass priority boarding so you skip the main queue.",
        "product_name": "Trip.com - Round-trip Peak Tram + Sky Terrace 428 + Ruby Pass (JPY 6,156)",
        "suppliers": [{"sp_name": TRIP, "product_ids": PID}],
        "comments": "RANK 2 / PRIMARY UPSELL. Skip-the-line is the one thing guests are unsure about and can be convinced on: research flags 1-2 hour queues as the #1 pain point and praises the Ruby pass ('well worth it'). Upsell kept inside the same experience as a variant, per the playbook - not a separate listing.",
        "confidence": 0.85},
       {"rank": 3, "name": "One-Way Peak Tram + Sky Terrace 428",
        "content": "One-way tram ascent + Sky Terrace 428 - for guests who plan to walk the Peak Circle Walk or take Bus 15 back down.",
        "product_name": "Trip.com - One-way Peak Tram + Sky Terrace 428 (from JPY 2,536)",
        "suppliers": [{"sp_name": TRIP, "product_ids": PID}],
        "comments": "RANK 3. Round-trip vs one-way is a genuine decision vector (how you descend), so it's a visible variant, not a hidden option. Lower demand than round-trip, hence last.",
        "confidence": 0.8},
     ]},
    {"rank": 2, "name": "Hong Kong Peak Tram Tickets",
     "variants": [
       {"rank": 1, "name": "Round-Trip Peak Tram (Tram Only)",
        "content": "A round-trip ride on the historic Peak Tram funicular. Sky Terrace 428 is not included.",
        "product_name": "Trip.com - Round-trip Peak Tram (JPY 2,373)",
        "suppliers": [{"sp_name": TRIP, "product_ids": PID}],
        "comments": "Distinct search intent ('Peak Tram tickets', 'Peak Tram price') - some guests want only the ride. Its own experience so it's directly findable; Sky Terrace deliberately excluded and that's stated up front.",
        "confidence": 0.82},
       {"rank": 2, "name": "One-Way Peak Tram (Tram Only)",
        "content": "A one-way ride on the Peak Tram, ascent or descent.",
        "product_name": "Trip.com - One-way Peak Tram (JPY 1,677)",
        "suppliers": [{"sp_name": TRIP, "product_ids": PID}],
        "comments": "One-way vs round-trip decision vector. '2 people' fare (JPY 3,354) is exactly 2x adult, not cheaper, so excluded from pax.",
        "confidence": 0.8},
     ]},
    {"rank": 3, "name": "Hong Kong Peak Tram, Sky Terrace 428 & Madame Tussauds Combo",
     "variants": [
       {"rank": 1, "name": "Round-Trip Peak Tram + Sky Terrace 428 + Madame Tussauds",
        "content": "Round-trip tram + Sky Terrace 428 + entry to Madame Tussauds, all in the Peak Tower (0-5 min between them).",
        "product_name": "Trip.com - RT Peak Tram + Sky Terrace 428 + Madame Tussauds (JPY 6,913)",
        "suppliers": [{"sp_name": TRIP, "product_ids": PID}],
        "comments": "'Peak Tram Madame Tussauds combo' is a named keyword cluster in the research, so it's surfaced as its own discoverable experience rather than buried as an add-on.",
        "confidence": 0.78},
       {"rank": 2, "name": "Round-Trip Peak Tram + Madame Tussauds (No Sky Terrace)",
        "content": "Round-trip tram + Madame Tussauds, without the Sky Terrace deck - a lower-priced combo.",
        "product_name": "Trip.com - RT Peak Tram + Madame Tussauds (JPY 5,686)",
        "suppliers": [{"sp_name": TRIP, "product_ids": PID}],
        "comments": "The 'with/without Sky Terrace' decision vector for Madame Tussauds visitors. Cheaper, hence offered as the second variant.",
        "confidence": 0.74},
     ]},
  ],
  "bench": [
    {"product": "RT Peak Tram + Sky Terrace 428 + Hong Kong Observation Wheel",
     "indicative_price": "JPY 3,539", "where_it_would_sit": "Exp 1 cross-sell",
     "why_bench": "Cheap attraction add (~+370 over base combo); cross-sell, not a core variant."},
    {"product": "RT Peak Tram + Sky Terrace 428 + Monopoly Dreams",
     "indicative_price": "JPY 6,034", "where_it_would_sit": "Exp 3",
     "why_bench": "Niche attraction add-on; lower demand."},
    {"product": "RT Peak Tram + Sky Terrace 428 + dining (Petit Jardin / Bakehouse / Snack Baby / Afternoon Tea)",
     "indicative_price": "JPY 3,068-4,205", "where_it_would_sit": "Exp 1 cross-sell",
     "why_bench": "Dining upsells; benched to keep the core experience tight (comprehensiveness via bench, not variant bloat)."},
    {"product": "Sky Terrace 428 Only", "indicative_price": "JPY 1,432",
     "where_it_would_sit": "standalone", "why_bench": "Terrace-only without tram; very low intent vs the combo."},
    {"product": "RT Peak Tram + Sky Terrace 428 (Night) + HK City Sightseeing Night Pass",
     "indicative_price": "JPY 5,154", "where_it_would_sit": "Exp 1",
     "why_bench": "Night-session bundle; seasonal / niche."},
  ],
  "notes": {
    "thesis": "Three experiences split by genuine guest decision-vectors - the core combo, tram-only, and the Madame Tussauds combo - each a distinct search intent. Add-ons (express, dining, extra attractions) are upsells/cross-sells inside variants or on the bench, not separate experiences.",
    "pax_rule": "Adult/Child/Senior only. '2 people' fares were exactly 2x the adult price (not cheaper), so excluded.",
    "multi_vendoring": "Only Trip.com supply was provided, so variants are single-sourced. With GlobalTix/BeMyGuest feeds added, identical products collapse into the same variant showing the lowest price.",
    "supply_gaps": "No Trip.com supply for guided/small-group Peak tours or a sunrise/early-morning slot - both are personas the research calls out. Onboard next.",
    "data_caveat": "Single-supplier (Trip.com ANT) feed; prices in JPY as listed on 2026-06.",
  },
}

import os
os.makedirs("out", exist_ok=True)
ce = map_to_assortment(assortment)
n = write_csv([ce], "out/peaktram_experienceos_upload.csv")
write_review_xlsx([ce], "out/peaktram_assortment_review.xlsx")
print(f"CSV rows: {n}")
print(open("out/peaktram_experienceos_upload.csv").read())
