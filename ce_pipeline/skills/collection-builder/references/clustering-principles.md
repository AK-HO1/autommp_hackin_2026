# Clustering Principles

How the engine decides which collection an experience belongs to — whether to
**assign it to an existing collection** or **create a new one**. These rules were
reverse-engineered from the 81 well-managed reference collections in
`reference_collections.md` (London Theatre Tickets, Broadway, Colosseum, Vatican
Museums, Eiffel Tower, Universal Studios Japan, Krakow→Auschwitz, and more).
Tune the engine's rule tables to a feed using this as the rationale; read it
before adapting rules for anything non-trivial.

These are decision principles for an automated pipeline, not a human tutorial.
Where a rule says "judgment call," that judgment is encoded in the rule tables and
backed by a confidence score: when the call is genuinely close, lower the
confidence and set `needs_review` rather than guessing silently.

## Table of contents
1. The mental model
2. The decision order (with stop conditions)
3. Tricky cases
4. Worked examples
5. Anti-patterns to avoid

---

## 1. The mental model

Cluster by **shopper intent**, not by surface text. Two listings belong in the
same collection when a traveler would consider them substitutes or companions
for the same trip decision. A person deciding to "do the Colosseum" weighs a
plain ticket, a guided arena tour, a VIP underground tour, a VR add-on, and a
Colosseum+Roman Forum combo against each other — so all of those are one
collection. The differences that feel large in the raw data (operator, tour
style, language, duration, price) are exactly the differences a collection is
meant to absorb.

Conversely, two listings that share words can still belong apart. "St. Peter's
Basilica" is its own collection even though it sits inside Vatican City and many
Vatican tours pass it — because travelers shop for it as a distinct landmark.
Proximity is not membership; **distinct iconic identity** is.

## 2. The decision order

For each experience, walk these in order and stop at the first that fits.

**(1) Iconic POI / landmark / attraction.**
A single, famous, named place is the strongest possible anchor. Monuments,
museums, palaces, towers, cathedrals, theme parks, stadiums, observation decks,
named parks and gardens, named natural wonders. If the title names such a place
and the experience is *about visiting it*, it joins that POI's collection.
- Size does not matter. A POI with a single product still gets its own
  collection (reference set includes size-1 collections like *Aquarabia Qiddiya
  City Tickets*). Iconic identity, not volume, justifies a collection.
- Add-ons and tour styles do not split it. Ticket, skip-the-line, guided,
  semi-private, private, VIP, by night, with a meal, by Segway, VR, audio guide
  — all the same POI collection.

**(2) Distinct theme / signature experience.**
A recognizable kind of experience travelers seek as its own category, not tied
to one building. In the reference set these are usually *city-anchored show or
activity themes*: **London Theatre Tickets**, **Broadway**, **Las Vegas Shows**,
**Hawaii Luaus**, **Iceland Hot Springs**, **Boston Whale Watching Cruises**.
The test: would a traveler search for the theme by name? If yes, and it's a
strong signature for that city, it earns a named theme collection. If it's just
"a generic instance of a category," send it to rule (4) instead.

**(3) Route / day-trip / activity-to-a-place.**
Defined by getting *from* a hub *to* a destination, or doing an activity at a
destination outside the home city. Anchor on the destination or the route.
Examples: **Krakow to Auschwitz Birkenau Tours**, **Niagara Falls (Canada)
Tours**, **Plitvice Lakes National Park Tours**, **Wieliczka Salt Mine**. Many
products bundle two destinations ("Auschwitz + Wieliczka Salt Mine in One
Day") — assign to the **primary/headline** destination (the one the trip is sold
on), and note the secondary.

**(4) Generic experience → category+city bucket.**
No distinctive POI or theme: a generic city highlights tour, a private car
charter, a hop-on-hop-off loop, a cooking class, a market food tour, a river
cruise, a spa visit, a craft workshop. These fold into a
`<Category or Subcategory ID> - <City>` collection (see `taxonomy.md`). This is
the catch-all that keeps the long tail organized without inventing hundreds of
one-off names.

A junk/test title is dropped before this point and never reaches a collection. A
blank title with no usable signal is emitted with `decision="needs_review"`,
`is_new=false`, and an empty collection — never forced into a bucket, because
there is nothing to name it after. A title that reaches (4) but matches no
keyword falls to the safest default bucket (`1010 - <City>`) with low confidence
and `needs_review=true`, so the review queue catches it.

### Assign-existing vs create-new, at every step

At steps (1)–(4) the same fork applies: once you have a candidate collection,
check the reference-collections memory (and the collections already minted in this
batch). **If it exists, assign to it** (`is_new=false`, reuse its id/name);
**only if nothing exists do you create** (`is_new=true`). Canonicalize the
candidate name first (alias + diacritic folding) so a POI that already has a
collection is recognized regardless of spelling or language, and so two
experiences implying the same new collection mint it once and both assign.

