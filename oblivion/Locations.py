from BaseClasses import Location
from typing import Dict, NamedTuple, Optional

EventId: Optional[int] = None

class OblivionLocation(Location):
    game: str = "Oblivion Remastered"

class LocationData(NamedTuple):
    id: int
    region: str = "Cyrodiil"

# Region constants
REGIONS = [
    "Blackwood",
    "Colovian Highlands", 
    "Gold Coast",
    "Great Forest",
    "Heartlands",
    "Jerall Mountains",
    "Nibenay Basin",
    "Nibenay Valley",
    "Valus Mountains",
    "West Weald"
]

# Dungeon to region mapping
DUNGEON_REGIONS = {
    # Blackwood Region
    "Amelion Tomb": "Blackwood",
    "Atatar": "Blackwood",
    "Bloodrun Cave": "Blackwood", 
    "Fieldhouse Cave": "Blackwood",
    "Fort Doublecross": "Blackwood",
    "Fort Nomore": "Blackwood",
    "Fort Redman": "Blackwood",
    "Fort Redwater": "Blackwood",
    "Fort Teleman": "Blackwood",
    "Kindred Cave": "Blackwood",
    "Onyx Caverns": "Blackwood",
    "Redwater Slough": "Blackwood",
    "Reedstand Cave": "Blackwood",
    "Rockmilk Cave": "Blackwood",
    "Telepe": "Blackwood",
    "Undertow Cavern": "Blackwood",
    "Veyond": "Blackwood",
    "Welke": "Blackwood",
    
    # Colovian Highlands Region
    "Black Rock Caverns": "Colovian Highlands",
    "Broken Promises Cave": "Colovian Highlands",
    "Fort Dirich": "Colovian Highlands",
    "Fort Hastrel": "Colovian Highlands",
    "Fort Linchal": "Colovian Highlands",
    "Fort Rayles": "Colovian Highlands",
    "Fort Wariel": "Colovian Highlands",
    "Hrotanda Vale": "Colovian Highlands",
    "Lipsand Tarn": "Colovian Highlands",
    "Nonungalo": "Colovian Highlands",
    "Rock Bottom Caverns": "Colovian Highlands",
    "Talwinque": "Colovian Highlands",
    "Trumbe": "Colovian Highlands",
    "Varondo": "Colovian Highlands",
    "Wind Cave": "Colovian Highlands",
    
    # Gold Coast Region
    "Garlas Agea": "Gold Coast",
    "Niryastare": "Gold Coast",
    "Smoke Hole Cave": "Gold Coast",
    
    # Great Forest Region
    "Ceyatatar": "Great Forest",
    "Charcoal Cave": "Great Forest",
    "Crumbling Mine": "Great Forest",
    "Elenglynn": "Great Forest",
    "Felgageldt Cave": "Great Forest",
    "Fingerbowl Cave": "Great Forest",
    "Fort Ash": "Great Forest",
    "Fort Carmala": "Great Forest",
    "Fort Coldcorn": "Great Forest",
    "Fort Wooden Hand": "Great Forest",
    "Greenmead Cave": "Great Forest",
    "Lindai": "Great Forest",
    "Moranda": "Great Forest",
    "Moss Rock Cavern": "Great Forest",
    "Narfinsel": "Great Forest",
    "Outlaw Endre's Cave": "Great Forest",
    "Piukanda": "Great Forest",
    "Robber's Glen Cave": "Great Forest",
    "Sardavar Leed": "Great Forest",
    "Serpent Hollow Cave": "Great Forest",
    "Underpall Cave": "Great Forest",
    "Unmarked Cave": "Great Forest",
    "Vindasel": "Great Forest",
    "Wendir": "Great Forest",
    "Wenyandawik": "Great Forest",
    
    # Heartlands Region
    "Belda": "Heartlands",
    "Culotte": "Heartlands",
    "Dzonot Cave": "Heartlands",
    "Fanacasecul": "Heartlands",
    "Fatback Cave": "Heartlands",
    "Fort Alessia": "Heartlands",
    "Fort Chalman": "Heartlands",
    "Fort Empire": "Heartlands",
    "Fort Homestead": "Heartlands",
    "Fort Magia": "Heartlands",
    "Fort Nikel": "Heartlands",
    "Fort Urasek": "Heartlands",
    "Fort Variela": "Heartlands",
    "Fort Virtue": "Heartlands",
    "Memorial Cave": "Heartlands",
    "Nagastani": "Heartlands",
    "Sercen": "Heartlands",
    "Sideways Cave": "Heartlands",
    "Sinkhole Cave": "Heartlands",
    "Veyond Cave": "Heartlands",
    "Vilverin": "Heartlands",
    
    # Jerall Mountains Region
    "Capstone Cave": "Jerall Mountains",
    "Fort Horunn": "Jerall Mountains",
    "Ninendava": "Jerall Mountains",
    "Rielle": "Jerall Mountains",
    "Silver Tooth Cave": "Jerall Mountains",
    
    # Nibenay Basin Region
    "Arrowshaft Cavern": "Nibenay Basin",
    "Bramblepoint Cave": "Nibenay Basin",
    "Cracked Wood Cave": "Nibenay Basin",
    "Crayfish Cave": "Nibenay Basin",
    "Fort Cedrian": "Nibenay Basin",
    "Fort Cuptor": "Nibenay Basin",
    "Fort Entius": "Nibenay Basin",
    "Fort Facian": "Nibenay Basin",
    "Fort Naso": "Nibenay Basin",
    "Hame": "Nibenay Basin",
    "Lost Boy Cavern": "Nibenay Basin",
    "Mackamentain": "Nibenay Basin",
    "Nornal": "Nibenay Basin",
    "Ondo": "Nibenay Basin",
    "Rickety Mine": "Nibenay Basin",
    "Sage Glen Hollow": "Nibenay Basin",
    "Timberscar Hollow": "Nibenay Basin",
    "Wendelbek": "Nibenay Basin",
    "Wenderbek Cave": "Nibenay Basin",
    
    # Nibenay Valley Region
    "Anutwyll": "Nibenay Valley",
    "Bawn": "Nibenay Valley",
    "Bloodmayne Cave": "Nibenay Valley",
    "Fort Gold-Throat": "Nibenay Valley",
    "Morahame": "Nibenay Valley",
    "Nenalata": "Nibenay Valley",
    
    # Valus Mountains Region
    "Dark Fissure": "Valus Mountains",
    "Fanacas": "Valus Mountains",
    "Fort Scinia": "Valus Mountains",
    "Kemen": "Valus Mountains",
    
    # West Weald Region
    "Bloodcrust Cavern": "West Weald",
    "Cursed Mine": "West Weald",
    "Dasek Moor": "West Weald",
    "Fort Black Boot": "West Weald",
    "Fort Istirus": "West Weald",
    "Fort Vlastarus": "West Weald",
    "Fyrelight Cave": "West Weald",
    "Howling Cave": "West Weald",
    "Nornalhorst": "West Weald",
}

