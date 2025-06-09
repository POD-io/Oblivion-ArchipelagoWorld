import asyncio
import os
import time
import glob
from typing import Dict, List, Set
from CommonClient import CommonContext, server_loop, gui_enabled, ClientCommandProcessor, logger, get_base_parser
from NetUtils import ClientStatus


class OblivionClientCommandProcessor(ClientCommandProcessor):
    def _cmd_oblivion(self):
        """Print information about connected Oblivion game."""
        if not isinstance(self.ctx, OblivionContext):
            return
            
        self.output(f"Oblivion Remastered Status:")
        self.output(f"- Items received: {len(self.ctx.items_received)}")
        self.output(f"- Locations checked: {len(self.ctx.checked_locations)}")
        self.output(f"- Missing locations: {len(self.ctx.missing_locations)}")


class OblivionContext(CommonContext):
    command_processor = OblivionClientCommandProcessor
    game = "Oblivion Remastered"
    items_handling = 0b111  # Full item handling
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
        }
        
        # State tracking
        self.last_completion_check = 0
        self.file_prefix = ""
        self.session_id = ""  # Session ID for file isolation
        self.game_loop_task = None
        self.items_processed_count = 0  # Track how many items we've sent to game
        self.shrines_completed = 0  # Track how many shrines have been completed
        self.victory_sent = False  # Track if victory has been sent
        
        # Ensure save directory exists
        os.makedirs(self.oblivion_save_path, exist_ok=True)
        
    async def server_auth(self, password_requested: bool = False):
        if password_requested and not self.password:
            await super().server_auth(password_requested)
        await self.get_username()
        await self.send_connect()
        
    def on_package(self, cmd: str, args: dict):
        """Handle incoming server packages."""
        if cmd == "Connected":
            self.slot_data = args.get("slot_data", {})
            # Extract session_id from slot_data
            self.session_id = self.slot_data.get("session_id", "")
            logger.info(f"Received session_id: {self.session_id}")
            
            # Set up file prefix immediately to avoid race conditions
            auth_name = getattr(self, 'auth', None) or getattr(self, 'player_name', None) or getattr(self, 'name', None)
            if auth_name:
                self.auth = auth_name
                self._setup_file_prefix()
                logger.info(f"File prefix set: {self.file_prefix}")
            # Schedule connection setup for next event loop iteration
            asyncio.create_task(self._setup_after_connection())
        elif cmd == "ReceivedItems":
            asyncio.create_task(self._send_items_to_oblivion())
        elif cmd == "LocationInfo":
            pass  # We don't need to handle this for our implementation
            
    async def _setup_after_connection(self):
        """Complete setup after successful connection to slot."""
        if not self.file_prefix or not self.session_id:
            logger.error("File prefix or session_id not set during connection")
            return
            
        # Clean up old session files first
        self._cleanup_old_sessions()
            
        # Display existing items queue info
        self._check_existing_items_file()
        
        # Write game configuration files
        self._write_settings_file()
        self._write_connection_info()
        self._write_session_info()  # Write session info for OBSE mod
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
    
    def _cleanup_old_sessions(self):
        """Clean up old session files, keeping only the 3 most recent."""
        if not self.auth:
            return
            
        try:
            from Utils import get_file_safe_name
            safe_auth = get_file_safe_name(self.auth)
            
            # Find all files matching our player pattern
            pattern = os.path.join(self.oblivion_save_path, f"AP_{safe_auth}_*")
            all_files = glob.glob(pattern)
            
            if not all_files:
                return
                
            # Group files by session (extract session from filename)
            sessions = {}
            for filepath in all_files:
                basename = os.path.basename(filepath)
                if basename.startswith(f"AP_{safe_auth}_"):
                    # Extract session ID from filename
                    parts = basename.split("_")
                    if len(parts) >= 3:
                        session_part = parts[2].split(".")[0]  # Remove file extension
                        if session_part not in sessions:
                            sessions[session_part] = []
                        sessions[session_part].append(filepath)
            
            # Keep only the 3 most recent sessions (by file modification time)
            if len(sessions) > 3:
                session_times = {}
                for session, files in sessions.items():
                    # Use the newest file time from each session
                    max_time = max(os.path.getmtime(f) for f in files)
                    session_times[session] = max_time
                
                # Sort by time, keep newest 3
                sorted_sessions = sorted(session_times.items(), key=lambda x: x[1], reverse=True)
                sessions_to_keep = [s[0] for s in sorted_sessions[:3]]
                
                # Delete files from old sessions
                deleted_count = 0
                for session, files in sessions.items():
                    if session not in sessions_to_keep and session != self.session_id[:8]:
                        for filepath in files:
                            try:
                                os.remove(filepath)
                                deleted_count += 1
                            except Exception as e:
                                logger.warning(f"Failed to delete old session file {filepath}: {e}")
                
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} files from old sessions")
                    
        except Exception as e:
            logger.warning(f"Failed to clean up old sessions: {e}")
    
    def _write_session_info(self):
        """Write current session info for the OBSE mod to read."""
        session_file = os.path.join(self.oblivion_save_path, "current_session.txt")
        try:
            with open(session_file, "w") as f:
                f.write(f"session_id={self.session_id}\n")
                f.write(f"file_prefix={self.file_prefix}\n")
                f.write(f"slot_name={self.auth}\n")
                f.write(f"connected_time={int(time.time())}\n")
            logger.info(f"Session info written: {self.session_id[:8]}")
        except Exception as e:
            logger.error(f"Error writing session info: {e}")
    
    def _check_existing_items_file(self):
        """Check if items file exists and display warning to user."""
        items_file = os.path.join(self.oblivion_save_path, f"{self.file_prefix}_items.txt")
        if not os.path.exists(items_file):
            return
            
        try:
            with open(items_file, "r") as f:
                items = [line.strip() for line in f.readlines() if line.strip()]
            
            if items:
                logger.warning("=" * 60)
                logger.warning(f"EXISTING ITEMS QUEUE: {len(items)} items waiting")
                logger.warning("Items in queue:")
                for item in items[:5]:  # Show first 5
                    logger.warning(f"  - {item}")
                if len(items) > 5:
                    logger.warning(f"  ... and {len(items) - 5} more")
                logger.warning("")
                logger.warning("These will be processed when you start Oblivion.")
                logger.warning("New items will be added to this queue.")
                logger.warning("=" * 60)
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
        # Try current session first
        session_file = os.path.join(self.oblivion_save_path, "current_session.txt")
        if os.path.exists(session_file):
            try:
                with open(session_file, "r") as f:
                    for line in f:
                        if line.startswith("session_id="):
                            self.session_id = line.split("=", 1)[1].strip()
                        elif line.startswith("file_prefix="):
                            self.file_prefix = line.split("=", 1)[1].strip()
                return bool(self.file_prefix and self.session_id)
            except Exception as e:
                logger.error(f"Error loading session info: {e}")
        
        # Fallback to old connection file
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
                logger.info(f"Settings written: free_offerings={str(free_offerings)}")
                
                # Write shrine-specific offerings
                if shrine_offerings:
                    for shrine, offerings in shrine_offerings.items():
                        if offerings:
                            f.write(f"offerings_{shrine}={','.join(offerings)}\n")
                    
            logger.info(f"Settings written for {self.auth}")
        except Exception as e:
            logger.error(f"Error writing settings: {e}")
        
    async def _send_items_to_oblivion(self):
        """Send received items to the game via file queue."""
        if not self.file_prefix:
            if not self._load_connection_info():
                logger.warning("No file prefix available, cannot send items")
                return
        
        logger.info(f"Processing {len(self.items_received)} received items, {self.items_processed_count} already processed")
        
        # Process only new items beyond what we've already processed
        from worlds.oblivion.Items import item_table
        new_items = []
        for i in range(self.items_processed_count, len(self.items_received)):
            network_item = self.items_received[i]
            
            # Look up item name by ID
            item_name = None
            for name, data in item_table.items():
                if data.id == network_item.item:
                    item_name = name
                    break
                    
            if item_name:
                logger.info(f"Adding item to queue: {item_name} (ID: {network_item.item})")
                new_items.append(item_name)
            else:
                logger.warning(f"Unknown item ID: {network_item.item}")
                
        if new_items:
            logger.info(f"Sending {len(new_items)} new items to queue: {new_items}")
            self._append_items_to_queue(new_items)
            # Update our processed count
            self.items_processed_count = len(self.items_received)
        else:
            logger.info("No new items to send")
            
    def _append_items_to_queue(self, items):
        """Append items to the game's item queue file."""
        try:
            queue_path = os.path.join(self.oblivion_save_path, f"{self.file_prefix}_items.txt")
            with open(queue_path, "a") as f:
                for item_name in items:
                    f.write(f"{item_name}\n")
            logger.info(f"Added {len(items)} items to queue")
        except Exception as e:
            logger.error(f"Error adding items to queue: {e}")

    async def _wait_for_connection_data(self):
        """Wait for missing_locations to be populated (indicates full connection)."""
        max_wait = 10  # Maximum 10 seconds
        wait_count = 0
        while not hasattr(self, 'missing_locations') or len(self.missing_locations) == 0:
            await asyncio.sleep(0.5)
            wait_count += 1
            if wait_count > max_wait * 2:  # 0.5s intervals
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
            logger.info("Processing completion file")
            
            # Read completion tokens from file
            with open(completion_path, "r") as f:
                completed_shrines = [line.strip() for line in f.readlines() if line.strip()]
            
            logger.info(f"Found {len(completed_shrines)} completion tokens")
            
            # Build location ID lookup table
            from worlds.oblivion.Locations import location_table
            name_to_id_map = {name: data.id for name, data in location_table.items()}
                
            # Process each completion token
            new_locations = []
            for shrine_token in completed_shrines:
                if shrine_token in self.completion_tokens:
                    location_name = self.completion_tokens[shrine_token]
                    
                    if location_name in name_to_id_map:
                        location_id = name_to_id_map[location_name]
                        
                        # Only add if this location is still missing
                        if location_id in self.missing_locations:
                            new_locations.append(location_id)
                            logger.info(f"Processing shrine token: {shrine_token} -> {location_name}")
                    else:
                        logger.error(f"Location '{location_name}' not found in location table")
                else:
                    logger.warning(f"Unknown shrine token: {shrine_token}")
                            
            # Send location checks to server
            if new_locations:
                found_locations = await self.check_locations(new_locations)
                
                for location_id in found_locations:
                    self.locations_checked.add(location_id)
                    location_name = self.location_names.lookup_in_game(location_id, self.game)
                    logger.info(f'New Check: {location_name} ({len(self.locations_checked)}/{len(self.missing_locations) + len(self.checked_locations)})')
                    
                    # Track shrine completions for victory condition
                    if location_name.endswith(" Quest Complete"):
                        self.shrines_completed += 1
                        logger.info(f"Shrines completed: {self.shrines_completed}")
                        await self._check_victory_condition()
            
            # Always delete the completion file after processing
            try:
                os.remove(completion_path)
                if new_locations:
                    logger.info("Completion file processed and deleted")
                else:
                    logger.info("All locations already completed, file deleted")
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
            
        # Only clean up current session files - other files are managed by the game/client
        for filename in [f"{self.file_prefix}_settings.txt", "current_session.txt", "current_connection.txt"]:
            filepath = os.path.join(self.oblivion_save_path, filename)
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
            except Exception:
                pass  # Ignore cleanup errors
    
    async def _check_victory_condition(self):
        """Check if victory condition is met and send goal completion to server."""
        if self.victory_sent:
            return
            
        if not hasattr(self, 'slot_data') or not self.slot_data:
            return
            
        # Get goal settings from slot data (player's YAML configuration)
        goal = self.slot_data.get("goal", "complete_specific_count")
        required_count = self.slot_data.get("shrine_count_required", 2)
        total_shrines = len(self.slot_data.get("active_shrines", []))
        
        victory_achieved = False
        
        if goal == "complete_all_shrines":
            victory_achieved = self.shrines_completed >= total_shrines
            required_for_display = total_shrines
        else:  # complete_specific_count
            victory_achieved = self.shrines_completed >= required_count
            required_for_display = required_count
            
        if victory_achieved:
            logger.info(f"🎉 VICTORY! Completed {self.shrines_completed} shrines (required: {required_for_display})")
            logger.info("🎉 Sending goal completion to Archipelago server!")
            
            # Import ClientStatus and send goal completion message
            from NetUtils import ClientStatus
            await self.send_msgs([{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}])
            
            logger.info("🎉 VICTORY! Oblivion Remastered completed!")
            self.victory_sent = True
    
    async def disconnect(self, allow_autoreconnect: bool = False):
        """Handle disconnection from server."""
        # Stop the game monitoring loop
        if hasattr(self, 'game_loop_task') and self.game_loop_task and not self.game_loop_task.done():
            self.game_loop_task.cancel()
        
        self._cleanup_files()
        await super().disconnect(allow_autoreconnect)
            
    async def _run_game_loop(self):
        """Main game monitoring loop - checks for location completions."""
        try:
            while not self.exit_event.is_set():
                # Check if we're still connected
                if not (hasattr(self, 'slot_data') and self.slot_data):
                    break
                    
                await self._check_for_locations()
                await asyncio.sleep(0.1)  # Standard polling interval
        except asyncio.CancelledError:
            logger.info("Game loop cancelled")
        except Exception as e:
            logger.error(f"Game loop error: {e}")
        finally:
            logger.info("Game loop ended")


    def run_gui(self):
        """Launch the client with GUI."""
        from kvui import GameManager
        
        class OblivionManager(GameManager):
            logging_pairs = [
                ("Client", "Archipelago")
            ]
            base_title = "Archipelago Oblivion Remastered Client"
        
        self.ui = OblivionManager(self)
        self.ui_task = asyncio.create_task(self.ui.async_run(), name="UI")


def launch():
    """Launch function for the launcher components."""
    async def main(args):
        ctx = OblivionContext(args.connect, args.password)
        ctx.server_task = asyncio.create_task(server_loop(ctx), name="ServerLoop")
        
        if gui_enabled:
            ctx.run_gui()
        ctx.run_cli()

        await ctx.exit_event.wait()
        ctx.server_address = None

        await ctx.shutdown()

    import colorama
    parser = get_base_parser(description="Oblivion Remastered Client, for use with Archipelago.")
    args, rest = parser.parse_known_args()
    colorama.just_fix_windows_console()
    asyncio.run(main(args))
    colorama.deinit()


if __name__ == '__main__':
    async def main(args):
        ctx = OblivionContext(args.connect, args.password)
        ctx.server_task = asyncio.create_task(server_loop(ctx), name="ServerLoop")

        if gui_enabled:
            ctx.run_gui()
        ctx.run_cli()
        
        await ctx.exit_event.wait()
        ctx.server_address = None

        await ctx.shutdown()

    import colorama
    parser = get_base_parser(description="Oblivion Remastered Client, for use with Archipelago.")
    args, rest = parser.parse_known_args()
    colorama.just_fix_windows_console()
    asyncio.run(main(args))
    colorama.deinit() 