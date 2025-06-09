"""
Shrine Progression Configuration for Oblivion Remastered

This module handles the selection and progression logic for Daedric shrine quests.
It provides weighted randomization for shrine selection, tier-based progression
requirements, and offering management for the free_offerings mode.

Key Components:
- SHRINE_PROGRESSION_TIERS: Defines when shrines become available based on other completions
- SHRINE_SELECTION_WEIGHTS: Controls likelihood of shrine selection when < 15 shrines active  
- SHRINE_OFFERINGS: Required items for each shrine when free_offerings is enabled
"""

## This is a WIP. Included this in case we find that some shrines are too difficult 
## to start with, we, so we can use this to move them to later tiers.
## This ensures player has likely received some useful items before they start.

from typing import Dict, List, Set

# Shrine difficulty/level tiers - controls when shrines become available
# Lower numbers = earlier availability, higher numbers = later availability
SHRINE_PROGRESSION_TIERS = {
    # Tier 1 - available immediately
    "Azura": 1,
    "Meridia": 1, 
    "Namira": 1,
    "Sanguine": 1,
    
    # Tier 2 - requires 1-2 other shrines completed
    "Nocturnal": 2,
    "Hircine": 2,
    "Malacath": 2,
    "Peryite": 2,
    
    # Tier 3 - requires 3-4 other shrines completed) 
    "Boethia": 3,
    "Mephala": 3,
    "Clavicus Vile": 3,
    "Vaermina": 3,
    
    # Tier 4 - requires 5+ other shrines completed
    "Molag Bal": 4,
    
    # Tier 5 - requires 7+ other shrines completed
    "Hermaeus Mora": 5,
    "Sheogorath": 5,
}

# Shrine selection weights for randomization
# Higher values = more likely to be selected when using fewer than 15 shrines
# Might remove this, but kept it included for now.
SHRINE_SELECTION_WEIGHTS = {
    "Azura": 10,
    "Sheogorath": 8,
    "Hermaeus Mora": 8,
    "Meridia": 7,
    
    "Nocturnal": 6,
    "Hircine": 6,
    "Molag Bal": 6,
    "Boethia": 5,
    "Clavicus Vile": 5,
    
    "Mephala": 4,
    "Namira": 4,
    "Peryite": 4,
    "Malacath": 4,
    "Vaermina": 4,
    "Sanguine": 4,
}

# Required offerings for each shrine
# These are the items that get auto-provided when free_offerings is enabled
SHRINE_OFFERINGS = {
    "Azura": ["Glow Dust"],
    "Boethia": ["Daedra Heart"],
    "Clavicus Vile": ["Cheap Wine"],  
    "Hermaeus Mora": ["Daedra Heart"], 
    "Hircine": ["Wolf Pelt"],
    "Malacath": ["Troll Fat"],
    "Mephala": ["Nightshade"],
    "Meridia": ["Glow Dust"],
    "Molag Bal": ["Lion Pelt"],
    "Namira": ["Ectoplasm"],
    "Nocturnal": ["Lesser Soul Gem"],
    "Peryite": ["Daedra Heart"],
    "Sanguine": ["Cyrodilic Brandy"],
    "Sheogorath": ["Lettuce", "Yarn", "Lesser Soul Gem"],
    "Vaermina": ["Black Soul Gem"],
}

def get_shrine_progression_requirements(shrine_name: str) -> int:
    """
    Get the number of other shrines that must be completed before this shrine becomes accessible.
    Returns 0 for tier 1 shrines, increasing numbers for higher tiers.
    
    EDIT THESE VALUES to change progression requirements:
    - Tier 1: 0 shrines required (immediate access)
    - Tier 2: 1 shrine required  
    - Tier 3: 3 shrines required
    - Tier 4: 5 shrines required
    - Tier 5: 7 shrines required
    """
    tier = SHRINE_PROGRESSION_TIERS.get(shrine_name, 1)
    
    requirements = {
        1: 0,  # Immediate access
        2: 1,  # Requires 1 other shrine
        3: 3,  # Requires 3 other shrines  
        4: 5,  # Requires 5 other shrines
        5: 7,  # Requires 7 other shrines
    }
    
    return requirements.get(tier, 0)

def select_active_shrines(total_count: int, random_source, required_shrines: List[str] = None) -> List[str]:
    """
    Select which shrines will be active for this seed based on weighted randomization.
    
    Args:
        total_count: Number of shrines to select (from options)
        random_source: Archipelago's random number generator
        required_shrines: Shrines that must be included (from start_inventory tokens)
        
    Returns:
        List of shrine names that will be active
    """
    all_shrines = list(SHRINE_SELECTION_WEIGHTS.keys())
    
    if required_shrines is None:
        required_shrines = []
    
    if total_count >= len(all_shrines):
        return all_shrines  # Use all shrines
    
    # Start with required shrines (from start_inventory)
    selected = required_shrines.copy()
    remaining_count = total_count - len(selected)
    remaining_shrines = [s for s in all_shrines if s not in selected]
    
    # Weighted selection for remaining slots
    for _ in range(remaining_count):
        if not remaining_shrines:
            break
            
        # Calculate weights for remaining shrines
        weights = [SHRINE_SELECTION_WEIGHTS[shrine] for shrine in remaining_shrines]
        
        # Select one shrine based on weights
        chosen_shrine = random_source.choices(remaining_shrines, weights=weights, k=1)[0]
        selected.append(chosen_shrine)
        remaining_shrines.remove(chosen_shrine)
    
    return selected

def get_shrine_offerings(shrine_name: str) -> List[str]:
    """
    Get the required offering items for a shrine.
    Used when free_offerings is enabled.
    """
    return SHRINE_OFFERINGS.get(shrine_name, []) 