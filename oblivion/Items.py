from BaseClasses import Item, ItemClassification
from typing import Dict, NamedTuple

class OblivionItem(Item):
    game: str = "Oblivion Remastered"

class ItemData(NamedTuple):
    id: int
    classification: ItemClassification

# Base item ID
BASE_ITEM_ID = 4000000

# Shrine names for generating tokens
shrine_names = [
    "Azura", "Boethia", "Clavicus Vile", "Hermaeus Mora", "Hircine",
    "Malacath", "Mephala", "Meridia", "Molag Bal", "Namira", 
    "Nocturnal", "Peryite", "Sanguine", "Sheogorath", "Vaermina"
]

# Progression items - Daedric Shrine Unlock Tokens (required to access shrine quests)
progression_items = []

# Useful items - Daedric Artifacts (powerful rewards)
useful_items = []

# Filler items - Potions and Scrolls
filler_items = [
    # Potions
    "Strong Potion of Healing",
    "Strong Potion of Speed",
    "Skooma",
    
    # Summoning Scrolls
    "Scroll of Frost Atronach",
    "Scroll of Fire Atronach",
    "Scroll of Storm Atronach", 
    "Scroll of Dremora Lord",
    "Scroll of Lich",
    "Scroll of Xivilai",
    "Scroll of Dremora",
    
    # Bound Weapon Scrolls
    "Scroll of Bound Sword",
    "Scroll of Bound Bow",
    "Scroll of Bound Axe",
    "Scroll of Bound Dagger",
    "Scroll of Bound Mace",
    "Scroll of Bound Shield",
    
    # Powerful Damage Scrolls
    "Scroll of Fire Storm",
    "Scroll of Flame Tempest",
    "Scroll of Ice Storm",
    "Scroll of Blizzard",
    "Scroll of Lightning Storm",
    "Scroll of Shocking Burst",
    
    # Powerful Shield/Protection Scrolls
    "Scroll of Fire Shield",
    "Scroll of Frost Shield",
    "Scroll of Lightning Wall",
    "Scroll of Aegis",
    
    # Powerful Fortify Scrolls
    "Scroll of Greater Fortify Health",
    "Scroll of Greater Fortify Magicka",
    
    # Additional Helpful Scrolls
    "Scroll of Invisibility",
    "Scroll of Telekinesis",
    "Scroll of Unlock",
    "Scroll of Light",
    "Scroll of Water Walking",
    "Scroll of Beast of Burden",
]

# Item table mapping names to data
item_table: Dict[str, ItemData] = {}

# Add progression items (shrine tokens)
current_id = BASE_ITEM_ID
for shrine_name in shrine_names:
    token_name = f"{shrine_name} Shrine Token"
    item_table[token_name] = ItemData(current_id, ItemClassification.progression)
    progression_items.append(token_name)
    current_id += 1

# Arena Unlock Tokens (Progressive Item - 7 total for 21 matches)
arena_unlock_item_name = "Progressive Arena Rank"
item_table[arena_unlock_item_name] = ItemData(current_id, ItemClassification.progression)
# Add 7 instances to progression items list
for i in range(7):
    progression_items.append(arena_unlock_item_name)
current_id += 1

# Progressive Shop Stock Items (4 total - unlocks sets 2-5)
progressive_shop_stock_item_name = "Progressive Shop Stock"
item_table[progressive_shop_stock_item_name] = ItemData(current_id, ItemClassification.progression)
# Add 4 instances to progression items list
for i in range(4):
    progression_items.append(progressive_shop_stock_item_name)
current_id += 1

# Oblivion Gate Key (added dynamically based on gate_count)
oblivion_gate_key_item_name = "Oblivion Gate Key"
item_table[oblivion_gate_key_item_name] = ItemData(current_id, ItemClassification.progression)
current_id += 1

# Add useful items (Daedric artifacts)
useful_artifact_names = [
    "Azura's Star", "Goldbrand", "Masque of Clavicus Vile", "Oghma Infinium",
    "Savior's Hide", "Volendrung", "Ebony Blade", "Ring of Khajiiti",
    "Ring of Namira", "Skeleton Key", "Spellbreaker", "Sanguine Rose",
    "Wabbajack", "Skull of Corruption", "Mace of Molag Bal"
]

for artifact_name in useful_artifact_names:
    item_table[artifact_name] = ItemData(current_id, ItemClassification.useful)
    useful_items.append(artifact_name)
    current_id += 1

# Add Oblivion Gate Vision item
gate_vision_item_name = "Oblivion Gate Vision"
item_table[gate_vision_item_name] = ItemData(current_id, ItemClassification.useful)
current_id += 1

# Add filler items
for item_name in filler_items:
    item_table[item_name] = ItemData(current_id, ItemClassification.filler)
    current_id += 1 