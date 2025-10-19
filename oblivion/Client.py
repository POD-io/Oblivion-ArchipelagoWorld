import asyncio
import os
import time
from typing import Dict, List, Set
from CommonClient import CommonContext, server_loop, gui_enabled, ClientCommandProcessor, logger, get_base_parser
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
                loc_id = Locations.location_table.get(f"Shop Item Value {value}")
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
        if location_name not in Locations.location_table:
            return False
            
        slot_data = getattr(self.ctx, 'slot_data', {})
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
        if location_name.startswith("Shop Item Value "):
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
                mq_order = {
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
                }.get(text)
                
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
                elif "Gate" in text and "Closed" in text and text not in mq_order:
                    parts = text.split()
                    if len(parts) >= 3 and parts[0] == "Gate" and parts[1].isdigit() and parts[-1] == "Closed":
                        num = int(parts[1])
                        return (4, num)
                    else:
                        return (4, 9999, text)
                
                # Category 5: Shop Items
                elif "Shop Item Value" in text:
                    num = int(text.split()[-1])
                    return (5, num)
                
                # Category 6: Everything else (Visit an Ayleid Well, etc.)
                else:
                    return (6, text)
            
            sorted_locations = sorted(accessible_locations, key=natural_sort_key)
            # Append (Region) to dungeon names in tracker for clarity
            for entry in sorted_locations:
                name = entry["text"]
                if name in Locations.DUNGEON_REGIONS:
                    entry["text"] = f"{name} ({Locations.DUNGEON_REGIONS[name]})"
                elif name in self.stone_regions:
                    entry["text"] = f"{name} ({self.stone_regions[name]})"

            if sorted_locations:
                self.ctx.tab_locations.content.data = sorted_locations
            else:
                self.ctx.tab_locations.content.data = [{"text": "All currently available locations have been checked."}]

    # ===== SHOP SCOUT / TAB LOGIC =====
    def _shop_get_location_id(self, value: int):
        loc_name = f"Shop Item Value {value}"
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
            accessible_values = [v for v in tier if self.check_location_accessibility(f"Shop Item Value {v}")]
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


class OblivionClientCommandProcessor(ClientCommandProcessor):
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
            
            # Gate keys if relevant
            if gate_count > 0:
                extra_keys = self.ctx.slot_data.get("extra_gate_keys", 0)
                total_keys = gate_count + extra_keys
                self.output(f"\nGate keys: {total_keys} total ({extra_keys} extra)")
    
                # Gate Vision setting
                gate_vision = self.ctx.slot_data.get("gate_vision", "item")
                self.output(f"Gate Vision: {gate_vision.title()}")
    
    def _cmd_tracker(self):
        """Toggles the built in logic Tracker."""
        if hasattr(self.ctx, 'tracker_enabled'):
            self.ctx.tracker_enabled = not self.ctx.tracker_enabled
        else:
            self.ctx.tracker_enabled = True
        
        if hasattr(self.ctx, 'tracker'):
            self.ctx.tracker.update_locations()
        
        self.output(f"Tracker {'enabled' if self.ctx.tracker_enabled else 'disabled'}.")
        return True


