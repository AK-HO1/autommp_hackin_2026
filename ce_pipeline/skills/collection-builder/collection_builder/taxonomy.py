"""
taxonomy.py — Headout category/subcategory IDs and the routing conventions.

This is the single source of truth for how a classified experience becomes a
collection ID. Edit the tables here; the engine logic never hardcodes IDs.

Two kinds of output ID:
  - "<ID> - <City>"  for non-POI experiences that map to an existing
    category/subcategory bucket (e.g. "18 - Sydney" = Sydney Cruises).
  - a named collection (POI landmark, or a day-trip/destination umbrella).

Note the ID LEVEL varies by activity and is NOT inferable from the table alone
(cruises resolve at the CATEGORY level = 18; food tours at the SUBCATEGORY level
= 1026). ACTIVITY_ID is therefore an explicit lookup, confirmed with the GM.
"""

# --- Category IDs (level 1) -------------------------------------------------
CATEGORY = {
    1: "Tickets", 2: "Tours", 3: "Transportation", 4: "Travel Services",
    5: "Food & Drink", 6: "Day Trips", 7: "Entertainment", 8: "Adventure",
    9: "Aerial Sightseeing", 10: "Water Sports", 11: "Nature & Wildlife",
    12: "Wellness", 13: "Classes", 14: "Specials", 15: "RV Rentals",
    16: "Staycations", 18: "Cruises", 19: "Sports",
}

# --- Subcategory IDs (level 2) -> (name, parent_category_id) ----------------
# Trimmed to the ones the router needs + the full set for the LLM to choose from.
SUBCATEGORY = {
    1002: ("Museums", 1), 1001: ("Theme Parks", 1), 1003: ("Zoos", 1),
    1004: ("Parks", 1), 1005: ("Water Parks", 1), 1006: ("Religious Sites", 1),
    1007: ("Landmarks", 1), 1008: ("City Cards", 1), 1098: ("Observation Decks", 1),
    1140: ("Aquariums", 1), 1149: ("Immersive Experiences", 1), 1152: ("Churches", 1),
    1009: ("Walking Tours", 2), 1010: ("Guided Tours", 2), 1011: ("HOHO", 2),
    1012: ("City Tours", 2), 1013: ("Private Tours", 2), 1014: ("Bikes & Segway", 2),
    1015: ("Shopping", 2), 1016: ("Multi-Day Tours", 2), 1017: ("Photography Tours", 2),
    1018: ("Port of Call Tours", 2), 1143: ("Day trips", 2), 1068: ("Speed Boat Tours", 2),
    1147: ("Heritage Experiences", 2), 1019: ("Airport Transfers", 3),
    1020: ("Car Rentals", 3), 1021: ("Attraction Transfers", 3), 1022: ("Public Transport", 3),
    1108: ("Ferry Tickets", 3), 1133: ("Train Tickets", 3), 1139: ("Train Passes", 3),
    1144: ("Private Airport Transfers", 3), 1145: ("Shared Airport Transfers", 3),
    1023: ("Wifi & SIM Cards", 4), 1024: ("Travel Insurance", 4),
    1025: ("Dining", 5), 1026: ("Food Tours", 5), 1027: ("Cooking Classes", 5),
    1028: ("Wineries", 5), 1029: ("Coffee & Tea", 5), 1030: ("Pub Crawls", 5),
    1031: ("Food Passes", 5), 1032: ("Nearby cities", 6), 1033: ("Nature Escapes", 6),
    1034: ("Adventure", 6), 1035: ("Sightseeing", 6), 1049: ("Skydiving", 8),
    1050: ("Skiing", 8), 1051: ("Bungee Jumping", 8), 1052: ("Ziplining", 8),
    1053: ("Climbing", 8), 1054: ("Racing", 8), 1055: ("Indoor Adventure", 8),
    1056: ("Outdoor Activities", 8), 1073: ("Desert Safari", 8), 1113: ("Snowboarding", 8),
    1114: ("Sledding", 8), 1115: ("Snowshoeing", 8), 1116: ("Mountain Excursions", 8),
    1057: ("Helicopter Tours", 9), 1058: ("Hot Air Balloon", 9), 1059: ("Airplane Tours", 9),
    1061: ("Sightseeing Cruises", 18), 1060: ("Dinner Cruises", 18),
    1094: ("Lunch Cruises", 18), 1095: ("Evening Cruises", 18), 1069: ("Yacht Tours", 18),
    1062: ("Scuba Diving", 10), 1063: ("Surfing", 10), 1064: ("Jet Skiing", 10),
    1067: ("Kayaking", 10),
}


# --- ACTIVITY -> routing ID -------------------------------------------------
# The explicit, GM-confirmed mapping of each non-POI activity class to the ID
# used in "<ID> - City". The LLM gate returns an `activity` key from this set;
# the router looks the ID up here. Level (category vs subcategory) is baked in.
ACTIVITY_TO_ID = {
    "cruise":            18,    # CATEGORY level (Sightseeing Cruises -> 18 - City)
    "ferry":             1108,  # Ferry Tickets
    "food_tour":         1026,  # Food Tours
    "wine_tour":         1028,  # Wineries
    "skydiving":         1049,  # Skydiving
    "ziplining":         1052,  # Ziplining
    "helicopter":        1057,  # Helicopter Tours / scenic flights
    "city_tour":         1010,  # Guided Tours (city tours, single-city sightseeing)
    # adventure-activity classes that resolve to a subcategory bucket
    "bungee":            1051,  # Bungee Jumping
    "jet_boat":          1056,  # Outdoor Activities (no dedicated jet-boat subcat)
    "rafting":           1056,  # Outdoor Activities
    "kayaking":          1067,  # Kayaking
    "scuba":             1062,  # Scuba Diving
    "surfing":           1063,  # Surfing
    "skiing":            1050,  # Skiing
    "hot_air_balloon":   1058,  # Hot Air Balloon
    "water_sports":      10,    # CATEGORY level (confirmed: "10 - Sydney" exists)
    "speed_boat":        1068,  # Speed Boat Tours (confirmed: "1068 - Sydney")
    "hoho":              1011,  # Hop-on Hop-off (confirmed: "1011 - Sydney")
    "airport_transfer":  1019,  # Airport Transfers (confirmed: "1019 - Auckland")
}

# Activity classes that are ALWAYS non-POI even if a landmark is in the title
# (the "veto" — a Milford Sound CRUISE is non-POI because cruise vetoes POI).
ACTIVITY_VETO = set(ACTIVITY_TO_ID.keys())


def activity_collection_id(activity, city):
    """Return the '<ID> - City' collection id for a non-POI activity, or None."""
    aid = ACTIVITY_TO_ID.get(activity)
    if aid is None:
        return None
    return f"{aid} - {city}"


def activity_collection_name(activity, city):
    """Human-readable name for an activity bucket, e.g. 'Sightseeing Cruises - Sydney'.
    For cruises we use the category label to match the '18 - City' convention."""
    aid = ACTIVITY_TO_ID.get(activity)
    if aid is None:
        return None
    if aid in CATEGORY:
        label = CATEGORY[aid]
    else:
        label = SUBCATEGORY[aid][0]
    return f"{label} - {city}"


def subcategory_options_for_prompt():
    """Compact list of subcategories for the LLM gate to choose from."""
    lines = []
    for sid, (name, cat) in sorted(SUBCATEGORY.items()):
        lines.append(f"{sid}={name} (cat {cat} {CATEGORY[cat]})")
    return "; ".join(lines)
