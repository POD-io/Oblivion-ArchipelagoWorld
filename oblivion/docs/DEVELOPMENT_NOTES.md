# Development Notes - Oblivion Remastered APWorld

### ID Range Assignment Required

This APWorld currently uses placeholder IDs that need official assignment:

- **BASE_ITEM_ID:** Currently `4000000` in `Items.py` line 11
- **BASE_LOCATION_ID:** Currently `4000000` in `Locations.py` line 13

These need to be updated to the officially assigned ID range before merging into main Archipelago.

### ID Usage Summary
- **Item IDs:** 29 items total (15 shrine tokens + 14 artifacts + variable filler items)
- **Location IDs:** 15 locations (shrine quest completions) + 1 Victory event location

## Code Architecture

### File-Based Communication
The integration uses a file-based communication system instead of memory hooks.

**Advantages:**
- Works with UE4SS Lua scripting
- No need for complex memory manipulation

**File Types:**
- `*_items.txt`: Item queue from Archipelago to game
- `*_completed.txt`: Location completion from game to Archipelago
- `*_settings.txt`: Configuration data
- `current_session.txt`: Session management

### Session Management
Each connection gets a unique session ID to prevent file conflicts:
- Format: `AP_{PlayerName}_{SessionID}_{FileType}.txt`
- Automatic cleanup of old sessions (keeps 3 most recent)
- Safe for multiple AP world runs on same computer

### Known Limitations

### Current Constraints
- **Windows Only:** File paths assume Windows directory structure
- **UE4SS Dependency:** Requires specific modding framework
- **File Polling:** Not real-time (100ms polling interval)
- **No Save State Integration:** Doesn't interact with game saves