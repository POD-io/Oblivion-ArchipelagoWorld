import uuid
from worlds.AutoWorld import World, WebWorld
from BaseClasses import Region, Entrance, Item, ItemClassification, Location
from Options import Range, Choice, Toggle, DefaultOnToggle, PerGameCommonOptions
from typing import Dict, Any, List
import logging

from .Items import item_table, OblivionItem, progression_items, useful_items, filler_items
from .Locations import location_table, OblivionLocation, EventId
from .Rules import set_rules
from .Options import OblivionOptions
from .ShrineProgression import select_active_shrines, get_shrine_offerings

# Client registration
def launch_client():
    from .Client import launch
    launch_component(launch, name="OblivionRemasteredClient")

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
    
    Key Features:
    - 15 Daedric shrine quest locations with configurable availability
    - Tier-based progression system for shrine unlocking
    - File-based communication with UE4SS mod integration
    - Flexible victory conditions (complete X out of Y shrines)
    """
    
    game = "Oblivion Remastered"
    web = OblivionWebWorld()
    
    options_dataclass = OblivionOptions
    options: OblivionOptions
    
    item_name_to_id = {name: data.id for name, data in item_table.items()}
    location_name_to_id = {name: data.id for name, data in location_table.items()}
    
    def generate_early(self) -> None:
        # Get shrines that have tokens in start_inventory (these must be active)
        start_inventory_items = self.options.start_inventory.value
        logger.info(f"Player {self.player}: Raw start_inventory option: {start_inventory_items}")
        required_shrines = []
        for item_name in start_inventory_items:
            if item_name.endswith(" Shrine Token"):
                shrine_name = item_name.replace(" Shrine Token", "")
                required_shrines.append(shrine_name)
        
        # Select which shrines will be active for this seed
        self.active_shrines = select_active_shrines(
            self.options.total_active_shrines.value, 
            self.multiworld.random,
            required_shrines
        )
        
        logger.info(f"Player {self.player}: Required shrines from start_inventory: {required_shrines}")
        logger.info(f"Player {self.player}: Total active shrines requested: {self.options.total_active_shrines.value}")
        logger.info(f"Player {self.player}: Selected active shrines: {self.active_shrines}")
        
        # Get required offerings for each active shrine
        self.shrine_offerings = {}
        for shrine in self.active_shrines:
            self.shrine_offerings[shrine] = get_shrine_offerings(shrine)
    

    
    def create_items(self) -> None:
        # Create event items first
        self.create_and_assign_event_items()
        
        # Create all items for this world
        item_pool = []
        
        # Get items that are precollected (includes start_inventory) - Timespinner method
        precollected_items = {item.name for item in self.multiworld.precollected_items[self.player]}
        
        logger.info(f"Player {self.player}: Precollected items: {precollected_items}")
        logger.info(f"Player {self.player}: Progression items: {progression_items}")
        
        # Add progression items (shrine unlock tokens) only for active shrines, except precollected ones
        for shrine in self.active_shrines:
            token_name = f"{shrine} Shrine Token"
            if token_name in item_table and token_name not in precollected_items:
                logger.info(f"Player {self.player}: Adding {token_name} to item pool")
                item_pool.append(self.create_item(token_name))
            else:
                logger.info(f"Player {self.player}: Skipping {token_name} (precollected or not in table)")
        
        # Only create items to match the number of active shrine locations
        total_locations = len(self.active_shrines)
        current_items = len(item_pool)
        remaining_slots = total_locations - current_items
        
        # Fill remaining slots using weighted selection between useful and filler items
        current_items = len(item_pool)
        filler_needed = total_locations - current_items
        
        useful_items_list = list(useful_items)
        filler_list = list(filler_items) 
        useful_weight = self.options.useful_items_weight.value
        
        for i in range(filler_needed):
            # Weighted choice between useful items and filler
            if self.multiworld.random.randint(1, useful_weight + 1) <= useful_weight and useful_items_list:
                # Pick a useful item
                item_name = useful_items_list[i % len(useful_items_list)]
            else:
                # Pick a filler item
                item_name = filler_list[i % len(filler_list)]
            
            if item_name in item_table:
                item_pool.append(self.create_item(item_name))
        
        self.multiworld.itempool += item_pool
    
    def create_item(self, name: str) -> Item:
        item_data = item_table[name]
        return OblivionItem(name, item_data.classification, item_data.id, self.player)
    
    def create_event(self, event: str) -> Item:
        return OblivionItem(event, ItemClassification.progression, None, self.player)

    def create_regions(self) -> None:
        # Create the main region
        menu_region = Region("Menu", self.player, self.multiworld)
        
        # Create the main game region  
        cyrodiil_region = Region("Cyrodiil", self.player, self.multiworld)
        
        # Add only locations for active shrines to Cyrodiil
        for shrine in self.active_shrines:
            location_name = f"{shrine} Quest Complete"
            if location_name in location_table:
                location_data = location_table[location_name]
                location = OblivionLocation(self.player, location_name, location_data.id, cyrodiil_region)
                cyrodiil_region.locations.append(location)
        
        # Add Victory event location
        victory_location = OblivionLocation(self.player, "Victory", EventId, cyrodiil_region)
        cyrodiil_region.locations.append(victory_location)
        
        # Connect menu to game
        connection = Entrance(self.player, "New Game", menu_region)
        connection.connect(cyrodiil_region)
        menu_region.exits.append(connection)
        
        # Add regions to multiworld
        self.multiworld.regions += [menu_region, cyrodiil_region]
    
    def set_rules(self) -> None:
        set_rules(self.multiworld, self.player)
        
        # Set completion condition to check for Victory event
        self.multiworld.completion_condition[self.player] = lambda state: state.has("Victory", self.player)
    
    def create_and_assign_event_items(self) -> None:
        # Create event items for event locations (like Victory)
        for location in self.multiworld.get_locations(self.player):
            if location.address == EventId:
                item = Item(location.name, ItemClassification.progression, EventId, self.player)
                location.place_locked_item(item)
    
    def generate_basic(self) -> None:
        logger.info(f"Player {self.player}: Generating basic setup")
        
        # Set access rule for Victory location based on shrine completion goal
        goal = self.options.goal.current_key
        required_count = self.options.shrine_count_required.value
        victory_location = self.multiworld.get_location("Victory", self.player)
        
        # Victory requires completing the specified number of shrines
        victory_location.access_rule = lambda state: (
            sum(1 for shrine in self.active_shrines 
                if state.can_reach(f"{shrine} Quest Complete", "Location", self.player)) >= required_count
        )
    

    
    def fill_slot_data(self) -> Dict[str, Any]:
        # Data sent to the client
        return {
            "items": {name: data.id for name, data in item_table.items()},
            "locations": {name: data.id for name, data in location_table.items()},
            "free_offerings": self.options.free_offerings.value,
            "active_shrines": self.active_shrines,
            "shrine_offerings": self.shrine_offerings,
            "goal": self.options.goal.current_key,
            "shrine_count_required": self.options.shrine_count_required.value,
            "session_id": getattr(self, 'session_id', None),  # Include session_id if it exists
        }
    
    def generate_output(self, output_directory: str) -> None:
        """Generate unique session ID for this world instance."""
        self.session_id = str(uuid.uuid4())
        logger.info(f"Player {self.player}: Generated session_id: {self.session_id}") 