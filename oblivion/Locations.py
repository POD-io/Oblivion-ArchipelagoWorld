from BaseClasses import Location
from typing import Dict, NamedTuple, Optional

EventId: Optional[int] = None

class OblivionLocation(Location):
    game: str = "Oblivion Remastered"

class LocationData(NamedTuple):
    id: int
    region: str = "Cyrodiil"

# Base location ID
BASE_LOCATION_ID = 4100000

# Location names corresponding to completion tokens that are generated when shrines are completed
location_names = [
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
    # Skill Increases (30 max)
    "Skill Increase 1",
    "Skill Increase 2",
    "Skill Increase 3",
    "Skill Increase 4",
    "Skill Increase 5",
    "Skill Increase 6",
    "Skill Increase 7",
    "Skill Increase 8",
    "Skill Increase 9",
    "Skill Increase 10",
    "Skill Increase 11",
    "Skill Increase 12",
    "Skill Increase 13",
    "Skill Increase 14",
    "Skill Increase 15",
    "Skill Increase 16",
    "Skill Increase 17",
    "Skill Increase 18",
    "Skill Increase 19",
    "Skill Increase 20",
    "Skill Increase 21",
    "Skill Increase 22",
    "Skill Increase 23",
    "Skill Increase 24",
    "Skill Increase 25",
    "Skill Increase 26",
    "Skill Increase 27",
    "Skill Increase 28",
    "Skill Increase 29",
    "Skill Increase 30",
    # Dungeon Clears (30 max)
    "Dungeon Clear 1",
    "Dungeon Clear 2",
    "Dungeon Clear 3",
    "Dungeon Clear 4",
    "Dungeon Clear 5",
    "Dungeon Clear 6",
    "Dungeon Clear 7",
    "Dungeon Clear 8",
    "Dungeon Clear 9",
    "Dungeon Clear 10",
    "Dungeon Clear 11",
    "Dungeon Clear 12",
    "Dungeon Clear 13",
    "Dungeon Clear 14",
    "Dungeon Clear 15",
    "Dungeon Clear 16",
    "Dungeon Clear 17",
    "Dungeon Clear 18",
    "Dungeon Clear 19",
    "Dungeon Clear 20",
    "Dungeon Clear 21",
    "Dungeon Clear 22",
    "Dungeon Clear 23",
    "Dungeon Clear 24",
    "Dungeon Clear 25",
    "Dungeon Clear 26",
    "Dungeon Clear 27",
    "Dungeon Clear 28",
    "Dungeon Clear 29",
    "Dungeon Clear 30",

]

# Create location table
location_table: Dict[str, LocationData] = {}

for i, location_name in enumerate(location_names):
    location_table[location_name] = LocationData(BASE_LOCATION_ID + i, "Cyrodiil")

# Add goal-specific victory event locations (victory-only, no items placed)
location_table["Arena Grand Champion"] = LocationData(EventId, "Cyrodiil")
location_table["Shrine Seeker"] = LocationData(EventId, "Cyrodiil")
location_table["Gatecloser"] = LocationData(EventId, "Cyrodiil") 

# Add shop item locations (progressive shop stock system - always on)
shop_item_locations = [
    # Set 1 (always available)
    "Shop Item Value 1",
    "Shop Item Value 10", 
    "Shop Item Value 100",
    # Set 2 (Progressive Shop Stock 1)
    "Shop Item Value 2",
    "Shop Item Value 20",
    "Shop Item Value 200",
    # Set 3 (Progressive Shop Stock 2)
    "Shop Item Value 3",
    "Shop Item Value 30",
    "Shop Item Value 300",
    # Set 4 (Progressive Shop Stock 3)
    "Shop Item Value 4",
    "Shop Item Value 40",
    "Shop Item Value 400",
    # Set 5 (Progressive Shop Stock 4)
    "Shop Item Value 5",
    "Shop Item Value 50",
    "Shop Item Value 500",
]

for i, shop_location in enumerate(shop_item_locations, start=len(location_names)):
    location_table[shop_location] = LocationData(BASE_LOCATION_ID + i, "Cyrodiil") 