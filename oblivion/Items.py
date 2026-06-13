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

# Region unlock items - required to access content in each region
region_unlock_items = [
    "Blackwood Access",
    "Colovian Highlands Access", 
    "Gold Coast Access",
    "Great Forest Access",
    "Heartlands Access",
    "Jerall Mountains Access",
    "Nibenay Basin Access",
    "Nibenay Valley Access",
    "Valus Mountains Access",
    "West Weald Access"
]

# Useful items - Daedric Artifacts
useful_items = []

# Filler items - All filler categories combined with weighted distribution
filler_items = [
    # Lockpick (25%)
    "Lockpick",
    "Lockpick",
    "Lockpick",
    "Lockpick",
    "Lockpick",
    
    # Gold (20%)
    "Gold (10)",
    "Gold (10)",
    "Gold (10)",
    "Gold (10)",
    
    # Steel Arrows (20%)
    "Steel Arrows",
    "Steel Arrows",
    "Steel Arrows",
    "Steel Arrows",
    
    # Common Soul Gem (15%)
    "Common Soul Gem",
    "Common Soul Gem",
    "Common Soul Gem",

    # Repair Hammer (5%)
    "Repair Hammer",

    # Torch (5%)
    "Torch",
    
    # Potion (5%) - random potion selection
    "Random Potion",
    
    # Scroll (5%) - random scroll selection
    "Random Scroll",
]

# Potions - Pool for random selection when "Random Potion" is chosen (5% of filler = 1.25% of total)
# Equal weight between all potions
potion_items = [
    "Strong Potion of Healing",
    "Strong Potion of Speed",
    "Skooma",
]