## 3. Tricky cases

**Combos (one product, two+ POIs).** Each product lives in exactly one
collection, so pick the **anchor POI** — the one the product is primarily sold
on (usually named first, or the bigger draw). "Combo: Eiffel Tower Summit +
Versailles" → Eiffel Tower. "Combo: Colosseum + Vatican Museums Guided Tour" →
whichever is the headline; if genuinely co-equal, default to the first-named and
flag it. Don't create a "X + Y" collection.

**Sub-attractions and bundled sites.** Places routinely sold *as part of*
visiting a bigger POI roll up into the parent. Roman Forum & Palatine Hill ride
along with **Colosseum**; the Sistine Chapel rides with **Vatican Museums**.
But a sub-site that has its own strong identity and its own dedicated products
becomes its own collection (St. Peter's Basilica, Wieliczka Salt Mine).
Judgment call: does it have a standalone shopper identity and its own listings?
If yes → own collection; if it's only ever an add-on → roll up.

**Near-duplicate / same-named POIs.** Disambiguate explicitly, by country or
qualifier, exactly as the reference set does: *Niagara Falls (Canada) Tours* vs
*Niagara Falls (US) Tours*; *Universal Studios Japan / Singapore / Orlando /
Hollywood* are four separate collections, one per location.

**Language variants.** Italian/Spanish/French/Korean titles describing the same
POI cluster together. "Accesso prioritario: visita guidata della Città del
Vaticano" and "El Vaticano y Audiencia Papal" both → Vatican Museums.

**Theme vs category+city — where's the line?** Make a *named* theme collection
only when the theme is a strong, searchable signature (London Theatre, Vegas
Shows, Hawaii Luaus). For ordinary instances of a category, use the `<ID> - City`
bucket. When unsure, prefer the category+city bucket — it's reversible and keeps
the namespace clean; you can always promote a bucket to a named theme later if
it grows a clear identity.

**A "tour" that merely passes a POI.** If the POI is incidental (a city
sightseeing tour that drives past the Eiffel Tower without entry), it's a
generic city tour → category+city, not the POI collection. Membership requires
the experience to be *about* the POI.

## 4. Worked examples

| Experience title | Collection | Why |
|---|---|---|
| Colosseum Arena & Roman Forum Small-Group Guided Tour | **Colosseum** | POI; Forum rolls up |
| Colosseum Access with Virtual Reality Experience | **Colosseum** | add-on doesn't split |
| Combo: Colosseum + Vatican Museums Pass | **Vatican Museums** (anchor) | combo → one anchor, flag other |
| El Vaticano y Audiencia Papal – Tour a pie | **Vatican Museums** | language variant |
| Dinner at the Eiffel Tower's Madame Brasserie | **Eiffel Tower Tickets** | experience is about the POI |
| From Krakow: Auschwitz-Birkenau & Wieliczka in One Day | **Krakow to Auschwitz Birkenau Tours** | route; headline destination |
| Guided Tour of Santiago Bernabéu Museum | **Santiago Bernabeu Tours** | stadium POI |
| 2.5-Hour Prague Introductory Walking Tour | **Prague Castle**? No → `1009 - Prague` | generic walk, POI only incidental |
| Korean Street Food Market Tour (Seoul) | `1026 - Seoul` (Food Tours) | generic theme → category+city |
| N Seoul Tower Observatory Official Ticket | **N Seoul Tower** | POI; assign if in memory, else create |
| Coliseo: acceso prioritario a la arena | **Colosseum** | language variant; folds to same canonical key |
| Flask 1 / Free / Combo: 8905 + 12096 | *dropped* | junk/test row — never seeds a collection |
| (blank title) | *needs_review* | nothing to name a collection after |

Note the Prague example: a generic introductory walking tour is **not** forced
into Prague Castle just because the castle is the city's headline POI. If the
product isn't about entering the castle, it's a city walking tour.

## 5. Anti-patterns to avoid

- **Don't let a big generic bucket hide missing POIs.** If `1010 - Rome` (Guided
  Tours) has 200 items, scan it — many are probably Colosseum/Vatican/Pantheon
  products that need extracting into POI collections.
- **Don't over-split into size-1 category buckets.** One "Surfing - Valencia"
  product with no others is fine, but if you're generating dozens of singletons,
  consider whether a broader category bucket fits.
- **Don't create combo collections** ("Eiffel + Louvre"). Pick an anchor.
- **Don't cluster by language or operator.** Those are within-collection
  variation.
- **Don't seed a collection from a junk row.** Clean first.
- **Don't invent a named theme when a category+city bucket would do.** Named
  collections are a commitment; reserve them for genuine POIs and signature
  themes.
