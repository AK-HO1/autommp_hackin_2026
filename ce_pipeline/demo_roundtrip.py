"""Demo: build a slice of the real Hong Kong Peak Tram CE and render outputs.
Proves the output stage matches the ExperienceOS format end-to-end."""
from pipeline.schema import CEAssortment, Experience, Variant, SupplierRef, BenchItem
from pipeline.stages.output import write_csv, write_review_xlsx

ce = CEAssortment(
    ce_name="Hong Kong Peak Tram & Sky Terrace 428",
    ce_id=2067, ce_type="POI", is_new_ce=False, confidence=0.91,
    experiences=[
        Experience(rank=1, name="Hong Kong Peak Tram & Sky Terrace 428", variants=[
            Variant(rank=1, name="Peak Tram Round Trip + Sky Terrace 428",
                    content="Round-trip ride on the historic Peak Tram + Sky Terrace 428 admission.",
                    product_name="GlobalTix 20037 - 'Special Combo (Round Trip)'",
                    suppliers=[SupplierRef("GlobalTix", ["290941","290947","279169"], "primary"),
                               SupplierRef("BeMyGuest", ["59324"])],
                    comments="RANK 1 = core, highest-demand product.", confidence=0.95),
            Variant(rank=2, name="Skip-the-Line Round Trip + Sky Terrace 428",
                    content="Same round-trip tram + Sky Terrace 428, with fast-track queue access.",
                    product_name="GlobalTix 20037 - 'Peak Tram Ruby Special'",
                    suppliers=[SupplierRef("GlobalTix", ["304141","280113"])],
                    comments="RANK 2 and the PRIMARY UPSELL. Queue jump.", confidence=0.88),
        ]),
        Experience(rank=4, name="Hong Kong Peak Tram Tickets", variants=[
            Variant(rank=1, name="Peak Tram Round Trip (tram only)",
                    content="A round-trip ride on the historic Peak Tram, tram only.",
                    product_name="Trip.com 113164 - 'Round-trip Peak Tram'",
                    suppliers=[SupplierRef("Trip.com", ["113164"], "single-sourced")],
                    comments="NEW TGID, RANK 4 (last). The honest tram-only option.",
                    confidence=0.72, is_new=True),
        ]),
    ],
    bench=[BenchItem("Round-trip + Sky Terrace 428 + Madame Tussauds", "JPY 3,539",
                     "Exp 1 cross-sell", "Cheap attraction add (~+370 over base).")],
    notes={"Thesis": "Four experiences, each <=3 variants, MECE on buyer intent.",
           "Supply gaps to onboard next": "No supply yet for guided small-group Peak tours."},
)

n = write_csv([ce], "out/experienceos_upload.csv")
write_review_xlsx([ce], "out/assortment_review.xlsx")
print(f"CSV rows written: {n}\n")
print(open("out/experienceos_upload.csv").read())
