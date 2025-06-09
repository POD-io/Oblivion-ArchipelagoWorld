# Oblivion Remastered - Archipelago World

An Archipelago integration for **The Elder Scrolls IV: Oblivion Remastered**.

## What is this?

This APWorld allows Oblivion Remastered to participate in Archipelago multiworld randomizers. Complete Daedric shrine quests to send items to other players, while receiving helpful items and shrine unlock tokens from the multiworld.

## Game Information

- **Game:** The Elder Scrolls IV: Oblivion Remastered  
- **Platform:** PC (Windows) with Unreal Engine 4 SS (UE4SS) mod support
- **Archipelago Protocol:** File-based communication through save directory

## How it Works

### Core Gameplay Loop
1. Receive **Shrine Tokens** from the multiworld to unlock specific Daedric shrine quests
2. Complete shrine quests by gathering offerings and fulfilling quest requirements  
3. Quest completion sends location checks to Archipelago and provides items to other players
4. Continue until you've completed enough shrines to achieve victory

### What Gets Randomized
- **Locations:** 15 Daedric shrine quest completions (Azura, Boethia, Clavicus Vile, etc.)
- **Items Sent:** Shrine unlock tokens, Daedric artifacts, useful consumables, magic scrolls
- **Victory Condition:** Complete a configurable number of shrine quests

## Setup Requirements

### Prerequisites
- Oblivion Remastered (Steam version)
- UE4SS
- Archipelago Oblivion mod installed in UE4SS mods directory

## Configuration Options

Configure these in your Archipelago YAML file:

### Goal Settings
```yaml
oblivion_remastered:
  goal: complete_specific_count        # or complete_all_shrines
  shrine_count_required: 10           # Number of shrines to complete for victory
  total_active_shrines: 12            # Total shrines available in this seed
```

### Quality of Life
```yaml
  free_offerings: true                # Auto-provide shrine offering items
  useful_items_weight: 2              # Higher = more useful items vs scrolls
```

### Goal Types Explained
- **`complete_specific_count`:** Complete X shrines out of Y available (most common)
- **`complete_all_shrines`:** Complete all shrines that spawn (ignores shrine_count_required)

### Progression Difficulty
Shrines are organized into tiers that unlock as you complete others:
- **Tier 1 (immediate):** Azura, Meridia, Namira, Sanguine
- **Tier 2 (1+ shrine):** Nocturnal, Hircine, Malacath, Peryite  
- **Tier 3 (3+ shrines):** Boethia, Mephala, Clavicus Vile, Vaermina
- **Tier 4 (5+ shrines):** Molag Bal
- **Tier 5 (7+ shrines):** Hermaeus Mora, Sheogorath

## Technical Implementation

### Communication Method
- **File-based:** Uses text files in `Documents/My Games/Oblivion Remastered/Saved/Archipelago/`


### Key Components

#### APWorld Core
- **`__init__.py`:** Main world definition, item/location creation, victory conditions
- **`Client.py`:** Archipelago client for communication with game
- **`Items.py`:** Item definitions (shrine tokens, artifacts, consumables)
- **`Locations.py`:** Location definitions (shrine quest completions)
- **`Options.py`:** Player-configurable settings
- **`Rules.py`:** Logic rules (shrine access requirements)
- **`ShrineProgression.py`:** Shrine selection and progression logic

#### Game Integration
- **UE4SS Lua mod:** In-game hooks for quest completion detection and item delivery
- **File monitoring:** Real-time communication between client and game
- **Console integration:** Item delivery via Oblivion console commands

### Item Categories

#### Progression Items (Required)
- **Shrine Tokens:** Unlock access to specific Daedric shrine quests
- Example: "Azura Shrine Token", "Sheogorath Shrine Token"

#### Useful Items (High Value)
- **Daedric Artifacts:** Powerful weapons and items from vanilla Oblivion
- Example: "Azura's Star", "Wabbajack", "Volendrung"

#### Filler Items (Common)
- **Potions:** Health, magicka, and stamina restoration
- **Magic Scrolls:** Summoning, bound weapons, damage spells