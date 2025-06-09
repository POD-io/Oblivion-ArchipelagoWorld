from worlds.generic.Rules import set_rule
from BaseClasses import MultiWorld
from typing import List

def set_rules(multiworld: MultiWorld, player: int) -> None:
    """
    Set the logical rules for Oblivion Remastered.
    Each shrine quest completion requires having the corresponding unlock token.
    Shrine offerings are handled by the game/mod, not the multiworld logic.
    """
    
    # Get the world instance to access active shrines
    world = multiworld.worlds[player]
    
    for shrine in world.active_shrines:
        location_name = f"{shrine} Quest Complete"
        token_name = f"{shrine} Shrine Token"
        
        # Each shrine quest just requires its own token
        # Offerings are handled by the game (vanilla items or free_offerings mode)
        set_rule(
            multiworld.get_location(location_name, player),
            lambda state, token=token_name: state.has(token, player)
        )

 