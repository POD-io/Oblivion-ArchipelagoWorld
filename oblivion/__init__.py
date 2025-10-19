import uuid
from worlds.AutoWorld import World, WebWorld
from BaseClasses import Region, Entrance, Item, ItemClassification, Location
from typing import Dict, Any, List
import logging

from .Items import (
    item_table,
    OblivionItem,
    progression_items,
    useful_items,
    filler_items,
    item_name_groups,
    region_unlock_items,
)
from .Locations import location_table, OblivionLocation, EventId, LocationData, DUNGEON_REGIONS
from .Rules import set_rules
from .Options import OblivionOptions
from .ShrineProgression import select_active_shrines, get_shrine_offerings
from .Classes import get_class_data, get_all_class_names, get_class_skills, get_filtered_class_skills

# Client registration
def launch_client(*args):
    from .Client import launch
    from worlds.LauncherComponents import launch as launch_component
    launch_component(launch, name="Oblivion Client", args=args)

from worlds.LauncherComponents import Component, components, Type, launch as launch_component, icon_paths
components.append(Component("Oblivion Remastered Client", 
                           game_name="Oblivion Remastered", 
                           func=launch_client, 
                           component_type=Type.CLIENT,
                           icon="oblivion",
                           supports_uri=True))

icon_paths["oblivion"] = f"ap:{__name__}/icons/oblivion.png"

logger = logging.getLogger("Oblivion")

class OblivionWebWorld(WebWorld):
    theme = "stone"


