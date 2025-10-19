from dataclasses import dataclass
from Options import Choice, DefaultOnToggle, Toggle, Range, PerGameCommonOptions, OptionDict

# Goal Settings
class OblivionGoal(Choice):
    """
    Choose your victory condition:
    
    Arena: Complete 21 Arena matches and become Grand Champion
    Gatecloser: Close X Oblivion Gates (number set by Gate Count)
    Shrine Seeker: Complete X Daedric Shrine quests (number set by Shrine Goal)
    Dungeon Delver: Complete all dungeons in your seed. (Regions * Dungeons per Region)
    Light the Dragonfires: Complete the Main Quest
    """
    display_name = "Goal"
    option_arena = 0
    option_gatecloser = 1
    option_shrine_seeker = 2
    option_dungeon_delver = 3
    option_light_the_dragonfires = 4
    default = 4

class GateCount(Range):
    """
    Number of Oblivion Gates available as location checks. Gates require Oblivion Gate Keys to access.
    
    When Goal is Gatecloser: You must close this many gates for victory.
    When Goal is NOT Gatecloser: This many gates are available as location checks.
    When Goal is Light the Dragonfires: This setting is ignored (set to 0 automatically).
    
    Set to 0 to disable Gate content entirely (only allowed when Goal is not Gatecloser).
    """
    display_name = "Gate Count"
    range_start = 0
    range_end = 10
    default = 5

class ShrineGoal(Range):
    """
    For Shrine Seeker goal: How many Daedric Shrine quests you need to complete for victory.
    You can complete any of the available shrines to reach this goal.
    
    Only relevant when Goal is Shrine Seeker. Ignored for other goals.
    """
    display_name = "Shrine Goal"
    range_start = 1
    range_end = 15
    default = 5

class ShrineCount(Range):
    """
    Number of Daedric Shrine quests available as location checks. Shrines require Shrine Unlock Tokens to access.
    
    When Goal is Shrine Seeker: This many total shrines are available, complete any X (set by Shrine Goal) to win.
    When Goal is NOT Shrine Seeker: This many shrines are available as location checks.

    Useful for increased routing flexibility.
    Set to 0 to disable shrine content entirely (only allowed when Goal is not Shrine Seeker).
    """
    display_name = "Shrine Count"
    range_start = 0
    range_end = 15
    default = 5

class RegionUnlocks(Range):
    """
    Number of regions that will appear as unlock items.
    Only these regions' dungeons will be available as location checks.

    Note: You are granted one of these region unlocks at the start of the game.
    """
    display_name = "Regions per Seed"
    range_start = 1
    range_end = 10
    default = 5

class DungeonsPerRegion(Range):
    """
    Maximum number of dungeons selected from each unlocked region.
    If Dungeon Delver is your goal, you will need to complete every dungeon in the selected regions.

    Note: If a region has fewer dungeons than this value, all of its dungeons are selected.
    """
    display_name = "Dungeons per Region"
    range_start = 1
    range_end = 24
    default = 3


# Class System Options
class ClassSelection(Choice):
    """
    Choose your character class:
    
    OFF: No class location checks
    RANDOM: Randomly select a class from all available classes
    [Class Names]: Choose a specific class
    
    When enabled, all associated major skills for the class will be checks.
    """
    display_name = "Class Selection"
    option_off = 0
    option_random = 1
    option_acrobat = 2
    option_agent = 3
    option_archer = 4
    option_assassin = 5
    option_barbarian = 6
    option_bard = 7
    option_battlemage = 8
    option_crusader = 9
    option_healer = 10
    option_knight = 11
    option_mage = 12
    option_monk = 13
    option_nightblade = 14
    option_pilgrim = 15
    option_rogue = 16
    option_scout = 17
    option_sorcerer = 18
    option_spellsword = 19
    option_thief = 20
    option_warrior = 21
    option_witchhunter = 22
    default = 1

class ClassLevelMaximum(Range):
    """
    Maximum class level when Class Selection is enabled.
    This number will determine how many Progressive <Class> items are available in the item pool.
    
    Each level provides 14 additional skill checks (2 per class skill).
    With the default of 3, this adds 42 checks.

    Note: This does not change how you level up in-game. This is for AP checks only.

    Ignored when Class Selection is Off.
    """
    display_name = "Class Level Maximum"
    range_start = 1
    range_end = 5
    default = 3

class StartWithClass(Toggle):
    """
    When true: Start with your above selected class unlocked immediately.

    When false: You must receive the first Progressive <Class> Level in the multiworld
    to unlock class skill checks.

    Note: Your first Class level is always located in Sphere 1. [early locations]
    
    Ignored when Class Selection is Off.
    """
    display_name = "Start With Class"
    default = 0

