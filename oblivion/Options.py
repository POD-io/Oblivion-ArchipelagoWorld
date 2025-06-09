from dataclasses import dataclass
from Options import Choice, DefaultOnToggle, Range, PerGameCommonOptions

class OblivionGoal(Choice):
    """
    Choose the victory condition for Oblivion Remastered.
    
    Complete Specific Count: Complete a specific number of shrine quests
    Complete All Shrines: Complete every shrine that spawns in your seed
    """
    display_name = "Goal"
    option_complete_specific_count = 0
    option_complete_all_shrines = 1
    default = 0

class ShrineCountRequired(Range):
    """
    Number of shrine quests required to complete when goal is set to Complete Specific Count.
    """
    display_name = "Required Shrine Count"
    range_start = 1
    range_end = 15
    default = 10

class TotalActiveShrineCount(Range):
    """
    Total number of Daedric shrines that will be active/available in this seed.
    Lower values create more focused runs with fewer shrine options.
    Higher values provide more choice but longer games.
    """
    display_name = "Total Active Shrines"
    range_start = 3
    range_end = 15
    default = 5

class FreeOfferings(DefaultOnToggle):
    """
    When enabled, shrine offering items are automatically provided when needed.
    When disabled, you must find or obtain shrine offerings yourself.
    """
    display_name = "Free Shrine Offerings"

class UsefulItemsWeight(Range):
    """
    Multiplier for how often useful items appear as filler items.
    Higher values = more useful items, lower values = more scrolls and basic filler.
    """
    display_name = "Useful Items Weight"
    range_start = 1
    range_end = 5
    default = 2

@dataclass
class OblivionOptions(PerGameCommonOptions):
    goal: OblivionGoal
    shrine_count_required: ShrineCountRequired  
    total_active_shrines: TotalActiveShrineCount
    free_offerings: FreeOfferings
    useful_items_weight: UsefulItemsWeight 