# Birthsign Doomstone to region mapping
# These are gated by region access items when region system is enabled.
DOOMSTONE_REGIONS = {
    "Visit the Tower Stone": "Heartlands",
    "Visit the Steed Stone": "Heartlands",
    "Visit the Warrior Stone": "West Weald",
    "Visit the Apprentice Stone": "West Weald",
    "Visit the Atronach Stone": "Colovian Highlands",
    "Visit the Lord Stone": "Colovian Highlands",
    "Visit the Lady Stone": "Gold Coast",
    "Visit the Thief Stone": "Great Forest",
    "Visit the Shadow Stone": "Nibenay Basin",
    "Visit the Mage Stone": "Nibenay Basin",
    "Visit the Lover Stone": "Nibenay Valley",
    "Visit the Ritual Stone": "Blackwood",
    "Visit the Serpent Stone": "Blackwood",
}

# Sidequest to region mapping
# These are gated by region access items when region system is enabled.
SIDEQUEST_REGIONS = {
    # Exploration sidequests
    "Obtain Fin Gleam": "Gold Coast",
    "Visit Dive Rock": "Jerall Mountains",
    "Obtain Bands of Kwang Lao": "Heartlands",
    # Wealth sidequests
    "Acquire Akaviri Sunderblade": "Heartlands",
    "Acquire Captain Kordan's Saber": "Nibenay Valley",
    "Acquire Battleaxe of Hatred": "Heartlands",
    "Acquire Akavari Warblade": "Heartlands",
    "Acquire Truncheon of Submission": "Gold Coast",
    "Acquire Destarine's Cleaver": "Blackwood",
    "Acquire Bow of Infliction": "Nibenay Basin",
    "Acquire Aegis of the Apocalypse": "Heartlands",
    "Acquire Helm of the Deep Delver": "Heartlands",
    "Acquire Monkeypants": "Jerall Mountains",
}