# Scroll pool for random selection when "Random Scroll" is chosen (5% of filler = 1.25% of total)
# Equal weight between all scrolls
scroll_pool = [
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

# Add Region Access items (progression)
for access_name in region_unlock_items:
    item_table[access_name] = ItemData(current_id, ItemClassification.progression)
    # Do not automatically add to progression_items here; pool count is decided per seed
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

# Sidequest License Items
wealth_license_item_name = "Wealth Sidequest License"
item_table[wealth_license_item_name] = ItemData(current_id, ItemClassification.progression_skip_balancing)
current_id += 1

exploration_license_item_name = "Exploration Sidequest License"
item_table[exploration_license_item_name] = ItemData(current_id, ItemClassification.progression)
current_id += 1

# Progressive Class Level Items
progressive_class_level_items = [
    "Progressive Acrobat Level",
    "Progressive Agent Level", 
    "Progressive Archer Level",
    "Progressive Assassin Level",
    "Progressive Barbarian Level",
    "Progressive Bard Level",
    "Progressive Battlemage Level",
    "Progressive Crusader Level",
    "Progressive Healer Level",
    "Progressive Knight Level",
    "Progressive Mage Level",
    "Progressive Monk Level",
    "Progressive Nightblade Level",
    "Progressive Pilgrim Level",
    "Progressive Rogue Level",
    "Progressive Scout Level",
    "Progressive Sorcerer Level",
    "Progressive Spellsword Level",
    "Progressive Thief Level",
    "Progressive Warrior Level",
    "Progressive Witchhunter Level"
]

for item_name in progressive_class_level_items:
    item_table[item_name] = ItemData(current_id, ItemClassification.progression)
    current_id += 1

# Progressive Armor Set Items (3 total - unlocks tiers 2, 4, 5; first one placed early)
# Skips tiers 1 and 3 for better mid-late game scaling
progressive_armor_set_item_name = "Progressive Armor Set"
item_table[progressive_armor_set_item_name] = ItemData(current_id, ItemClassification.useful)

for i in range(3):
    useful_items.append(progressive_armor_set_item_name)
current_id += 1

# Progressive Nirnroot Satchel (5 total - gates Nirnroot harvesting capacity)
progressive_nirnroot_satchel_item_name = "Progressive Nirnroot Satchel"
item_table[progressive_nirnroot_satchel_item_name] = ItemData(current_id, ItemClassification.progression)
current_id += 1

# Nirnroot (goal items for Nirnsanity - collected from multiworld)
# These are the actual items needed for victory, separate from the harvesting locations
nirnroot_item_name = "Nirnroot"
item_table[nirnroot_item_name] = ItemData(current_id, ItemClassification.progression_skip_balancing)
current_id += 1

# Progressive Septim Satchel Items (5 total - gates gold collection capacity)
# Unlike Nirnsanity, Treasure Hunter has no goal items - victory is achieved by reaching capacity thresholds with in-game gold
progressive_septim_satchel_item_name = "Progressive Septim Satchel"
item_table[progressive_septim_satchel_item_name] = ItemData(current_id, ItemClassification.progression)
current_id += 1

# Main Quest progression items (for Light the Dragonfires goal)
amulet_of_kings_item_name = "Amulet of Kings"
item_table[amulet_of_kings_item_name] = ItemData(current_id, ItemClassification.progression)
current_id += 1

# Kvatch Gate Key (second MQ progression step, only used when Light the Dragonfires goal active)
kvatch_gate_key_item_name = "Kvatch Gate Key"
item_table[kvatch_gate_key_item_name] = ItemData(current_id, ItemClassification.progression)
current_id += 1

# MQ06 - Dagon Shrine access item
dagon_shrine_passphrase_item_name = "Dagon Shrine Passphrase"
item_table[dagon_shrine_passphrase_item_name] = ItemData(current_id, ItemClassification.progression)
current_id += 1

# Fort Sutch Gate Key (post-MQ06 optional quest access; only when MQ goal active)
fort_sutch_gate_key_item_name = "Fort Sutch Gate Key"
item_table[fort_sutch_gate_key_item_name] = ItemData(current_id, ItemClassification.progression)
current_id += 1

# MQ07 - Spies gating item (unlocks Spies quest locations)
blades_report_item_name = "Blades' Report: Strangers at Dusk"
item_table[blades_report_item_name] = ItemData(current_id, ItemClassification.progression)
current_id += 1

# MQ05 gating item (unlocks MQ05 locations)
encrypted_scroll_item_name = "Encrypted Scroll of the Blades"
item_table[encrypted_scroll_item_name] = ItemData(current_id, ItemClassification.progression)
current_id += 1

# Decoded Xarxes pages 
decoded_page_daedra_item_name = "Decoded Page of the Xarxes: Daedric"
item_table[decoded_page_daedra_item_name] = ItemData(current_id, ItemClassification.progression)
current_id += 1
decoded_page_divines_item_name = "Decoded Page of the Xarxes: Divine"
item_table[decoded_page_divines_item_name] = ItemData(current_id, ItemClassification.progression)
current_id += 1
decoded_page_ayleid_item_name = "Decoded Page of the Xarxes: Ayleid"
item_table[decoded_page_ayleid_item_name] = ItemData(current_id, ItemClassification.progression)
current_id += 1
decoded_page_sigillum_item_name = "Decoded Page of the Xarxes: Sigillum"
item_table[decoded_page_sigillum_item_name] = ItemData(current_id, ItemClassification.progression)
current_id += 1

# Bruma Gate Key (gates Bruma Gate milestone)
bruma_gate_key_item_name = "Bruma Gate Key"
item_table[bruma_gate_key_item_name] = ItemData(current_id, ItemClassification.progression)
current_id += 1

# Paradise Access (gates Paradise sequence)
paradise_access_item_name = "Paradise Access"
item_table[paradise_access_item_name] = ItemData(current_id, ItemClassification.progression)
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

# Add Greater Soulgem Package item
greater_soulgem_package_item_name = "Greater Soulgem Package"
item_table[greater_soulgem_package_item_name] = ItemData(current_id, ItemClassification.useful)
useful_items.append(greater_soulgem_package_item_name)
current_id += 1

# Fire Arrow Bundle: Gives 100 fire-damage arrows
fire_arrow_bundle_item_name = "Fire Arrow Bundle"
item_table[fire_arrow_bundle_item_name] = ItemData(current_id, ItemClassification.useful)
useful_items.append(fire_arrow_bundle_item_name)
current_id += 1

# Unique Merchant Items - Organized by equipment type
# These are unique items that are not quest rewards or faction rewards
# A random subset from each category will appear in each seed (see create_items in __init__.py)

unique_weapons = [
    "Akavari Sunderblade",
    "Captain Kordan's Saber",
    "Akavari Warblade",
    "Truncheon of Submission",
    "Battleaxe of Hatred",
    "Destarine's Cleaver",
    "Bow of Infliction",
    "Redwave",
    "Calliben's Grim Retort",
    "Frostwyrm Bow",
]

unique_shields = [
    "Aegis of the Apocalypse",
    "Birthright of Astalon",
    "Dondoran's Juggernaut",
]

unique_gauntlets = [
    "Fists of the Drunkard",
    "Gauntlets of Gluttony",
    "Hands of the Atronach",
    "Rasheda's Special",
]

unique_helmets = [
    "Fin Gleam",
    "Helm of the Deep Delver",
    "Helm of Ferocity",
    "Tower of the Nine",
]

unique_boots = [
    "Boots of the Swift Merchant",
    "Quicksilver Boots",
    "Nistor's Boots",
    "Boots of Springheel Jak",
]

unique_greaves = [
    "Monkeypants",
]

unique_clothing = [
    "Cowl of the Druid",
    "Mantle of the Woodsman",
    "Imperial Breeches",
    "Apron of the Master Artisan",
    "Robe of Creativity",
    "Vest of the Bard",
]

unique_amulets = [
    "Circlet of Omnipotence",
]

unique_rings = [
    "Ring of Transmutation",
    "Ring of Wortcraft",
    "Spectre Ring",
    "Ring of the Gray",
]

unique_staves = [
    "Apotheosis",
]

# Combine all unique item categories
unique_merchant_categories = {
    "weapons": unique_weapons,
    "shields": unique_shields,
    "gauntlets": unique_gauntlets,
    "helmets": unique_helmets,
    "boots": unique_boots,
    "greaves": unique_greaves,
    "clothing": unique_clothing,
    "amulets": unique_amulets,
    "rings": unique_rings,
    "staves": unique_staves,
}

# Add all unique merchant items to item_table but NOT to useful_items
for category_items in unique_merchant_categories.values():
    for unique_item_name in category_items:
        item_table[unique_item_name] = ItemData(current_id, ItemClassification.useful)
        current_id += 1

# Add Fast Travel item
fast_travel_item_name = "Fast Travel"
item_table[fast_travel_item_name] = ItemData(current_id, ItemClassification.useful)
useful_items.append(fast_travel_item_name)
current_id += 1

# Add Dungeon Warp item
dungeon_warp_item_name = "Dungeon Warp"
item_table[dungeon_warp_item_name] = ItemData(current_id, ItemClassification.useful)
useful_items.append(dungeon_warp_item_name)
current_id += 1

# Add Horse item
horse_item_name = "Horse"
item_table[horse_item_name] = ItemData(current_id, ItemClassification.useful)
useful_items.append(horse_item_name)
current_id += 1

# Add Birth Sign item
birth_sign_item_name = "Birth Sign"
item_table[birth_sign_item_name] = ItemData(current_id, ItemClassification.useful)
useful_items.append(birth_sign_item_name)
current_id += 1

# Add attribute fortification items
attribute_useful_items = [
    "Fortify Strength",
    "Fortify Intelligence",
    "Fortify Willpower",
    "Fortify Agility",
    "Fortify Speed",
    "Fortify Endurance",
    "Fortify Personality",
    "Fortify Luck",
]

for attr_item in attribute_useful_items:
    item_table[attr_item] = ItemData(current_id, ItemClassification.useful)
    useful_items.append(attr_item)
    current_id += 1

# Add filler items
for item_name in filler_items:
    item_table[item_name] = ItemData(current_id, ItemClassification.filler)
    current_id += 1

# Add potion items as filler
for item_name in potion_items:
    if item_name not in item_table:  # Avoid duplicates
        item_table[item_name] = ItemData(current_id, ItemClassification.filler)
        current_id += 1

# Add all scroll pool items to item table (filler)
for item_name in scroll_pool:
    if item_name not in item_table:  # Avoid duplicates
        item_table[item_name] = ItemData(current_id, ItemClassification.filler)
        current_id += 1 

# Trap items - replace a configurable percentage of filler slots
trap_items = [
    "Movement Trap",
    "Storm Trap",
    "Spawn Trap",
]

trap_code_map: Dict[str, str] = {
    "Movement Trap": "APMovementTrapReceived",
    "Storm Trap": "APStormTrapReceived",
    "Spawn Trap": "APSpawnTrapReceived",
}


# Add trap items to item_table with trap classification
for _trap_name in trap_items:
    item_table[_trap_name] = ItemData(current_id, ItemClassification.trap)
    current_id += 1

# Item groups for hinting
item_name_groups = {
    "Shrine Token": [f"{shrine} Shrine Token" for shrine in shrine_names],
    "Oblivion Gate Key": ["Oblivion Gate Key"],
    "Progressive Arena Rank": ["Progressive Arena Rank"],
    "Progressive Shop Stock": ["Progressive Shop Stock"],
    "Progressive Nirnroot Satchel": ["Progressive Nirnroot Satchel"],
    "Progressive Septim Satchel": ["Progressive Septim Satchel"],
    "Progressive Armor Set": ["Progressive Armor Set"],
    "Progressive Class Level": progressive_class_level_items,
    "Fortify Attribute": attribute_useful_items,
    "Region Access": region_unlock_items,
} 