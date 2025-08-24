from BaseClasses import MultiWorld
from typing import List

def set_rules(multiworld: MultiWorld, player: int) -> None:
    """
    Set the logical rules for Oblivion Remastered.
    
    Shrine Rules: Each shrine quest completion requires having the corresponding unlock token.
    Arena Rules: Arena matches require Progressive Arena Rank items (higher matches need more ranks).
    Gate Rules: Gate locations are always accessible.
    Shop Rules: Progressive Shop Stock system with 5 sets of 3 locations each.
        - Set 1 (1/10/100): Always available
        - Set 2 (2/20/200): Requires Progressive Shop Stock 1
        - Set 3 (3/30/300): Requires Progressive Shop Stock 2
        - Set 4 (4/40/400): Requires Progressive Shop Stock 3
        - Set 5 (5/50/500): Requires Progressive Shop Stock 4
    """
    
    # Get the world instance to access active settings
    world = multiworld.worlds[player]
    
    # ===== SHRINE RULES =====
    # Only set rules for shrine locations if shrines are enabled
    if world.shrines_enabled:
        for shrine in world.active_shrines:
            location_name = f"{shrine} Quest Complete"
            token_name = f"{shrine} Shrine Token"
            
            location = multiworld.get_location(location_name, player)
            location.access_rule = lambda state, token=token_name: state.has(token, player)
    
    # ===== ARENA RULES =====
    # Arena matches require Progressive Arena Rank items
    if world.arena_enabled:
        # Arena progression tiers: 
        # Matches 1-3: Need 1 Progressive Arena Rank
        # Matches 4-6: Need 2 Progressive Arena Rank  
        # Matches 7-9: Need 3 Progressive Arena Rank
        # Matches 10-12: Need 4 Progressive Arena Rank
        # Matches 13-15: Need 5 Progressive Arena Rank
        # Matches 16-18: Need 6 Progressive Arena Rank
        # Matches 19-21: Need 7 Progressive Arena Rank
        
        for match_num in range(1, min(world.arena_count + 1, 22)):
            location_name = f"Arena Match {match_num} Victory"
            
            # Calculate required rank for this match
            required_ranks = min(((match_num - 1) // 3) + 1, 7)
            
            location = multiworld.get_location(location_name, player)
            location.access_rule = lambda state, ranks=required_ranks: state.has("Progressive Arena Rank", player, ranks)
    
    # ===== GATE RULES =====
    # Gate locations require cumulative keys (sequential progression)
    for gate_num in range(1, world.gate_count + 1):
        gate_location_name = f"Gate {gate_num} Closed"
        
        required_keys = gate_num
        
        location = multiworld.get_location(gate_location_name, player)
        location.access_rule = lambda state, keys=required_keys: state.has("Oblivion Gate Key", player, keys)
    
    # ===== PROGRESSIVE SHOP STOCK RULES =====
    # Set 1 (always available): Value 1, 10, 100 - no requirements
    # Set 2 requires 1 Progressive Shop Stock: Value 2, 20, 200
    # Set 3 requires 2 Progressive Shop Stock: Value 3, 30, 300  
    # Set 4 requires 3 Progressive Shop Stock: Value 4, 40, 400
    # Set 5 requires 4 Progressive Shop Stock: Value 5, 50, 500
    
    shop_sets = [
        ([2, 20, 200], 1),
        ([3, 30, 300], 2),
        ([4, 40, 400], 3),
        ([5, 50, 500], 4)
    ]
    
    for values, required_count in shop_sets:
        for value in values:
            location_name = f"Shop Item Value {value}"
            location = multiworld.get_location(location_name, player)
            location.access_rule = lambda state, count=required_count: state.has("Progressive Shop Stock", player, count)
    
    # [DISABLED_STONES] Wayshrine/Runestone/Doomstone rules disabled - debating if i want this
    # # ===== WAYSHRINE RULES =====
    # wayshrine_location = multiworld.get_location("Visit a Wayshrine", player)
    # wayshrine_location.access_rule = lambda state: True
    # 
    # # ===== RUNESTONE RULES =====
    # runestone_location = multiworld.get_location("Visit a Runestone", player)
    # runestone_location.access_rule = lambda state: True
    # 
    # # ===== DOOMSTONE RULES =====
    # doomstone_location = multiworld.get_location("Visit a Doomstone", player)
    # doomstone_location.access_rule = lambda state: True
    
    # ===== AYLEID WELL RULES =====
    # Ayleid Well location is always accessible
    ayleid_well_location = multiworld.get_location("Visit an Ayleid Well", player)
    ayleid_well_location.access_rule = lambda state: True
    
    # ===== CLASS SKILL RULES =====
    # Class skill locations require Progressive Class Level items
    if world.selected_class is not None:
        from .Classes import get_class_skills
        class_skills = get_class_skills(world.selected_class)
        
        # Each Progressive Class Level provides 2 additional skill increases per class skill
        for level in range(1, world.class_level_maximum + 1):
            for skill in class_skills:
                # Each level provides 2 skill increases per skill
                for skill_level in range(1, 3):  # 2 skill increases per skill per level
                    # Calculate the skill increase number (1-40 for 20 levels)
                    skill_increase_num = (level - 1) * 2 + skill_level
                    location_name = f"{skill} Skill Increase {skill_increase_num}"
                    
                    # Each level requires that many Progressive Class Level items
                    required_levels = level
                    
                    location = multiworld.get_location(location_name, player)
                    location.access_rule = lambda state, levels=required_levels, item_name=world.progressive_class_level_item_name: state.has(item_name, player, levels)
    
    # DUNGEON RULES - require corresponding region Access item
    if world.dungeons_enabled:
        from .Locations import DUNGEON_REGIONS
        for dungeon_name in world.selected_dungeons:
            region_name = DUNGEON_REGIONS.get(dungeon_name)
            if not region_name:
                continue
            access_item = f"{region_name} Access"
            location = multiworld.get_location(dungeon_name, player)
            # If the region is unlocked at start, no item is required; otherwise require the region access item.
            if region_name in getattr(world, "starting_unlocked_regions", []):
                location.access_rule = lambda state: True
            else:
                location.access_rule = lambda state, item_name=access_item: state.has(item_name, player)