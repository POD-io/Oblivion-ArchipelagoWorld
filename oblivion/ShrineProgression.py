"""
Shrine Progression Configuration for Oblivion Remastered

This handles the selection and progression logic for Daedric shrines.
It provides level-based weighted randomization for shrine selection and the 
offering lookup table for free_offerings mode.
"""

from typing import Dict, List, Set

# Shrine tier weights for selection (lower numbers = higher selection weight)
SHRINE_TIER_WEIGHTS = {
    # Hard
    "Hermaeus Mora": 20,
    "Boethia": 20,
    "Clavicus Vile": 20,
    
    # Medium
    "Azura": 9,
    "Meridia": 9,
    "Hircine": 9,
    "Malacath": 9,
    "Vaermina": 9,
    "Peryite": 9,
    
    # Easy
    "Namira": 5,
    "Nocturnal": 5,
    "Sanguine": 5,
    "Sheogorath": 5,
    "Molag Bal": 5,
    "Mephala": 5,
}

# All available shrines
ALL_SHRINES = [
    "Azura",
    "Sheogorath", 
    "Hermaeus Mora",
    "Meridia",
    "Nocturnal",
    "Hircine",
    "Molag Bal",
    "Boethia",
    "Clavicus Vile",
    "Mephala",
    "Namira",
    "Peryite",
    "Malacath",
    "Vaermina",
    "Sanguine",
]

# Required offerings for each shrine (auto-sent when free_offerings is enabled)
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

def _calculate_shrine_weight(shrine_name: str) -> float:
    """
    Calculate selection weight for a shrine based on its tier.
    """
    tier_weight = SHRINE_TIER_WEIGHTS.get(shrine_name, 10)
    return max(15 - (tier_weight / 2), 1)

def select_active_shrines(total_count: int, random_source, required_shrines: List[str] = None) -> List[str]:
    """Select which shrines will be active for this seed based on tier-weighted randomization."""
    if required_shrines is None:
        required_shrines = []
    
    if total_count >= len(ALL_SHRINES):
        return ALL_SHRINES.copy() 
    
    # Start with required shrines (from start_inventory)
    selected = required_shrines.copy()
    remaining_count = total_count - len(selected)
    remaining_shrines = [s for s in ALL_SHRINES if s not in selected]
    
    # Weighted selection for remaining slots - favor lower level shrines
    for _ in range(remaining_count):
        if not remaining_shrines:
            break
            
        # Calculate weights for remaining shrines
        weights = [_calculate_shrine_weight(shrine) for shrine in remaining_shrines]
        
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