# Base location ID
BASE_LOCATION_ID = 4100000

# Location names corresponding to completion tokens that are generated when shrines are completed
location_names = [
    # [DISABLED_STONES] Wayshrine/Runestone/Doomstone disabled
    # "Visit a Wayshrine",
    # "Visit a Runestone",
    # Birthsign Doomstones (per-region)
    "Visit the Tower Stone",
    "Visit the Steed Stone",
    "Visit the Warrior Stone",
    "Visit the Apprentice Stone",
    "Visit the Atronach Stone",
    "Visit the Lord Stone",
    "Visit the Lady Stone",
    "Visit the Thief Stone",
    "Visit the Shadow Stone",
    "Visit the Mage Stone",
    "Visit the Lover Stone",
    "Visit the Ritual Stone",
    "Visit the Serpent Stone",
    "Azura Quest Complete",
    "Boethia Quest Complete", 
    "Clavicus Vile Quest Complete",
    "Hermaeus Mora Quest Complete",
    "Hircine Quest Complete",
    "Malacath Quest Complete",
    "Mephala Quest Complete", 
    "Meridia Quest Complete",
    "Molag Bal Quest Complete",
    "Namira Quest Complete",
    "Nocturnal Quest Complete",
    "Peryite Quest Complete",
    "Sanguine Quest Complete",
    "Sheogorath Quest Complete",
    "Vaermina Quest Complete",
    # Arena match victories
    "Arena Match 1 Victory",
    "Arena Match 2 Victory",
    "Arena Match 3 Victory",
    "Arena Match 4 Victory",
    "Arena Match 5 Victory",
    "Arena Match 6 Victory",
    "Arena Match 7 Victory",
    "Arena Match 8 Victory",
    "Arena Match 9 Victory",
    "Arena Match 10 Victory",
    "Arena Match 11 Victory",
    "Arena Match 12 Victory",
    "Arena Match 13 Victory",
    "Arena Match 14 Victory",
    "Arena Match 15 Victory",
    "Arena Match 16 Victory",
    "Arena Match 17 Victory",
    "Arena Match 18 Victory",
    "Arena Match 19 Victory",
    "Arena Match 20 Victory",
    "Arena Match 21 Victory",
    # Gate tracking
    "Gate 1 Closed",
    "Gate 2 Closed", 
    "Gate 3 Closed",
    "Gate 4 Closed",
    "Gate 5 Closed",
    "Gate 6 Closed",
    "Gate 7 Closed",
    "Gate 8 Closed",
    "Gate 9 Closed",
    "Gate 10 Closed",
    "Gate 11 Closed",
    "Gate 12 Closed",
    "Gate 13 Closed",
    "Gate 14 Closed",
    "Gate 15 Closed",
    "Gate 16 Closed",
    "Gate 17 Closed",
    "Gate 18 Closed",
    "Gate 19 Closed",
    "Gate 20 Closed",
]

# Add dungeon locations to the main list (IDs) - logic will gate access via region items
location_names.extend(list(DUNGEON_REGIONS.keys()))

# Create location table
location_table: Dict[str, LocationData] = {}

for i, location_name in enumerate(location_names):
    location_table[location_name] = LocationData(BASE_LOCATION_ID + i, "Cyrodiil")


