from dataclasses import dataclass
from Options import Choice, DefaultOnToggle, Toggle, Range, PerGameCommonOptions, OptionDict, DeathLink, OptionGroup

# =====================================================
# VICTORY CONDITION
# =====================================================

class OblivionGoal(Choice):
    """
    Choose your victory condition:
    
    Arena: Complete 21 Arena matches and become Grand Champion
    Gatecloser: Close X Oblivion Gates (number set by Gate Count)
    Shrine Seeker: Complete X Daedric Shrine quests (number set by Shrine Goal)
    Dungeon Delver: Complete all dungeons in your seed. (Regions * Dungeons per Region)
    Light the Dragonfires: Complete the Main Quest
    Nirnsanity: Collect Nirnroot plants and complete the Seeking Your Roots quest
    Treasure Hunter: Collect a specific amount of gold (set by Gold Goal)
    """
    display_name = "Goal"
    option_arena = 0
    option_gatecloser = 1
    option_shrine_seeker = 2
    option_dungeon_delver = 3
    option_light_the_dragonfires = 4
    option_nirnsanity = 5
    option_treasure_hunter = 6
    default = 4

# =====================================================
# GOAL-SPECIFIC SETTINGS
# These settings customize your chosen victory condition
# =====================================================



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



class GoldGoal(Range):
    """
    For Treasure Hunter goal: How much gold you need to collect for victory.
    
    Gold is tracked in increments with checks along the way.
    Your Gold capacity is gated by Progressive Septim Satchels.
    
    Only relevant when Goal is Treasure Hunter. Ignored for other goals.
    """
    display_name = "Gold Goal"
    range_start = 1000
    range_end = 100000
    default = 10000

# =====================================================
# WORLD CONTENT SETTINGS
# These settings determine what content appears in all seeds
# =====================================================

class ShrineCount(Range):
    """
    Number of Daedric Shrine quests available as location checks. Shrines require Shrine Unlock Tokens to access.
    
    When Goal is Shrine Seeker: This many total shrines are available, complete any X (set by Shrine Goal) to win.
    When Goal is NOT Shrine Seeker: This many shrines are available as location checks.
    """
    display_name = "Shrine Count"
    range_start = 0
    range_end = 15
    default = 5

class GateCount(Range):
    """
    Number of Oblivion Gates available as location checks. Gates require Oblivion Gate Keys to access.
    
    When Goal is Gatecloser: You must close this many gates for victory.
    When Goal is NOT Gatecloser: This many gates are available as location checks.
    When Goal is Light the Dragonfires: This setting is ignored.
    """
    display_name = "Gate Count"
    range_start = 0
    range_end = 20
    default = 5

class ArenaMatches(Range):
    """
    Number of Arena matches available as location checks. Arena matches require Arena Rank items to access.
    
    When Goal is Arena: This setting is IGNORED - all 21 matches are always available and required for victory.
    When Goal is NOT Arena: This many arena matches (1 through X) are available as location checks.
    """
    display_name = "Arena Matches"
    range_start = 0
    range_end = 21
    default = 12

class NirnrootCount(Range):
    """
    Number of Nirnroot harvesting location checks available in the world.
    
    When Goal is Nirnsanity: You must collect this many Nirnroot for victory. Your Nirnroot 
    harvesting limit is gated by Progressive Nirnroot Satchels.
    
    When Goal is NOT Nirnsanity: This many Nirnroot plants are available as location checks. 
    All are immediately harvestable with no capacity restrictions.
    """
    display_name = "Nirnroot Harvesting Checks"
    range_start = 0
    range_end = 100
    default = 0

class RegionUnlocks(Range):
    """
    Number of regions that will appear as unlock items.
    Only these regions' dungeons and sidequests will be available as location checks.

    Set to 0 to disable regional dungeon content entirely (only allowed when Goal is not Dungeon Delver).
    Note: When regions > 0, you are granted one region unlock at the start of the game.
    """
    display_name = "Regions per Seed"
    range_start = 0
    range_end = 10
    default = 5

class DungeonsPerRegion(Range):
    """
    Maximum number of dungeons selected from each unlocked region.
    If Dungeon Delver is your goal, you will need to complete every dungeon in the selected regions.

    Note: If a region has fewer dungeons than this value, all of its dungeons are selected.
    Note: This setting is ignored when region_unlocks is set to 0.
    """
    display_name = "Dungeons per Region"
    range_start = 0
    range_end = 24
    default = 3

