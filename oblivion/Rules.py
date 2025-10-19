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
        from .Classes import get_filtered_class_skills
        class_skills = get_filtered_class_skills(world.selected_class, world.excluded_skills)
        
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

    # MAIN QUEST (Light the Dragonfires) milestone rules
    if world.options.goal.current_key == "light_the_dragonfires":
        try:
            deliver_loc = multiworld.get_location("Deliver the Amulet", player)
            deliver_loc.access_rule = lambda state: state.has("Amulet of Kings", player)
        except Exception:
            pass
        try:
            gate_closed_loc = multiworld.get_location("Breaking the Siege of Kvatch: Gate Closed", player)
            gate_closed_loc.access_rule = lambda state: state.has("Kvatch Gate Key", player)
        except Exception:
            pass
        try:
            heir_loc = multiworld.get_location("Find the Heir", player)
            # Requires Deliver the Amulet completed first, plus Amulet + Key and Siege logically reachable
            heir_loc.access_rule = lambda state: (
                state.can_reach_location("Deliver the Amulet", player)
                and state.has("Amulet of Kings", player)
                and state.has("Kvatch Gate Key", player)
                and state.can_reach_location("Breaking the Siege of Kvatch", player)
            )
        except Exception:
            pass
        try:
            siege_loc = multiworld.get_location("Breaking the Siege of Kvatch", player)
            # Require that the Gate Closed stage be logically reachable (implies key access & gate closure path)
            siege_loc.access_rule = lambda state: state.can_reach_location("Breaking the Siege of Kvatch: Gate Closed", player)
        except Exception:
            pass
        try:
            weynon_loc = multiworld.get_location("Weynon Priory", player)
            # Weynon Priory requires completion of Find the Heir
            weynon_loc.access_rule = lambda state: state.can_reach_location("Find the Heir", player)
        except Exception:
            pass
        try:
            ms49_loc = multiworld.get_location("Battle for Castle Kvatch", player)
            # requires Siege first
            ms49_loc.access_rule = lambda state: state.can_reach_location("Breaking the Siege of Kvatch", player)
        except Exception:
            pass

    # MQ05 - The Path of Dawn: all checks require Encrypted Scroll of the Blades
        try:
            for name in [
                "The Path of Dawn: Acquire Commentaries Vol I",
                "The Path of Dawn: Acquire Commentaries Vol II",
                "The Path of Dawn: Acquire Commentaries Vol III",
                "The Path of Dawn: Acquire Commentaries Vol IV",
                "The Path of Dawn",
            ]:
                try:
                    loc = multiworld.get_location(name, player)
                    loc.access_rule = lambda state: state.has("Encrypted Scroll of the Blades", player)
                except Exception:
                    pass
        except Exception:
            pass

        # MQ06 - Mysterium Xarxes and Dagon Shrine
        try:
            mx_loc = multiworld.get_location("Dagon Shrine: Mysterium Xarxes Acquired", player)
            mx_loc.access_rule = lambda state: state.has("Dagon Shrine Passphrase", player)
        except Exception:
            pass
        try:
            dagon_loc = multiworld.get_location("Dagon Shrine", player)
            # Requires MX acquired (reachable) and Martin at Cloud Ruler Temple (Weynon Priory reachable)
            dagon_loc.access_rule = lambda state: (
                state.can_reach_location("Dagon Shrine: Mysterium Xarxes Acquired", player)
                and state.can_reach_location("Weynon Priory", player)
            )
        except Exception:
            pass
        try:
            harrow_loc = multiworld.get_location("Dagon Shrine: Kill Harrow", player)
            harrow_loc.access_rule = lambda state: state.has("Dagon Shrine Passphrase", player)
        except Exception:
            pass
        # Optional: Attack on Fort Sutch (requires completing Dagon Shrine and possessing Fort Sutch Gate Key)
        try:
            sutch_loc = multiworld.get_location("Attack on Fort Sutch", player)
            # Require Dagon Shrine to be reachable (completed) and the Fort Sutch Gate Key item
            sutch_loc.access_rule = lambda state: (
                state.can_reach_location("Dagon Shrine", player)
                and state.has("Fort Sutch Gate Key", player)
            )
        except Exception:
            pass

        # MQ07 - Spies: gated by Blades' Report and Weynon Priory
        try:
            spies_prereq = lambda state: (
                state.has("Blades' Report: Strangers at Dusk", player)
                and state.can_reach_location("Weynon Priory", player)
            )
            for name in [
                "Spies: Kill Saveri Faram",
                "Spies: Kill Jearl",
                "Spies",
            ]:
                try:
                    loc = multiworld.get_location(name, player)
                    loc.access_rule = spies_prereq
                except Exception:
                    pass
        except Exception:
            pass

    # MQ08 - Blood of the Daedra: requires Decoded Page (Daedric) + Weynon Priory reachable
        try:
            bod_loc = multiworld.get_location("Blood of the Daedra", player)
            bod_loc.access_rule = lambda state: (
                state.has("Decoded Page of the Xarxes: Daedric", player)
                and state.can_reach_location("Weynon Priory", player)
            )
        except Exception:
            pass

        # MQ09 - Blood of the Divines main + sub-steps: all require Decoded Page (Divine) + Weynon Priory
        try:
            div_page_rule = lambda state: (
                state.has("Decoded Page of the Xarxes: Divine", player)
                and state.can_reach_location("Weynon Priory", player)
            )
            for name in [
                "Blood of the Divines: Free Spirit 1",
                "Blood of the Divines: Free Spirit 2",
                "Blood of the Divines: Free Spirit 3",
                "Blood of the Divines: Free Spirit 4",
                "Blood of the Divines: Armor of Tiber Septim",
                "Blood of the Divines",
            ]:
                try:
                    loc = multiworld.get_location(name, player)
                    loc.access_rule = div_page_rule
                except Exception:
                    pass
        except Exception:
            pass

        # Bruma Gate - requires Bruma Gate Key item (independent MQ milestone)
        try:
            bruma_gate_loc = multiworld.get_location("Bruma Gate", player)
            bruma_gate_loc.access_rule = lambda state: state.has("Bruma Gate Key", player)
        except Exception:
            pass

        # Miscarcand + Great Welkynd Stone gated by Decoded Page: Ayleid + Weynon Priory
        try:
            ayleid_rule = lambda state: (
                state.has("Decoded Page of the Xarxes: Ayleid", player)
                and state.can_reach_location("Weynon Priory", player)
            )
            for name in [
                "Miscarcand: Great Welkynd Stone",
                "Miscarcand",
            ]:
                try:
                    loc = multiworld.get_location(name, player)
                    loc.access_rule = ayleid_rule
                except Exception:
                    pass
        except Exception:
            pass

        # Defense of Bruma and Great Gate gated by Decoded Page: Sigillum + Weynon Priory
        try:
            sig_rule = lambda state: (
                state.has("Decoded Page of the Xarxes: Sigillum", player)
                and state.can_reach_location("Weynon Priory", player)
            )
            for name in [
                "Defense of Bruma",
                "Great Gate",
            ]:
                try:
                    loc = multiworld.get_location(name, player)
                    loc.access_rule = sig_rule
                except Exception:
                    pass
        except Exception:
            pass

        # Paradise sequence gated by Paradise Access + all four pages + Weynon Priory
        try:
            paradise_rule = lambda state: (
                state.has("Paradise Access", player)
                and state.has("Decoded Page of the Xarxes: Daedric", player)
                and state.has("Decoded Page of the Xarxes: Divine", player)
                and state.has("Decoded Page of the Xarxes: Ayleid", player)
                and state.has("Decoded Page of the Xarxes: Sigillum", player)
                and state.can_reach_location("Dagon Shrine: Mysterium Xarxes Acquired", player)
                and state.can_reach_location("Dagon Shrine", player)
                and state.can_reach_location("Weynon Priory", player)
                and state.has("Cloud Ruler Temple Established", player)  # chapter milestone event item
            )
            for name in [
                "Paradise: Bands of the Chosen Acquired",
                "Paradise: Bands of the Chosen Removed",
                "Paradise",
            ]:
                try:
                    loc = multiworld.get_location(name, player)
                    loc.access_rule = paradise_rule
                except Exception:
                    pass
        except Exception:
            pass

        # Chapter event: Weynon Priory Quest Complete (establishes Cloud Ruler Temple)
        try:
            crt_loc = multiworld.get_location("Weynon Priory Quest Complete", player)
            crt_loc.access_rule = lambda state: state.can_reach_location("Weynon Priory", player)
        except Exception:
            pass

        # Chapter event: Paradise Complete (after reaching Paradise)
        try:
            paradise_complete_loc = multiworld.get_location("Paradise Complete", player)
            paradise_complete_loc.access_rule = lambda state: state.can_reach_location("Paradise", player)
        except Exception:
            pass

        # Final Victory: Light the Dragonfires (spoiler-log only event location)
        # Requires Paradise Complete event (chapter milestone)
        try:
            victory_loc = multiworld.get_location("Light the Dragonfires", player)
            victory_loc.access_rule = lambda state: (
                state.has("Dragonfires Ready", player)  # chapter milestone event item
                and state.can_reach_location("Weynon Priory", player)
            )
        except Exception:
            pass

    # BIRTHSIGN DOOMSTONE RULES - gated by their region access item
    birthsign_stones = [
        ("Visit the Tower Stone", "Heartlands"),
        ("Visit the Steed Stone", "Heartlands"),
        ("Visit the Warrior Stone", "West Weald"),
        ("Visit the Apprentice Stone", "West Weald"),
        ("Visit the Atronach Stone", "Colovian Highlands"),
        ("Visit the Lord Stone", "Colovian Highlands"),
        ("Visit the Lady Stone", "Gold Coast"),
        ("Visit the Thief Stone", "Great Forest"),
        ("Visit the Shadow Stone", "Nibenay Basin"),
        ("Visit the Mage Stone", "Nibenay Basin"),
        ("Visit the Lover Stone", "Nibenay Valley"),
        ("Visit the Ritual Stone", "Blackwood"),
        ("Visit the Serpent Stone", "Blackwood"),
    ]
    for stone_name, region_name in birthsign_stones:
        try:
            location = multiworld.get_location(stone_name, player)
        except KeyError:
            continue
        access_item = f"{region_name} Access"
        # If region starts unlocked, always accessible
        if region_name in getattr(world, "starting_unlocked_regions", []):
            location.access_rule = lambda state: True
        else:
            # Otherwise gated by region access item
            location.access_rule = (lambda state, item_name=access_item: state.has(item_name, player))