# Add shop item locations (progressive shop stock system - always on)
shop_item_locations = [
    # Set 1 (always available)
    "Innkeeper Shop Item Value 1",
    "Innkeeper Shop Item Value 10", 
    "Innkeeper Shop Item Value 100",
    # Set 2 (Progressive Shop Stock 1)
    "Innkeeper Shop Item Value 2",
    "Innkeeper Shop Item Value 20",
    "Innkeeper Shop Item Value 200",
    # Set 3 (Progressive Shop Stock 2)
    "Innkeeper Shop Item Value 3",
    "Innkeeper Shop Item Value 30",
    "Innkeeper Shop Item Value 300",
    # Set 4 (Progressive Shop Stock 3)
    "Innkeeper Shop Item Value 4",
    "Innkeeper Shop Item Value 40",
    "Innkeeper Shop Item Value 400",
    # Set 5 (Progressive Shop Stock 4)
    "Innkeeper Shop Item Value 5",
    "Innkeeper Shop Item Value 50",
    "Innkeeper Shop Item Value 500",
]

for i, shop_location in enumerate(shop_item_locations, start=len(location_names)):
    location_table[shop_location] = LocationData(BASE_LOCATION_ID + i, "Cyrodiil") 

# Class skill locations (for class system - up to 40 increases per skill, 21 skills total)
def generate_class_skill_locations() -> Dict[str, LocationData]:
    locations = {}
    location_id = BASE_LOCATION_ID + len(location_names) + len(shop_item_locations)
    
    all_skills = [
        "Acrobatics", "Alchemy", "Alteration", "Armorer", "Athletics", "Blade", "Block", 
        "Blunt", "Conjuration", "Destruction", "Hand-to-Hand", "Heavy Armor", "Illusion", 
        "Light Armor", "Marksman", "Mercantile", "Mysticism", "Restoration", "Security", 
        "Sneak", "Speechcraft"
    ]
    
    for skill in all_skills:
        for skill_increase_num in range(1, 41):  # 1-40 for up to 20 levels
            location_name = f"{skill} Skill Increase {skill_increase_num}"
            locations[location_name] = LocationData(location_id, "Cyrodiil")
            location_id += 1
    
    return locations

class_skill_locations = generate_class_skill_locations()
location_table.update(class_skill_locations)

# Nirnroot locations (up to 100 harvesting checks)
# World generation adds only the subset needed based on nirnroot_count setting
def generate_nirnroot_locations() -> Dict[str, LocationData]:
    locations = {}
    location_id = BASE_LOCATION_ID + len(location_names) + len(shop_item_locations) + len(class_skill_locations)
    
    for nirnroot_num in range(1, 101):  # 1-100
        location_name = f"Nirnroot {nirnroot_num} Harvested"
        locations[location_name] = LocationData(location_id, "Cyrodiil")
        location_id += 1
    
    return locations

nirnroot_locations = generate_nirnroot_locations()
location_table.update(nirnroot_locations)

# Gold capacity milestone locations (Treasure Hunter goal).
# World generation adds only thresholds <= gold_goal (same pattern as nirnroot_count).
GOLD_CAPACITY_THRESHOLDS = [
    500, 1000, 2500, 5000, 7500, 10000,
    20000, 30000, 40000, 50000, 60000, 70000, 80000, 90000, 100000,
]

# Gold threshold locations (for Treasure Hunter goal)
gold_base_id = BASE_LOCATION_ID + len(location_names) + len(shop_item_locations) + len(class_skill_locations) + len(nirnroot_locations)
location_table["Gold: 500 Collected"] = LocationData(gold_base_id, "Cyrodiil")
location_table["Gold: 1000 Collected"] = LocationData(gold_base_id + 1, "Cyrodiil")
location_table["Gold: 2500 Collected"] = LocationData(gold_base_id + 2, "Cyrodiil")
location_table["Gold: 5000 Collected"] = LocationData(gold_base_id + 3, "Cyrodiil")
location_table["Gold: 7500 Collected"] = LocationData(gold_base_id + 4, "Cyrodiil")
location_table["Gold: 10000 Collected"] = LocationData(gold_base_id + 5, "Cyrodiil")
location_table["Gold: 20000 Collected"] = LocationData(gold_base_id + 6, "Cyrodiil")
location_table["Gold: 30000 Collected"] = LocationData(gold_base_id + 7, "Cyrodiil")
location_table["Gold: 40000 Collected"] = LocationData(gold_base_id + 8, "Cyrodiil")
location_table["Gold: 50000 Collected"] = LocationData(gold_base_id + 9, "Cyrodiil")
location_table["Gold: 60000 Collected"] = LocationData(gold_base_id + 10, "Cyrodiil")
location_table["Gold: 70000 Collected"] = LocationData(gold_base_id + 11, "Cyrodiil")
location_table["Gold: 80000 Collected"] = LocationData(gold_base_id + 12, "Cyrodiil")
location_table["Gold: 90000 Collected"] = LocationData(gold_base_id + 13, "Cyrodiil")
location_table["Gold: 100000 Collected"] = LocationData(gold_base_id + 14, "Cyrodiil")

