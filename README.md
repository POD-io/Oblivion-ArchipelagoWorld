## Oblivion Remastered - Archipelago World

An Archipelago integration for **The Elder Scrolls IV: Oblivion Remastered**.

## Overview

This APWorld allows Oblivion Remastered to participate in Archipelago multiworld randomizers. Much content is now gated behind progression items that must be received from the multiworld. Your goals range from completing Daedric shrines, conquering the Arena, or closing Oblivion Gates, and can be configured to a length that suits your desired experience.

## How it Works

### Locked Content

Content in Oblivion Remastered is now gated behind progression items that must be received from the multiworld:

#### Daedric Shrine Access
The Daedra lords will no longer grant you access to their shrines without first receiving their blessing in the form of a Shrine Token.
Upon completion of their quest, you no longer receive their artifact, but instead a random item from the multiworld.
Each included shrine will have their artifact mixed into the pool of available items.
- **Requirement:** Shrine Unlock Tokens (e.g., "Azura Shrine Token")
- **Available:** Random shrines are selected from the 15 total Daedric shrines based on Shrine Count setting

#### Arena Questline
To take place in Arena matches, you must have received the corresponding Progressive Arena Rank item from the multiworld.
Each rank unlocks a group of 3 matches, which reward a random item from the multiworld.
- **Requirement:** Progressive Arena Rank items
- **Progression:** 7 ranks unlock matches in groups of 3

#### Oblivion Gate Access
To access Oblivion Gates, you must have received an Oblivion Gate Key item from the multiworld.
Closing a gate will award a random item from the multiworld.
- **Requirement:** Oblivion Gate Keys
- **Progression:** Each gate requires a key to access

#### Progressive Shop Stock / Shopsanity
Innkeepers around Cyrodiil have a series of key items that can be bought in exchange for gold.
These items are location checks that award a random item from the multiworld.
- **Requirement:** Progressive Shop Stock items
- **Progression:** 4 ranks unlock higher-value shop items:
  - **Set 1:** Always available (Value 1, 10, 100)
  - **Set 2:** Requires Progressive Shop Stock 1 (Value 2, 20, 200)
  - **Set 3:** Requires Progressive Shop Stock 2 (Value 3, 30, 300)
  - **Set 4:** Requires Progressive Shop Stock 3 (Value 4, 40, 400)
  - **Set 5:** Requires Progressive Shop Stock 4 (Value 5, 50, 500)

### Core Loop
1. **Receive progression items** from the multiworld to unlock content
2. **Complete location checks** by performing activities in-game  
3. **Send items to other players** when you complete checks
4. **Achieve your victory condition** to win

## Supported Locations

- **Daedric Shrine Quests**
- **Arena Matches**
- **Oblivion Gates**
- **Dungeon Clears**
- **Shop Items**
- **Skill Increases**

## Available Settings

### Goals
- **`shrine_seeker`:** Complete X Daedric Shrine quests
- **`arena`:** Complete all 21 Arena matches and become Grand Champion
- **`gatecloser`:** Close X Oblivion Gates

### Content Scaling
- **`gate_count`:** Number of Oblivion Gates available (0-10, 0 disables gates)
- **`shrine_count`:** Number of Daedric Shrine quests available (0-15, 0 disables shrines)
- **`arena_matches`:** Number of Arena matches available (0-21, 0 disables arena)
- **`shrine_goal`:** For Shrine Seeker goal: How many shrine quests needed for victory (1-15)
- **`skill_checks`:** Number of Skill Increase locations (10-30)
- **`dungeon_clears`:** Number of Dungeon Clear locations (0-30)

### Quality of Life
- **`extra_gate_keys`:** Additional Oblivion Gate Keys beyond required amount (0-5)
- **`gate_vision`:** How Oblivion Gate map markers are visible:
  - `on`: Visible immediately
  - `off`: Must be found (vanilla)
  - `item`: Visible when finding Oblivion Gate Vision item
- **`free_offerings`:** Automatically provide Daedric Shrine offering items when needed


## Technical Details

### Communication
File-based communication through `Documents/My Games/Oblivion Remastered/Saved/Archipelago/`

## Helpful Commands

### `/oblivion`
Displays current game status including:
- Items received and locations checked
- Available content counts (gates, shrines, arena matches, etc.)
- Gate key information
- Configured Goal

### `/dungeons`
Lists all 149 valid dungeons that can be used for dungeon clear checks.

Examples:
- `/dungeons`                    # Shows all dungeons
- `/dungeons f`                  # Shows dungeons starting with F
- `/dungeons cave`               # Shows all dungeons containing "cave"
