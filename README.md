## Oblivion Remastered - Archipelago World

An Archipelago integration for **The Elder Scrolls IV: Oblivion Remastered**.  
**Requires:** [Oblivion-ArchipelagoMod](https://github.com/POD-io/Oblivion-ArchipelagoMod) and APWorld **0.5.0**.

[Download Latest Release](https://github.com/POD-io/Oblivion-ArchipelagoWorld/releases/latest)  

## Overview

This APWorld integrates Oblivion Remastered into the Archipelago multiworld system. Daedric shrines, Oblivion gates, the Arena, dungeons, shops, classes, and more unlock as you receive progression items from other players. Configure which content appears in each seed, pick a victory goal, and scale from small curated runs to a full Cyrodiil marathon.

## How it Works

Most vanilla content is gated behind multiworld items. Receive progression, complete the activity in-game, send checks to other players, and complete your goal.

| System | Gated by | Checks |
|--------|----------|--------|
| Main Quest | Story progression items | Quests and milestones |
| Daedric Shrines | Shrine Unlock Tokens | Shrine quests |
| Arena | Progressive Arena Rank | Match wins |
| Oblivion Gates | Oblivion Gate Keys | Gate closures |
| Shops | Progressive Shop Stock | Buy key items from innkeepers |
| Regions & Dungeons | Region Access | Clear the dungeons in each region |
| Class | Progressive Class Level | Class skill increases |

## Supported Locations

- **Main Questline**
- **Daedric Shrine Quests**
- **Arena Matches**
- **Oblivion Gates**
- **Dungeon Clears**
- **Shop Items**
- **Class Skill Increases**
- **Sidequests**
- **Nirnroot harvesting**
- **Dungeon & Overworld kills**

## Available Settings

### Goals
- **`light_the_dragonfires`:** Complete the main questline
- **`shrine_seeker`:** Complete X Daedric shrine quests
- **`arena`:** Become Grand Champion
- **`gatecloser`:** Close X Oblivion Gates
- **`dungeon_delver`:** Clear all selected dungeons
- **`nirnsanity`:** Collect X Nirnroots from the multiworld
- **`treasure_hunter`:** Reach a specified gold total

### Content Scaling
- **`gate_count`:** Number of Oblivion Gates available (0-20, 0 disables gates)
- **`shrine_count`:** Number of Daedric Shrine quests available (0-15, 0 disables shrines)
- **`arena_matches`:** Number of Arena matches available (0-21, 0 disables arena)
- **`shrine_goal`:** For Shrine Seeker goal: How many shrine quests needed for victory (1-15)
- **`region_unlocks`:** Number of regions that appear as unlock items (0-10, you start with one region)
- **`dungeons_per_region`:** Maximum dungeons selected per unlocked region (0-24)
- **`wealth_sidequest_count` / `exploration_sidequest_count`:** Sidequests added to the seed (0–10 / 0–5)
- **`dungeon_kills` / `overworld_kills`:** Kill checks (0–200 each)
- **`nirnroot_count`:** Nirnroot harvesting checks (0–100)

### Class System
- **`class_selection`:** Choose your character class (default: Random Class)
  - **`off`:** No class location checks
  - **`random_class`:** Randomly select a class
  - **Specific classes:** Acrobat, Agent, Archer, Assassin, Barbarian, Bard, Battlemage, Crusader, Healer, Knight, Mage, Monk, Nightblade, Pilgrim, Rogue, Scout, Sorcerer, Spellsword, Thief, Warrior, Witchhunter
- **`class_level_maximum`:** Max progressive class levels (1-5, default 3)
  - Each level provides 14 additional skill checks (2 per class skill)
- **`start_with_class`:** Start with first class level unlocked (default: Off)
  - When false, you must receive the first Progressive Class Level from the multiworld
- **`excluded_skills`:** Exclude specific skills from generating checks

### Quality of Life
- **`extra_gate_keys`:** Additional Oblivion Gate Keys beyond required amount (0-5, default 0)
  - Useful for increased routing flexibility
- **`gate_vision`:** How Oblivion Gate map markers are visible (default: Item)
  - **`on`:** Visible immediately
  - **`off`:** Must be found (vanilla behavior)
  - **`item`:** Visible when finding Oblivion Gate Vision item
- **`free_offerings`:** Automatically provide Daedric Shrine offering items when needed (default: On)
- **`fast_travel_item`:** Lock fast travel until item is received (default: Off)
- **`dungeon_marker_mode`:** Control dungeon map markers (default: Reveal and Fast Travel)
  - **`reveal_and_fast_travel`:** All selected dungeon markers revealed and fast travel enabled
  - **`reveal_only`:** Dungeon markers shown as "rumors" (faded), must venture to them normally
- **`shop_scout_type`:** How shop item information is displayed (default: Summary)
  - **`off`:** No shop scouting information displayed
  - **`summary`:** Shows receiving player name and item classification (Progression/Useful/Filler)
  - **`player_only`:** Shows only the receiving player name
  - **`full_info`:** Shows complete item name and receiving player
- **`fast_arena`:** Skip arena announcer dialogue and fight immediately
- **`auto_tracking`:** Guide the player to nearby boss chests or nirnroot. Press **F11** in-game to manually toggle the mode
- **`silent_auto_tracking`:** Hide in-game tracking messages, track via quest marker only

### Traps
- **`trap_percentage`:** Amount of filler slots replaced by traps
- Current trap types: Movement / Storm / Spawn

### Deathlink
Uses Archipelago’s standard **`death_link`** option. When enabled, a player death can trigger deaths for others who also have deathlink on.

## Technical Details

### Communication
The Archipelago client and Oblivion Remastered mod communicate through shared files in the game's save directory. The client writes session data and item information to files, which the mod reads to synchronize your game state with the multiworld.

**Windows:** `C:\Users\<username>\Documents\My Games\Oblivion Remastered\Saved\Archipelago\`

**Linux:** The client auto-detects your Proton prefix by searching common Steam library locations (standard, Flatpak, Snap, and custom mount points). The detected path is displayed when you connect. If auto-detection fails, use `/set_save_path` to manually specify the directory. You can also create `path_override.txt` in the default `Saved/Archipelago/` folder (one line with your custom path) to redirect where the client reads and writes Archipelago files.

### Session Management
Each Archipelago seed generates a unique session ID, which is used to distinguish separate playthroughs. When the Oblivion client connects, it uses this session ID to create and manage settings and progress tracking for that specific session. 
This ensures that multiple games can be played on the same system without conflicts.

## Helpful Commands

### `/oblivion`
Displays current game status including:
- Items received and locations checked
- Available content counts (gates, shrines, arena matches, etc.)
- Gate key information
- Configured Goal
- Region progress, sidequests, nirnroot/gold/kill progress when enabled

### `/set_save_path <path>`
Manually set the Oblivion save path if auto-detection fails.
- Example: `/set_save_path ~/.local/share/Steam/steamapps/compatdata/2623190/pfx/drive_c/users/steamuser/Documents/My Games/Oblivion Remastered/Saved`
- Can end with `/Saved` or `/Saved/Archipelago` - the client will append `/Archipelago` if needed
- Path is expanded (supports `~` for home directory)
