from BaseClasses import Location
from typing import Dict, NamedTuple, Optional

EventId: Optional[int] = None

class OblivionLocation(Location):
    game: str = "Oblivion Remastered"

class LocationData(NamedTuple):
    id: int
    region: str = "Cyrodiil"

# Base location ID (Archipelago assigns ranges per game)  
BASE_LOCATION_ID = 4000000  # This should be assigned by Archipelago maintainers

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

]

# Create location table
location_table: Dict[str, LocationData] = {}

for i, location_name in enumerate(location_names):
    location_table[location_name] = LocationData(BASE_LOCATION_ID + i, "Cyrodiil")

# Add Victory event location
location_table["Victory"] = LocationData(EventId, "Cyrodiil") 