# Taxonomy

Category and subcategory IDs used to classify experiences, plus the
`<ID> - <City>` convention for generic collections. These IDs match the
GetYourGuide-style taxonomy. If the user supplies their own ID set, use theirs
instead — this file is the default.

## The `<ID> - <City>` convention for generic collections

When an experience has no distinctive POI or theme, its collection is named by
**category or subcategory + city**:

- ID = `<Category ID or Subcategory ID> - <City>` (e.g. `18 - Seoul`, `1027 - Tokyo`).
- Name = `<Category/Subcategory Name> - <City>` (e.g. `Cruises - Seoul`,
  `Cooking Classes - Tokyo`).

Use a **subcategory** ID when one fits precisely (cooking classes → `1027`); fall
back to a **category** ID when no subcategory fits (general wellness → `12`,
generic classes/workshops → `13`).

## Categories

| ID | Name |
|----|------|
| 1 | Tickets |
| 2 | Tours |
| 3 | Transportation |
| 4 | Travel Services |
| 5 | Food & Drink |
| 6 | Day Trips |
| 7 | Entertainment |
| 8 | Adventure |
| 9 | Aerial Sightseeing |
| 10 | Water Sports |
| 11 | Nature & Wildlife |
| 12 | Wellness |
| 13 | Classes |
| 14 | Specials |
| 15 | RV Rentals |
| 16 | Staycations |
| 18 | Cruises |
| 19 | Sports |

## Subcategories (ID → Name → parent Category)

### Tickets (1)
1001 Theme Parks · 1002 Museums · 1003 Zoos · 1004 Parks · 1005 Water Parks ·
1006 Religious Sites · 1007 Landmarks · 1008 City Cards · 1098 Observation Decks ·
1140 Aquariums · 1149 Immersive Experiences · 1152 Churches

### Tours (2)
1009 Walking Tours · 1010 Guided Tours · 1011 HOHO (hop-on hop-off) ·
1012 City Tours · 1013 Private Tours · 1014 Bikes & Segway · 1015 Shopping ·
1016 Multi-Day Tours · 1017 Photography Tours · 1018 Port of Call Tours (Cruise
Visitors) · 1068 Speed Boat Tours · 1143 Day trips · 1147 Heritage Experiences

### Transportation (3)
1019 Airport Transfers · 1020 Car Rentals · 1021 Attraction Transfers ·
1022 Public Transport · 1108 Ferry Tickets · 1133 Train Tickets · 1139 Train
Passes · 1144 Private Airport Transfers · 1145 Shared Airport Transfers

### Travel Services (4)
1023 Wifi & SIM Cards · 1024 Travel Insurance

### Food & Drink (5)
1025 Dining · 1026 Food Tours · 1027 Cooking Classes · 1028 Wineries ·
1029 Coffee & Tea · 1030 Pub Crawls · 1031 Food Passes

### Day Trips (6)
1032 Nearby cities · 1033 Nature Escapes · 1034 Adventure · 1035 Sightseeing

### Entertainment (7)
1036 Musicals · 1037 Plays · 1038 Opera · 1039 Cinema · 1040 Classical Concerts ·
1041 Comedy Shows · 1042 Sports · 1043 Cabarets · 1044 Ballet · 1045 Shows
Opening Soon · 1046 New Arrivals · 1047 Kids' Shows · 1048 Shows Reopening ·
1096 Pantomimes · 1097 See it in Style · 1100 Dance · 1103 Magic Shows ·
1104 Immersive Theater · 1105 Circus Shows · 1106 Fantasy Shows · 1107 Drama
Shows · 1118 Recital Concerts · 1119 Theatrical Concerts · 1120 Rock Concerts ·
1121 Church Concerts · 1146 Flamenco Shows · 1148 Nightlife · 1150 Plays ·
1151 Adult Shows

### Adventure (8)
1049 Skydiving · 1050 Skiing · 1051 Bungee Jumping · 1052 Ziplining ·
1053 Climbing · 1054 Racing · 1055 Indoor Adventure · 1056 Outdoor Activities ·
1073 Desert Safari · 1113 Snowboarding · 1114 Sledding · 1115 Snowshoeing ·
1116 Mountain Excursions

### Aerial Sightseeing (9)
1057 Helicopter Tours · 1058 Hot Air Balloon · 1059 Airplane Tours

### Water Sports (10)
1062 Scuba Diving · 1063 Surfing · 1064 Jet Skiing · 1067 Kayaking

### Cruises (18)
1060 Dinner Cruises · 1061 Sightseeing Cruises · 1069 Yacht Tours ·
1094 Lunch Cruises · 1095 Evening Cruises

## Choosing a category/subcategory — quick heuristics

- Admission to an attraction → **Tickets (1)** + the matching subcategory
  (museum, theme park, observation deck, aquarium…).
- Anything guided/walked/driven around a place → **Tours (2)**; pick
  private/walking/city/photography/heritage/HOHO as fits, else 1010 Guided Tours.
- Excursion outside the home city → **Day Trips (6)** (or a route/POI collection).
- Cooking, food/market tours, tastings, pub crawls → **Food & Drink (5)**.
- Shows, concerts, performances, nightlife, sports spectating → **Entertainment (7)**.
- Hiking, ski, climb, kart, motorbike → **Adventure (8)**; water → **Water Sports
  (10)**; flight/balloon → **Aerial (9)**.
- Boat/yacht/river cruises → **Cruises (18)**.
- Spa, bath, massage, sauna, retreat → **Wellness (12)**.
- Hands-on craft/workshop/lesson (pottery, perfume, jewelry, language, K-pop
  dance) → **Classes (13)**.
- SIM/wifi, insurance → **Travel Services (4)**; transfers/passes →
  **Transportation (3)**.
- Cultural dress-up / hard-to-place cultural experiences → **Specials (14)**.

## Existing collections (assign before you create)

The engine matches every experience against the existing-collections memory in
`reference_collections.md` (plus any collections already minted earlier in the
same batch) **first**. If an experience belongs to one of those, emit
`decision="assign_existing"`, `is_new=false`, and reuse that real id/name. Only
when no existing collection fits does it create one (`decision="create_new"`,
`is_new=true`). The category+city buckets that already exist (e.g. `18 - Seoul`,
`1011 - Tokyo`) are existing collections too — reuse their ids rather than minting
duplicates. This ordering is what keeps results idempotent and the namespace free
of duplicate collections.
