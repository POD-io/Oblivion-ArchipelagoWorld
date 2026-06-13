import asyncio
import os
import platform
import time
from typing import Dict, List, Set
from CommonClient import CommonContext, server_loop, gui_enabled, ClientCommandProcessor, logger, get_base_parser
from MultiServer import mark_raw
from NetUtils import ClientStatus

# Import for tracker functionality
from . import Items, Locations
from .Rules import set_rules

class OblivionTracker:
    """Tracker for Oblivion Remastered logic and items."""
    
    def __init__(self, ctx):
        self.ctx = ctx
        self.locations = set()
        self.items = {item_name: 0 for item_name in Items.item_table.keys()}
        self.slot_data = ctx.slot_data if hasattr(ctx, 'slot_data') else {}
        # Doomstone regions imported from Locations for central definition
        self.stone_regions = Locations.DOOMSTONE_REGIONS

        # Shop scouting caches
        self.shop_cache = {}  # location_id -> {"item_id": int, "item_name": str, "player": int (finding), "receiving_player": int, "flags": int}
        self._shop_scout_task = None
        self._shop_tier_unlocked = set()  # tiers already hinted
        if not hasattr(ctx, 'hinted_location_ids'):
            ctx.hinted_location_ids = []
        self.hinted_shop_location_ids = set()
        # Predefine shop value groups (tiers)
        self.shop_tiers = [
            [1, 10, 100],
            [2, 20, 200],
            [3, 30, 300],
            [4, 40, 400],
            [5, 50, 500],
        ]
        # Precompute set of shop location ids
        self.shop_ids = set()
        for tier in self.shop_tiers:
            for value in tier:
                loc_id = Locations.location_table.get(f"Innkeeper Shop Item Value {value}")
                if loc_id:
                    try:
                        self.shop_ids.add(loc_id.id)
                    except Exception:
                        pass
        self.refresh_items()
        # Initialization retry state for shop tab
        self._shop_init_attempts = 0
        self._shop_init_done = False

    def ensure_shop_initialized(self):
        """Populate shop_cache from stored hints (once they load) with retry backoff."""
        if self._shop_init_done:
            return
        hints_key = f"_read_hints_{getattr(self.ctx, 'team', 0)}_{getattr(self.ctx, 'slot', 0)}"
        hints = getattr(self.ctx, 'stored_data', {}).get(hints_key, [])
        loaded_any = False
        for hint in hints:
            loc_id = hint.get("location")
            if not isinstance(loc_id, int) or loc_id not in self.shop_ids:
                continue
            item_id = hint.get("item")
            if not isinstance(item_id, int):
                continue
            try:
                item_name = self.ctx.item_names.lookup_in_slot(item_id, hint.get("receiving_player"))
            except Exception:
                item_name = f"Item {item_id}"
            self.shop_cache[loc_id] = {
                "item_id": item_id,
                "item_name": item_name,
                "player": hint.get("finding_player"),
                "receiving_player": hint.get("receiving_player"),
                "flags": hint.get("item_flags", 0)
            }
            loaded_any = True
        if loaded_any:
            self._shop_init_done = True
            try:
                self.update_shop_tab()
            except Exception:  # pragma: no cover
                pass
            return
        backoff = [0.25, 0.5, 1, 1.5, 2, 3, 4]
        if self._shop_init_attempts < len(backoff):
            delay = backoff[self._shop_init_attempts]
            self._shop_init_attempts += 1
            import asyncio as _a
            _a.get_event_loop().call_later(delay, self.ensure_shop_initialized)

        #needed for updating shop tab when Progressive Shop Stock is obtained
    def refresh_shop_from_stored_hints(self):
        """Re-scan stored hints for new shop entries."""
        hints_key = f"_read_hints_{getattr(self.ctx, 'team', 0)}_{getattr(self.ctx, 'slot', 0)}"
        hints = getattr(self.ctx, 'stored_data', {}).get(hints_key, [])
        added = 0
        for hint in hints:
            loc_id = hint.get('location')
            if not isinstance(loc_id, int) or loc_id not in self.shop_ids or loc_id in self.shop_cache:
                continue
            item_id = hint.get('item')
            flags = hint.get('item_flags', 0) or hint.get('flags', 0)
            receiving_player = hint.get('receiving_player')
            finding_player = hint.get('finding_player')
            try:
                item_name = self.ctx.item_names.lookup_in_slot(item_id, receiving_player)
            except Exception:
                item_name = f"Item {item_id}"
            self.shop_cache[loc_id] = {
                'item_id': item_id,
                'item_name': item_name,
                'player': finding_player,
                'receiving_player': receiving_player,
                'flags': flags
            }
            added += 1
    
    def is_location_checked(self, location_name):
        """Check if a specific location has been checked (completed) by the player."""
        if location_name not in Locations.location_table:
            return False
        location_data = Locations.location_table.get(location_name)
        if not location_data or location_data.id is None:
            return False
        checked_locations = getattr(self.ctx, 'checked_locations', set())
        return location_data.id in checked_locations
    
    def check_location_accessibility(self, location_name):
        """Check if a location is accessible based on the game rules."""
        slot_data = getattr(self.ctx, 'slot_data', {})
        
        # Check sidequest rules first
        if location_name in Locations.WEALTH_SIDEQUESTS or location_name in Locations.EXPLORATION_SIDEQUESTS:
            selected_sidequests = self.ctx.slot_data.get("selected_sidequests", [])
            if location_name not in selected_sidequests:
                return False
            
            # Check if this sidequest requires a region access item
            region_name = Locations.SIDEQUEST_REGIONS.get(location_name)
            has_license = False
            
            # Check if player has the required license
            if location_name in Locations.WEALTH_SIDEQUESTS:
                has_license = self.has("Wealth Sidequest License", 1)
            elif location_name in Locations.EXPLORATION_SIDEQUESTS:
                has_license = self.has("Exploration Sidequest License", 1)
            
            # If no license, can't access
            if not has_license:
                return False
            
            # If region is required, check region access
            if region_name:
                # Check if region starts unlocked
                starting_unlocked = set(self.ctx.slot_data.get("starting_unlocked_regions", []) or [])
                if region_name not in starting_unlocked:
                    # Need region access item
                    access_item_name = f"{region_name} Access"
                    if not self.has(access_item_name, 1):
                        return False
            
            return True
        
        # For other locations, check if in static location table
        if location_name not in Locations.location_table:
            return False
            
        if not slot_data:
            return True
            
        # Check shrine rules
        if location_name.endswith(" Quest Complete"):
            shrine_name = location_name.replace(" Quest Complete", "")
            token_name = f"{shrine_name} Shrine Token"
            return self.has(token_name, 1)
            
        # Check arena rules
        if location_name.startswith("Arena Match ") and location_name.endswith(" Victory"):
            match_num = int(location_name.split()[2])
            arena_matches = slot_data.get("arena_matches", 21)
            if match_num > arena_matches:
                return False
            required_ranks = min(((match_num - 1) // 3) + 1, 7)
            return self.has("Progressive Arena Rank", 1, required_ranks)
            
        # Check gate rules
        if location_name.startswith("Gate ") and location_name.endswith(" Closed"):
            gate_num = int(location_name.split()[1])
            gate_count = slot_data.get("gate_count_required", 0)
            if gate_count == 0 or gate_num > gate_count:
                return False 
            return self.has("Oblivion Gate Key", 1, gate_num)
            
        # Check progressive shop stock rules
        if location_name.startswith("Innkeeper Shop Item Value "):
            value = int(location_name.split()[-1])
            if value in [1, 10, 100]:  # Set 1 - always available
                return True
            elif value in [2, 20, 200]:  # Set 2
                return self.has("Progressive Shop Stock", 1, 1)
            elif value in [3, 30, 300]:  # Set 3
                return self.has("Progressive Shop Stock", 1, 2)
            elif value in [4, 40, 400]:  # Set 4
                return self.has("Progressive Shop Stock", 1, 3)
            elif value in [5, 50, 500]:  # Set 5
                return self.has("Progressive Shop Stock", 1, 4)

        # Check Nirnroot harvesting rules
        if location_name.startswith("Nirnroot ") and location_name.endswith(" Harvested"):
            # When goal is NOT Nirnsanity: All Nirnroot locations are immediately accessible
            goal = slot_data.get("goal")
            if goal != "nirnsanity":
                return True
            
            # When goal IS Nirnsanity: Gated by Progressive Nirnroot Satchel capacity
            try:
                # Extract the nirnroot number from "Nirnroot X Harvested"
                parts = location_name.split()
                nirnroot_num = int(parts[1])
                
                # Determine required satchel count based on capacity needed
                if nirnroot_num <= 1:
                    # First Nirnroot is within starting capacity
                    return True
                elif nirnroot_num <= 5:
                    # Need 1 satchel for capacity 5
                    return self.has("Progressive Nirnroot Satchel", 1, 1)
                elif nirnroot_num <= 15:
                    # Need 2 satchels for capacity 15
                    return self.has("Progressive Nirnroot Satchel", 1, 2)
                elif nirnroot_num <= 30:
                    # Need 3 satchels for capacity 30
                    return self.has("Progressive Nirnroot Satchel", 1, 3)
                elif nirnroot_num <= 50:
                    # Need 4 satchels for capacity 50
                    return self.has("Progressive Nirnroot Satchel", 1, 4)
                else:  # 51-100
                    # Need 5 satchels for capacity 100
                    return self.has("Progressive Nirnroot Satchel", 1, 5)
            except (ValueError, IndexError):
                return False

        # Check Gold collection rules (Treasure Hunter goal)
        if location_name.startswith("Gold: ") and location_name.endswith(" Collected"):
            try:
                # Extract the gold amount from "Gold: X Collected"
                parts = location_name.split()
                gold_amount = int(parts[1])
                
                # Determine required satchel count based on capacity needed
                if gold_amount <= 1000:
                    # Within starting capacity
                    return True
                elif gold_amount <= 2500:
                    # Need 1 satchel for capacity 2500
                    return self.has("Progressive Septim Satchel", 1, 1)
                elif gold_amount <= 5000:
                    # Need 2 satchels for capacity 5000
                    return self.has("Progressive Septim Satchel", 1, 2)
                elif gold_amount <= 10000:
                    # Need 3 satchels for capacity 10000
                    return self.has("Progressive Septim Satchel", 1, 3)
                elif gold_amount <= 25000:
                    # Need 4 satchels for capacity 25000
                    return self.has("Progressive Septim Satchel", 1, 4)
                else:
                    # Need 5 satchels for unlimited capacity
                    return self.has("Progressive Septim Satchel", 1, 5)
            except (ValueError, IndexError):
                return False

        # Main Quest milestone rules
        if location_name == "Deliver the Amulet":
            return self.has("Amulet of Kings", 1)
        if location_name == "Breaking the Siege of Kvatch: Gate Closed":
            return self.has("Kvatch Gate Key", 1)
        if location_name == "Breaking the Siege of Kvatch":
            # Requires that the Gate Closed be logically reachable
            return self.check_location_accessibility("Breaking the Siege of Kvatch: Gate Closed")
        if location_name == "Find the Heir":
            # Requires Deliver the Amulet completed first, plus Amulet + Key and Siege logically reachable
            return (
                self.check_location_accessibility("Deliver the Amulet")
                and self.has("Amulet of Kings", 1)
                and self.has("Kvatch Gate Key", 1)
                and self.check_location_accessibility("Breaking the Siege of Kvatch")
            )
        if location_name == "Weynon Priory":
            return self.check_location_accessibility("Find the Heir")
        if location_name == "Battle for Castle Kvatch":
            # Requires Siege in logic
            if not self.check_location_accessibility("Breaking the Siege of Kvatch"):
                return False
            prev_data = Locations.location_table.get("Breaking the Siege of Kvatch")
            if prev_data and hasattr(self.ctx, 'checked_locations'):
                prev_id = getattr(prev_data, "id", None)
                if isinstance(prev_id, int):
                    if prev_id not in getattr(self.ctx, 'checked_locations', set()):
                        return False
            return True
        # MQ05 - All five locations require the Encrypted Scroll of the Blades
        if location_name in {
            "The Path of Dawn: Acquire Commentaries Vol I",
            "The Path of Dawn: Acquire Commentaries Vol II",
            "The Path of Dawn: Acquire Commentaries Vol III",
            "The Path of Dawn: Acquire Commentaries Vol IV",
            "The Path of Dawn",
        }:
            return self.has("Encrypted Scroll of the Blades", 1)
        # MQ06 - MX and Kill Harrow require Passphrase only; Dagon Shrine completion requires turning in MX to Martin at CRT
        if location_name == "Dagon Shrine: Mysterium Xarxes Acquired":
            return self.has("Dagon Shrine Passphrase", 1)
        if location_name == "Dagon Shrine: Kill Harrow":
            return self.has("Dagon Shrine Passphrase", 1)
        if location_name == "Dagon Shrine":
            if not self.is_location_checked("Weynon Priory"):
                return False
            return (
                self.check_location_accessibility("Dagon Shrine: Mysterium Xarxes Acquired")
                and self.check_location_accessibility("Weynon Priory")
            )
        # Attack on Fort Sutch spawns after Dagon Shrine quest is fully complete
        if location_name == "Attack on Fort Sutch":
            if not self.is_location_checked("Weynon Priory"):
                return False
            return (
                self.check_location_accessibility("Dagon Shrine")
                and self.has("Fort Sutch Gate Key", 1)
            )
    # MQ07 Spies: All three locations gated by Blades' Report item + Weynon Priory reachable
        if location_name in {
            "Spies: Kill Saveri Faram",
            "Spies: Kill Jearl",
            "Spies",
        }:
            if not self.is_location_checked("Weynon Priory"):
                return False
            return (
                self.has("Blades' Report: Strangers at Dusk", 1)
                and self.check_location_accessibility("Weynon Priory")
            )
        if location_name == "Blood of the Daedra":
            if not self.is_location_checked("Weynon Priory"):
                return False
            return (
                self.has("Decoded Page of the Xarxes: Daedric", 1)
                and self.check_location_accessibility("Weynon Priory")
            )
        if location_name == "Blood of the Divines":
            if not self.is_location_checked("Weynon Priory"):
                return False
            return (
                self.has("Decoded Page of the Xarxes: Divine", 1)
                and self.check_location_accessibility("Weynon Priory")
            )
        if location_name in {
            "Blood of the Divines: Free Spirit 1",
            "Blood of the Divines: Free Spirit 2",
            "Blood of the Divines: Free Spirit 3",
            "Blood of the Divines: Free Spirit 4",
            "Blood of the Divines: Armor of Tiber Septim",
        }:
            if not self.is_location_checked("Weynon Priory"):
                return False
            return (
                self.has("Decoded Page of the Xarxes: Divine", 1)
                and self.check_location_accessibility("Weynon Priory")
            )
        if location_name == "Bruma Gate":
            return self.has("Bruma Gate Key", 1)
        if location_name in {"Miscarcand: Great Welkynd Stone", "Miscarcand"}:
            if not self.is_location_checked("Weynon Priory"):
                return False
            return (
                self.has("Decoded Page of the Xarxes: Ayleid", 1)
                and self.check_location_accessibility("Weynon Priory")
            )
        if location_name in {"Defense of Bruma", "Great Gate"}:
            if not self.is_location_checked("Weynon Priory"):
                return False
            return (
                self.has("Decoded Page of the Xarxes: Sigillum", 1)
                and self.check_location_accessibility("Weynon Priory")
            )
        # Paradise requires all 4 pages + Dagon Shrine (Signifying Mysterium Xarxes turned in at Cloud Ruler Temple)
        # PLUS: Gate behind Dagon Shrine being CHECKED (Chapter 3 requires Chapter 2 completion)
        if location_name in {
            "Paradise: Bands of the Chosen Acquired",
            "Paradise: Bands of the Chosen Removed",
            "Paradise",
        }:
            if not self.is_location_checked("Dagon Shrine"):
                return False
            return (
                self.has("Paradise Access", 1)
                and self.has("Decoded Page of the Xarxes: Daedric", 1)
                and self.has("Decoded Page of the Xarxes: Divine", 1)
                and self.has("Decoded Page of the Xarxes: Ayleid", 1)
                and self.has("Decoded Page of the Xarxes: Sigillum", 1)
                and self.check_location_accessibility("Dagon Shrine")
            )
        if location_name == "Weynon Priory Quest Complete":
            return self.check_location_accessibility("Weynon Priory")
        if location_name == "Paradise Complete":
            return self.check_location_accessibility("Paradise")
        if location_name == "Light the Dragonfires":
            # Final victory event requires Paradise accessible
            return (
                self.check_location_accessibility("Paradise")
            )
        
        # Check class skill rules
        if " Skill Increase " in location_name:
            # Parse class skill location: "Skill Skill Increase X"
            parts = location_name.split(" Skill Increase ")
            if len(parts) != 2:
                return False
            
            skill_name = parts[0]
            try:
                skill_increase_num = int(parts[1])
            except ValueError:
                return False
            
            # Calculate which level this skill increase belongs to
            # Skill increases 1-2 = Level 1, 3-4 = Level 2, etc.
            level = (skill_increase_num - 1) // 2 + 1
            
            # Check if class system is enabled
            selected_class = slot_data.get("selected_class")
            if not selected_class:
                return False
            
            # Check if this skill is valid for the selected class
            class_skills = slot_data.get("class_skills", [])
            if skill_name not in class_skills:
                return False
            
            # Check if we have enough Progressive Class Level items
            class_level_maximum = slot_data.get("class_level_maximum", 5)
            if level > class_level_maximum:
                return False
            
            # Check if we have the required Progressive Class Level items
            required_levels = level
            progressive_class_level_item_name = self.ctx.slot_data.get("progressive_class_level_item_name")
            if not progressive_class_level_item_name:
                return False
            progressive_class_level_count = self.count(progressive_class_level_item_name, self.ctx.slot)
            if progressive_class_level_count < required_levels:
                return False
            
            return True
                
        # Dungeon access requires region Access item
        if location_name in Locations.DUNGEON_REGIONS:
            region_name = Locations.DUNGEON_REGIONS.get(location_name)
            # Only selected dungeons for this seed are valid
            selected_dungeons = set(self.ctx.slot_data.get("selected_dungeons", []))
            if location_name not in selected_dungeons:
                return False
            access_item_name = f"{region_name} Access"
            return self.has(access_item_name, 1)

        # Birthsign Doomstone access: require region Access when region system active
        if location_name in self.stone_regions:
            # If region system disabled (no selected_regions) treat as always accessible
            selected_regions = self.ctx.slot_data.get("selected_regions", []) or []
            if not selected_regions:
                return True
            region_name = self.stone_regions[location_name]
            if region_name not in selected_regions:
                # Stone not part of this seed
                return False
            access_item_name = f"{region_name} Access"
            # If region starts unlocked (present in starting_unlocked_regions) allow without item
            starting_unlocked = set(self.ctx.slot_data.get("starting_unlocked_regions", []) or [])
            if region_name in starting_unlocked:
                return True
            return self.has(access_item_name, 1)

        # Kill location access: gated by region unlock count in batches
        if location_name.startswith("Dungeon Kill ") or location_name.startswith("Overworld Kill "):
            try:
                import math
                kill_type = "dungeon" if location_name.startswith("Dungeon Kill ") else "overworld"
                kill_num = int(location_name.split()[-1])
                kills_per_region = slot_data.get(f"{kill_type}_kills_per_region", 0)
                selected_regions = slot_data.get("selected_regions", []) or []
                if not selected_regions or kills_per_region == 0:
                    return True
                required_regions = math.ceil(kill_num / kills_per_region)
                regions_unlocked = sum(1 for r in selected_regions if self.has(f"{r} Access", 1))
                return regions_unlocked >= required_regions
            except (ValueError, IndexError):
                return True

        return True
    
    def update_locations(self):
        """Update the locations tab with accessible locations from the server."""
        if hasattr(self.ctx, 'tab_locations'):
            if not self.ctx.tracker_enabled:
                self.ctx.tab_locations.content.data = [{"text": "Tracker disabled. Use /tracker to enable it."}]
                return

            accessible_locations = []
            # Use server-provided missing_locations and checked_locations
            for location_id in getattr(self.ctx, 'missing_locations', set()):
                if location_id in getattr(self.ctx, 'checked_locations', set()):
                    continue
                location_name = self.ctx.location_names.lookup_in_game(location_id, self.ctx.game)
                if self.check_location_accessibility(location_name):
                    accessible_locations.append({"text": location_name})
            
            # Add goal location to MQ section
            slot_goal_data = getattr(self.ctx, 'slot_data', {}) or {}
            goal_key = slot_goal_data.get("goal") if isinstance(slot_goal_data, dict) else None
            if goal_key == "light_the_dragonfires" and self.check_location_accessibility("Light the Dragonfires"):
                accessible_locations.append({"text": "[Goal] Light the Dragonfires"})

            def natural_sort_key(location_dict):
                text = location_dict["text"]
                
                # Main Quest story order mapping
                mq_order_dict = {
                    "Deliver the Amulet": (1,1), "Breaking the Siege of Kvatch: Gate Closed": (1,2), "Breaking the Siege of Kvatch": (1,3),
                    "Battle for Castle Kvatch": (1,4), "Find the Heir": (1,5), "Weynon Priory": (1,6),
                    "The Path of Dawn: Acquire Commentaries Vol I": (2,1), "The Path of Dawn: Acquire Commentaries Vol II": (2,2),
                    "The Path of Dawn: Acquire Commentaries Vol III": (2,3), "The Path of Dawn: Acquire Commentaries Vol IV": (2,4), "The Path of Dawn": (2,5),
                    "Dagon Shrine: Mysterium Xarxes Acquired": (2,6), "Dagon Shrine: Kill Harrow": (2,7), "Dagon Shrine": (2,8), "Attack on Fort Sutch": (2,9),
                    "Spies: Kill Saveri Faram": (2,10), "Spies: Kill Jearl": (2,11), "Spies": (2,12), "Blood of the Daedra": (2,13),
                    "Blood of the Divines: Free Spirit 1": (2,14), "Blood of the Divines: Free Spirit 2": (2,15), "Blood of the Divines: Free Spirit 3": (2,16),
                    "Blood of the Divines: Free Spirit 4": (2,17), "Blood of the Divines: Armor of Tiber Septim": (2,18), "Blood of the Divines": (2,19),
                    "Bruma Gate": (2,20), "Miscarcand: Great Welkynd Stone": (2,21), "Miscarcand": (2,22), "Defense of Bruma": (2,23), "Great Gate": (2,24),
                    "Paradise: Bands of the Chosen Acquired": (3,1), "Paradise: Bands of the Chosen Removed": (3,2), "Paradise": (3,3),
                    "[Goal] Light the Dragonfires": (3,4),
                }
                mq_order = mq_order_dict.get(text)
                
                # Category 0: Class Skills
                if " Skill Increase " in text:
                    parts = text.split(" Skill Increase ")
                    skill_name = parts[0]
                    skill_increase_num = int(parts[1])
                    return (0, skill_name, skill_increase_num)
                
                # Category 1: Dungeons and Birthsign Stones by region
                elif text in Locations.DUNGEON_REGIONS:
                    region = Locations.DUNGEON_REGIONS.get(text, "")
                    return (1, region, text)
                elif text in self.stone_regions:
                    region = self.stone_regions.get(text, "")
                    return (1, region, f"~{text}")
    
                # Category 2: Arena matches
                elif "Arena Match" in text:
                    num = int(text.split()[-2])
                    return (2, num)
                
                # Category 3: Main Quest (in story progression order)
                elif mq_order:
                    return (3, mq_order)
                
                # Category 4: Oblivion Gates (numeric) - but exclude MQ gates
                elif "Gate" in text and "Closed" in text and text not in mq_order_dict:
                    parts = text.split()
                    if len(parts) >= 3 and parts[0] == "Gate" and parts[1].isdigit() and parts[-1] == "Closed":
                        num = int(parts[1])
                        return (4, num)
                    else:
                        return (4, 9999, text)
                
                # Category 5: Shop Items
                elif "Innkeeper Shop Item Value" in text:
                    num = int(text.split()[-1])
                    return (5, num)
                
                # Category 6: Gold Collection (Treasure Hunter goal)
                elif text.startswith("Gold: ") and text.endswith(" Collected"):
                    try:
                        # Extract gold amount from "Gold: X Collected"
                        parts = text.split()
                        amount = int(parts[1])
                        return (6, amount)
                    except (ValueError, IndexError):
                        return (6, 999999, text)
                
                # Category 7: Nirnroot Harvesting (Nirnsanity goal)
                elif text.startswith("Nirnroot ") and text.endswith(" Harvested"):
                    try:
                        parts = text.split()
                        num = int(parts[1])
                        return (7, num)
                    except (ValueError, IndexError):
                        return (7, 999999, text)
                
                # Category 8: Sidequests (Wealth and Exploration)
                elif text in Locations.SIDEQUEST_METADATA:
                    # Sort by type (Wealth=0, Exploration=1) then alphabetically
                    if text in Locations.WEALTH_SIDEQUESTS:
                        return (8, 0, text)
                    elif text in Locations.EXPLORATION_SIDEQUESTS:
                        return (8, 1, text)
                    else:
                        return (8, 2, text)
                
                # Category 9: Kill locations
                elif "Overworld Kill" in text or "Dungeon Kill" in text:
                    # extract last number safely
                    num = int(text.split()[-1])
                    
                    if "Overworld Kill" in text:
                        return (10, 0, num, text)
                    else:  # Dungeon Kill
                        return (10, 1, num, text)
                
                # Category 10: Everything else
                else:
                    return (9, text)
            
            sorted_locations = sorted(accessible_locations, key=natural_sort_key)
            # Append (Region) to dungeon names, (gold cost) to sidequests in tracker for clarity
            for entry in sorted_locations:
                name = entry["text"]
                if name in Locations.DUNGEON_REGIONS:
                    entry["text"] = f"{name} ({Locations.DUNGEON_REGIONS[name]})"
                elif name in self.stone_regions:
                    entry["text"] = f"{name} ({self.stone_regions[name]})"
                elif name in Locations.SIDEQUEST_METADATA:
                    gold_cost = Locations.SIDEQUEST_METADATA[name]
                    if gold_cost > 0:
                        entry["text"] = f"{name} ({gold_cost} gold)"

            if sorted_locations:
                self.ctx.tab_locations.content.data = sorted_locations
            else:
                self.ctx.tab_locations.content.data = [{"text": "All currently available locations have been checked."}]

    def _shop_get_location_id(self, value: int):
        loc_name = f"Innkeeper Shop Item Value {value}"
        data = Locations.location_table.get(loc_name)
        if data:
            return data.id
        return None

    def schedule_shop_scout(self):
        """Determine newly in-logic shop locations and send create_as_hint scouts."""
        if not hasattr(self.ctx, 'location_names'):
            return
        # Get shop scout type setting (0=off, 1=summary, 2=player_only, 3=full_info)
        shop_scout_type = getattr(self.ctx, 'slot_data', {}).get('shop_scout_type', 1)
        
        # Only Full Info mode (3) actually creates hints visible to all players
        # Other modes just scout for display purposes
        create_as_hint = 2 if shop_scout_type == 3 else 0
        
        # If off, don't scout at all
        if shop_scout_type == 0:
            return
            
        to_scout_ids = []
        for tier_index, tier in enumerate(self.shop_tiers, start=1):
            accessible_values = [v for v in tier if self.check_location_accessibility(f"Innkeeper Shop Item Value {v}")]
            tier_in_logic = bool(accessible_values) if tier_index == 1 else len(accessible_values) == len(tier)
            if not tier_in_logic or tier_index in self._shop_tier_unlocked:
                continue
            for value in accessible_values:
                loc_id = self._shop_get_location_id(value)
                if not loc_id:
                    continue
                if loc_id not in self.hinted_shop_location_ids:
                    if not hasattr(self.ctx, 'missing_locations') or loc_id in getattr(self.ctx, 'missing_locations', set()):
                        to_scout_ids.append(loc_id)
            if to_scout_ids:
                self._shop_tier_unlocked.add(tier_index)
        if not to_scout_ids:
            return
        from Utils import async_start
        async_start(self.ctx.send_msgs([{ "cmd": "LocationScouts", "locations": to_scout_ids, "create_as_hint": create_as_hint }]))
        for loc_id in to_scout_ids:
            self.hinted_shop_location_ids.add(loc_id)
            if create_as_hint == 2:  # Only add to hinted_location_ids if actually creating hints
                if hasattr(self.ctx, 'hinted_location_ids') and loc_id not in self.ctx.hinted_location_ids:
                    self.ctx.hinted_location_ids.append(loc_id)
        self.update_shop_tab()

    def update_shop_tab(self):
        if not hasattr(self.ctx, 'tab_shop'):
            return
        
        # Get shop scout type setting (0=off, 1=summary, 2=player_only, 3=full_info)
        slot_data = getattr(self.ctx, 'slot_data', {})
        shop_scout_type = slot_data.get('shop_scout_type', 1)
        
        # If off, show placeholder
        if shop_scout_type == 0:
            self.ctx.tab_shop.content.data = [{"text": "Shop scouting disabled in settings."}]
            return
            
        if not self.shop_cache:
            self.ensure_shop_initialized()
        
        # Get checked locations to filter out purchased items
        checked_locations = getattr(self.ctx, 'checked_locations', set())
        
        rows_map: list[tuple] = []
        for tier in self.shop_tiers:
            for value in tier:
                loc_id = self._shop_get_location_id(value)
                if not loc_id:
                    continue
                # Skip checked/purchased items
                if loc_id in checked_locations:
                    continue
                entry = self.shop_cache.get(loc_id)
                if not entry:
                    continue
                rows_map.append((value,
                                 entry.get('item_id'),
                                 entry.get('item_name'),
                                 entry.get('player'),
                                 entry.get('flags', 0),
                                 entry.get('receiving_player')))
        
        # Sort by tier groups: (1,10,100), (2,20,200), etc.
        def get_sort_key(row):
            value = row[0]
            # Determine tier (1-5) based on value
            if value in [1, 10, 100]:
                tier = 1
            elif value in [2, 20, 200]:
                tier = 2
            elif value in [3, 30, 300]:
                tier = 3
            elif value in [4, 40, 400]:
                tier = 4
            elif value in [5, 50, 500]:
                tier = 5
            else:
                tier = 999  # fallback
            # Within tier, sort by value
            return (tier, value)
        
        rows_map.sort(key=get_sort_key)
        
        out_rows = []
        parser = getattr(getattr(self.ctx, 'ui', None), 'json_to_kivy_parser', None)
        
        # Build rows based on mode
        if shop_scout_type == 2:  # Player Only mode - show only value and player
            # Precompute widths
            value_strs = [f"Value {v}:" for v, *_ in rows_map]
            value_col_width = max((len(s) for s in value_strs), default=0)
            
            for (v, item_id, name, player_id, flags, receiving_player) in rows_map:
                # Get receiving player name
                if isinstance(receiving_player, int):
                    try:
                        recv_pname = self.ctx.player_names[receiving_player]
                    except Exception:
                        recv_pname = f"P{receiving_player}"
                else:
                    recv_pname = ""
                
                value_part = f"Value {v}:".ljust(value_col_width)
                if recv_pname:
                    player_markup = f"[color=EE00EE][{recv_pname}][/color]"
                    line = f"{value_part}  {player_markup}"
                else:
                    line = value_part
                out_rows.append({"text": line})
                
        else:  # Summary (1) or Full Info (3) modes - show value, item info, and player
            # Precompute widths for alignment
            value_strs = [f"Value {v}:" for v, *_ in rows_map]
            value_col_width = max((len(s) for s in value_strs), default=0)
            
            # Collect plain item/player names for width calcs
            item_plain_list = []
            player_plain_list = []
            item_markups = []
            
            for (v, item_id, name, player_id, flags, receiving_player) in rows_map:
                # Get receiving player name
                if isinstance(receiving_player, int):
                    try:
                        recv_pname = self.ctx.player_names[receiving_player]
                    except Exception:
                        recv_pname = f"P{receiving_player}"
                else:
                    recv_pname = ""
                
                # Determine item classification from flags
                # flags & 0b001 = progression, flags & 0b010 = useful, flags & 0b100 = trap
                is_progression = bool(flags & 0b001)
                is_useful = bool(flags & 0b010)
                is_trap = bool(flags & 0b100)
                
                if shop_scout_type == 1:  # Summary mode
                    # Show classification instead of item name, disguise traps as filler
                    if is_trap:
                        item_classification = "Filler"
                        color_code = '6375D6'  # Blue for filler
                    elif is_progression:
                        item_classification = "Progression"
                        color_code = 'BB99FF'  # Purple/plum for progression
                    elif is_useful:
                        item_classification = "Useful"
                        color_code = '00EEEE'  # Cyan for useful
                    else:
                        item_classification = "Filler"
                        color_code = '6375D6'  # Blue for filler
                    
                    name_plain = item_classification
                    name_markup = f"[color={color_code}]{item_classification}[/color]" if color_code else item_classification
                else:  # Full Info mode (3)
                    # Show full item name with colors
                    name_plain = name
                    if parser and isinstance(item_id, int):
                        try:
                            name_markup = parser.handle_node({"type": "item_id", "text": item_id, "flags": flags, "player": receiving_player})
                        except Exception:
                            name_markup = name
                    else:
                        color_code = None
                        if flags & 0b001:  # Progression
                            color_code = 'BB99FF'  # Purple/plum for progression
                        elif flags & 0b100:  # Trap
                            color_code = 'EE0000'  # Red for trap
                        elif flags & 0b010:  # Useful
                            color_code = '00EEEE'  # Cyan for useful
                        else:  # Filler
                            color_code = '6375D6'  # Blue for filler
                        name_markup = f"[color={color_code}]{name}[/color]" if color_code else name
                
                player_plain_list.append(recv_pname)
                item_plain_list.append(name_plain)
                item_markups.append((v, name_plain, name_markup, recv_pname))
            
            item_col_width = max((len(n) for n in item_plain_list), default=0)
            player_col_width = max((len(n) for n in player_plain_list), default=0)
            
            # Build formatted lines
            for (v, name_plain, name_markup, pname) in item_markups:
                value_part = f"Value {v}:".ljust(value_col_width)
                # Compensate for invisible markup characters so columns align
                item_padding = max(0, item_col_width - len(name_plain))
                if pname:
                    player_markup = f"[color=EE00EE][{pname}][/color]"
                    # Right justify player inside its column width
                    player_padding = max(0, player_col_width - len(pname))
                    player_part = (" " * player_padding) + player_markup
                else:
                    player_part = ""
                # Use separator columns for clearer grid feel
                line = f"{value_part}  {name_markup}{' ' * item_padding}    {player_part}".rstrip()
                out_rows.append({"text": line})
        
        if not out_rows:
            out_rows.append({"text": "All shop items have been purchased!"})
        
        self.ctx.tab_shop.content.data = out_rows
        # Force rebind to ensure UI refresh
        try:
            content = self.ctx.tab_shop.content
            content.data = []
            content.data = out_rows
        except Exception:
            pass
    
    def refresh_locations(self):
        """Refresh the locations based on current items."""
        self.locations.clear()
        for location_id in getattr(self.ctx, 'missing_locations', set()):
            location_name = self.ctx.location_names.lookup_in_game(location_id, self.ctx.game)
            if self.check_location_accessibility(location_name):
                self.locations.add(location_id)
        self.update_locations()
    
    def refresh_items(self):
        """Refresh the items display."""
        # Reset item counts
        for item in self.items:
            self.items[item] = 0
        
        # Count received items
        for item in self.ctx.items_received:
            item_name = self.ctx.item_names.lookup_in_game(item.item)
            if item_name in self.items:
                self.items[item_name] += 1
        
        # Update items tab
        if hasattr(self.ctx, 'tab_items'):
            self.ctx.tab_items.content.data = []
            for item_name, amount in sorted(self.items.items()):
                if amount == 0:
                    continue
                if amount > 1:
                    self.ctx.tab_items.content.data.append({"text": f"{item_name}: {amount}"})
                else:
                    self.ctx.tab_items.content.data.append({"text": f"{item_name}"})
        
        self.refresh_locations()
        self.update_goal_progress()
    
    def update_goal_progress(self):
        """Update the Goal Progress tab based on the current goal."""
        if not hasattr(self.ctx, 'tab_goal'):
            return
        
        slot_data = getattr(self.ctx, 'slot_data', {}) or {}
        goal_key = slot_data.get("goal")
        
        if not goal_key:
            self.ctx.tab_goal.content.data = [{"text": "No goal data available."}]
            return
        
        out_rows = []
        
        goal_display = goal_key.replace('_', ' ').title()
        out_rows.append({"text": f"[b]Goal: {goal_display}[/b]"})
        out_rows.append({"text": "[i]*Counts reflect server state and may include locations checked via !collect[/i]"})
        out_rows.append({"text": ""})
        
        if goal_key == "gatecloser":
            # Gate Closer: Show gate keys collected and closed gates count
            gate_count = slot_data.get("gate_count_required", 5)
            gate_keys_collected = self.items.get("Oblivion Gate Key", 0)
            
            # Count gates closed from checked_locations
            gates_closed = 0
            for i in range(1, gate_count + 1):
                location_name = f"Gate {i} Closed"
                if self.is_location_checked(location_name):
                    gates_closed += 1
            
            out_rows.append({"text": f"[b]Gate Keys:[/b] {gate_keys_collected}/{gate_count}"})
            out_rows.append({"text": f"[b]Gates Closed:[/b] {gates_closed}/{gate_count}"})
            out_rows.append({"text": ""})
            
            for i in range(1, gate_count + 1):
                gate_closed = self.is_location_checked(f"Gate {i} Closed")
                has_key = i <= gate_keys_collected
                
                if gate_closed:
                    out_rows.append({"text": f"[color=00ff00]Gate {i} - Closed[/color]"})
                elif has_key:
                    out_rows.append({"text": f"Gate {i} - Key obtained"})
                else:
                    out_rows.append({"text": f"Gate {i}"})
            
            # Check if goal is accessible and/or complete
            out_rows.append({"text": ""})
            if gates_closed >= gate_count:
                out_rows.append({"text": "[color=00ff00]Goal Complete![/color]"})
            elif gate_keys_collected >= gate_count:
                out_rows.append({"text": "[color=FFD700][b]GO MODE — Close your gates to win![/b][/color]"})
        
        elif goal_key == "shrine_seeker":
            # Shrine Seeker: Show shrine quest completions from checked_locations
            shrine_goal = slot_data.get("shrine_goal", 5)
            shrine_count = slot_data.get("shrine_count", 10)
            active_shrines = slot_data.get("active_shrines", []) or []
            
            # Count quest completions from checked_locations
            checked_locations = getattr(self.ctx, 'checked_locations', set())
            shrine_completions = 0
            for shrine in active_shrines:
                location_name = f"{shrine} Quest Complete"
                if self.is_location_checked(location_name):
                    shrine_completions += 1
            
            # Count shrine tokens collected (enables quests)
            total_tokens = sum(count for item_name, count in self.items.items() 
                             if "Shrine Token" in item_name)
            
            out_rows.append({"text": f"[b]Shrine Quests Complete:[/b] {shrine_completions}/{shrine_goal}"})
            out_rows.append({"text": f"[b]Shrine Tokens Collected:[/b] {total_tokens}/{shrine_count}"})
            out_rows.append({"text": f"(Any {shrine_goal} of {shrine_count} available shrines)"})
            out_rows.append({"text": ""})
            
            if shrine_completions >= shrine_goal:
                out_rows.append({"text": "[color=00ff00]Goal Complete![/color]"})
            elif total_tokens >= shrine_goal:
                out_rows.append({"text": "[color=FFD700][b]GO MODE — Complete your shrine quests to win![/b][/color]"})
            else:
                out_rows.append({"text": f"Go Mode: Need {shrine_goal - shrine_completions} more shrine quest(s)"})
        
        elif goal_key == "arena":
            # Arena: Show Progressive Arena Rank progress and matches won
            arena_rank_count = self.items.get("Progressive Arena Rank", 0)
            ranks = ["Pit Dog", "Brawler", "Bloodletter", "Myrmidon", "Warrior", "Gladiator", "Hero", "Grand Champion"]
            
            # Count arena matches won from checked_locations
            matches_won = 0
            total_matches = 21  # 7 ranks × 3 matches per rank
            for i in range(1, total_matches + 1):
                location_name = f"Arena Match {i} Victory"
                if self.is_location_checked(location_name):
                    matches_won += 1
            
            out_rows.append({"text": f"[b]Arena Ranks:[/b] {arena_rank_count}/{len(ranks)}"})
            out_rows.append({"text": f"[b]Matches Won:[/b] {matches_won}/{total_matches}"})
            out_rows.append({"text": ""})
            
            for i, rank in enumerate(ranks):
                has_rank = i < arena_rank_count
                # Check if all 3 matches for this rank are complete
                matches_for_rank = []
                for match_num in range(i * 3 + 1, (i + 1) * 3 + 1):
                    if match_num <= total_matches:
                        matches_for_rank.append(self.is_location_checked(f"Arena Match {match_num} Victory"))
                
                rank_complete = all(matches_for_rank) if matches_for_rank else False
                
                if rank_complete:
                    out_rows.append({"text": f"[color=00ff00]{rank} - Complete[/color]"})
                elif has_rank:
                    out_rows.append({"text": f"[color=ffff00]{rank} - Rank obtained[/color]"})
                else:
                    out_rows.append({"text": f"{rank}"})
            
            # Check if goal is accessible
            out_rows.append({"text": ""})
            if arena_rank_count >= 7:
                out_rows.append({"text": "[color=FFD700][b]GO MODE — Complete Arena to become Grand Champion![/b][/color]"})
        
        elif goal_key == "light_the_dragonfires":
            # Required items for victory (items needed to reach Paradise and complete MQ)
            required_for_victory = [
                "Amulet of Kings",
                "Kvatch Gate Key",
                "Dagon Shrine Passphrase",
                "Decoded Page of the Xarxes: Daedric",
                "Decoded Page of the Xarxes: Divine",
                "Decoded Page of the Xarxes: Ayleid",
                "Decoded Page of the Xarxes: Sigillum",
                "Paradise Access",
            ]

            # Optional items
            optional_mq_items = [
                "Encrypted Scroll of the Blades",
                "Fort Sutch Gate Key",
                "Blades' Report: Strangers at Dusk",
                "Bruma Gate Key",
            ]

            # Required items section
            out_rows.append({"text": "[b]Required for Victory:[/b]"})
            required_collected = 0
            for item_name in required_for_victory:
                has_item = self.items.get(item_name, 0) > 0
                if has_item:
                    out_rows.append({"text": f"[color=00ff00]{item_name}[/color]"})
                    required_collected += 1
                else:
                    out_rows.append({"text": f"{item_name}"})

            # Optional progression items section
            out_rows.append({"text": ""})
            out_rows.append({"text": "[b]Optional Progression Items:[/b]"})
            for item_name in optional_mq_items:
                has_item = self.items.get(item_name, 0) > 0
                if has_item:
                    out_rows.append({"text": f"[color=00ff00]{item_name}[/color]"})
                else:
                    out_rows.append({"text": f"{item_name}"})

            # Check location completions for victory condition
            has_weynon_complete = self.is_location_checked("Weynon Priory")
            has_dagon_complete = self.is_location_checked("Dagon Shrine")
            has_dragonfires_complete = self.is_location_checked("Light the Dragonfires")

            out_rows.append({"text": ""})
            if has_dragonfires_complete:
                out_rows.append({"text": "[color=00ff00]Goal Complete![/color]"})
            elif required_collected >= len(required_for_victory) and has_weynon_complete and has_dagon_complete:
                out_rows.append({"text": "[color=FFD700][b]GO MODE — Light the Dragonfires to win![/b][/color]"})
        
        elif goal_key == "dungeon_delver":
            # Dungeon Delver: Show dungeons completed per region
            selected_regions = slot_data.get("selected_regions", []) or []
            dungeons_by_region = slot_data.get("dungeons_by_region", {}) or {}
            
            out_rows.append({"text": "[b]Dungeons by Region:[/b]"})
            out_rows.append({"text": ""})
            
            checked_locations = getattr(self.ctx, 'checked_locations', set())
            regions_unlocked = 0
            total_dungeons = 0
            total_completed = 0
            
            for region in sorted(selected_regions):
                region_dungeons = dungeons_by_region.get(region, [])
                completed = 0
                
                for dungeon in region_dungeons:
                    dungeon_data = Locations.location_table.get(dungeon)
                    if dungeon_data and dungeon_data.id in checked_locations:
                        completed += 1
                
                total = len(region_dungeons)
                total_dungeons += total
                total_completed += completed
                
                # Check if we have region access
                access_item = f"{region} Access"
                starting_unlocked = set(slot_data.get("starting_unlocked_regions", []) or [])
                has_access = region in starting_unlocked or self.items.get(access_item, 0) > 0
                
                if has_access:
                    regions_unlocked += 1
                
                if completed == total and total > 0:
                    out_rows.append({"text": f"[color=00ff00]{region}: {completed}/{total}[/color]"})
                elif has_access:
                    out_rows.append({"text": f"[color=00BFFF]{region}: {completed}/{total}[/color]"})
                else:
                    out_rows.append({"text": f"{region}: {completed}/{total}"})
            
            # Check if goal is complete or accessible
            out_rows.append({"text": ""})
            if total_dungeons > 0 and total_completed >= total_dungeons:
                out_rows.append({"text": "[color=00ff00]Goal Complete![/color]"})
            elif regions_unlocked >= len(selected_regions) and len(selected_regions) > 0:
                out_rows.append({"text": "[color=FFD700][b]GO MODE — All regions unlocked! Clear all dungeons for victory.[/b][/color]"})
        
        elif goal_key == "nirnsanity":
            # Nirnsanity: Track count of received Nirnroots and harvesting progress
            nirnroot_count = slot_data.get("nirnroot_count", 100)
            extra_nirnroots = slot_data.get("extra_nirnroot", 0)
            total_nirnroots_available = nirnroot_count + extra_nirnroots
            nirnroots_collected = self.items.get("Nirnroot", 0)
            
            # Display collected count in green when goal is reached
            out_rows.append({"text": "[b][color=FFD700]Nirnroot Items (from multiworld) [/color][/b]"})
            if nirnroots_collected >= nirnroot_count:
                if extra_nirnroots > 0:
                    out_rows.append({"text": f"  [color=00ff00]Collected: {nirnroots_collected}/{nirnroot_count}[/color] ({total_nirnroots_available} available)"})
                else:
                    out_rows.append({"text": f"  [color=00ff00]Collected: {nirnroots_collected}/{nirnroot_count}[/color]"})
            else:
                if extra_nirnroots > 0:
                    out_rows.append({"text": f"  Collected: {nirnroots_collected}/{nirnroot_count} ({total_nirnroots_available} available)"})
                else:
                    out_rows.append({"text": f"  Collected: {nirnroots_collected}/{nirnroot_count}"})
            
            out_rows.append({"text": ""})
            
            # Count harvested nirnroots from checked locations
            harvested_count = 0
            for i in range(1, nirnroot_count + 1):
                location_name = f"Nirnroot {i} Harvested"
                if self.is_location_checked(location_name):
                    harvested_count += 1
            
            # Calculate current capacity and remaining harvest checks
            nirnroot_satchels = self.items.get("Progressive Nirnroot Satchel", 0)
            satchel_capacities = [1, 5, 15, 30, 50, 100]
            current_capacity = satchel_capacities[nirnroot_satchels] if nirnroot_satchels < len(satchel_capacities) else 100
            
            # Show harvest progress
            out_rows.append({"text": "[b]In-Game Harvesting Checks:[/b]"})
            out_rows.append({"text": f"  Harvested: {harvested_count}/{nirnroot_count}"})
            out_rows.append({"text": f"  Current bag capacity: {current_capacity}"})
            
            # Show remaining checks with current bag
            remaining_this_bag = max(0, current_capacity - harvested_count)
            if remaining_this_bag > 0:
                out_rows.append({"text": f"  Remaining with current bag: {remaining_this_bag}"})
            
            # Show total remaining once all bags obtained
            if nirnroot_satchels >= len(satchel_capacities) - 1:  # Have all bags
                total_remaining = nirnroot_count - harvested_count
                out_rows.append({"text": f"  Total remaining (all bags): {total_remaining}"})
            
            out_rows.append({"text": ""})
            
            # Show progression satchels needed for this goal
            out_rows.append({"text": "[b]Progression Items:[/b]"})
            nirnroot_satchels = self.items.get("Progressive Nirnroot Satchel", 0)
            satchel_capacities = [1, 5, 15, 30, 50, 100]
            capacity_gates = [5, 15, 30, 50, 100]
            
            # Only show satchels needed to reach goal (find minimum capacity >= goal)
            needed_capacity = min((c for c in capacity_gates if c >= nirnroot_count), default=100)
            satchels_needed = sum(1 for c in capacity_gates if c <= needed_capacity)
            
            for i in range(satchels_needed):
                has_satchel = i < nirnroot_satchels
                capacity = satchel_capacities[i + 1]
                if has_satchel:
                    out_rows.append({"text": f"[color=00ff00]Progressive Nirnroot Satchel {i+1} (Capacity: {capacity})[/color]"})
                else:
                    out_rows.append({"text": f"Progressive Nirnroot Satchel {i+1} (Capacity: {capacity})"})
            
            # Check if goal is complete
            out_rows.append({"text": ""})
            nirnsanity_complete = self.is_location_checked("Nirnsanity")
            
            if nirnsanity_complete:
                out_rows.append({"text": "[color=00ff00]Goal Complete![/color]"})
        
        elif goal_key == "treasure_hunter":
            # Treasure Hunter: Track septim satchels needed to reach gold goal amount
            gold_goal = slot_data.get("gold_goal", 10000)
            septim_satchels = self.items.get("Progressive Septim Satchel", 0)
            
            # Satchel capacities
            satchel_capacities = [1000, 2500, 5000, 10000, 25000, float('inf')]
            current_capacity = satchel_capacities[septim_satchels] if septim_satchels < len(satchel_capacities) else float('inf')
            
            # Determine how many satchels are needed for the goal
            needed_satchels = 0
            for i, cap in enumerate(satchel_capacities):
                if cap >= gold_goal:
                    needed_satchels = i
                    break
            
            out_rows.append({"text": f"[b]Gold Goal:[/b] {gold_goal:,}"})
            # Display current capacity
            if current_capacity == float('inf'):
                out_rows.append({"text": "[b]Current Capacity:[/b] Unlimited"})
            else:
                out_rows.append({"text": f"[b]Current Capacity:[/b] {int(current_capacity):,} gold"})
            out_rows.append({"text": ""})
            
            # Show only the satchels needed for the goal
            if needed_satchels > 0:
                out_rows.append({"text": "[b]Progressive Septim Satchels:[/b]"})
                for i in range(needed_satchels):
                    has_satchel = i < septim_satchels
                    capacity = satchel_capacities[i + 1]
                    # Format capacity display
                    if capacity == float('inf'):
                        capacity_str = "Unlimited"
                    else:
                        capacity_str = f"{int(capacity):,}"
                    
                    if has_satchel:
                        out_rows.append({"text": f"[color=00ff00]Satchel {i+1}: {capacity_str} capacity[/color]"})
                    else:
                        out_rows.append({"text": f"Satchel {i+1}: {capacity_str} capacity"})
                out_rows.append({"text": ""})
            
            # Check if goal is complete or in go mode
            treasure_hunter_complete = self.is_location_checked("Treasure Hunter")
            
            if treasure_hunter_complete:
                out_rows.append({"text": "[color=00ff00]Goal Complete![/color]"})
            elif current_capacity >= gold_goal:
                out_rows.append({"text": "[color=FFD700][b]GO MODE — Collect in-game gold to reach your goal![/b][/color]"})
            else:
                if current_capacity == float('inf'):
                    out_rows.append({"text": f"Need capacity of {gold_goal:,} (currently Unlimited)"})
                else:
                    out_rows.append({"text": f"Need capacity of {gold_goal:,} (currently {int(current_capacity):,})"})
        
        else:
            out_rows.append({"text": "Unknown goal type."})

        self.ctx.tab_goal.content.data = out_rows
    
    def has(self, item, player, count=1):
        """Check if player has the specified item with the given count."""
        return self.items.get(item, 0) >= count
    
    def has_all(self, items, player):
        """Check if player has all specified items."""
        for item in items:
            if not self.items.get(item, 0):
                return False
        return True
    
    def has_any(self, items, player):
        """Check if player has any of the specified items."""
        for item in items:
            if self.items.get(item, 0):
                return True
        return False
    
    def count(self, item, player):
        """Get the count of a specific item."""
        return self.items.get(item, 0)


def _find_proton_save_path():
    """Auto-detect Oblivion save path in Proton prefix (Linux)."""
    import glob
    
    # The unique Proton path signature for Oblivion Remastered (2623190 is the Steam App ID)
    pattern = "steamapps/compatdata/2623190/pfx/drive_c/users/steamuser/Documents/My Games/Oblivion Remastered/Saved"
    
    # Search common Steam library locations
    home = os.path.expanduser("~")
    search_roots = [
        f"{home}/.local/share/Steam",                                            # Standard Steam
        f"{home}/.steam/debian-installation/",                                   # Debian
        f"{home}/.var/app/com.valvesoftware.Steam/.local/share/Steam",           # Flatpak
        f"{home}/snap/steam/common/.local/share/Steam",                          # Snap
        "/mnt/*",
        "/media/*"
    ]
    
    for root in search_roots:
        full_pattern = f"{root}/{pattern}"
        matches = glob.glob(full_pattern)
        if matches:
            return os.path.join(matches[0], "Archipelago")
    
    return None


def _load_path_override(default_path: str) -> tuple[str, str]:
    """Check for path_override.txt in default location and load custom path if valid."""
    override_file = os.path.join(default_path, "path_override.txt")
    if not os.path.exists(override_file):
        return default_path, ""  # No override file, use default
    
    try:
        with open(override_file, 'r') as f:
            custom_path = f.readline().strip()
    except Exception as e:
        return default_path, f"Error reading path_override.txt: {e}"
    
    if not custom_path or custom_path == "":
        return default_path, "Path override file is empty, using default path"
    
    # Normalize the path
    custom_path = custom_path.replace("/", os.sep)
    custom_path = custom_path.rstrip(os.sep)
    
    # Validate the path
    if custom_path == "" or (os.sep not in custom_path and ":" not in custom_path):
        return default_path, f"Invalid path in override file: {custom_path}"
    
    # Accept the path
    custom_path = os.path.expanduser(custom_path)
    return custom_path, f"Path override loaded: {custom_path}"


class OblivionClientCommandProcessor(ClientCommandProcessor):
    @mark_raw
    def _cmd_set_save_path(self, path: str = ""):
        """Set Oblivion save path manually."""
        if not path:
            self.output("Usage: /set_save_path <path>")
            return True
        
        # Require disconnection before changing path
        if hasattr(self.ctx, 'slot_data') and self.ctx.slot_data:
            self.output("Error: You must disconnect from the multiworld before changing the save path.")
            return True
        
        # Normalize the path
        path = os.path.expanduser(path)
        if path.endswith(os.sep + "Saved"):
            path = os.path.join(path, "Archipelago")
        
        # Convert to absolute path to ensure it's valid
        path = os.path.abspath(path)
        
        try:
            os.makedirs(path, exist_ok=True)
            self.ctx.oblivion_save_path = path
            self.output(f"Path set to: {path}")

            # Write path_override.txt to the default Archipelago directory so the path
            # persists across game launches (Lua mod reads this file at startup).
            if platform.system() == "Windows":
                default_path = os.path.join(
                    os.environ.get("USERPROFILE", ""),
                    "Documents", "My Games", "Oblivion Remastered", "Saved", "Archipelago"
                )
            else:
                default_path = os.path.join(os.path.expanduser("~"), ".config", "Archipelago", "oblivion")
            os.makedirs(default_path, exist_ok=True)
            override_file = os.path.join(default_path, "path_override.txt")
            with open(override_file, 'w') as f:
                f.write(path + "\n")
            self.output(f"Saved to path_override.txt — path will persist across launches.")
        except Exception as e:
            self.output(f"Error: {e}")
        return True
    
    def _cmd_oblivion(self):
        """Print information about connected Oblivion game."""
        if not isinstance(self.ctx, OblivionContext):
            return
            
        self.output(f"Oblivion Remastered Status:")
        self.output(f"- Items received: {len(self.ctx.items_received)}")
        self.output(f"- Locations checked: {len(self.ctx.checked_locations)}")
        self.output(f"- Missing locations: {len(self.ctx.missing_locations)}")
        
        # Display essential world information if available
        if hasattr(self.ctx, 'slot_data') and self.ctx.slot_data:
            # Goal and content limits
            goal = self.ctx.slot_data.get("goal", "shrine_seeker")
            self.output(f"Goal: {goal.replace('_', ' ').title()}")
            
            if goal == "shrine_seeker":
                shrine_goal = self.ctx.slot_data.get("shrine_goal", 5)
                shrine_count = self.ctx.slot_data.get("shrine_count", 10)
                self.output(f"- Complete {shrine_goal} of {shrine_count} shrines to win")
            elif goal == "gatecloser":
                gate_count = self.ctx.slot_data.get("gate_count_required", 5)
                self.output(f"- Close {gate_count} gates to win")
            elif goal == "arena":
                self.output("- Complete 21 Arena matches and become Grand Champion to win")
            elif goal == "light_the_dragonfires":
                self.output("- Progress the Main Quest and light the Dragonfires to win")
            elif goal == "dungeon_delver":
                regions_required = len(self.ctx.slot_data.get("selected_regions", []) or [])
                self.output(f"- Clear all dungeons in {regions_required} selected region(s) to win")
            
            # Content available
            gate_count = self.ctx.slot_data.get("gate_count_required", 0)
            shrine_count = self.ctx.slot_data.get("shrine_count", 10)
            arena_matches = self.ctx.slot_data.get("arena_matches", 21)
            dungeons_selected_count = self.ctx.slot_data.get("dungeons_selected", 0)
            
            # Class system information
            selected_class = self.ctx.slot_data.get("selected_class")
            class_level_maximum = self.ctx.slot_data.get("class_level_maximum", 5)
            class_skills = self.ctx.slot_data.get("class_skills", [])
            
            self.output(f"\nContent Available:")
            if gate_count > 0:
                self.output(f"- Gates: {gate_count}")
            if shrine_count > 0:
                self.output(f"- Shrines: {shrine_count}")
            if arena_matches > 0:
                self.output(f"- Arena matches: {arena_matches}")
            # Show selected dungeons/regions when region-based system is active
            selected_dungeons = self.ctx.slot_data.get("selected_dungeons", []) or []
            selected_regions = self.ctx.slot_data.get("selected_regions", []) or []
            if selected_dungeons:
                self.output(f"- Dungeons selected: {len(selected_dungeons)} across {len(selected_regions)} region(s)")
            elif dungeons_selected_count > 0:
                self.output(f"- Dungeons selected: {dungeons_selected_count}")
            
            # Class system display
            if selected_class:
                self.output(f"\nClass System:")
                self.output(f"- Selected Class: {selected_class.title()}")
                self.output(f"- Class Level Maximum: {class_level_maximum}")
                self.output(f"- Class Skills: {', '.join(class_skills)}")
                total_class_checks = class_level_maximum * len(class_skills) * 2
                self.output(f"- Total Class Skill Checks: {total_class_checks}")
            else:
                self.output(f"\nClass System: Disabled (no skill checks available)")
    
    def _cmd_regions(self):
        """Display all regions with their dungeons and doomstones."""
        from worlds.oblivion.Locations import DUNGEON_REGIONS, DOOMSTONE_REGIONS
        
        # Organize dungeons by region
        regions_data = {}
        for dungeon, region in DUNGEON_REGIONS.items():
            if region not in regions_data:
                regions_data[region] = {"dungeons": [], "doomstones": []}
            regions_data[region]["dungeons"].append(dungeon)
        
        # Add doomstones to regions
        for doomstone_location, region in DOOMSTONE_REGIONS.items():
            # Extract stone name from "Visit the X Stone" format
            stone_name = doomstone_location.replace("Visit the ", "").replace(" Stone", "")
            if region in regions_data:
                regions_data[region]["doomstones"].append(stone_name)
        
        # Display in alphabetical order
        self.output("=== CYRODIIL REGIONS ===\n")
        for region in sorted(regions_data.keys()):
            data = regions_data[region]
            dungeon_count = len(data["dungeons"])
            
            self.output(f"[{region}]")
            if data["doomstones"]:
                doomstones_str = ", ".join(sorted(data["doomstones"]))
                self.output(f"  Doomstones: {doomstones_str}")
            else:
                self.output(f"  Doomstones: None")
            self.output(f"  Dungeons ({dungeon_count}):")
            
            # Sort and display dungeons in columns
            dungeons = sorted(data["dungeons"])
            for dungeon in dungeons:
                self.output(f"    - {dungeon}")
            self.output("")
        
        # Gate keys if relevant
        gate_count = self.ctx.slot_data.get("gate_count_required", 0)
        if gate_count > 0:
                extra_keys = self.ctx.slot_data.get("extra_gate_keys", 0)
                total_keys = gate_count + extra_keys
                self.output(f"\nGate keys: {total_keys} total ({extra_keys} extra)")
    
                # Gate Vision setting
                gate_vision = self.ctx.slot_data.get("gate_vision", "item")
                self.output(f"Gate Vision: {gate_vision.title()}")


class OblivionContext(CommonContext):
    command_processor = OblivionClientCommandProcessor
    game = "Oblivion Remastered"
    items_handling = 0b111
    base_title = "Archipelago Oblivion Client"
    
    def __init__(self, server_address, password):
        super().__init__(server_address, password)
        
        # File system paths
        if platform.system() == "Windows":
            default_path = os.path.join(
                os.environ.get("USERPROFILE", ""), 
                "Documents", "My Games", "Oblivion Remastered", "Saved", "Archipelago"
            )
            self.oblivion_save_path = default_path
        else:
            # Linux: Auto-detect Proton prefix
            detected = _find_proton_save_path()
            if detected:
                default_path = detected
                self._path_detection_message = f"Auto-detected save path: {detected}"
            else:
                default_path = os.path.join(os.path.expanduser("~"), ".config", "Archipelago", "oblivion")
                self._path_detection_message = f"Could not auto-detect save path. Using: {default_path}\nUse /set_save_path <path> if incorrect"
            self.oblivion_save_path = default_path
        
        # Check for path override file in the default location
        new_path, status = _load_path_override(default_path)
        self._path_override_message = ""
        if status:
            (logger.warning if "Error" in status or "Invalid" in status else logger.info)(status)
            if "loaded" in status.lower():
                self.oblivion_save_path = new_path
                self._path_override_message = status
        
        # Completion token mapping: mod token -> location name
        self.completion_tokens = {
            "APAzuraCompletionToken": "Azura Quest Complete",
            "APBoethiaCompletionToken": "Boethia Quest Complete", 
            "APClavicusVileCompletionToken": "Clavicus Vile Quest Complete",
            "APHermaeusMoraCompletionToken": "Hermaeus Mora Quest Complete",
            "APHircineCompletionToken": "Hircine Quest Complete",
            "APMalacathCompletionToken": "Malacath Quest Complete",
            "APMephalaCompletionToken": "Mephala Quest Complete",
            "APMeridiaCompletionToken": "Meridia Quest Complete",
            "APMolagBalCompletionToken": "Molag Bal Quest Complete",
            "APNamiraCompletionToken": "Namira Quest Complete",
            "APNocturnalCompletionToken": "Nocturnal Quest Complete",
            "APPeryiteCompletionToken": "Peryite Quest Complete",
            "APSanguineCompletionToken": "Sanguine Quest Complete",
            "APSheogorathCompletionToken": "Sheogorath Quest Complete", 
            "APVaerminaCompletionToken": "Vaermina Quest Complete",
            # Arena checks
            "APArenaMatch1Victory": "Arena Match 1 Victory",
            "APArenaMatch2Victory": "Arena Match 2 Victory",
            "APArenaMatch3Victory": "Arena Match 3 Victory",
            "APArenaMatch4Victory": "Arena Match 4 Victory",
            "APArenaMatch5Victory": "Arena Match 5 Victory",
            "APArenaMatch6Victory": "Arena Match 6 Victory",
            "APArenaMatch7Victory": "Arena Match 7 Victory",
            "APArenaMatch8Victory": "Arena Match 8 Victory",
            "APArenaMatch9Victory": "Arena Match 9 Victory",
            "APArenaMatch10Victory": "Arena Match 10 Victory",
            "APArenaMatch11Victory": "Arena Match 11 Victory",
            "APArenaMatch12Victory": "Arena Match 12 Victory",
            "APArenaMatch13Victory": "Arena Match 13 Victory",
            "APArenaMatch14Victory": "Arena Match 14 Victory",
            "APArenaMatch15Victory": "Arena Match 15 Victory",
            "APArenaMatch16Victory": "Arena Match 16 Victory",
            "APArenaMatch17Victory": "Arena Match 17 Victory",
            "APArenaMatch18Victory": "Arena Match 18 Victory",
            "APArenaMatch19Victory": "Arena Match 19 Victory",
            "APArenaMatch20Victory": "Arena Match 20 Victory",
            "APArenaMatch21Victory": "Arena Match 21 Victory",
            # Progressive Shop Stock checks (mod tokens stay same, only Python mapping changes)
            "APShopTokenValue1CompletionToken": "Innkeeper Shop Item Value 1",
            "APShopTokenValue10CompletionToken": "Innkeeper Shop Item Value 10", 
            "APShopTokenValue100CompletionToken": "Innkeeper Shop Item Value 100",
            "APShopTokenValue2CompletionToken": "Innkeeper Shop Item Value 2",
            "APShopTokenValue20CompletionToken": "Innkeeper Shop Item Value 20",
            "APShopTokenValue200CompletionToken": "Innkeeper Shop Item Value 200",
            "APShopTokenValue3CompletionToken": "Innkeeper Shop Item Value 3",
            "APShopTokenValue30CompletionToken": "Innkeeper Shop Item Value 30",
            "APShopTokenValue300CompletionToken": "Innkeeper Shop Item Value 300",
            "APShopTokenValue4CompletionToken": "Innkeeper Shop Item Value 4",
            "APShopTokenValue40CompletionToken": "Innkeeper Shop Item Value 40",
            "APShopTokenValue400CompletionToken": "Innkeeper Shop Item Value 400",
            "APShopTokenValue5CompletionToken": "Innkeeper Shop Item Value 5",
            "APShopTokenValue50CompletionToken": "Innkeeper Shop Item Value 50",
            "APShopTokenValue500CompletionToken": "Innkeeper Shop Item Value 500",
            # Main Quest checks
            "Deliver the Amulet": "Deliver the Amulet",
            "Breaking the Siege of Kvatch: Gate Closed": "Breaking the Siege of Kvatch: Gate Closed",
            "Breaking the Siege of Kvatch": "Breaking the Siege of Kvatch",
            "Find the Heir": "Find the Heir",
            "Weynon Priory": "Weynon Priory",
            "Battle for Castle Kvatch": "Battle for Castle Kvatch",
            # MQ05
            "The Path of Dawn: Acquire Commentaries Vol I": "The Path of Dawn: Acquire Commentaries Vol I",
            "The Path of Dawn: Acquire Commentaries Vol II": "The Path of Dawn: Acquire Commentaries Vol II",
            "The Path of Dawn: Acquire Commentaries Vol III": "The Path of Dawn: Acquire Commentaries Vol III",
            "The Path of Dawn: Acquire Commentaries Vol IV": "The Path of Dawn: Acquire Commentaries Vol IV",
            "The Path of Dawn": "The Path of Dawn",
            # MQ06
            "Dagon Shrine: Mysterium Xarxes Acquired": "Dagon Shrine: Mysterium Xarxes Acquired",
            "Dagon Shrine: Kill Harrow": "Dagon Shrine: Kill Harrow",
            "Dagon Shrine": "Dagon Shrine",
            # MQ07 Spies
            "Spies: Kill Saveri Faram": "Spies: Kill Saveri Faram",
            "Spies: Kill Jearl": "Spies: Kill Jearl",
            "Spies": "Spies",
            # MQ07+ and event/milestone completions
            "Blood of the Daedra": "Blood of the Daedra",
            "Blood of the Divines": "Blood of the Divines",
            "Blood of the Divines: Free Spirit 1": "Blood of the Divines: Free Spirit 1",
            "Blood of the Divines: Free Spirit 2": "Blood of the Divines: Free Spirit 2",
            "Blood of the Divines: Free Spirit 3": "Blood of the Divines: Free Spirit 3",
            "Blood of the Divines: Free Spirit 4": "Blood of the Divines: Free Spirit 4",
            "Blood of the Divines: Armor of Tiber Septim": "Blood of the Divines: Armor of Tiber Septim",
            "Bruma Gate": "Bruma Gate",
            "Miscarcand": "Miscarcand",
            "Miscarcand: Great Welkynd Stone": "Miscarcand: Great Welkynd Stone",
            "Defense of Bruma": "Defense of Bruma",
            "Great Gate": "Great Gate",
            "Paradise": "Paradise",
            "Paradise: Bands of the Chosen Acquired": "Paradise: Bands of the Chosen Acquired",
            "Paradise: Bands of the Chosen Removed": "Paradise: Bands of the Chosen Removed",
            "Attack on Fort Sutch": "Attack on Fort Sutch",
            "Weynon Priory Quest Complete": "Weynon Priory Quest Complete",
            "Paradise Complete": "Paradise Complete",
            "Light the Dragonfires": "Light the Dragonfires",
        }
        
        # State tracking
        self.last_completion_check = 0
        self.file_prefix = ""
        self.session_id = ""
        self.game_loop_task = None
        self.bridge_processed_items = {}
        self.victory_sent = False
        self.regions_completed_sent = set()
        
        # Deathlink state
        self.deathlink_enabled = False
        self.deathlink_pending = False
        self.last_death_sent = 0

        # Trap state: track which indices in items_received have already been
        # written to _traps.txt so we never fire the same trap twice.
        self.sent_trap_indices: Set[int] = set()

        
        # Progressive item tracking
        self.progressive_states = {
            "Progressive Arena Rank": 0,
            "Progressive Shop Stock": 0,
            "Progressive Armor Set": 0,
            "Progressive Nirnroot Satchel": 0,
            "Progressive Septim Satchel": 0,
            **{f"Progressive {class_name} Level": 0
               for class_name in [
                   "Acrobat", "Agent", "Archer", "Assassin", "Barbarian", "Bard", "Battlemage",
                   "Crusader", "Healer", "Knight", "Mage", "Monk", "Nightblade", "Pilgrim",
                   "Rogue", "Scout", "Sorcerer", "Spellsword", "Thief", "Warrior", "Witchhunter"
               ]}
        }
        
        # Progressive item lookup tables
        self.progressive_lookups = {
            "Progressive Arena Rank": [
                "APArenaPitDogUnlock",
                "APArenaBrawlerUnlock", 
                "APArenaBloodletterUnlock",
                "APArenaMyrmidonUnlock",
                "APArenaWarriorUnlock",
                "APArenaGladiatorUnlock",
                "APArenaHeroUnlock"
            ],
            "Progressive Shop Stock": [
                ["APShopCheckValue2", "APShopCheckValue20", "APShopCheckValue200"],   # Set 2
                ["APShopCheckValue3", "APShopCheckValue30", "APShopCheckValue300"],   # Set 3
                ["APShopCheckValue4", "APShopCheckValue40", "APShopCheckValue400"],   # Set 4
                ["APShopCheckValue5", "APShopCheckValue50", "APShopCheckValue500"]    # Set 5
            ],
            "Progressive Armor Set": [
                ["APArmorTier2"],   # Tier 2 (Chainmail/Dwarven) - 1st Progressive Armor Set (early placement)
                ["APArmorTier4"],   # Tier 4 (Elven/Ebony) - 2nd Progressive Armor Set
                ["APArmorTier5"]    # Tier 5 (Glass/Daedric) - 3rd Progressive Armor Set
            ],
            "Progressive Nirnroot Satchel": [
                "APNirnrootSatchel1",  # Capacity 5
                "APNirnrootSatchel2",  # Capacity 15
                "APNirnrootSatchel3",  # Capacity 30
                "APNirnrootSatchel4",  # Capacity 50
                "APNirnrootSatchel5"   # Capacity 100
            ],
            "Progressive Septim Satchel": [
                "APSeptimSatchel1",  # Capacity 2500
                "APSeptimSatchel2",  # Capacity 5000
                "APSeptimSatchel3",  # Capacity 10000
                "APSeptimSatchel4",  # Capacity 25000
                "APSeptimSatchel5"   # Capacity Unlimited
            ],
            # Progressive Class Level items
            **{f"Progressive {class_name} Level": [f"APClassLevel{i}" for i in range(1, 21)]
             for class_name in [
                "Acrobat", "Agent", "Archer", "Assassin", "Barbarian", "Bard", "Battlemage",
                "Crusader", "Healer", "Knight", "Mage", "Monk", "Nightblade", "Pilgrim",
                "Rogue", "Scout", "Sorcerer", "Spellsword", "Thief", "Warrior", "Witchhunter"
             ]}
    }
        
        # Ensure save directory exists
        try:
            os.makedirs(self.oblivion_save_path, exist_ok=True)
        except Exception:
            pass  # Failure reported to UI in the Connected handler
        
        # Initialize tracker
        self.tracker_enabled = True
        self.tracker = None  # Will be initialized after connection
        
    async def server_auth(self, password_requested: bool = False):
        if password_requested and not self.password:
            await super().server_auth(password_requested)
        await self.get_username()
        await self.send_connect()
        
    def on_deathlink(self, data: dict):
        """Handle incoming deathlink from another player."""
        try:
            super().on_deathlink(data)
            self.deathlink_pending = True
            asyncio.create_task(self._send_deathlink_to_mod())
        except Exception as e:
            logger.error(f"[DeathLink] Error in on_deathlink: {e}", exc_info=True)
    
    def on_package(self, cmd: str, args: dict):
        """Handle incoming server packages."""
        if cmd == "Connected":
            self.slot_data = args.get("slot_data", {})
            self.session_id = self.slot_data.get("session_id", "")
            
            # Set up file prefix
            auth_name = getattr(self, 'auth', None) or getattr(self, 'player_name', None) or getattr(self, 'name', None)
            if auth_name:
                self.auth = auth_name
                self._setup_file_prefix()
            
            # Add selected progressive class level item to states
            progressive_class_level_item_name = self.slot_data.get("progressive_class_level_item_name")
            if progressive_class_level_item_name:
                self.progressive_states[progressive_class_level_item_name] = 0
            
            # Enable deathlink if option is set
            if self.slot_data.get("death_link", False):
                logger.info("[DeathLink] Enabling deathlink for this session")
                # Add DeathLink tag directly and send ConnectUpdate
                old_tags = self.tags.copy()
                self.tags.add("DeathLink")
                self.deathlink_enabled = True
                # Send ConnectUpdate if tags changed and we're connected
                if old_tags != self.tags and self.server and not self.server.socket.closed:
                    asyncio.create_task(self.send_msgs([{"cmd": "ConnectUpdate", "tags": self.tags}]))
            
            # Initialize tracker after slot_data is available
            self.tracker = OblivionTracker(self)
            
            asyncio.create_task(self._setup_after_connection())
            # Initial shop tier (tier 1) scout scheduling
            if self.tracker:
                self.tracker.schedule_shop_scout()
                self.tracker.update_goal_progress()
            
            # Display available item groups for hinting
            self._display_item_groups()
            
            # Display path override message if one was loaded
            if hasattr(self, '_path_override_message') and self._path_override_message:
                logger.info(self._path_override_message)
            
            # Display path detection message if Linux
            if hasattr(self, '_path_detection_message'):
                logger.info(self._path_detection_message)

            # Check that we can actually write to the save directory
            try:
                os.makedirs(self.oblivion_save_path, exist_ok=True)
                test_file = os.path.join(self.oblivion_save_path, ".ap_write_test")
                with open(test_file, "w") as f:
                    f.write("test")
                os.remove(test_file)
            except Exception as e:
                logger.error(f"[Oblivion] Cannot write to save directory: {self.oblivion_save_path}")
                logger.error(f"[Oblivion] Error: {e}")
                logger.error("[Oblivion] The mod will not receive items. Try running as Administrator or use /set_save_path to choose a different location.")
        elif cmd == "ReceivedItems":
            asyncio.create_task(self._send_items_to_oblivion())
            # Update tracker with new items
            if self.tracker:
                self.tracker.refresh_items()
                # Progressive Shop Stock will unlock a new tier
                self.tracker.schedule_shop_scout()
                # Update existing rows
                self.tracker.update_shop_tab()
        elif cmd == "LocationInfo":
            # Handle scout responses for shop items (when not using create_as_hint)
            if self.tracker and "locations" in args:
                for location_info in args["locations"]:
                    # NetworkItem objects use attributes, not dict keys
                    loc_id = location_info.location
                    if not isinstance(loc_id, int) or loc_id not in self.tracker.shop_ids:
                        continue
                    item_id = location_info.item
                    if not isinstance(item_id, int):
                        continue
                    receiving_player = location_info.player
                    flags = location_info.flags
                    try:
                        item_name = self.item_names.lookup_in_slot(item_id, receiving_player)
                    except Exception:
                        item_name = f"Item {item_id}"
                    
                    # Store in shop_cache
                    self.tracker.shop_cache[loc_id] = {
                        "item_id": item_id,
                        "item_name": item_name,
                        "player": self.slot,  # finding player is us
                        "receiving_player": receiving_player,
                        "flags": flags
                    }
                # Mark initialization as done and update display
                self.tracker._shop_init_done = True
                self.tracker.update_shop_tab()
        elif cmd == "RoomUpdate":
            if "checked_locations" in args:
                # Sync checked_locations and missing_locations with server
                new_checked = set(args["checked_locations"])
                if hasattr(self, 'checked_locations'):
                    self.checked_locations |= new_checked
                else:
                    self.checked_locations = set(new_checked)
                if hasattr(self, 'missing_locations'):
                    self.missing_locations -= new_checked
            # Capture full missing_locations set when provided
            if "missing_locations" in args:
                # Server provides list of all location ids still missing
                self.missing_locations = set(args["missing_locations"])
                # Remove any we already have marked as checked (safety)
                if hasattr(self, 'checked_locations'):
                    self.missing_locations -= self.checked_locations
            # After updating sets, refresh tracker state
            if self.tracker:
                self.tracker.update_locations()
                self.tracker.update_shop_tab()
                self.tracker.schedule_shop_scout()
                self.tracker.update_goal_progress()
            
    def on_print_json(self, args: dict):
        """Handle PrintJSON messages from server, including item transfers."""
        # Call parent method for normal handling
        super().on_print_json(args)
        # Live hint integration for Shop tab
        if not hasattr(self, 'tracker') or not self.tracker:
            return
        if args.get('type') == 'Hint':
            # Re-scan stored hints and update UI
            self.tracker.refresh_shop_from_stored_hints()
            self.tracker.update_shop_tab()

        # Live hint arrival: capture shop item hints immediately
        if args.get("type") == "Hint":
            try:
                hint = args.get("hint", {})
                loc_id = hint.get("location")
                if isinstance(loc_id, int) and getattr(self, 'tracker', None) and loc_id in getattr(self.tracker, 'shop_ids', set()):
                    item_id = hint.get("item")
                    if isinstance(item_id, int):
                        try:
                            item_name = self.item_names.lookup_in_slot(item_id, hint.get("receiving_player"))
                        except Exception:
                            item_name = f"Item {item_id}"
                        self.tracker.shop_cache[loc_id] = {"item_id": item_id,
                                                           "item_name": item_name,
                                                           "player": hint.get("finding_player"),
                                                           "receiving_player": hint.get("receiving_player"),
                                                           "flags": hint.get("item_flags", 0)}
                        self.tracker._shop_init_done = True
                        if hasattr(self, 'tab_shop'):
                            self.tracker.update_shop_tab()
            except Exception:
                pass
        
        # Check if this is an item transfer message
        if args.get("type") == "ItemSend":
            item = args.get("item")
            if not item:
                return
                
            source_player = item.player
            destination_player = args.get("receiving")
            self_slot = self.slot
            
            # Only process if we're involved (sender or receiver)
            if self_slot not in [source_player, destination_player]:
                return
                
            # We sent an item to another player
            if self_slot == source_player and self_slot != destination_player:
                recipient_name = self.player_names[destination_player]
                item_name = self.item_names.lookup_in_slot(item.item, destination_player)
                location_name = None
                try:
                    if hasattr(item, 'location') and item.location is not None:
                        location_name = self.location_names.lookup_in_slot(item.location, source_player)
                except Exception:
                    location_name = None
                data = {"direction": "sent", "item": item_name, "other_player": recipient_name}
                if location_name:
                    data["location"] = location_name
                self._write_transfer_log(data)
                
            # We received an item from another player
            elif self_slot == destination_player and self_slot != source_player:
                sender_name = self.player_names[source_player]
                item_name = self.item_names.lookup_in_slot(item.item, self_slot)
                location_name = None
                try:
                    if hasattr(item, 'location') and item.location is not None:
                        location_name = self.location_names.lookup_in_slot(item.location, source_player)
                except Exception:
                    location_name = None
                data = {"direction": "received", "item": item_name, "other_player": sender_name}
                if location_name:
                    data["location"] = location_name
                self._write_transfer_log(data)
            
            # We found our own item
            elif self_slot == source_player and self_slot == destination_player:
                item_name = self.item_names.lookup_in_slot(item.item, self_slot)
                location_name = self.location_names.lookup_in_slot(item.location, self_slot)
                self._write_transfer_log({
                    "direction": "found",
                    "item": item_name,
                    "location": location_name
                })
    
    def _write_transfer_log(self, transfer_info: dict):
        """Write transfer information to a file the mod can read."""
        if not self.file_prefix:
            return
            
        transfer_file = os.path.join(self.oblivion_save_path, f"{self.file_prefix}_item_events.txt")
        
        try:
            with open(transfer_file, "a") as f:
                if transfer_info["direction"] == "found":
                    # Found items include location
                    f.write(f"{transfer_info['direction']}|{transfer_info['item']}|{transfer_info['location']}\n")
                else:
                    # Sent/received items
                    if 'location' in transfer_info and transfer_info['location']:
                        f.write(f"{transfer_info['direction']}|{transfer_info['item']}|{transfer_info['other_player']}|{transfer_info['location']}\n")
                    else:
                        f.write(f"{transfer_info['direction']}|{transfer_info['item']}|{transfer_info['other_player']}\n")
        except Exception as e:
            logger.error(f"Error writing transfer log: {e}")
    
    def _display_item_groups(self):
        """Display available item groups for hinting on client startup."""
        try:
            from worlds.oblivion.Items import item_name_groups
            
            logger.info("==========================================")
            logger.info("Available Item Groups:")
            
            # Format groups in a compact comma-separated list with better spacing
            group_names = sorted(item_name_groups.keys())
            groups_text = ",  ".join(group_names)
            logger.info(groups_text)
            logger.info("")
            logger.info("Use '!hint <group name>' to get a hint for the next logical item in that group.")
            logger.info("==========================================")
        except Exception as e:
            logger.warning(f"Could not load item groups: {e}")
            
    async def _setup_after_connection(self):
        """Complete setup after successful connection to slot."""
        if not self.file_prefix or not self.session_id:
            logger.error("File prefix or session_id not set during connection")
            return
            
        self._load_progressive_states()
            
        self._check_existing_items_file()
        
        # Write game configuration files
        self._write_settings_file()
        self._write_connection_info()
        logger.info(f"Connected as {self.auth} with session {self.session_id[:8]}")
        
        # Wait for connection data to be fully populated
        await self._wait_for_connection_data()
        
        # Check for any existing completion files
        await self._check_for_locations(force_check=True)
        
        # Start the file monitoring loop
        self._start_game_loop()
            
    def _setup_file_prefix(self):
        """Setup file prefix based on player name and session ID."""
        from Utils import get_file_safe_name
        safe_auth = get_file_safe_name(self.auth)
        session_short = self.session_id[:8] if self.session_id else "nosession"
        self.file_prefix = f"AP_{safe_auth}_{session_short}"
        self._load_sent_trap_indices()

    def _load_sent_trap_indices(self):
        if not self.file_prefix:
            return
        path = os.path.join(self.oblivion_save_path, f"{self.file_prefix}_traps_sent.txt")
        if not os.path.exists(path):
            return
        try:
            with open(path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.isdigit():
                        self.sent_trap_indices.add(int(line))
        except Exception as e:
            logger.error(f"Error loading trap sent indices: {e}")

    def _save_sent_trap_indices(self):
        if not self.file_prefix:
            return
        path = os.path.join(self.oblivion_save_path, f"{self.file_prefix}_traps_sent.txt")
        try:
            with open(path, "w") as f:
                for idx in sorted(self.sent_trap_indices):
                    f.write(f"{idx}\n")
        except Exception as e:
            logger.error(f"Error saving trap sent indices: {e}")
    
    def _load_progressive_states(self):
        """Load progressive item states from file."""
        if not self.file_prefix:
            return
            
        progressive_file = os.path.join(self.oblivion_save_path, f"{self.file_prefix}_progression_levels.txt")
        
        if not os.path.exists(progressive_file):
            return
            
        try:
            with open(progressive_file, "r") as f:
                for line in f:
                    if "=" in line:
                        item_type, count_str = line.strip().split("=", 1)
                        if item_type in self.progressive_states:
                            self.progressive_states[item_type] = int(count_str)
        except Exception as e:
            # Reset to defaults on error
            self.progressive_states = {
                "Progressive Arena Rank": 0,
                "Progressive Shop Stock": 0,
                "Progressive Armor Set": 0,
                **{f"Progressive {class_name} Level": 0
                   for class_name in [
                       "Acrobat", "Agent", "Archer", "Assassin", "Barbarian", "Bard", "Battlemage",
                       "Crusader", "Healer", "Knight", "Mage", "Monk", "Nightblade", "Pilgrim",
                       "Rogue", "Scout", "Sorcerer", "Spellsword", "Thief", "Warrior", "Witchhunter"
                   ]}
            }
    
    def _save_progressive_states(self):
        """Save progressive item states to file."""
        if not self.file_prefix:
            return
            
        progressive_file = os.path.join(self.oblivion_save_path, f"{self.file_prefix}_progression_levels.txt")
        
        try:
            with open(progressive_file, "w") as f:
                for item_type, count in self.progressive_states.items():
                    f.write(f"{item_type}={count}\n")
        except Exception as e:
            logger.error(f"Error saving progressive states: {e}")
    
    def _process_progressive_items(self, items):
        """Process a list of items, converting progressive items to queue items."""
        queue_items = []
        
        for item_name in items:
            if item_name in self.progressive_states:
                # This is a progressive item
                current_level = self.progressive_states[item_name]
                max_level = len(self.progressive_lookups[item_name])
                
                if current_level < max_level:
                    # Get the item(s) for this progression level
                    level_items = self.progressive_lookups[item_name][current_level]
                    
                    if isinstance(level_items, list):
                        # Shop Stock - add all 3 items for this set
                        queue_items.extend(level_items)
                    else:
                        # Arena Rank - add single item
                        queue_items.append(level_items)
                else:
                    logger.warning(f"Progressive item {item_name} already at max level ({max_level})")
            else:
                # Regular item, pass through unchanged
                queue_items.append(item_name)
        
        return queue_items

    def _check_existing_items_file(self):
        """Check if items file exists and display warning to user."""
        items_file = os.path.join(self.oblivion_save_path, f"{self.file_prefix}_items.txt")
        if not os.path.exists(items_file):
            return
            
        try:
            with open(items_file, "r") as f:
                items = [line.strip() for line in f.readlines() if line.strip()]
            
            if items:
                logger.warning(f"{len(items)} items in queue - will be sent when Oblivion starts.")
        except Exception as e:
            logger.error(f"Error checking existing items file: {e}")
        
    def _write_connection_info(self):
        """Write connection info for the mod to read."""
        connection_file = os.path.join(self.oblivion_save_path, "current_connection.txt")
        try:
            with open(connection_file, "w") as f:
                f.write(f"file_prefix={self.file_prefix}\n")
                f.write(f"session_id={self.session_id}\n")
                f.write(f"slot_name={self.auth}\n")
                f.write(f"connected_time={int(time.time())}\n")
        except Exception as e:
            logger.error(f"Error writing connection info: {e}")
            
    def _load_connection_info(self):
        """Load connection info from file."""
        connection_file = os.path.join(self.oblivion_save_path, "current_connection.txt")
        if not os.path.exists(connection_file):
            return False
            
        try:
            with open(connection_file, "r") as f:
                for line in f:
                    if line.startswith("file_prefix="):
                        self.file_prefix = line.split("=", 1)[1].strip()
                    elif line.startswith("session_id="):
                        self.session_id = line.split("=", 1)[1].strip()
            return bool(self.file_prefix)
        except Exception as e:
            logger.error(f"Error loading connection info: {e}")
            return False

    def _write_settings_file(self):
        """Write game settings for the mod to read."""
        settings_path = os.path.join(self.oblivion_save_path, f"{self.file_prefix}_settings.txt")
        
        # Check if settings file already exists for this session_id
        if os.path.exists(settings_path):
            try:
                with open(settings_path, "r") as f:
                    for line in f:
                        if line.startswith("session_id="):
                            existing_session_id = line.split("=", 1)[1].strip()
                            if existing_session_id == self.session_id:
                                # Settings file already exists for this session
                                return
                            break
            except Exception as e:
                logger.error(f"Error checking existing settings file: {e}")
        
        free_offerings = bool(self.slot_data.get("free_offerings", False))
        active_shrines = self.slot_data.get("active_shrines", [])
        shrine_offerings = self.slot_data.get("shrine_offerings", {})
        
        try:
            with open(settings_path, "w") as f:
                # Use Python's standard boolean string conversion
                f.write(f"free_offerings={str(free_offerings)}\n")
                f.write(f"active_shrines={','.join(active_shrines)}\n")
                f.write(f"shrine_count={len(active_shrines)}\n")
                f.write(f"session_id={self.session_id}\n")  # Include session_id in settings
                
                # Write goal setting
                goal = self.slot_data.get("goal")
                if goal is None:
                    logger.error("Goal not found in slot_data")
                    return
                f.write(f"goal={goal}\n")

                # Write goal-specific requirements
                if goal == "shrine_seeker":
                    shrine_goal = int(self.slot_data["shrine_goal"]) 
                    f.write(f"goal_required={shrine_goal}\n")
                elif goal == "gatecloser":
                    gate_count_required = int(self.slot_data["gate_count_required"]) 
                    f.write(f"goal_required={gate_count_required}\n")
                elif goal == "dungeon_delver":
                    regions_required = len(self.slot_data.get("selected_regions", []) or [])
                    f.write(f"goal_required={regions_required}\n")
                elif goal == "nirnsanity":
                    nirnroot_count = int(self.slot_data.get("nirnroot_count", 50))
                    f.write(f"goal_required={nirnroot_count}\n")
                elif goal == "treasure_hunter":
                    gold_goal = int(self.slot_data.get("gold_goal", 10000))
                    f.write(f"goal_required={gold_goal}\n")

                # For non-nirnsanity goals, write nirnroot_count separately if > 0
                # (nirnsanity uses goal_required for this; other goals need a separate field)
                if goal != "nirnsanity":
                    nirnroot_count = int(self.slot_data.get("nirnroot_count", 0))
                    if nirnroot_count > 0:
                        f.write(f"nirnroot_count={nirnroot_count}\n")

                # Write progressive shop stock settings (always enabled)
                f.write(f"progressive_shop_stock=True\n")
                
                # Write progressive item states
                f.write(f"arena_rank_unlocked={self.progressive_states.get('Progressive Arena Rank', 0)}\n")
                f.write(f"shop_stock_unlocked={self.progressive_states.get('Progressive Shop Stock', 0)}\n")
                
                # Write gate vision setting
                gate_vision = self.slot_data.get("gate_vision", "item")
                f.write(f"gate_vision={gate_vision}\n")
                
                # Write gate count setting
                gate_count = self.slot_data.get("gate_count", 0)
                f.write(f"gate_count={gate_count}\n")


                # Write dungeon marker mode (controls reveal vs fast travel)
                dungeon_marker_mode = self.slot_data.get("dungeon_marker_mode", "reveal_and_fast_travel")
                f.write(f"dungeon_marker_mode={dungeon_marker_mode}\n")

                # Write dungeon selection and count for mod visibility
                selected_regions = self.slot_data.get("selected_regions", []) or []
                dungeons_by_region = self.slot_data.get("dungeons_by_region", {}) or {}
                selected_dungeons = self.slot_data.get("selected_dungeons", []) or []
                # Totals for selected dungeons and regions in this seed
                f.write(f"dungeon_selected_count={len(selected_dungeons)}\n")
                f.write(f"regions_selected_count={len(selected_regions)}\n")
                
                # Write arena settings
                arena_matches = self.slot_data.get("arena_matches", 0)
                if arena_matches > 0:
                    f.write(f"enable_arena=True\n")
                f.write(f"arena_matches={arena_matches}\n")
                
                # Write fast arena setting
                fast_arena = self.slot_data.get("fast_arena", False)
                f.write(f"fast_arena={'true' if bool(fast_arena) else 'false'}\n")
                
                # Write class system settings
                selected_class = self.slot_data.get("selected_class")
                
                if selected_class is not None:
                    f.write(f"class_system_enabled=True\n")
                    f.write(f"selected_class={selected_class}\n")
                else:
                    f.write(f"class_system_enabled=False\n")
                
                # Write fast travel item setting
                fast_travel_item = self.slot_data.get("fast_travel_item", False)
                f.write(f"fast_travel_item={'true' if bool(fast_travel_item) else 'false'}\n")
                
                # Write dungeon warp setting
                dungeon_warp = self.slot_data.get("dungeon_warp", "off")
                f.write(f"dungeon_warp={dungeon_warp}\n")

                # Write auto-tracking settings
                auto_tracking = self.slot_data.get("auto_tracking", False)
                f.write(f"auto_tracking={'True' if bool(auto_tracking) else 'False'}\n")
                silent_auto_tracking = self.slot_data.get("silent_auto_tracking", False)
                f.write(f"silent_auto_tracking={'True' if bool(silent_auto_tracking) else 'False'}\n")

                # Write kill check settings (enables kill tracking in the mod when > 0)
                dungeon_kills = self.slot_data.get("dungeon_kills", 0)
                overworld_kills = self.slot_data.get("overworld_kills", 0)
                if dungeon_kills > 0 or overworld_kills > 0:
                    f.write(f"track_kills=True\n")
                    f.write(f"dungeon_kills={dungeon_kills}\n")
                    f.write(f"overworld_kills={overworld_kills}\n")
                    f.write(f"dungeon_kills_per_region={self.slot_data.get('dungeon_kills_per_region', dungeon_kills)}\n")
                    f.write(f"overworld_kills_per_region={self.slot_data.get('overworld_kills_per_region', overworld_kills)}\n")

                # Write selected regions and per-region dungeon lists for the mod
                selected_regions = self.slot_data.get("selected_regions", []) or []
                dungeons_by_region = self.slot_data.get("dungeons_by_region", {}) or {}
                if selected_regions:
                    f.write(f"selected_regions={','.join(selected_regions)}\n")
                    for region_name in selected_regions:
                        region_dungeons = dungeons_by_region.get(region_name, []) or []
                        # Use a simple CSV list; region name preserved for readability
                        key = f"region_{region_name}_dungeons"
                        f.write(f"{key}={','.join(region_dungeons)}\n")
                        # provide the selected dungeon count per region
                        count_key = f"region_{region_name}_dungeon_count"
                        f.write(f"{count_key}={len(region_dungeons)}\n")
                
                # Write shrine-specific offerings
                if shrine_offerings:
                    for shrine, offerings in shrine_offerings.items():
                        if offerings:
                            f.write(f"offerings_{shrine}={','.join(offerings)}\n")
                
                # Write sidequest data
                selected_sidequests = self.slot_data.get("selected_sidequests", []) or []
                sidequest_count = self.slot_data.get("sidequest_count", 0)
                f.write(f"sidequest_count={sidequest_count}\n")
                if selected_sidequests:
                    f.write(f"selected_sidequests={','.join(selected_sidequests)}\n")
                    
        except Exception as e:
            logger.error(f"Error writing settings: {e}")
        

    def _read_bridge_status(self):
        """Read bridge status file to sync with already processed items."""
        if not self.file_prefix:
            return
            
        status_path = os.path.join(self.oblivion_save_path, f"{self.file_prefix}_bridge_status.txt")
        
        # Always initialize to empty - will be populated if file has content
        self.bridge_processed_items = {}
        
        if not os.path.exists(status_path):
            return
            
        try:
            with open(status_path, "r") as f:
                content = f.read().strip()
                if content:
                    processed_items = [item.strip() for item in content.split(",") if item.strip()]
                    # Count occurrences of each item
                    for item in processed_items:
                        self.bridge_processed_items[item] = self.bridge_processed_items.get(item, 0) + 1
        except Exception as e:
            logger.error(f"Error reading bridge status: {e}")
            self.bridge_processed_items = {}
        
    async def _send_items_to_oblivion(self):
        """Send received items to the game via file queue."""
        if not self.file_prefix:
            if not self._load_connection_info():
                return
        
        # Read latest bridge status before sending items
        self._read_bridge_status()
        
        # Read what's already in the queue
        queue_path = os.path.join(self.oblivion_save_path, f"{self.file_prefix}_items.txt")
        queued_items = []
        if os.path.exists(queue_path):
            try:
                with open(queue_path, "r") as f:
                    queued_items = [line.strip() for line in f if line.strip()]
            except Exception as e:
                logger.error(f"Error reading queue file: {e}")
        
        # Build list of items that need to be sent, separating traps from regular items
        from worlds.oblivion.Items import item_table, trap_code_map
        from BaseClasses import ItemClassification
        received_items = []
        # (index_in_items_received, trap_code) pairs for pending traps
        pending_traps: List[tuple] = []

        for idx, network_item in enumerate(self.items_received):
            # Look up item name by ID
            item_name = None
            for name, data in item_table.items():
                if data.id == network_item.item:
                    item_name = name
                    break
            if not item_name:
                continue
            # Traps are routed separately, never to _items.txt
            if item_table[item_name].classification == ItemClassification.trap:
                if idx not in self.sent_trap_indices:
                    trap_code = trap_code_map.get(item_name)
                    if trap_code:
                        pending_traps.append((idx, trap_code))
            else:
                received_items.append(item_name)

        # Fire any new traps before processing regular items
        if pending_traps:
            self._send_traps_to_oblivion(pending_traps)

        # Separate progressive items from regular items
        progressive_items = []
        regular_items = []
        
        for item_name in received_items:
            if item_name in self.progressive_states:
                progressive_items.append(item_name)
            else:
                regular_items.append(item_name)
        
        # Handle regular items with normal counting
        from collections import Counter
        regular_received_counts = Counter(regular_items)
        processed_counts = self.bridge_processed_items
        queued_counts = Counter(queued_items)
        
        new_regular_items = []
        for item_name, received_count in regular_received_counts.items():
            processed_count = processed_counts.get(item_name, 0)
            queued_count = queued_counts.get(item_name, 0)
            need_to_send = received_count - processed_count - queued_count
            
            for _ in range(max(0, need_to_send)):
                new_regular_items.append(item_name)
        
        # Handle progressive items separately
        new_progressive_items = []
        progressive_received_counts = Counter(progressive_items)

        for item_name, received_count in progressive_received_counts.items():
            max_level = len(self.progressive_lookups[item_name])
            for level in range(min(received_count, max_level)):
                level_items = self.progressive_lookups[item_name][level]
                if not isinstance(level_items, list):
                    level_items = [level_items]
                for level_item in level_items:
                    # Only queue if not already processed by bridge and not already in the queue
                    if processed_counts.get(level_item, 0) == 0 and queued_counts.get(level_item, 0) == 0:
                        new_progressive_items.append(level_item)

        # Combine all new items
        new_items = new_regular_items + new_progressive_items
                
        if new_items:
            # Process progressive items and convert them to queue items
            queue_items = self._process_progressive_items(new_items)
            
            if queue_items:
                self._append_items_to_queue(queue_items)
            else:
                logger.info("No items to send after progressive processing")
            
    def _append_items_to_queue(self, items):
        """Append items to the game's item queue file."""
        try:
            queue_path = os.path.join(self.oblivion_save_path, f"{self.file_prefix}_items.txt")
            with open(queue_path, "a") as f:
                for item_name in items:
                    f.write(f"{item_name}\n")
        except Exception as e:
            logger.error(f"Error adding items to queue: {e}")

    def _send_traps_to_oblivion(self, pending_traps: List[tuple]):
        """Write pending trap codes to the _traps.txt file for the mod to process.

        Each entry in pending_traps is a (items_received_index, trap_code) pair.
        Traps are appended to the file one code per line.  The mod reads the file,
        executes each trap, then deletes it.  sent_trap_indices (in-memory) prevents
        duplicate fires within a session.
        """
        if not self.file_prefix or not pending_traps:
            return
        traps_path = os.path.join(self.oblivion_save_path, f"{self.file_prefix}_traps.txt")
        try:
            with open(traps_path, "a") as f:
                for idx, trap_code in pending_traps:
                    f.write(f"{trap_code}\n")
                    self.sent_trap_indices.add(idx)
            self._save_sent_trap_indices()
        except Exception as e:
            logger.error(f"Error writing trap file: {e}")

    async def _send_deathlink_to_mod(self):
        """Send deathlink notification to the mod via a signal file."""
        if not self.file_prefix:
            logger.warning("[DeathLink] Cannot send to mod: file_prefix not set")
            if not self._load_connection_info():
                logger.error("[DeathLink] Failed to load connection info")
                return
        
        if not self.deathlink_pending:
            logger.debug("[DeathLink] No pending deathlink to send")
            return
            
        try:
            # Create a blank signal file that the mod will detect and delete
            deathlink_path = os.path.join(self.oblivion_save_path, f"{self.file_prefix}_deathlink.txt")
            
            with open(deathlink_path, "w") as f:
                f.write("")  # Blank file
            
            self.deathlink_pending = False
            
        except Exception as e:
            logger.error(f"Error sending deathlink to mod: {e}")

    async def _wait_for_connection_data(self):
        """Wait for missing_locations to be populated (indicates full connection)."""
        max_wait = 10
        wait_count = 0
        while not hasattr(self, 'missing_locations') or len(self.missing_locations) == 0:
            await asyncio.sleep(0.5)
            wait_count += 1
            if wait_count > max_wait * 2:
                logger.warning("Timeout waiting for missing_locations to populate, proceeding anyway")
                break
    
    async def _check_for_locations(self, force_check=False):
        """Check for completed locations from the game."""
        # Ensure we have the necessary connection data
        if not self.file_prefix:
            if not self._load_connection_info():
                return
        
        # Only proceed if fully connected to a slot
        if not hasattr(self, 'slot_data') or not self.slot_data:
            return
        if not hasattr(self, 'missing_locations') or not hasattr(self, 'checked_locations'):
            return
            
        completion_path = os.path.join(self.oblivion_save_path, f"{self.file_prefix}_completed.txt")
        
        if not os.path.exists(completion_path):
            return
            
        try:
            # Check file modification time to avoid redundant processing
            file_mtime = os.path.getmtime(completion_path)
            if not force_check and file_mtime <= self.last_completion_check:
                return
                
            self.last_completion_check = file_mtime
            
            # Read completion tokens from file
            with open(completion_path, "r") as f:
                completed_items = [line.strip() for line in f.readlines() if line.strip()]
            
            # Build location ID lookup table from pre-defined locations
            name_to_id_map = {name: data.id for name, data in Locations.location_table.items()}
            
            # Get configuration values for processing
            dungeons_selected_count = self.slot_data.get("dungeons_selected", 0)
                
            # Process each completion entry
            new_locations = []
            
            # Find the starting gate number
            next_gate_num = 1
            for i in range(1, 21):  # Up to 20 gates
                location_name = f"Gate {i} Closed"
                if location_name in name_to_id_map:
                    location_id = name_to_id_map[location_name]
                    if location_id in self.missing_locations:
                        next_gate_num = i
                        break
            
            for item in completed_items:
                # Check if this is a gate closed log entry
                if item == "Oblivion Gate Closed":
                    # Find the next available gate location
                    location_name = f"Gate {next_gate_num} Closed"
                    if location_name in name_to_id_map:
                        location_id = name_to_id_map[location_name]
                        if location_id in self.missing_locations and location_id not in new_locations:
                            new_locations.append(location_id)
                            next_gate_num += 1
                        else:
                            # We reached the maximum number of gates, so we can't award any more
                            #logger.warning(f"Could not award Gate, '{location_name}' is not available or already queued.")
                            pass
                    else:
                        logger.error(f"Location '{location_name}' not found in location table")
                        
                # Check if this is a Class Skill Increase text (format: "SkillName Skill Increase")
                elif " Skill Increase" in item and not item.endswith(" "):
                    # Parse class skill item: "SkillName Skill Increase"
                    skill_name = item.replace(" Skill Increase", "")
                    
                    # Basic safety check: ensure class system is enabled
                    selected_class = self.slot_data.get("selected_class")
                    if not selected_class:
                        logger.warning(f"Class system disabled, ignoring skill increase: {item}")
                        continue
                    
                    # Find the next available skill increase number for this skill
                    # Look for the next missing location for this skill
                    next_skill_increase_num = None
                    for skill_increase_num in range(1, 41):  # Up to 40 skill increases
                        location_name = f"{skill_name} Skill Increase {skill_increase_num}"
                        if location_name in name_to_id_map:
                            location_id = name_to_id_map[location_name]
                            if location_id in self.missing_locations:
                                next_skill_increase_num = skill_increase_num
                                break
                    
                    if next_skill_increase_num is None:
                        # Skill may be excluded - skip silently
                        continue
                    
                    # Validate against progressive state bounds
                    progressive_class_level_item_name = self.slot_data.get("progressive_class_level_item_name")
                    if not progressive_class_level_item_name:
                        continue
                    progressive_class_level_count = self.tracker.count(progressive_class_level_item_name, self.slot)
                    max_skill_increases = progressive_class_level_count * 2
                    
                    if next_skill_increase_num > max_skill_increases:
                        logger.warning(f"Skill increase {next_skill_increase_num} exceeds progressive state bounds ({max_skill_increases}): {item}")
                        continue
                    
                    # Find the corresponding location
                    location_name = f"{skill_name} Skill Increase {next_skill_increase_num}"
                    if location_name in name_to_id_map:
                        location_id = name_to_id_map[location_name]
                        
                        # Only add if this location is still missing and not already queued
                        if location_id in self.missing_locations and location_id not in new_locations:
                            new_locations.append(location_id)
                        else:
                            #logger.warning(f"Could not award Class Skill Increase, '{location_name}' is not available or already queued.")
                            pass
                    else:
                        logger.error(f"Location '{location_name}' not found in location table")
                        
                # Check if this is a specific dungeon cleared text, e.g., "Moss Rock Cavern Dungeon Cleared"
                elif item.endswith(" Dungeon Cleared"):
                    dungeon_name = item[: -len(" Dungeon Cleared")]
                    selected_dungeons = set(self.slot_data.get("selected_dungeons", []))
                    if dungeon_name in selected_dungeons and dungeon_name in name_to_id_map:
                        # Only award if the dungeon is currently accessible (region access owned)
                        is_accessible = False
                        try:
                            if self.tracker:
                                is_accessible = self.tracker.check_location_accessibility(dungeon_name)
                        except Exception:
                            is_accessible = False
                        if not is_accessible:
                            # Silently ignore early completion; player must redo later when accessible
                            continue
                        location_id = name_to_id_map[dungeon_name]
                        if location_id in self.missing_locations and location_id not in new_locations:
                            new_locations.append(location_id)
                    else:
                        logger.warning(f"Unknown or unselected dungeon entry: {item}")
                        
                # Check if this is a Victory completion
                elif item == "Victory":
                    if not self.victory_sent:
                        from NetUtils import ClientStatus
                        await self.send_msgs([{ "cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL }])
                        self.victory_sent = True
                        
                # Check if this is a Deathlink
                elif item == "Deathlink":
                    if self.deathlink_enabled:
                        # Only send deathlink if we haven't sent one recently
                        current_time = time.time()
                        if current_time - self.last_death_sent > 3.0:  # 3 second cooldown
                            await self.send_death("The Adventurer of Cyrodiil has fallen.")
                            self.last_death_sent = current_time
                
                # Check if this is a Nirnroot Harvested event
                elif item == "Nirnroot Harvested":
                    nirnroot_count = self.slot_data.get("nirnroot_count", 100)
                    
                    # Find the first unchecked Nirnroot location
                    for nirnroot_num in range(1, nirnroot_count + 1):
                        location_name = f"Nirnroot {nirnroot_num} Harvested"
                        if location_name in name_to_id_map:
                            location_id = name_to_id_map[location_name]
                            if location_id in self.missing_locations and location_id not in new_locations:
                                new_locations.append(location_id)
                                break  # Only send one check per harvest event

                # Kill location events
                elif item in ("Dungeon Kill", "Overworld Kill"):
                    kill_type = "dungeon" if item == "Dungeon Kill" else "overworld"
                    total_kills = self.slot_data.get(f"{kill_type}_kills", 0)
                    if total_kills == 0:
                        continue

                    # Find the next missing kill location and check it is in logic
                    for kill_num in range(1, total_kills + 1):
                        location_name = f"{'Dungeon' if kill_type == 'dungeon' else 'Overworld'} Kill {kill_num}"
                        if location_name in name_to_id_map:
                            location_id = name_to_id_map[location_name]
                            if location_id in self.missing_locations and location_id not in new_locations:
                                # Silently skip if out of logic (mirrors skill increase cap pattern)
                                is_accessible = False
                                try:
                                    if self.tracker:
                                        is_accessible = self.tracker.check_location_accessibility(location_name)
                                except Exception:
                                    is_accessible = True
                                if not is_accessible:
                                    logger.debug(f"{location_name} is out of logic (insufficient region access), skipping kill")
                                    break  # Higher-numbered kills are also out of logic
                                new_locations.append(location_id)
                                break
                
                # Check if this is a specific gold threshold event (for Treasure Hunter goal)
                elif item.endswith(" Gold Collected"):
                    try:
                        # Extract the amount from the item name
                        amount_str = item.replace(" Gold Collected", "")
                        amount = int(amount_str)
                        
                        # Map to location name format
                        location_name = f"Gold: {amount} Collected"
                        if location_name in name_to_id_map:
                            location_id = name_to_id_map[location_name]
                            if location_id in self.missing_locations and location_id not in new_locations:
                                new_locations.append(location_id)
                    except (ValueError, AttributeError):
                        # Invalid format, skip
                        pass
                        


                        
                # Check if this is an Ayleid Well Visited completion (now a sidequest)
                elif item == "Ayleid Well Visited":
                    location_name = "Visit an Ayleid Well"
                    # Check if this sidequest is in the selected sidequests
                    if location_name in self.slot_data.get("selected_sidequests", []):
                        if location_name in name_to_id_map:
                            location_id = name_to_id_map[location_name]
                            if location_id in self.missing_locations and location_id not in new_locations:
                                new_locations.append(location_id)

                # Doomstone visits
                elif item.endswith(" Doomstone Visited"):
                    stone_prefix = item[:-len(" Doomstone Visited")]
                    location_name = f"Visit the {stone_prefix} Stone"
                    if location_name in name_to_id_map:
                        location_id = name_to_id_map[location_name]
                        if location_id in self.missing_locations and location_id not in new_locations:
                            new_locations.append(location_id)
                    else:
                        logger.error(f"Location '{location_name}' not found in location table")
                
                # Check for sidequest completions
                elif item in self.slot_data.get("selected_sidequests", []):
                    # This is a selected sidequest location
                    location_name = item
                    if location_name in name_to_id_map:
                        location_id = name_to_id_map[location_name]
                        if location_id in self.missing_locations and location_id not in new_locations:
                            new_locations.append(location_id)
                    else:
                        logger.error(f"Location '{location_name}' not found in location table")
                        
                # Check if this is a completion token
                elif item in self.completion_tokens:
                    location_name = self.completion_tokens[item]
                    
                    if location_name in name_to_id_map:
                        location_id = name_to_id_map[location_name]
                        if location_id in self.missing_locations and location_id not in new_locations:
                            new_locations.append(location_id)
                    else:
                        logger.error(f"Location '{location_name}' not found in location table")
                else:
                    logger.warning(f"Unknown completion entry: {item}")
                            
            # Send location checks to server
            if new_locations:
                found_locations = await self.check_locations(new_locations)
                for location_id in found_locations:
                    location_name = self.location_names.lookup_in_game(location_id, self.game)
                    if self.tracker:
                        self.tracker.update_locations()
            
            # Always delete the completion file after processing
            try:
                os.remove(completion_path)
            except Exception as delete_error:
                logger.error(f"Failed to delete completion file: {delete_error}")
                
        except Exception as e:
            logger.error(f"Error checking locations: {e}")
            import traceback
            logger.error(traceback.format_exc())

    
    
    def _start_game_loop(self):
        """Start the game monitoring loop."""
        if not hasattr(self, 'game_loop_task') or self.game_loop_task is None or self.game_loop_task.done():
            self.game_loop_task = asyncio.create_task(self._run_game_loop(), name="game loop")

    def _cleanup_files(self):
        """Clean up temporary files on disconnect."""
        if not self.file_prefix or not self.session_id:
            return
            
        # Purge the current connection file to allow for a new connection in between sessions
        connection_file = os.path.join(self.oblivion_save_path, "current_connection.txt")
        try:
            if os.path.exists(connection_file):
                os.remove(connection_file)
        except Exception:
            pass
            
        # Clean up item events file, we only monitor while we are connected to the server
        item_events_file = os.path.join(self.oblivion_save_path, f"{self.file_prefix}_item_events.txt")
        try:
            if os.path.exists(item_events_file):
                os.remove(item_events_file)
        except Exception:
            pass
        
    
    async def disconnect(self, allow_autoreconnect: bool = False):
        """Handle disconnection from server."""
        # Stop the game monitoring loop
        if hasattr(self, 'game_loop_task') and self.game_loop_task and not self.game_loop_task.done():
            self.game_loop_task.cancel()
        
        self._cleanup_files()
        
        # Clear connection state after cleanup
        self.slot_data = {}
        self.session_id = ""
        
        await super().disconnect(allow_autoreconnect)
    
    async def shutdown(self):
        """Handle shutdown and ensure cleanup happens."""
        # Stop the game monitoring loop
        if hasattr(self, 'game_loop_task') and self.game_loop_task and not self.game_loop_task.done():
            self.game_loop_task.cancel()
        
        # Clean up files even if we didn't properly disconnect
        self._cleanup_files()
        
        # Call parent shutdown
        await super().shutdown()
            
    async def _run_game_loop(self):
        """Main game monitoring loop - checks for location completions."""
        try:
            while not self.exit_event.is_set():
                # Check if we're still connected
                if not (hasattr(self, 'slot_data') and self.slot_data):
                    break
                    
                await self._check_for_locations()
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            #logger.info("Game loop cancelled")
            pass
        except Exception as e:
            #logger.error(f"Game loop error: {e}")
            pass
        finally:
            #logger.info("Game loop ended")
            pass



    def run_gui(self):
        """Launch the client with GUI."""
        from kvui import GameManager, UILog
        
        class OblivionManager(GameManager):
            logging_pairs = [
                ("Client", "Archipelago")
            ]
            base_title = "Archipelago Oblivion Remastered Client"
            
            def build(self):
                ret = super().build()
                self.ctx.tab_items = self.add_client_tab("Items", UILog())
                self.ctx.tab_goal = self.add_client_tab("Goal Progress", UILog())
                self.ctx.tab_locations = self.add_client_tab("Tracker", UILog())
                self.ctx.tab_shop = self.add_client_tab("Shop", UILog())
                # delayed initialization to ensure data populates
                try:
                    import asyncio as _a
                    async def _after():
                        for d in (0.2, 0.6, 1.2):
                            await _a.sleep(d)
                            tracker = getattr(self.ctx, 'tracker', None)
                            if tracker:
                                tracker.ensure_shop_initialized()
                                tracker.update_shop_tab()
                                tracker.schedule_shop_scout()
                                tracker.update_goal_progress()
                    _a.get_event_loop().create_task(_after())
                except Exception:
                    pass
                return ret
        
        self.ui = OblivionManager(self)
        self.ui_task = asyncio.create_task(self.ui.async_run(), name="UI")





def launch(*launch_args):
    """Launch the Oblivion client."""
    import colorama
    import urllib.parse
    
    async def main(args):
        # Handle archipelago:// URLs
        connect = None
        password = None
        if args.url:
            url = urllib.parse.urlparse(args.url)
            if url.scheme == "archipelago":
                connect = url.netloc
                if url.password:
                    password = urllib.parse.unquote(url.password)
            else:
                parser.error(f"bad url, found {args.url}, expected url in form of archipelago://archipelago.gg:38281")
        elif hasattr(args, 'connect') and args.connect:
            connect = args.connect
            password = args.password
        
        ctx = OblivionContext(connect, password)
        ctx.server_task = asyncio.create_task(server_loop(ctx), name="ServerLoop")
        
        if gui_enabled:
            ctx.run_gui()
        ctx.run_cli()

        await ctx.exit_event.wait()
        ctx.server_address = None

        await ctx.shutdown()
    
    parser = get_base_parser(description="Oblivion Remastered Client.")
    parser.add_argument("url", nargs="?", help="Archipelago connection url")
    
    args = parser.parse_args(launch_args)
    colorama.just_fix_windows_console()
    asyncio.run(main(args))
    colorama.deinit()


if __name__ == '__main__':
    launch() 