class OblivionContext(CommonContext):
    command_processor = OblivionClientCommandProcessor
    game = "Oblivion Remastered"
    items_handling = 0b111
    base_title = "Archipelago Oblivion Client"
    
    def __init__(self, server_address, password):
        super().__init__(server_address, password)
        
        # File system paths
        self.oblivion_save_path = os.path.join(
            os.environ.get("USERPROFILE", ""), 
            "Documents", "My Games", "Oblivion Remastered", "Saved", "Archipelago"
        )
        
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
            # Progressive Shop Stock checks
            "APShopTokenValue1CompletionToken": "Shop Item Value 1",
            "APShopTokenValue10CompletionToken": "Shop Item Value 10", 
            "APShopTokenValue100CompletionToken": "Shop Item Value 100",
            "APShopTokenValue2CompletionToken": "Shop Item Value 2",
            "APShopTokenValue20CompletionToken": "Shop Item Value 20",
            "APShopTokenValue200CompletionToken": "Shop Item Value 200",
            "APShopTokenValue3CompletionToken": "Shop Item Value 3",
            "APShopTokenValue30CompletionToken": "Shop Item Value 30",
            "APShopTokenValue300CompletionToken": "Shop Item Value 300",
            "APShopTokenValue4CompletionToken": "Shop Item Value 4",
            "APShopTokenValue40CompletionToken": "Shop Item Value 40",
            "APShopTokenValue400CompletionToken": "Shop Item Value 400",
            "APShopTokenValue5CompletionToken": "Shop Item Value 5",
            "APShopTokenValue50CompletionToken": "Shop Item Value 50",
            "APShopTokenValue500CompletionToken": "Shop Item Value 500",
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

        
        # Progressive item tracking
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
                ["APArmorTier1"],   # Tier 1 (Leather/Steel)
                ["APArmorTier2"],   # Tier 2 (Chainmail/Dwarven)
                ["APArmorTier3"]    # Tier 3 (Mithril/Orcish)
                # ["APArmorTier4"],   # Tier 4 (Elven/Ebony)
                # ["APArmorTier5"]    # Tier 5 (Glass/Daedric)
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
        os.makedirs(self.oblivion_save_path, exist_ok=True)
        
        # Initialize tracker
        self.tracker_enabled = True
        self.tracker = None  # Will be initialized after connection
        
    async def server_auth(self, password_requested: bool = False):
        if password_requested and not self.password:
            await super().server_auth(password_requested)
        await self.get_username()
        await self.send_connect()
        
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
            
            # Initialize tracker after slot_data is available
            self.tracker = OblivionTracker(self)
            
            asyncio.create_task(self._setup_after_connection())
            # Initial shop tier (tier 1) scout scheduling
            if self.tracker:
                self.tracker.schedule_shop_scout()
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
        
        # Build list of items that need to be sent
        from worlds.oblivion.Items import item_table
        received_items = []
        for network_item in self.items_received:
            # Look up item name by ID
            item_name = None
            for name, data in item_table.items():
                if data.id == network_item.item:
                    item_name = name
                    break
            if item_name:
                received_items.append(item_name)
        
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
            
            # Build location ID lookup table
            from worlds.oblivion.Locations import location_table
            name_to_id_map = {name: data.id for name, data in location_table.items()}
            
            # Get configuration values for processing
            dungeons_selected_count = self.slot_data.get("dungeons_selected", 0)
                
            # Process each completion entry
            new_locations = []
            
            # Find the starting gate number
            next_gate_num = 1
            for i in range(1, 11):  # Up to 10 gates
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
                        
                # [DISABLED_STONES] Ignore Wayshrine/Runestone/Doomstone completions while disabled
                # elif item == "Wayshrine Visited":
                #     location_name = "Visit a Wayshrine"
                #     if location_name in name_to_id_map:
                #         location_id = name_to_id_map[location_name]
                #         if location_id in self.missing_locations and location_id not in new_locations:
                #             new_locations.append(location_id)
                #     else:
                #         logger.error(f"Location '{location_name}' not found in location table")
                # 
                # elif item == "Runestone Visited":
                #     location_name = "Visit a Runestone"
                #     if location_name in name_to_id_map:
                #         location_id = name_to_id_map[location_name]
                #         if location_id in self.missing_locations and location_id not in new_locations:
                #             new_locations.append(location_id)
                #     else:
                #         logger.error(f"Location '{location_name}' not found in location table")
                # 
                # elif item == "Doomstone Visited":
                #     location_name = "Visit a Doomstone"
                #     if location_name in name_to_id_map:
                #         location_id = name_to_id_map[location_name]
                #         if location_id in self.missing_locations and location_id not in new_locations:
                #             new_locations.append(location_id)
                #     else:
                #         logger.error(f"Location '{location_name}' not found in location table")
                        
                # Check if this is an Ayleid Well Visited completion
                elif item == "Ayleid Well Visited":
                    location_name = "Visit an Ayleid Well"
                    if location_name in name_to_id_map:
                        location_id = name_to_id_map[location_name]
                        if location_id in self.missing_locations and location_id not in new_locations:
                            new_locations.append(location_id)

                # Birthsign Doomstone visits
                elif item.endswith(" Doomstone Visited"):
                    stone_prefix = item[:-len(" Doomstone Visited")]
                    location_name = f"Visit the {stone_prefix} Stone"
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