class ExcludedSkills(OptionDict):
    """
    Exclude specific skills from the class system.
    
    Set a skill to 1 (or any non-zero #) to exclude it (it will not generate checks).
    
    Only affects major skills for your selected class.
    Example: If you're an Acrobat and exclude Acrobatics and Sneak, 
    you'll only get checks for your remaining 5 major skills.
    
    Ignored when Class Selection is Off.
    """
    display_name = "Excluded Skills"
    default = {
        "Acrobatics": 0,
        "Alchemy": 0,
        "Alteration": 0,
        "Armorer": 0,
        "Athletics": 0,
        "Blade": 0,
        "Block": 0,
        "Blunt": 0,
        "Conjuration": 0,
        "Destruction": 0,
        "Hand-to-Hand": 0,
        "Heavy Armor": 0,
        "Illusion": 0,
        "Light Armor": 0,
        "Marksman": 0,
        "Mercantile": 0,
        "Mysticism": 0,
        "Restoration": 0,
        "Security": 0,
        "Sneak": 0,
        "Speechcraft": 0,
    }
    valid_keys = frozenset([
        "Acrobatics", "Alchemy", "Alteration", "Armorer", "Athletics", "Blade", "Block", "Blunt",
        "Conjuration", "Destruction", "Hand-to-Hand", "Heavy Armor", "Illusion", "Light Armor",
        "Marksman", "Mercantile", "Mysticism", "Restoration", "Security", "Sneak", "Speechcraft"
    ])

# Content Counts
class ArenaMatches(Range):
    """
    Number of Arena matches available as location checks. Arena matches require Arena Rank items to access.
    
    When Goal is Arena: This setting is IGNORED - all 21 matches are always available and required for victory.
    When Goal is NOT Arena: This many arena matches (1 through X) are available as location checks.
    
    Set to 0 to disable arena content entirely (only allowed when Goal is not Arena).
    Note: Arena requires Progressive Arena Rank items to unlock each rank's matches.
    """
    display_name = "Arena Matches"
    range_start = 0
    range_end = 21
    default = 12


# Quality of Life
class ExtraGateKeys(Range):
    """
    Additional Oblivion Gate Keys beyond the base amount needed.
    
    Adds extra Gate Keys to the item pool beyond the base number, which is equal to the number of gates. 
    Useful for increased routing flexibility and redundancy in case of hard to reach checks.
    """
    display_name = "Extra Gate Keys"
    range_start = 0
    range_end = 5
    default = 0

class OblivionGateVision(Choice):
    """
    Determines how Oblivion Gate map markers are visible:
    
    On: Gate markers are visible immediately
    Off: Gate markers must be found (vanilla behavior)
    Item: Gate markers become visible when you find the Oblivion Gate Vision item (default)
    
    Ignored when Gate Count is 0.
    """
    display_name = "Oblivion Gate Vision"
    option_on = 0
    option_off = 1
    option_item = 2
    default = 2

class FreeOfferings(DefaultOnToggle):
    """
    When true: Daedric Shrine offering items are automatically provided when needed.
    When false: You must find or obtain shrine offerings yourself in the game.
    """
    display_name = "Free Shrine Offerings"

class FastTravelItem(Toggle):
    """
    When true: Fast travel is disabled until you find the Fast Travel item.
    """
    display_name = "Fast Travel Item"
    default = 0

class DungeonMarkerMode(Choice):
    """
    Controls how dungeon map markers are revealed and whether fast travel to them is enabled.

    Reveal and Fast Travel (default): All selected dungeon markers are revealed and fast travel is allowed.
    Reveal Only: All selected dungeon markers are shown as "rumors" (faded out), and must be ventured to normally.
    """
    display_name = "Dungeon Marker Mode"
    option_reveal_and_fast_travel = 0
    option_reveal_only = 1
    default = 0

class ShopScoutType(Choice):
    """
    How shop item scouting displays information.
    
    Off: No shop scouting - shop tab will not display any information
    Summary: Shows the receiving player name and item classification (Progression/Useful/Filler) - default
    Player Only: Shows only the receiving player name for each shop item
    Full Info: Shows the complete item name and receiving player (creates !hint commands)
    
    Note: Trap items are always disguised in Summary mode.
    """
    display_name = "Shop Scout Type"
    option_off = 0
    option_summary = 1
    option_player_only = 2
    option_full_info = 3
    default = 1

class FastArena(Toggle):
    """
    When true: Skip arena announcer dialogue before matches and fight immediately.
    When false: Must wait for announcer dialogue before match begins (default).
    """
    display_name = "Fast Arena"
    default = 0

@dataclass
class OblivionOptions(PerGameCommonOptions):
    # Goal Settings
    goal: OblivionGoal
    gate_count: GateCount
    shrine_goal: ShrineGoal  
    shrine_count: ShrineCount

    # Content Counts
    arena_matches: ArenaMatches
    region_unlocks: RegionUnlocks
    dungeons_per_region: DungeonsPerRegion

    # Class System
    class_selection: ClassSelection
    class_level_maximum: ClassLevelMaximum
    start_with_class: StartWithClass
    excluded_skills: ExcludedSkills

    # Quality of Life   
    extra_gate_keys: ExtraGateKeys
    gate_vision: OblivionGateVision
    free_offerings: FreeOfferings
    fast_travel_item: FastTravelItem
    dungeon_marker_mode: DungeonMarkerMode
    shop_scout_type: ShopScoutType
    fast_arena: FastArena
    # useful_items_percentage: UsefulItemsPercentage
