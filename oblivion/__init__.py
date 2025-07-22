import uuid
from worlds.AutoWorld import World, WebWorld
from BaseClasses import Region, Entrance, Item, ItemClassification, Location
from typing import Dict, Any, List
import logging

from .Items import item_table, OblivionItem, progression_items, useful_items, filler_items
from .Locations import location_table, OblivionLocation, EventId
from .Rules import set_rules
from .Options import OblivionOptions
from .ShrineProgression import select_active_shrines, get_shrine_offerings

# Client registration
def launch_client(*args):
    from .Client import launch
    from worlds.LauncherComponents import launch as launch_component
    launch_component(launch, name="Oblivion Client", args=args)

from worlds.LauncherComponents import Component, components, Type, launch as launch_component
components.append(Component("Oblivion Remastered Client", 
                           game_name="Oblivion Remastered", 
                           func=launch_client, 
                           component_type=Type.CLIENT,
                           supports_uri=True))

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
    
    # Item groups for hints and logic
    item_name_groups: Dict[str, List[str]] = {
        "Shrine Tokens": [f"{shrine} Shrine Token" for shrine in [
            "Azura", "Boethia", "Clavicus Vile", "Hermaeus Mora", "Hircine", 
            "Malacath", "Mephala", "Meridia", "Molag Bal", "Namira", 
            "Nocturnal", "Peryite", "Sanguine", "Sheogorath", "Vaermina"
        ]],
        "Daedric Artifacts": [
            "Azura's Star", "Goldbrand", "Masque of Clavicus Vile", "Oghma Infinium",
            "Savior's Hide", "Volendrung", "Ebony Blade", "Ring of Khajiiti",
            "Ring of Namira", "Skeleton Key", "Spellbreaker", "Sanguine Rose",
            "Wabbajack", "Skull of Corruption"
        ],
        "Progression Items": ["Progressive Arena Rank", "Progressive Shop Stock", "Oblivion Gate Key"],
    }
    
    def generate_early(self) -> None:
        # Validate goal/count combinations
        goal = self.options.goal.current_key
        if goal == "shrine_seeker" and self.options.shrine_count.value == 0:
            raise Exception("Shrine Count cannot be 0 when Goal is Shrine Seeker")
        if goal == "gatecloser" and self.options.gate_count.value == 0:
            raise Exception("Gate Count cannot be 0 when Goal is Gatecloser")
        if goal == "shrine_seeker" and self.options.shrine_goal.value > self.options.shrine_count.value:
            raise Exception(f"Shrine Goal ({self.options.shrine_goal.value}) cannot be greater than Shrine Count ({self.options.shrine_count.value})")
        
        # Determine if content types are enabled based on count settings
        self.shrines_enabled = self.options.shrine_count.value > 0 or goal == "shrine_seeker"
        self.arena_enabled = (goal == "arena") or (goal != "arena" and self.options.arena_matches.value > 0)
        self.skills_enabled = True
        self.dungeons_enabled = self.options.dungeon_clears.value > 0
        
        # Set counts based on settings
        self.gate_count = self.options.gate_count.value
        self.skill_count = self.options.skill_checks.value
        self.dungeon_count = self.options.dungeon_clears.value
        
        # For arena: ignore setting when goal is arena, use setting otherwise
        if goal == "arena":
            self.arena_count = 21  # Always all 21 matches for arena goal
        else:
            self.arena_count = self.options.arena_matches.value if self.arena_enabled else 0
        
        # Handle gate vision setting
        self.gate_vision_setting = self.options.gate_vision.current_key
        
        # Initialize shrine data only if shrines are enabled
        if self.shrines_enabled:
            
            # Get required shrines from start_inventory
            start_inventory_items = self.options.start_inventory.value
            logger.info(f"Player {self.player}: Raw start_inventory option: {start_inventory_items}")
            required_shrines = []
            for item_name in start_inventory_items:
                if item_name.endswith(" Shrine Token"):
                    shrine_name = item_name.replace(" Shrine Token", "")
                    required_shrines.append(shrine_name)
            
            # Select which shrines will be active for this seed
            self.active_shrines = select_active_shrines(
                self.options.shrine_count.value, 
                self.multiworld.random,
                required_shrines
            )
            
            # Get required offerings for each active shrine
            self.shrine_offerings = {}
            for shrine in self.active_shrines:
                self.shrine_offerings[shrine] = get_shrine_offerings(shrine)
        else:
            # If shrines are disabled, set empty defaults
            self.active_shrines = []
            self.shrine_offerings = {}
    

    
    def create_regions(self) -> None:
        menu_region = Region("Menu", self.player, self.multiworld)
  
        cyrodiil_region = Region("Cyrodiil", self.player, self.multiworld)
        
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
            gate_location = OblivionLocation(
                self.player,
                f"Gate {i} Closed",
                location_table[f"Gate {i} Closed"].id,
                cyrodiil_region
            )
            cyrodiil_region.locations.append(gate_location)
        
        # Add goal-specific victory event locations (only for the active goal)
        goal = self.options.goal.current_key
        if goal == "arena":
            # Arena Grand Champion event location will be created in arena section
            pass
        elif goal == "gatecloser":
            # Create Gatecloser event location
            gate_victory_location = OblivionLocation(self.player, "Gatecloser", EventId, cyrodiil_region)
            cyrodiil_region.locations.append(gate_victory_location)
        elif goal == "shrine_seeker":
            # Create Shrine Seeker event location
            shrine_victory_location = OblivionLocation(self.player, "Shrine Seeker", EventId, cyrodiil_region)
            cyrodiil_region.locations.append(shrine_victory_location)

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
            
            # Add Arena Grand Champion event location only if Arena is the goal
            if self.options.goal.current_key == "arena":
                location_name = "Arena Grand Champion"
                if location_name in location_table:
                    location_data = location_table[location_name]
                    # Create as event location (no items placed on it)
                    location = OblivionLocation(self.player, location_name, location_data.id, cyrodiil_region)
                    cyrodiil_region.locations.append(location)
        
        # Add Skill Increase locations if enabled
        if self.skills_enabled:
            for i in range(1, self.skill_count + 1):
                location_name = f"Skill Increase {i}"
                if location_name in location_table:
                    location_data = location_table[location_name]
                    location = OblivionLocation(self.player, location_name, location_data.id, cyrodiil_region)
                    cyrodiil_region.locations.append(location)
        
        # Add Dungeon Clear locations if enabled
        if self.dungeons_enabled:
            for i in range(1, self.dungeon_count + 1):
                location_name = f"Dungeon Clear {i}"
                if location_name in location_table:
                    location_data = location_table[location_name]
                    location = OblivionLocation(self.player, location_name, location_data.id, cyrodiil_region)
                    cyrodiil_region.locations.append(location)
        
        # Connect menu to game
        connection = Entrance(self.player, "New Game", menu_region)
        connection.connect(cyrodiil_region)
        menu_region.exits.append(connection)
        
        # Add regions to multiworld
        self.multiworld.regions += [menu_region, cyrodiil_region]
    
    def set_rules(self) -> None:
        set_rules(self.multiworld, self.player)
    
    def create_items(self) -> None:
        item_pool = []
        
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
        
        # Add Oblivion Gate Keys based on gate count and extra keys setting
        gate_key_item_name = "Oblivion Gate Key"
        if gate_key_item_name in item_table and self.gate_count > 0:
            base_gate_keys = self.gate_count
            extra_keys = self.options.extra_gate_keys.value
            
            # Add base gate keys as progression items
            for i in range(base_gate_keys):
                item_pool.append(self.create_item(gate_key_item_name))
            
            # Add extra gate keys as progression_skip_balancing items
            for i in range(extra_keys):
                extra_key = OblivionItem(gate_key_item_name, ItemClassification.progression_skip_balancing, 
                                       item_table[gate_key_item_name].id, self.player)
                item_pool.append(extra_key)
        
        # Count enabled arena locations
        enabled_arena_count = self.arena_count if self.arena_enabled else 0
        
        # Count enabled shrine locations
        enabled_shrine_count = len(self.active_shrines) if self.shrines_enabled else 0
        
        # Count gate locations
        enabled_gate_count = self.gate_count
        
        # Count skill increase locations
        enabled_skill_count = self.skill_count if self.skills_enabled else 0
        
        # Count dungeon clear locations
        enabled_dungeon_count = self.dungeon_count if self.dungeons_enabled else 0
        
        # Count all fillable locations: shrines + shops + arena + gates + skills + dungeons (exclude Victory)
        total_locations = enabled_shrine_count + enabled_shop_count + enabled_arena_count + enabled_gate_count + enabled_skill_count + enabled_dungeon_count
        
        # Filter useful items based on randomized vs vanilla shrines
        filtered_useful_items = list(useful_items)
        
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
                self.multiworld.local_early_items[self.player][gate_vision_item_name] = 1
                # Remove from useful items to prevent duplicate placement
                if gate_vision_item_name in filtered_useful_items:
                    filtered_useful_items.remove(gate_vision_item_name)
        
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
        # Create goal-specific victory event locations and place Victory item
        goal = self.options.goal.current_key
        
        if goal == "arena":
            # Create Arena Grand Champion event location and place Victory item
            arena_victory_location = self.multiworld.get_location("Arena Grand Champion", self.player)
            arena_victory_location.place_locked_item(self.create_event("Victory"))
            # Set access rule: requires completing all 21 arena matches
            arena_victory_location.access_rule = lambda state: (
                sum(1 for i in range(1, 22) 
                    if state.can_reach_location(f"Arena Match {i} Victory", self.player)) >= 21
            )
            
        elif goal == "gatecloser":
            # Create Gatecloser event location and place Victory item
            gate_victory_location = self.multiworld.get_location("Gatecloser", self.player)
            gate_victory_location.place_locked_item(self.create_event("Victory"))
            # Set access rule: requires completing the goal number of gates
            required_count = self.gate_count
            gate_victory_location.access_rule = lambda state, count=required_count: (
                sum(1 for gate_num in range(1, count + 1) 
                    if state.can_reach_location(f"Gate {gate_num} Closed", self.player)) >= count
            )
            
        elif goal == "shrine_seeker":
            # Create Shrine Seeker event location and place Victory item
            shrine_victory_location = self.multiworld.get_location("Shrine Seeker", self.player)
            shrine_victory_location.place_locked_item(self.create_event("Victory"))
            # Set access rule: requires completing the goal number of shrines
            required_count = self.options.shrine_goal.value
            active_shrines = list(self.active_shrines)
            shrine_victory_location.access_rule = lambda state, count=required_count, shrines=active_shrines: (
                sum(1 for shrine in shrines 
                    if state.can_reach_location(f"{shrine} Quest Complete", self.player)) >= count
            )
        
        # Set completion condition to check for Victory item
        self.multiworld.completion_condition[self.player] = lambda state: state.has("Victory", self.player)
    

    
    def fill_slot_data(self) -> Dict[str, Any]:
        # Data sent to the client
        return {
            "items": {name: data.id for name, data in item_table.items()},
            "locations": {name: data.id for name, data in location_table.items()},
            "free_offerings": self.options.free_offerings.value,
            "active_shrines": self.active_shrines,
            "shrine_offerings": self.shrine_offerings,
            "goal": self.options.goal.current_key,
            "shrine_goal": self.options.shrine_goal.value,
            "shrine_count": len(self.active_shrines),
            "gate_count_required": self.gate_count,
            "extra_gate_keys": self.options.extra_gate_keys.value,
            "session_id": getattr(self, 'session_id', None),
            "progressive_shop_stock": True,
            
            # Count settings
            "arena_matches": self.arena_count,
            "skill_checks": self.skill_count,
            "dungeon_clears": self.dungeon_count,
            "gate_count": self.gate_count,
            "gate_vision": self.gate_vision_setting if self.gate_count > 0 else "off",
        }
    
    def generate_output(self, output_directory: str) -> None:
        """Generate unique session ID for this world instance."""
        self.session_id = str(uuid.uuid4()) 