class WealthSidequestCount(Range):
    """
    Number of wealth-focused sidequests that will be randomly selected and included in the seed.
    WARNING: These sidequests require accumulating a significant amount of gold to purchase expensive items.

    Note: Most sidequests require specific region access. You may receive less sidequests depending on the value of RegionUnlocks above.
    """
    display_name = "Wealth Sidequest Count"
    range_start = 0
    range_end = 10
    default = 0

class ExplorationSidequestCount(Range):
    """
    Number of exploration-focused sidequests that will be randomly selected and included in the seed.
    These sidequests involve exploration and adventure activities.

    Note: Most sidequests require specific region access. You may receive less sidequests depending on the value of RegionUnlocks above.
    """
    display_name = "Exploration Sidequest Count"
    range_start = 0
    range_end = 5
    default = 2

class DungeonKills(Range):
    """
    Number of dungeon kill location checks (enemies killed in dungeon or most interior cells).
    Set to 0 to disable dungeon kill checks.
    
    When regions are enabled, checks are divided evenly across regions: each region unlock
    makes the next batch accessible. For example, 50 kills with 5 regions = 10 kills per
    region batch, so you start with 10 accessible and gain 10 more per region unlock.
    """
    display_name = "Dungeon Kill Checks"
    range_start = 0
    range_end = 200
    default = 50

class OverworldKills(Range):
    """
    Number of overworld kill location checks (enemies killed in Tamriel).
    Set to 0 to disable overworld kill checks.
    
    When regions are enabled, checks are divided evenly across regions: each region unlock
    makes the next batch accessible. For example, 40 kills with 5 regions = 8 kills per
    region batch, so you start with 8 accessible and gain 8 more per region unlock.
    """
    display_name = "Overworld Kill Checks"
    range_start = 0
    range_end = 200
    default = 40

# =====================================================
# CLASS SYSTEM
# =====================================================

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
    option_acrobat = 1
    option_agent = 2
    option_archer = 3
    option_assassin = 4
    option_barbarian = 5
    option_bard = 6
    option_battlemage = 7
    option_crusader = 8
    option_healer = 9
    option_knight = 10
    option_mage = 11
    option_monk = 12
    option_nightblade = 13
    option_pilgrim = 14
    option_rogue = 15
    option_scout = 16
    option_sorcerer = 17
    option_spellsword = 18
    option_thief = 19
    option_warrior = 20
    option_witchhunter = 21
    option_random_class = 22
    default = "random_class"

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

# =====================================================
# QUALITY OF LIFE
# =====================================================
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

class ExtraNirnroot(Range):
    """
    Additional Nirnroot multiworld items beyond the Nirnroot Count setting.
    
    Provides a buffer so you don't need to find every single Nirnroot location check.
    This adds extra Nirnroot items to the multiworld item pool.
    
    Only relevant when Goal is Nirnsanity. Ignored for other goals.
    """
    display_name = "Extra Nirnroot"
    range_start = 0
    range_end = 25
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
    Locks the fast travel system behind an Archipelago item.
    
    When true: You cannot use fast travel until you receive the "Fast Travel" item from the multiworld.
    When false: Fast travel is available from the start (vanilla behavior).
    
    Warning: Fast Travel item can be anywhere in the seed, including late locations.
    """
    display_name = "Fast Travel Item"
    default = 0

class DungeonMarkerMode(Choice):
    """
    Controls how dungeon map markers appear on your map.

    Reveal and Fast Travel: All selected dungeon locations are revealed on the map immediately and can be fast traveled to (if Fast Travel Item allows).
    Reveal Only: Dungeon locations appear as "rumors" (grayed out markers) - you can see them but must physically travel there first.
    
    Note: This setting only affects dungeon map markers, not the overall fast travel system.
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

class AutoTracking(Toggle):
    """
    This feature enables auto-tracking for Nirnroot and Boss Chests.
    
    When true: Guides the player to any nearby Nirnroot or Boss Chest(if included in seed). 
    Entering the overworld switches to Nirnroot tracking. Entering a
    dungeon switches to Boss Chest tracking.
    
    Note: F11 can be used to manually cycle the mode or entirely disable the feature.
    """
    display_name = "Auto Tracking"
    default = 0

class SilentAutoTracking(Toggle):
    """
    When enabled, auto-tracking updates the in-game quest marker silently -
    no guidance via Message is shown. Cuts down on notifications in the Message queue.

    When disabled (default), compass direction is shown via Message 
    whenever the tracked target changes. 
    Note: The polarity of the message is incorrect in some dungeons.
    """
    display_name = "Silent Auto-Tracking"
    default = 0

# =====================================================
# TRAPS
# =====================================================