# Event & victory locations (used for playthrough generation)
location_table["Shrine Seeker"] = LocationData(EventId, "Cyrodiil")
location_table["Gatecloser"] = LocationData(EventId, "Cyrodiil")
location_table["Arena Grand Champion"] = LocationData(EventId, "Cyrodiil") 
location_table["Dungeon Delver"] = LocationData(EventId, "Cyrodiil")
location_table["Light the Dragonfires"] = LocationData(EventId, "Cyrodiil")
location_table["Nirnsanity"] = LocationData(EventId, "Cyrodiil")
location_table["Treasure Hunter"] = LocationData(EventId, "Cyrodiil")
location_table["Weynon Priory Quest Complete"] = LocationData(EventId, "Cyrodiil")
location_table["Paradise Complete"] = LocationData(EventId, "Cyrodiil")

# Main Quest locations (organized by chapter)

# Chapter 1: Tutorial through Weynon Priory (MQ01-MQ04)
mq_chapter_1_locations = [
    "Deliver the Amulet",
    "Find the Heir",
    "Breaking the Siege of Kvatch: Gate Closed",
    "Breaking the Siege of Kvatch",
    "Weynon Priory",
    "Battle for Castle Kvatch",  # Optional side quest (MS49)
]
for loc in mq_chapter_1_locations:
    if loc not in location_table:
        location_table[loc] = LocationData(BASE_LOCATION_ID + len(location_table), "Cyrodiil")

# Chapter 2: MQ05 through MQ13 (Path of Dawn, Dagon Shrine, Spies, blood/artifact arcs, Bruma defense)
mq_chapter_2_locations = [
    # MQ05 - The Path of Dawn
    "The Path of Dawn: Acquire Commentaries Vol I",
    "The Path of Dawn: Acquire Commentaries Vol II",
    "The Path of Dawn: Acquire Commentaries Vol III",
    "The Path of Dawn: Acquire Commentaries Vol IV",
    "The Path of Dawn",
    # MQ06 - Dagon Shrine
    "Dagon Shrine: Mysterium Xarxes Acquired",
    "Dagon Shrine: Kill Harrow",
    "Dagon Shrine",
    "Attack on Fort Sutch",  # Optional side quest after Dagon Shrine
    # MQ07 - Spies
    "Spies: Kill Saveri Faram",
    "Spies: Kill Jearl",
    "Spies",
    # MQ08-MQ13 - Blood/artifact quests and Bruma defense
    "Blood of the Daedra",
    "Blood of the Divines",
    "Blood of the Divines: Free Spirit 1",
    "Blood of the Divines: Free Spirit 2",
    "Blood of the Divines: Free Spirit 3",
    "Blood of the Divines: Free Spirit 4",
    "Blood of the Divines: Armor of Tiber Septim",
    "Bruma Gate",
    "Miscarcand",
    "Miscarcand: Great Welkynd Stone",
    "Defense of Bruma",
    "Great Gate",
]
for loc in mq_chapter_2_locations:
    if loc not in location_table:
        location_table[loc] = LocationData(BASE_LOCATION_ID + len(location_table), "Cyrodiil")

# Chapter 3: Paradise through Victory (MQ14-MQ15)
mq_chapter_3_locations = [
    "Paradise: Bands of the Chosen Acquired",
    "Paradise: Bands of the Chosen Removed",
    "Paradise",
]
for loc in mq_chapter_3_locations:
    if loc not in location_table:
        location_table[loc] = LocationData(BASE_LOCATION_ID + len(location_table), "Cyrodiil")

