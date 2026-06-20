# Naming Conventions

Name a new collection so it sits naturally beside the existing set. Consistency
matters more than any single rule: before naming, skim the existing collection
names for the same country/category and **match their style**.

## The five naming shapes (from the reference set)

1. **Bare POI name** — when the place name is unambiguous and iconic on its own.
   *Colosseum, Sagrada Familia, Prague Castle, Park Güell, Doge's Palace, London
   Eye, Edge NYC, Uffizi Gallery.*

2. **POI + `Tickets`** — for entry-led attractions where the product is mainly
   admission. *Eiffel Tower Tickets, Burj Khalifa Tickets, Acropolis Tickets,
   Versailles Tickets, Topkapi Palace Tickets, Disneyland® Paris Tickets.*

3. **POI + `Tours`** — for attractions experienced mainly via guided/visited
   tours rather than a turnstile. *Santiago Bernabeu Tours, Alcatraz Tours,
   Pompeii Tickets & Tours, Plitvice Lakes National Park Tours.*

4. **POI + type word + `Tickets`** — when the type clarifies the place.
   *Louvre Museum Tickets, Accademia Gallery Tickets, Jerónimos Monastery
   Tickets, Warner Bros. Studio Tour London Tickets.*

5. **`<Theme> <City>` or `<City> <Theme>`** — for theme and route collections.
   *London Theatre Tickets, Las Vegas Shows, Hawaii Luaus, Iceland Hot Springs,
   Boston Whale Watching Cruises, Krakow to Auschwitz Birkenau Tours.*

For **generic category+city buckets**, the name is the human-readable
subcategory/category plus city, and the ID is the machine form:
- Collection Name: `Cooking Classes - Seoul`; Collection ID: `1027 - Seoul`.
- Collection Name: `Cruises - Lisbon`; Collection ID: `18 - Lisbon`.

## Choosing the suffix (Tickets vs Tours vs bare)

- If most products are **admission/entry** → `Tickets`.
- If most are **guided experiences / there's no simple "buy a ticket" path**
  (stadiums, prisons, ruins, natural sites) → `Tours`.
- If the POI name **already reads as an attraction** and a suffix would be
  redundant → **bare** (*Colosseum*, not *Colosseum Tickets* — though either can
  be valid; match the local set).
- When an attraction genuinely spans both, the reference set sometimes uses
  **`Tickets & Tours`** (*Pompeii Tickets & Tours*).

## Disambiguation

- Same name, different place → add a parenthetical qualifier, usually country:
  *Niagara Falls (Canada) Tours* vs *Niagara Falls (US) Tours*.
- Same brand, different location → keep the location in the name:
  *Universal Studios Japan / Singapore / Orlando / Hollywood.*

## Formatting hygiene

- Preserve official diacritics and registered marks where the brand uses them
  (*Santiago Bernabéu*, *Disneyland® Paris*, *LEGOLAND® Windsor Resort*).
- Title Case. No trailing city when the POI name already implies it, unless the
  local set does otherwise.
- Keep names short and shopper-facing — what a traveler would search, not an
  internal code.

## Quick decision guide

```
Is it one iconic POI?
  ├─ entry/admission-led      → "<POI> Tickets"  (or "<POI> <Type> Tickets")
  ├─ guided/visited-led       → "<POI> Tours"
  └─ iconic name, no suffix needed → "<POI>"
Is it a strong signature theme or route?
  → "<Theme> <City>"  /  "<City> <Activity>"  /  "<Origin> to <Destination> Tours"
Generic instance of a category?
  → Name "<Subcategory/Category> - <City>", ID "<ID> - <City>"
```