class TrapPercentage(Range):
    """
    Percentage of filler item slots replaced by traps (0-20%). Set to 0 to disable traps entirely.
    Trap types and their relative frequency are controlled by the weight settings below.
    """
    display_name = "Trap Percentage"
    range_start = 0
    range_end = 20
    default = 0

class MovementTrapWeight(Range):
    """
    Relative weight for Movement Trap. Set to 0 to disable this trap type.
    By default, 60% of traps will be Movement Traps.
    """
    display_name = "Movement Trap Weight"
    range_start = 0
    range_end = 100
    default = 60

class SpawnTrapWeight(Range):
    """
    Relative weight for Spawn Trap. Set to 0 to disable this trap type.
    By default, 30% of traps will be Spawn Traps.
    """
    display_name = "Spawn Trap Weight"
    range_start = 0
    range_end = 100
    default = 30

class StormTrapWeight(Range):
    """
    Relative weight for Storm Trap. Set to 0 to disable this trap type.
    By default, 10% of traps will be Storm Traps.
    """
    display_name = "Storm Trap Weight"
    range_start = 0
    range_end = 100
    default = 10




class DungeonWarp(Choice):
    """
    Automatically warp the player out to the overworld when completing a seeded dungeon.
    
    Off: No warp (vanilla behavior)
    On: All dungeons that provide a check offer a warp-out option upon completion
    Item: Warp functionality unlocked when you receive the "Dungeon Warp" item from the multiworld
    Early Item: Same as Item, but the Dungeon Warp item is forced into early locations
    """
    display_name = "Dungeon Warp"
    option_off = 0
    option_on = 1
    option_item = 2
    option_early_item = 3
    default = 2

@dataclass
class OblivionOptions(PerGameCommonOptions):
    # Victory Condition
    goal: OblivionGoal
    
    # Goal-Specific Settings
    shrine_goal: ShrineGoal  
    gold_goal: GoldGoal

    # World Content Settings
    gate_count: GateCount
    shrine_count: ShrineCount
    arena_matches: ArenaMatches
    nirnroot_count: NirnrootCount
    region_unlocks: RegionUnlocks
    dungeons_per_region: DungeonsPerRegion
    wealth_sidequest_count: WealthSidequestCount
    exploration_sidequest_count: ExplorationSidequestCount
    dungeon_kills: DungeonKills
    overworld_kills: OverworldKills

    # Class System
    class_selection: ClassSelection
    class_level_maximum: ClassLevelMaximum
    start_with_class: StartWithClass
    excluded_skills: ExcludedSkills

    # Quality of Life
    extra_gate_keys: ExtraGateKeys
    extra_nirnroot: ExtraNirnroot
    gate_vision: OblivionGateVision
    free_offerings: FreeOfferings
    fast_travel_item: FastTravelItem
    dungeon_marker_mode: DungeonMarkerMode
    shop_scout_type: ShopScoutType
    fast_arena: FastArena
    auto_tracking: AutoTracking
    silent_auto_tracking: SilentAutoTracking
    dungeon_warp: DungeonWarp
    death_link: DeathLink

    # Traps
    trap_percentage: TrapPercentage
    movement_trap_weight: MovementTrapWeight
    spawn_trap_weight: SpawnTrapWeight
    storm_trap_weight: StormTrapWeight
    # useful_items_percentage: UsefulItemsPercentage

oblivion_option_groups = [
    OptionGroup("Victory Condition", [
        OblivionGoal
    ]),
    OptionGroup("Goal-Specific Settings", [
        ShrineGoal,
        GoldGoal
    ]),
    OptionGroup("World Content Settings", [
        ShrineCount,
        GateCount,
        ArenaMatches,
        NirnrootCount,
        RegionUnlocks,
        DungeonsPerRegion,
        WealthSidequestCount,
        ExplorationSidequestCount,
        DungeonKills,
        OverworldKills
    ]),
    OptionGroup("Class System", [
        ClassSelection,
        ClassLevelMaximum,
        StartWithClass,
        ExcludedSkills
    ]),
    OptionGroup("Quality of Life", [
        ExtraGateKeys,
        ExtraNirnroot,
        OblivionGateVision,
        FreeOfferings,
        FastTravelItem,
        DungeonMarkerMode,
        DungeonWarp,
        ShopScoutType,
        FastArena,
        AutoTracking,
        SilentAutoTracking
    ]),
    OptionGroup("Traps", [
        TrapPercentage,
        MovementTrapWeight,
        SpawnTrapWeight,
        StormTrapWeight,
    ]),
]