# Sidequest locations (pool for random selection based on SidequestCount option)

# Categorized sidequest pools
WEALTH_SIDEQUESTS = [
    "Acquire Akaviri Sunderblade",
    "Acquire Captain Kordan's Saber",
    "Acquire Battleaxe of Hatred",
    "Acquire Akavari Warblade",
    "Acquire Truncheon of Submission",
    "Acquire Destarine's Cleaver",
    "Acquire Bow of Infliction",
    "Acquire Aegis of the Apocalypse",
    "Acquire Helm of the Deep Delver",
    "Acquire Monkeypants",
]

EXPLORATION_SIDEQUESTS = [
    "Obtain a Varla Stone",
    "Obtain Fin Gleam",
    "Visit Dive Rock",
    "Obtain Bands of Kwang Lao",
    "Visit an Ayleid Well",
]

# Register all sidequest locations in location_table
sidequest_base_id = BASE_LOCATION_ID + len(location_table)
all_sidequests = WEALTH_SIDEQUESTS + EXPLORATION_SIDEQUESTS
for i, sidequest_name in enumerate(all_sidequests):
    location_table[sidequest_name] = LocationData(sidequest_base_id + i, "Cyrodiil")

# Sidequest metadata (gold costs and locations for reference)
SIDEQUEST_METADATA = {
    # Wealth sidequests - gold cost
    "Acquire Akaviri Sunderblade": 5000,  # Imperial Market
    "Acquire Captain Kordan's Saber": 6840,  # Cheydinhal
    "Acquire Battleaxe of Hatred": 15000,  # Imperial Market
    "Acquire Akavari Warblade": 5600,  # Imperial Market
    "Acquire Truncheon of Submission": 5500,  # Anvil
    "Acquire Destarine's Cleaver": 6400,  # Leyawiin
    "Acquire Bow of Infliction": 9100,  # Bravil
    "Acquire Aegis of the Apocalypse": 12000,  # Imperial Market
    "Acquire Helm of the Deep Delver": 8700,  # Imperial Market
    "Acquire Monkeypants": 3600,  # Suurootan at Novaroma, Bruma
    # Exploration sidequests - no gold cost
    "Obtain a Varla Stone": 0,
    "Obtain Fin Gleam": 0,
    "Visit Dive Rock": 0,
    "Obtain Bands of Kwang Lao": 0,
    "Visit an Ayleid Well": 0,
}

# Combined sidequest pool (all sidequests available)
SIDEQUEST_POOL = WEALTH_SIDEQUESTS + EXPLORATION_SIDEQUESTS

# Sidequest location names mapped to AP item names excluded from filler when seeded.
# Wealth sidequests must be purchased in-game; receiving the item from AP skips the check.
SIDEQUEST_TO_AP_ITEM = {
    "Acquire Akaviri Sunderblade": "Akavari Sunderblade",
    "Acquire Captain Kordan's Saber": "Captain Kordan's Saber",
    "Acquire Battleaxe of Hatred": "Battleaxe of Hatred",
    "Acquire Akavari Warblade": "Akavari Warblade",
    "Acquire Truncheon of Submission": "Truncheon of Submission",
    "Acquire Destarine's Cleaver": "Destarine's Cleaver",
    "Acquire Bow of Infliction": "Bow of Infliction",
    "Acquire Aegis of the Apocalypse": "Aegis of the Apocalypse",
    "Acquire Helm of the Deep Delver": "Helm of the Deep Delver",
    "Acquire Monkeypants": "Monkeypants",
    "Obtain Fin Gleam": "Fin Gleam",
}

# Kill check location pool
# Logic gates each batch by region unlock count
def generate_kill_locations() -> Dict[str, LocationData]:
    locations: Dict[str, LocationData] = {}
    location_id = BASE_LOCATION_ID + len(location_table)
    for i in range(1, 101):
        locations[f"Dungeon Kill {i}"] = LocationData(location_id, "Cyrodiil")
        location_id += 1
    for i in range(1, 101):
        locations[f"Overworld Kill {i}"] = LocationData(location_id, "Cyrodiil")
        location_id += 1
    return locations

kill_locations = generate_kill_locations()
location_table.update(kill_locations)