from dataclasses import dataclass
from Options import Choice, DefaultOnToggle, Range, PerGameCommonOptions

# Goal Settings
class OblivionGoal(Choice):
    """
    Choose your victory condition:
    
    Arena: Complete 21 Arena matches and become Grand Champion
    Gatecloser: Close X Oblivion Gates (number set by Gate Count)
    Shrine Seeker: Complete X Daedric Shrine quests (number set by Shrine Goal)
    """
    display_name = "Goal"
    option_arena = 0
    option_gatecloser = 1
    option_shrine_seeker = 2
    default = 1

class GateCount(Range):
    """
    Number of Oblivion Gates available as location checks. Gates require Oblivion Gate Keys to access.
    
    When Goal is Gatecloser: You must close this many gates for victory.
    When Goal is NOT Gatecloser: This many gates are available as location checks.
    
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
    
    Only used when Goal is Shrine Seeker. Ignored for other goals.
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
    default = 21

class SkillChecks(Range):
    """
    Number of Skill Increase locations available as location checks.

    """
    display_name = "Skill Checks"
    range_start = 10
    range_end = 30
    default = 20

class DungeonClears(Range):
    """
    Number of Dungeon Clear locations available as location checks.
    
    """
    display_name = "Dungeon Clears"
    range_start = 0
    range_end = 30
    default = 10

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
    """
    display_name = "Oblivion Gate Vision"
    option_on = 0
    option_off = 1
    option_item = 2
    default = 2

class FreeOfferings(DefaultOnToggle):
    """
    When enabled, Daedric Shrine offering items are automatically provided when needed.
    When disabled, you must find or obtain shrine offerings yourself in the game.
    """
    display_name = "Free Shrine Offerings"

@dataclass
class OblivionOptions(PerGameCommonOptions):
    # Goal Settings
    goal: OblivionGoal
    gate_count: GateCount
    shrine_goal: ShrineGoal  
    shrine_count: ShrineCount
    
    # Content Counts
    arena_matches: ArenaMatches
    skill_checks: SkillChecks
    dungeon_clears: DungeonClears
    
    # Quality of Life   
    extra_gate_keys: ExtraGateKeys
    gate_vision: OblivionGateVision
    free_offerings: FreeOfferings
    # useful_items_percentage: UsefulItemsPercentage