class OblivionWorld(World):
    """
    The Elder Scrolls IV: Oblivion Remastered - Archipelago Integration
    
    This APWorld allows Oblivion Remastered to participate in Archipelago multiworld
    randomizers. Players complete Daedric shrine quests to send location checks and
    items to other players, while receiving shrine unlock tokens and helpful items
    from the multiworld.
    """
    
    game: str = "Oblivion Remastered"
    web = OblivionWebWorld()
    
    explicit_indirect_conditions: bool = False
    topology_present: bool = False
    
    options_dataclass = OblivionOptions
    options: OblivionOptions
    
    item_name_to_id: Dict[str, int] = {name: data.id for name, data in item_table.items()}
    location_name_to_id: Dict[str, int] = {name: data.id for name, data in location_table.items()}
    
    # Item groups for hints
    item_name_groups: Dict[str, List[str]] = item_name_groups
    
    def interpret_slot_data(self, slot_data: Dict[str, Any]) -> Dict[str, Any] | None:
        """Return values to re-gen with server slot data.
        Pass through active shrine data, class selection, and region/dungeon selections.
        This allows the server to regenerate the world with the same settings, and
        clients like Universal Tracker share the same data.
        """
        out: Dict[str, Any] = {}
        # Class related
        sel = slot_data.get("selected_class")
        if sel:
            out["selected_class"] = sel
            if slot_data.get("progressive_class_level_item_name"):
                out["progressive_class_level_item_name"] = slot_data["progressive_class_level_item_name"]
            if slot_data.get("class_level_maximum"):
                out["class_level_maximum"] = slot_data["class_level_maximum"]
        # Regions/Dungeons related
        if "selected_regions" in slot_data:
            out["selected_regions"] = list(slot_data.get("selected_regions") or [])
        if "dungeons_by_region" in slot_data:
            out["dungeons_by_region"] = dict(slot_data.get("dungeons_by_region") or {})
        if "selected_dungeons" in slot_data:
            out["selected_dungeons"] = list(slot_data.get("selected_dungeons") or [])
        if "starting_unlocked_regions" in slot_data:
            out["starting_unlocked_regions"] = list(slot_data.get("starting_unlocked_regions") or [])
        # Shrines
        if "active_shrines" in slot_data:
            out["active_shrines"] = list(slot_data.get("active_shrines") or [])
        if "shrine_offerings" in slot_data:
            out["shrine_offerings"] = dict(slot_data.get("shrine_offerings") or {})
        return out or None

    def generate_early(self) -> None:
        # Validate goal/count combinations
        goal = self.options.goal.current_key
        if goal == "shrine_seeker" and self.options.shrine_count.value == 0:
            raise Exception("Shrine Count cannot be 0 when Goal is Shrine Seeker")
        if goal == "gatecloser" and self.options.gate_count.value == 0:
            raise Exception("Gate Count cannot be 0 when Goal is Gatecloser")
        if goal == "shrine_seeker" and self.options.shrine_goal.value > self.options.shrine_count.value:
            raise Exception(f"Shrine Goal ({self.options.shrine_goal.value}) cannot be greater than Shrine Count ({self.options.shrine_count.value})")
        if goal == "dungeon_delver":
            if self.options.region_unlocks.value == 0:
                raise Exception("Regions per Seed cannot be 0 when Goal is Dungeon Delver")
            if self.options.dungeons_per_region.value == 0:
                raise Exception("Dungeons per Region cannot be 0 when Goal is Dungeon Delver")
        
        # Handle class selection
        passthrough = getattr(self.multiworld, "re_gen_passthrough", None)
        pt = None
        if isinstance(passthrough, dict):
            pt = passthrough.get(self.game) or passthrough.get(getattr(self, "game", ""))

        if pt and pt.get("selected_class") is not None:
            self.selected_class = pt["selected_class"]
        else:
            class_selection = self.options.class_selection.current_key
            if class_selection == "random":
                # Randomly select a class from all available options
                available_classes = get_all_class_names()
                selected_class = self.multiworld.random.choice(available_classes)
                self.selected_class = selected_class
            elif class_selection == "off":
                self.selected_class = None
            else:
                # Direct class selection
                self.selected_class = class_selection

        # Set class level maximum
        self.class_level_maximum = int(pt.get("class_level_maximum", self.options.class_level_maximum.value)) if pt else self.options.class_level_maximum.value

        # Get excluded skills from options (dict format: skill_name: 1 = excluded, 0 = included)
        if self.selected_class is not None:
            # Extract skills where value is 1 (excluded)
            skill_dict = self.options.excluded_skills.value
            self.excluded_skills = {skill for skill, is_excluded in skill_dict.items() if is_excluded}
        else:
            self.excluded_skills = set()

        # Select the progressive class level item name based on chosen class
        if self.selected_class is not None:
            if pt and pt.get("progressive_class_level_item_name"):
                self.progressive_class_level_item_name = pt["progressive_class_level_item_name"]
            else:
                class_data = get_class_data(self.selected_class)
                if class_data:
                    class_name_for_item = class_data.name
                else:
                    class_name_for_item = str(self.selected_class).capitalize()
                self.progressive_class_level_item_name = f"Progressive {class_name_for_item} Level"
        else:
            self.progressive_class_level_item_name = "Progressive Class Level"
        
        # Determine if content types are enabled based on count settings
        self.shrines_enabled = self.options.shrine_count.value > 0 or goal == "shrine_seeker"
        self.arena_enabled = (goal == "arena") or (goal != "arena" and self.options.arena_matches.value > 0)
        self.skills_enabled = False  # Vanilla skill system is completely removed
        # Enable dungeon system based on region/dungeon options
        self.region_unlocks_count = self.options.region_unlocks.value
        self.dungeons_per_region = self.options.dungeons_per_region.value
        self.using_region_dungeons = self.region_unlocks_count > 0 and self.dungeons_per_region > 0
        self.dungeons_enabled = self.using_region_dungeons
        
        # Set counts based on settings
        # Suppress gate content entirely when Light the Dragonfires is the goal
        if goal == "light_the_dragonfires":
            self.gate_count = 0
        else:
            self.gate_count = self.options.gate_count.value
        self.skill_count = 0
        # Total dungeons will be computed after selecting regions/dungeons
        self.dungeon_count = 0
        
        # For arena: ignore setting when goal is arena, use setting otherwise
        if goal == "arena":
            self.arena_count = 21  # Always all 21 matches for arena goal
        else:
            self.arena_count = self.options.arena_matches.value if self.arena_enabled else 0
        
        # Handle gate vision setting
        # Gate vision item suppressed when gates disabled or MQ goal active
        self.gate_vision_setting = self.options.gate_vision.current_key if (self.gate_count > 0 and goal != "light_the_dragonfires") else "off"
        
        # Handle fast travel item setting
        self.fast_travel_item_enabled = self.options.fast_travel_item.value

        # Handle dungeon marker reveal / fast travel mode
        self.dungeon_marker_mode_setting = self.options.dungeon_marker_mode.current_key

        # Initialize shrine data only if shrines are enabled
        if self.shrines_enabled:
            
            # If passthrough provided the server's active shrines, use them
            if pt and pt.get("active_shrines") is not None:
                self.active_shrines = list(pt["active_shrines"])[: self.options.shrine_count.value]
                # Use provided offerings when available, else compute
                provided_offerings = pt.get("shrine_offerings") if isinstance(pt.get("shrine_offerings"), dict) else None
                self.shrine_offerings = {}
                for shrine in self.active_shrines:
                    self.shrine_offerings[shrine] = (
                        provided_offerings.get(shrine) if provided_offerings and shrine in provided_offerings
                        else get_shrine_offerings(shrine)
                    )
            else:
                # Get required shrines from start_inventory
                start_inventory_items = self.options.start_inventory.value
                logger.debug(f"Player {self.player}: Raw start_inventory option: {start_inventory_items}")
                required_shrines = []
                for item_name in start_inventory_items:
                    if item_name.endswith(" Shrine Token"):
                        shrine_name = item_name.replace(" Shrine Token", "")
                        required_shrines.append(shrine_name)

                # Select which shrines will be active for this seed
                self.active_shrines = select_active_shrines(
                    self.options.shrine_count.value,
                    self.multiworld.random,
                    required_shrines,
                )

                # Get required offerings for each active shrine
                self.shrine_offerings = {}
                for shrine in self.active_shrines:
                    self.shrine_offerings[shrine] = get_shrine_offerings(shrine)
        else:
            # If shrines are disabled, set empty defaults
            self.active_shrines = []
            self.shrine_offerings = {}

        # MQ goal adjustment: remove Azura from randomized shrine pool so vanilla Azura quest remains available for Blood of the Daedra
        try:
            if goal == "light_the_dragonfires" and "Azura" in self.active_shrines:
                self.active_shrines = [s for s in self.active_shrines if s != "Azura"]
                # Also drop offering mapping if present
                self.shrine_offerings.pop("Azura", None)
        except Exception:
            pass

        # Dungeon selection
        if self.using_region_dungeons:
            from .Locations import REGIONS, DUNGEON_REGIONS
            # Ensure passthrough reference is available in this block
            passthrough = getattr(self.multiworld, "re_gen_passthrough", None)
            pt = None
            if isinstance(passthrough, dict):
                pt = passthrough.get(self.game) or passthrough.get(getattr(self, "game", ""))
            # Track regions that are unlocked at the start for client compatibility
            # Prefer server-provided list from pt; otherwise derive from start_inventory.
            if pt and pt.get("starting_unlocked_regions") is not None:
                self.starting_unlocked_regions = list(pt.get("starting_unlocked_regions") or [])
            else:
                start_inv = self.options.start_inventory.value or {}
                start_inv_keys = set(start_inv.keys()) if hasattr(start_inv, 'keys') else set(start_inv)
                yaml_regions = sorted(list(set(region_unlock_items) & start_inv_keys))
                self.starting_unlocked_regions = [r.replace(" Access", "") for r in yaml_regions]
            # Choose regions (or take from passthrough)
            # Compute guaranteed regions from start_inventory once
            start_inv = self.options.start_inventory.value or {}
            start_inv_keys = set(start_inv.keys()) if hasattr(start_inv, 'keys') else set(start_inv)
            yaml_regions = set(region_unlock_items) & start_inv_keys
            guaranteed_regions = [r.replace(" Access", "") for r in yaml_regions if r.endswith(" Access") and r.replace(" Access", "") in REGIONS]

            if pt and pt.get("selected_regions"):
                base_selected = list(pt["selected_regions"])[: self.region_unlocks_count]
                # Add any newly guaranteed regions not already present
                missing = [r for r in guaranteed_regions if r not in base_selected]
                total_after = len(base_selected) + len(missing)
                if missing:
                    if total_after > self.region_unlocks_count:
                        raise Exception(
                            f"start_inventory adds guaranteed regions ({', '.join(missing)}) exceeding region_unlocks ({self.region_unlocks_count}) when combined with passthrough-selected regions ({', '.join(base_selected)}). Increase region_unlocks or remove extras."
                        )
                    base_selected.extend(missing)
                self.selected_regions = base_selected
                if guaranteed_regions:
                    logger.debug(
                        f"Player {self.player}: Passthrough regions after merging guarantees: {', '.join(self.selected_regions)} (guaranteed: {', '.join(guaranteed_regions)})"
                    )
            else:
                if len(guaranteed_regions) > self.region_unlocks_count:
                    raise Exception(
                        f"start_inventory specifies {len(guaranteed_regions)} region Access items ({', '.join(sorted(guaranteed_regions))}) "
                        f"but region_unlocks is {self.region_unlocks_count}. Increase region_unlocks or remove extras."
                    )
                remaining_pool = [r for r in REGIONS if r not in guaranteed_regions]
                slots_left = self.region_unlocks_count - len(guaranteed_regions)
                random_picks = self.multiworld.random.sample(remaining_pool, slots_left) if slots_left > 0 else []
                self.selected_regions = guaranteed_regions + random_picks
                if guaranteed_regions:
                    logger.debug(
                        f"Player {self.player}: Guaranteed regions from start_inventory: {', '.join(sorted(guaranteed_regions))}; randomly added: {', '.join(random_picks)}"
                    )
            # For each region, choose up to dungeons_per_region
            self.selected_dungeons_by_region = {}
            selected_flat: List[str] = []
            if pt and pt.get("dungeons_by_region"):
                # Use passthrough set
                for region_name in self.selected_regions:
                    chosen = list(pt["dungeons_by_region"].get(region_name, []))
                    if self.dungeons_per_region > 0:
                        chosen = chosen[: self.dungeons_per_region]
                    self.selected_dungeons_by_region[region_name] = chosen
                    selected_flat.extend(chosen)
            else:
                for region_name in self.selected_regions:
                    dungeons_in_region = [name for name, r in DUNGEON_REGIONS.items() if r == region_name]
                    pick = min(self.dungeons_per_region, len(dungeons_in_region))
                    chosen = self.multiworld.random.sample(dungeons_in_region, pick) if pick > 0 else []
                    self.selected_dungeons_by_region[region_name] = chosen
                    selected_flat.extend(chosen)
            self.selected_dungeons = selected_flat
            self.dungeon_count = len(self.selected_dungeons)
            # Start with one region unlocked unless start_inventory/precollect already grants any Region Access
            try:
                if self.selected_regions:
                    
                    if hasattr(self.multiworld, "generation_is_fake"):
                        # Trust self.starting_unlocked_regions (from pt if provided); do nothing else
                        pass
                    else:
                        # Server-side generation path
                        start_inv = self.options.start_inventory.value or {}
                        start_inv_keys = set(start_inv.keys()) if hasattr(start_inv, 'keys') else set(start_inv)
                        start_inv_has_region = bool(set(region_unlock_items) & start_inv_keys)
                        precollected_names = {item.name for item in self.multiworld.precollected_items[self.player]}
                        precollected_has_region = bool(set(region_unlock_items) & precollected_names)

                        if start_inv_has_region or precollected_has_region:
                            # Summarize which regions came from start_inventory/precollect
                            yaml_regions = sorted(list(set(region_unlock_items) & start_inv_keys))
                            prec_regions = sorted(list(set(region_unlock_items) & precollected_names))
                            combined = sorted(list(set(yaml_regions) | set(prec_regions)))
                            # Record region names (strip " Access") so graph rules can reflect starting reachability
                            self.starting_unlocked_regions = [r.replace(" Access", "") for r in combined]
                            if combined:
                                logger.debug(
                                    f"Player {self.player}: Starting regions from start_inventory/precollect: {', '.join(combined)}"
                                )
                            else:
                                logger.debug(
                                    f"Player {self.player}: Skipping random starting region; region access already granted by start_inventory/precollect."
                                )
                        else:
                            starting_region = self.multiworld.random.choice(self.selected_regions)
                            access_item_name = f"{starting_region} Access"
                            if access_item_name in item_table and access_item_name not in precollected_names:
                                self.multiworld.push_precollected(self.create_item(access_item_name))
                                # Also mark as unlocked in-graph for tools that ignore precollected items
                                self.starting_unlocked_regions = [starting_region]
                                logger.debug(
                                    f"Player {self.player}: Starting with one unlocked region"
                                )
            except Exception as e:
                logger.warning(f"Failed to precollect starting region access: {e}")
        else:
            self.selected_regions = []
            self.selected_dungeons_by_region = {}
            self.selected_dungeons = []
            self.starting_unlocked_regions = []
    

    
    def create_regions(self) -> None:
        menu_region = Region("Menu", self.player, self.multiworld)
  
        cyrodiil_region = Region("Cyrodiil", self.player, self.multiworld)
        
        # [DISABLED_STONES] Wayshrine/Runestone/Doomstone visit checks disabled - debating if i want this
        # # Add wayshrine location (always accessible)
        # wayshrine_location_name = "Visit a Wayshrine"
        # if wayshrine_location_name in location_table:
        #     location_data = location_table[wayshrine_location_name]
        #     location = OblivionLocation(self.player, wayshrine_location_name, location_data.id, cyrodiil_region)
        #     cyrodiil_region.locations.append(location)
        # 
        # # Add runestone location (always accessible)
        # runestone_location_name = "Visit a Runestone"
        # if runestone_location_name in location_table:
        #     location_data = location_table[runestone_location_name]
        #     location = OblivionLocation(self.player, runestone_location_name, location_data.id, cyrodiil_region)
        #     cyrodiil_region.locations.append(location)
        # 

        # Add ayleid well location (always accessible)
        ayleid_well_location_name = "Visit an Ayleid Well"
        if ayleid_well_location_name in location_table:
            location_data = location_table[ayleid_well_location_name]
            location = OblivionLocation(self.player, ayleid_well_location_name, location_data.id, cyrodiil_region)
            cyrodiil_region.locations.append(location)

        # Defer Birthsign Doomstone placement until after region AP regions are created (so they live in their region).
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
        self._birthsign_stones = birthsign_stones
        
        # Add shrine locations only if shrines are enabled
        if self.shrines_enabled:
            for shrine in self.active_shrines:
                location_name = f"{shrine} Quest Complete"
                if location_name in location_table:
                    location_data = location_table[location_name]
                    location = OblivionLocation(self.player, location_name, location_data.id, cyrodiil_region)
                    cyrodiil_region.locations.append(location)
        
        # Add gate locations
        for i in range(1, self.gate_count + 1):
            location_name = f"Gate {i} Closed"
            
            if location_name in location_table:
                location_data = location_table[location_name]
                gate_location = OblivionLocation(
                    self.player,
                    location_name,
                    location_data.id,
                    cyrodiil_region
                )
                cyrodiil_region.locations.append(gate_location)
        




        # Add all progressive shop stock locations (always enabled)
        shop_location_names = [
            "Shop Item Value 1", "Shop Item Value 10", "Shop Item Value 100",
            "Shop Item Value 2", "Shop Item Value 20", "Shop Item Value 200", 
            "Shop Item Value 3", "Shop Item Value 30", "Shop Item Value 300",
            "Shop Item Value 4", "Shop Item Value 40", "Shop Item Value 400",
            "Shop Item Value 5", "Shop Item Value 50", "Shop Item Value 500",
        ]
        
        for shop_location_name in shop_location_names:
            if shop_location_name in location_table:
                location_data = location_table[shop_location_name]
                location = OblivionLocation(self.player, shop_location_name, location_data.id, cyrodiil_region)
                cyrodiil_region.locations.append(location)
        
        # Add Arena locations if enabled
        if self.arena_enabled:
            for i in range(1, self.arena_count + 1):  # Arena Match 1 Victory through arena_count Victory
                location_name = f"Arena Match {i} Victory"
                
                if location_name in location_table:
                    location_data = location_table[location_name]
                    location = OblivionLocation(self.player, location_name, location_data.id, cyrodiil_region)
                    cyrodiil_region.locations.append(location)
        
        # Add Class Skill locations if class system is enabled
        if self.selected_class is not None:
            class_skills = get_filtered_class_skills(self.selected_class, self.excluded_skills)
            # Each Progressive Class Level provides 2 additional skill increases per class skill
            for level in range(1, self.class_level_maximum + 1):
                for skill in class_skills:
                    # Each level provides 2 skill increases per skill
                    for skill_level in range(1, 3):  # 2 skill increases per skill per level
                        # Calculate the skill increase number (1-40 for 20 levels)
                        skill_increase_num = (level - 1) * 2 + skill_level
                        location_name = f"{skill} Skill Increase {skill_increase_num}"
                        
                        if location_name in location_table:
                            location_data = location_table[location_name]
                            location = OblivionLocation(self.player, location_name, location_data.id, cyrodiil_region)
                            cyrodiil_region.locations.append(location)
        
        # Add Dungeon locations if enabled (based on selected regions/dungeons)
        # Create AP Regions and move their dungeons into them. Gate entrances with Region Access items.
        if self.dungeons_enabled:
            # Create region nodes and connect from Cyrodiil
            region_nodes: Dict[str, Region] = {}
            for region_name in self.selected_regions:
                ap_region = Region(region_name, self.player, self.multiworld)
                region_nodes[region_name] = ap_region
                # Entrance from Cyrodiil to region, gated by access item
                entrance_name = f"Enter {region_name}"
                entrance = Entrance(self.player, entrance_name, cyrodiil_region)
                cyrodiil_region.exits.append(entrance)
                # Always gate by the region's Access item so the item remains true progression.
                # this keeps the item in playthrough sphere 0 instead of being filtered out
                def make_rule(rn: str):
                    return lambda state, reg=rn: state.has(f"{reg} Access", self.player)
                entrance.access_rule = make_rule(region_name)
                entrance.connect(ap_region)

            # Place dungeons in their respective region nodes
            for region_name, dungeons in self.selected_dungeons_by_region.items():
                ap_region = region_nodes.get(region_name)
                if not ap_region:
                    continue
                for dungeon_name in dungeons:
                    if dungeon_name in location_table:
                        location_data = location_table[dungeon_name]
                        location = OblivionLocation(self.player, dungeon_name, location_data.id, ap_region)
                        ap_region.locations.append(location)

            # Place doomstones into their region nodes only if that region is selected
            for stone_name, region_name in getattr(self, '_birthsign_stones', []):
                if region_name not in region_nodes:
                    continue  # region not selected -> stone location excluded from seed
                if stone_name in location_table:
                    data = location_table[stone_name]
                    stone_loc = OblivionLocation(self.player, stone_name, data.id, region_nodes[region_name])
                    region_nodes[region_name].locations.append(stone_loc)
        # If dungeons/regions are disabled, doomstones are not included at all
        
        # Connect menu to game
        connection = Entrance(self.player, "New Game", menu_region)
        connection.connect(cyrodiil_region)
        menu_region.exits.append(connection)
        
        # Add regions to multiworld
        added_regions = [menu_region, cyrodiil_region]
        # Include macro-regions if dungeons enabled
        if self.dungeons_enabled:
            # Collect the Region objects created above
            region_objs = []
            for exit_conn in cyrodiil_region.exits:
                if exit_conn.connected_region and exit_conn.connected_region.player == self.player:
                    region_objs.append(exit_conn.connected_region)
            added_regions.extend(region_objs)
        self.multiworld.regions += added_regions
        
        # Add Victory locations for playthrough generation (event locations only)
        goal = self.options.goal.current_key
        if goal == "shrine_seeker":
            # Use existing Shrine Seeker victory location
            if "Shrine Seeker" in location_table:
                location_data = location_table["Shrine Seeker"]
                shrine_victory_location = OblivionLocation(self.player, "Shrine Seeker", location_data.id, cyrodiil_region)
                cyrodiil_region.locations.append(shrine_victory_location)
        elif goal == "gatecloser":
            # Use existing Gatecloser victory location
            if "Gatecloser" in location_table:
                location_data = location_table["Gatecloser"]
                gate_victory_location = OblivionLocation(self.player, "Gatecloser", location_data.id, cyrodiil_region)
                cyrodiil_region.locations.append(gate_victory_location)
        elif goal == "arena":
            # Use existing Arena Grand Champion victory location
            if "Arena Grand Champion" in location_table:
                location_data = location_table["Arena Grand Champion"]
                arena_victory_location = OblivionLocation(self.player, "Arena Grand Champion", location_data.id, cyrodiil_region)
                cyrodiil_region.locations.append(arena_victory_location)
        elif goal == "dungeon_delver":
            if "Dungeon Delver" in location_table:
                location_data = location_table["Dungeon Delver"]
                dungeon_victory_location = OblivionLocation(self.player, "Dungeon Delver", location_data.id, cyrodiil_region)
                cyrodiil_region.locations.append(dungeon_victory_location)
        elif goal == "light_the_dragonfires":
            # MQ locations organized by chapter matching Locations.py structure:
            # - Chapter 1: Up to Weynon Priory (tutorial/initial quests; optional MS49)
            # - Chapter 2: MQ05 through pre-Paradise (Dagon Shrine, Spies, blood/artifact arcs)
            # - Chapter 3: Paradise through Victory
            
            # Chapter 1: Tutorial through Weynon Priory
            mq_chapter_1 = [
                "Deliver the Amulet",
                "Find the Heir",
                "Breaking the Siege of Kvatch: Gate Closed",
                "Breaking the Siege of Kvatch",
                "Weynon Priory",
                "Battle for Castle Kvatch",
            ]
            
            # Chapter 2: MQ05 through MQ13 (pre-Paradise)
            mq_chapter_2 = [
                # MQ05 - The Path of Dawn
                "The Path of Dawn: Acquire Commentaries Vol I",
                "The Path of Dawn: Acquire Commentaries Vol II",
                "The Path of Dawn: Acquire Commentaries Vol III",
                "The Path of Dawn: Acquire Commentaries Vol IV",
                "The Path of Dawn",
                # MQ06 - Dagon Shrine
                "Dagon Shrine: Mysterium Xarxes Acquired",
                "Dagon Shrine: Kill Harrow",
                "Dagon Shrine",
                "Attack on Fort Sutch",
                # MQ07 - Spies
                "Spies: Kill Saveri Faram",
                "Spies: Kill Jearl",
                "Spies",
                # MQ08-MQ13 - Blood/artifact quests and Bruma defense
                "Blood of the Daedra",
                "Blood of the Divines",
                "Blood of the Divines: Free Spirit 1",
                "Blood of the Divines: Free Spirit 2",
                "Blood of the Divines: Free Spirit 3",
                "Blood of the Divines: Free Spirit 4",
                "Blood of the Divines: Armor of Tiber Septim",
                "Bruma Gate",
                "Miscarcand",
                "Miscarcand: Great Welkynd Stone",
                "Defense of Bruma",
                "Great Gate",
            ]
            
            # Chapter 3: Paradise through Victory
            mq_chapter_3 = [
                "Paradise: Bands of the Chosen Acquired",
                "Paradise: Bands of the Chosen Removed",
                "Paradise",
            ]

            for loc_name in mq_chapter_1 + mq_chapter_2 + mq_chapter_3:
                if loc_name in location_table:
                    loc_data = location_table[loc_name]
                    loc_obj = OblivionLocation(self.player, loc_name, loc_data.id, cyrodiil_region)
                    cyrodiil_region.locations.append(loc_obj)

            if "Light the Dragonfires" in location_table:
                loc_data = location_table["Light the Dragonfires"]
                mq_victory_loc = OblivionLocation(self.player, "Light the Dragonfires", loc_data.id, cyrodiil_region)
                cyrodiil_region.locations.append(mq_victory_loc)
            # Add chapter event locations
            for chapter_event in ["Weynon Priory Quest Complete", "Paradise Complete"]:
                if chapter_event in location_table:
                    ev_data = location_table[chapter_event]
                    ev_loc = OblivionLocation(self.player, chapter_event, ev_data.id, cyrodiil_region)
                    cyrodiil_region.locations.append(ev_loc)
    
    def set_rules(self) -> None:
        set_rules(self.multiworld, self.player)
    
    def create_items(self) -> None:
        item_pool: list[Item] = []
        goal: str = self.options.goal.current_key  # needed for MQ conditional items

        # Get items that are precollected (includes start_inventory)
        precollected_items = {item.name for item in self.multiworld.precollected_items[self.player]}
        
        # Add shrine unlock tokens only if shrines are enabled
        if self.shrines_enabled:
            for shrine in self.active_shrines:
                token_name = f"{shrine} Shrine Token"
                if token_name in item_table and token_name not in precollected_items:
                    item_pool.append(self.create_item(token_name))
        
        # Progressive shop stock is always enabled (15 locations total)
        enabled_shop_count = 15
        
        # Add Progressive Arena Rank items if Arena is enabled
        if self.arena_enabled:
            arena_item_name = "Progressive Arena Rank"
            if arena_item_name in item_table:
                # Calculate how many Progressive Arena Rank items are needed
                # Each rank unlocks 3 matches, so we need ceiling(arena_count / 3) ranks
                ranks_needed = min((self.arena_count + 2) // 3, 7)  # Cap at 7 ranks max
                for i in range(ranks_needed):
                    item_pool.append(self.create_item(arena_item_name))
        
        # Add Progressive Shop Stock items (always enabled)
        shop_stock_item_name = "Progressive Shop Stock"
        if shop_stock_item_name in item_table:
            # Add 4 Progressive Shop Stock items
            for i in range(4):
                item_pool.append(self.create_item(shop_stock_item_name))
        
        # Add Progressive Class Level items to item pool if class system is enabled
        if self.selected_class is not None:
            # Determine how many are already precollected
            precollected_names = {item.name for item in self.multiworld.precollected_items[self.player]}
            precollected_count = sum(1 for name in precollected_names if name == self.progressive_class_level_item_name)

            # If Start With Class is enabled and none are precollected yet, precollect one
            try:
                if self.options.start_with_class.value and precollected_count == 0:
                    self.multiworld.push_precollected(self.create_item(self.progressive_class_level_item_name))
                    precollected_count += 1
            except Exception:
                pass

            # If player does NOT start with class and none are precollected, guarantee one early placement
            # (not restricted to local locations)
            if not self.options.start_with_class.value and precollected_count == 0:
                self.multiworld.early_items[self.player][self.progressive_class_level_item_name] = 1

            # Add remaining Progressive Class Level items to the pool up to the maximum
            levels_to_add = max(0, self.class_level_maximum - precollected_count)
            for _ in range(levels_to_add):
                item_pool.append(self.create_item(self.progressive_class_level_item_name))
        
        # Add Oblivion Gate Keys based on gate count and extra keys setting
        gate_key_item_name = "Oblivion Gate Key"
        if gate_key_item_name in item_table and self.gate_count > 0:
            base_gate_keys = self.gate_count
            extra_keys = self.options.extra_gate_keys.value
            
            # Add base gate keys as progression items
            for _ in range(base_gate_keys):
                item_pool.append(self.create_item(gate_key_item_name))
            
            # Add extra gate keys as progression_skip_balancing items
            for _ in range(extra_keys):
                extra_key = OblivionItem(
                    gate_key_item_name,
                    ItemClassification.progression_skip_balancing,
                    item_table[gate_key_item_name].id,
                    self.player,
                )
                item_pool.append(extra_key)
        
        # Add Region Access items for selected regions (progression)
        if self.dungeons_enabled:
            for region_name in self.selected_regions:
                access_item_name = f"{region_name} Access"
                if access_item_name in item_table and access_item_name not in precollected_items:
                    item_pool.append(self.create_item(access_item_name))

        # Main Quest: add Amulet of Kings only when Light the Dragonfires is the selected goal
        if goal == "light_the_dragonfires" and "Amulet of Kings" in item_table:
            if not any(i.name == "Amulet of Kings" for i in item_pool):  # avoid accidental duplication
                item_pool.append(self.create_item("Amulet of Kings"))

        # Main Quest: add Kvatch Gate Key only when Light the Dragonfires is the selected goal
        if goal == "light_the_dragonfires" and "Kvatch Gate Key" in item_table:
            if not any(i.name == "Kvatch Gate Key" for i in item_pool):
                item_pool.append(self.create_item("Kvatch Gate Key"))

        # MQ06: add Dagon Shrine Passphrase only when MQ goal is active
        if goal == "light_the_dragonfires" and "Dagon Shrine Passphrase" in item_table:
            if not any(i.name == "Dagon Shrine Passphrase" for i in item_pool):
                item_pool.append(self.create_item("Dagon Shrine Passphrase"))

        # Post-MQ06 optional: Fort Sutch Gate Key (Attack on Fort Sutch) only when MQ goal is active
        if goal == "light_the_dragonfires" and "Fort Sutch Gate Key" in item_table:
            if not any(i.name == "Fort Sutch Gate Key" for i in item_pool):
                item_pool.append(self.create_item("Fort Sutch Gate Key"))

        # MQ07: Blades' Report: Strangers at Dusk (gates Spies quest) only when MQ goal active
        if goal == "light_the_dragonfires" and "Blades' Report: Strangers at Dusk" in item_table:
            if not any(i.name == "Blades' Report: Strangers at Dusk" for i in item_pool):
                item_pool.append(self.create_item("Blades' Report: Strangers at Dusk"))

        # MQ05: Encrypted Scroll of the Blades (gates all MQ05 checks) only when MQ goal active
        if goal == "light_the_dragonfires" and "Encrypted Scroll of the Blades" in item_table:
            if not any(i.name == "Encrypted Scroll of the Blades" for i in item_pool):
                item_pool.append(self.create_item("Encrypted Scroll of the Blades"))

        # MQ08: Decoded Pages of the Xarxes (four fragments) only when MQ goal active
        if goal == "light_the_dragonfires":
            for name in [
                "Decoded Page of the Xarxes: Daedric",
                "Decoded Page of the Xarxes: Divine",
                "Decoded Page of the Xarxes: Ayleid",
                "Decoded Page of the Xarxes: Sigillum",
            ]:
                if name in item_table and not any(i.name == name for i in item_pool):
                    item_pool.append(self.create_item(name))

        # Bruma Gate Key only when MQ goal active
        if goal == "light_the_dragonfires" and "Bruma Gate Key" in item_table:
            if not any(i.name == "Bruma Gate Key" for i in item_pool):
                item_pool.append(self.create_item("Bruma Gate Key"))

        # Paradise Access only when MQ goal active
        if goal == "light_the_dragonfires" and "Paradise Access" in item_table:
            if not any(i.name == "Paradise Access" for i in item_pool):
                item_pool.append(self.create_item("Paradise Access"))

        # Count enabled arena locations
        enabled_arena_count = self.arena_count if self.arena_enabled else 0
        
        # Count enabled shrine locations
        enabled_shrine_count = len(self.active_shrines) if self.shrines_enabled else 0
        
        # Count gate locations
        enabled_gate_count = self.gate_count
        
        # Count class skill locations
        enabled_class_skill_count = 0
        if self.selected_class is not None:
            class_skills = get_filtered_class_skills(self.selected_class, self.excluded_skills)
            # Each level provides 2 skill increases per class skill (14 total per level if no skills excluded)
            enabled_class_skill_count = self.class_level_maximum * len(class_skills) * 2
        
        # Count dungeon locations (selected via region system)
        enabled_dungeon_count = self.dungeon_count if self.dungeons_enabled else 0

        # Count visit locations (Ayleid Well always present + birthsign stones for selected regions or all if regions disabled)
        if self.dungeons_enabled:
            # Only include stones whose region is selected
            selected_regions_set = set(self.selected_regions)
            stone_count = sum(1 for _name, region in getattr(self, '_birthsign_stones', []) if region in selected_regions_set)
        else:
            # Regions disabled: include all stones
            stone_count = len(getattr(self, '_birthsign_stones', []))
        enabled_visit_count = 1 + stone_count

        # Count MQ milestone locations when MQ goal active
        # Composition:
        #   Core chain: 12 (Deliver the Amulet through Dagon Shrine)
        #   Late chain: 19 (Harrow, Spies trio, Daedra/Divines arcs, Bruma path, Paradise trio)
        #   Optional extras: 2 (Battle for Castle Kvatch, Attack on Fort Sutch)
        # Total (excluding final victory): 33
        # Light the Dragonfires victory location is excluded from fill count.
        mq_milestone_count = 33 if goal == "light_the_dragonfires" else 0

        # Count all fillable locations: visits + shrines + shops + arena + gates + class_skills + dungeons + mq milestones (exclude Victory event)
        total_locations = (
            enabled_visit_count + enabled_shrine_count + enabled_shop_count + enabled_arena_count +
            enabled_gate_count + enabled_class_skill_count + enabled_dungeon_count + mq_milestone_count
        )
        
        # Filter useful items based on randomized vs vanilla shrines
        filtered_useful_items = list(useful_items)
        # If class selection is off, remove Birth Sign from the item pool
        if self.selected_class is None:
            try:
                filtered_useful_items.remove("Birth Sign")
            except ValueError:
                pass

        # If Gate Vision is not configured as an item, or gates are disabled, ensure it cannot appear from the generic useful pool
        if self.gate_vision_setting != "item" or self.gate_count == 0:
            try:
                filtered_useful_items.remove("Oblivion Gate Vision")
            except ValueError:
                pass

        # If Fast Travel item option is disabled, ensure it cannot appear from the generic useful pool
        if not self.fast_travel_item_enabled:
            try:
                filtered_useful_items.remove("Fast Travel")
            except ValueError:
                pass
        
        # Mapping of shrine names to their artifact names
        shrine_to_artifact = {
            "Azura": "Azura's Star",
            "Boethia": "Goldbrand", 
            "Clavicus Vile": "Masque of Clavicus Vile",
            "Hermaeus Mora": "Oghma Infinium",
            "Hircine": "Savior's Hide",
            "Malacath": "Volendrung",
            "Mephala": "Ebony Blade",
            "Meridia": "Ring of Khajiiti",
            "Molag Bal": "Mace of Molag Bal",
            "Namira": "Ring of Namira",
            "Nocturnal": "Skeleton Key",
            "Peryite": "Spellbreaker",
            "Sanguine": "Sanguine Rose",
            "Sheogorath": "Wabbajack",
            "Vaermina": "Skull of Corruption"
        }
        
        # Remove artifacts for non-randomized shrines
        all_shrines = set(shrine_to_artifact.keys())
        active_shrines_set = set(self.active_shrines) if self.shrines_enabled else set()
        inactive_shrines = all_shrines - active_shrines_set
        
        for shrine in inactive_shrines:
            artifact = shrine_to_artifact.get(shrine)
            if artifact and artifact in filtered_useful_items:
                filtered_useful_items.remove(artifact)
        
        # Guarantee artifacts from randomized shrines are in the pool
        guaranteed_artifacts = []
        if self.shrines_enabled:
            for shrine in self.active_shrines:
                artifact = shrine_to_artifact.get(shrine)
                if artifact and artifact in filtered_useful_items:
                    guaranteed_artifacts.append(artifact)
                    item_pool.append(self.create_item(artifact))
                    filtered_useful_items.remove(artifact)
        
        # Add Oblivion Gate Vision item if setting is "item" and gates are enabled
        if self.gate_vision_setting == "item" and self.gate_count > 0:
            gate_vision_item_name = "Oblivion Gate Vision"
            if gate_vision_item_name in item_table:
                item_pool.append(self.create_item(gate_vision_item_name))
                # Hint to the Generator that this item should be placed early
                self.multiworld.early_items[self.player][gate_vision_item_name] = 1
                # Remove from useful items to prevent duplicate placement
                if gate_vision_item_name in filtered_useful_items:
                    filtered_useful_items.remove(gate_vision_item_name)
        
        # Add Fast Travel item if the option is enabled
        if self.fast_travel_item_enabled:
            fast_travel_item_name = "Fast Travel"
            if fast_travel_item_name in item_table:
                item_pool.append(self.create_item(fast_travel_item_name))
                # Remove from useful items to prevent duplicate placement
                if fast_travel_item_name in filtered_useful_items:
                    filtered_useful_items.remove(fast_travel_item_name)
        
        # Add Horse item with early placement hint
        horse_item_name = "Horse"
        if horse_item_name in item_table:
            item_pool.append(self.create_item(horse_item_name))
            self.multiworld.early_items[self.player][horse_item_name] = 1
            # Remove from useful items to prevent duplicate placement
            if horse_item_name in filtered_useful_items:
                filtered_useful_items.remove(horse_item_name)
        
        # Calculate filler needed after guaranteeing artifacts
        current_items = len(item_pool)
        filler_needed = total_locations - current_items
        
        useful_items_list = filtered_useful_items
        filler_list = list(filler_items) 
        useful_percentage = 70  # Default weight, but we need more useful items to matter
        
        for i in range(filler_needed):
            # Percentage-based choice between useful items and filler
            if (self.multiworld.random.randint(1, 100) <= useful_percentage and 
                useful_items_list and len(useful_items_list) > 0):
                # Pick a useful item (unique - remove from list after selection)
                item_name = self.multiworld.random.choice(useful_items_list)
                useful_items_list.remove(item_name)
            else:
                # Pick a filler item (fully random - can repeat)
                item_name = self.multiworld.random.choice(filler_list)
            
            if item_name in item_table:
                item_pool.append(self.create_item(item_name))
        
        self.multiworld.itempool += item_pool

    
    def create_item(self, name: str) -> Item:
        item_data = item_table[name]
        return OblivionItem(name, item_data.classification, item_data.id, self.player)
    
    def create_event(self, event: str) -> Item:
        return OblivionItem(event, ItemClassification.progression, None, self.player)

    def generate_basic(self) -> None:
        # Place Victory event items on victory locations for playthrough generation
        goal = self.options.goal.current_key
        
        if goal == "shrine_seeker":
            
            shrine_victory_location = self.multiworld.get_location("Shrine Seeker", self.player)
            victory_item = self.create_event("Victory")
            shrine_victory_location.place_locked_item(victory_item)
            # Set access rule: requires completing the goal number of shrines
            required_count = self.options.shrine_goal.value
            active_shrines = list(self.active_shrines)
            shrine_victory_location.access_rule = lambda state, count=required_count, shrines=active_shrines: (
                sum(1 for shrine in shrines 
                    if state.can_reach_location(f"{shrine} Quest Complete", self.player)) >= count
            )
            
        elif goal == "gatecloser":
            
            gate_victory_location = self.multiworld.get_location("Gatecloser", self.player)
            victory_item = self.create_event("Victory")
            gate_victory_location.place_locked_item(victory_item)
            # Set access rule: requires completing the goal number of gates
            required_count = self.gate_count
            gate_victory_location.access_rule = lambda state, count=required_count: (
                sum(1 for gate_num in range(1, count + 1) 
                    if state.can_reach_location(f"Gate {gate_num} Closed", self.player)) >= count
            )
            
        elif goal == "arena":
            
            arena_victory_location = self.multiworld.get_location("Arena Grand Champion", self.player)
            victory_item = self.create_event("Victory")
            arena_victory_location.place_locked_item(victory_item)
            # Set access rule: requires completing all 21 arena matches
            arena_victory_location.access_rule = lambda state: (
                sum(1 for i in range(1, 22) 
                    if state.can_reach_location(f"Arena Match {i} Victory", self.player)) >= 21
            )
        elif goal == "dungeon_delver":
            
            dungeon_victory_location = self.multiworld.get_location("Dungeon Delver", self.player)
            victory_item = self.create_event("Victory")
            dungeon_victory_location.place_locked_item(victory_item)
            # Require all selected dungeons to be completable
            required_dungeons = list(getattr(self, 'selected_dungeons', []))
            dungeon_victory_location.access_rule = lambda state, dungeons=required_dungeons: (
                all(state.can_reach_location(d, self.player) for d in dungeons)
            )
        elif goal == "light_the_dragonfires":
            # Chapter marker events
            chapter_event_items = {
                # Location : Event Item
                "Weynon Priory Quest Complete": "Cloud Ruler Temple Established",
                "Paradise Complete": "Dragonfires Ready",
            }
            for chapter_loc, item_name in chapter_event_items.items():
                try:
                    loc_obj = self.multiworld.get_location(chapter_loc, self.player)
                    loc_obj.place_locked_item(self.create_event(item_name))
                except Exception:
                    pass
            # Place standard Victory event item on final MQ location
            try:
                ltd_loc = self.multiworld.get_location("Light the Dragonfires", self.player)
                ltd_loc.place_locked_item(self.create_event("Victory"))
            except Exception:
                pass
            # MQ completion condition: obtain Victory
            self.multiworld.completion_condition[self.player] = lambda state: state.has("Victory", self.player)
            return
        
        # Default completion condition for other goals: require Victory event item (placed above)
        self.multiworld.completion_condition[self.player] = lambda state: state.has("Victory", self.player)
    
    def fill_slot_data(self) -> Dict[str, Any]:
        # Data sent to the client
        goal_key = self.options.goal.current_key
        shrine_goal_value = self.options.shrine_goal.value if goal_key == "shrine_seeker" else 0
        return {
            "items": self.item_name_to_id,
            "locations": self.location_name_to_id,
            "free_offerings": self.options.free_offerings.value,
            "active_shrines": self.active_shrines,
            "shrine_offerings": self.shrine_offerings,
            "goal": goal_key,
            "shrine_goal": shrine_goal_value,
            "shrine_count": len(self.active_shrines),
            "gate_count_required": self.gate_count,
            "extra_gate_keys": self.options.extra_gate_keys.value,
            "session_id": getattr(self, 'session_id', None),
            "progressive_shop_stock": True,
            "progressive_armor_sets": True,
            
            # Class system data
            "selected_class": self.selected_class,
            "class_level_maximum": self.class_level_maximum,
            "class_skills": get_filtered_class_skills(self.selected_class, self.excluded_skills) if self.selected_class else [],
            "progressive_class_level_item_name": self.progressive_class_level_item_name,
            "excluded_skills": list(self.excluded_skills) if self.selected_class else [],
            
            # Count settings
            "arena_matches": self.arena_count,
            "dungeons_selected": self.dungeon_count,
            "gate_count": self.gate_count,
            "gate_vision": self.gate_vision_setting if self.gate_count > 0 else "off",
            "fast_travel_item": self.fast_travel_item_enabled,
            "fast_arena": self.options.fast_arena.value,
            "dungeon_marker_mode": self.dungeon_marker_mode_setting,
            "selected_dungeons": getattr(self, 'selected_dungeons', []),
            "selected_regions": getattr(self, 'selected_regions', []),
            "dungeons_by_region": getattr(self, 'selected_dungeons_by_region', {}),
            # Compatibility hint for generic trackers
            "starting_unlocked_regions": getattr(self, 'starting_unlocked_regions', []),
            "shop_scout_type": self.options.shop_scout_type.value,
            
        }
    
    def generate_output(self, output_directory: str) -> None:
        """Generate unique session ID for this world instance."""
        self.session_id = str(uuid.uuid4()) 