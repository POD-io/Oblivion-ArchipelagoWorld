# Oblivion Remastered Setup Guide

## Required Software

- **Oblivion Remastered** (PC version)
- **UE4SS (Unreal Engine 4 Scripting System)** 
- **Archipelago** (latest version)

## Installation Steps

### 1. Install UE4SS

1. Download UE4SS from the official repository
2. Extract UE4SS files to your Oblivion Remastered installation directory

### 2. Install Archipelago Oblivion Mod & Requirements

1. Download the Archipelago Oblivion Mod from [To do]
2. Extract the mod files to your Oblivion Remastered installation directory
3. Ensure the mod folder structure is: `ue4ss/mods/Archipelago/Scripts/main.lua`

Note: ue4ss mods are currently manual installs on Nexus Mods, you can not manage with the mod manager. Steps 2 & 3 above are critical.

### 3. Configure Your Archipelago YAML

Create a YAML file with your settings:

```yaml
description: "Oblivion Remastered - Your Name"
name: YourName

oblivion_remastered:
  goal: complete_specific_count        # or complete_all_shrines  
  shrine_count_required: 10           # Number of shrines to complete
  total_active_shrines: 12            # Total shrines available
  free_offerings: true                # Auto-provide shrine offerings
  useful_items_weight: 2              # Higher = more useful items
```

### 4. Generate and Connect

1. Upload your YAML to the Archipelago website or use the local generator
2. Download your generated game files
3. Launch the Oblivion Remastered Client from Archipelago
4. Connect using your server details
5. Launch Oblivion Remastered

## Verification

To verify everything is working:

1. **Check Files:** `Documents/My Games/Oblivion Remastered/Saved/Archipelago/` should contain connection files
2. **Check Client:** Archipelago client should show "Connected" status


### Victory Conditions
- `complete_specific_count`: Flexible victory (complete X out of Y shrines)
- `complete_all_shrines`: Must complete every shrine