"""Bounty contract generation"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Set

MAX_BOUNTIES = 20

# Not used as bounty sites. Quest-locked, key-gated, or MQ.
SKIP_DUNGEONS = {
    # Main Quest
    "Miscarcand",
    "Lake Arrius Caverns",
    "Sancre Tor",
    "The Old Way",
    "Fort Sutch",
    # Daedric, guild, unique, or DLC quests
    "Fort Pale Pass",
    "Fort Farragut",
    "Fort Blueblood",
    "Fort Ontus",
    "Fort Bulwark",
    "Vahtacen",
    "Nenyond Twyll",
    "Wellspring Cave",
    "Echo Cave",
    "Silorn",
    "Malada",
    "Bloodcrust Cavern",
    "Memorial Cave",
    "Redwater Slough",
    "Sundercliff Watch",
    "Amelion Tomb",
    "Bleak Flats Cave",
    "Fathis Aren's Tower",
    "Temple of the Ancestor Moths",
    "Beldaburo",
    "Crowhaven",
    "Lost Boy Cavern",
    "Mingo Cave",
    "Leafrot Cave",
    "Redguard Valley Cave",
    # Goblin Trouble / early quest caves
    "Desolate Mine",
    "Forsaken Mine",
    "Bleak Mine",
    "Cracked Wood Cave",
    "Timberscar Hollow",
    # Keyed or empty until a quest fills them
    "Gutted Mine",
    "Hrota Cave",
    # Imperial City interiors
    "Talos Plaza Sewers",
    "The Elven Garden Sewers",
}

# Extra map-marker EDIDs (not in the seed dungeon ShowMap table).
BOUNTY_MAP_MARKERS = {
    "Abandoned Mine": "AbandonedMineMapMarker",
    "Exhausted Mine": "ExhaustedMineMapMarker",
    "Fort Flecia": "FortFleciaMapMarker",
    "Infested Mine": "InfestedMineMapMarker",
    "Barren Cave": "BarrenCaveMapMarker",
    "Goblin Jim's Cave": "GoblinJimsCaveMapMarker",
    "Derelict Mine": "DerelictMineMapMarker",
    "Barren Mine": "BarrenMineMapMarker",
    "Plundered Mine": "PlunderedMineMapMarker",
    "Squandered Mine": "SquanderedMineMapMarker",
    "Fort Irony": "FortIronyMapMarker",
    "Fort Strand": "FortStrandMapMarker",
    "Shattered Mine": "ShatteredMineMapMarker",
    "Shattered Scales Cave": "ShatteredScalesCaveMapMarker",
}

_LUA_MARKER_CACHE: Optional[Dict[str, str]] = None


def _load_lua_markers() -> Dict[str, str]:
    """Merge extra bounty markers with the Lua ShowMap table when the mod is nearby."""
    global _LUA_MARKER_CACHE
    if _LUA_MARKER_CACHE is not None:
        return _LUA_MARKER_CACHE
    markers = dict(BOUNTY_MAP_MARKERS)
    lua_path = os.path.normpath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "Oblivion-ArchipelagoMod",
            "ArchipelagoBridge",
            "Scripts",
            "ArchipelagoConfig.lua",
        )
    )
    if os.path.isfile(lua_path):
        in_table = False
        with open(lua_path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if "dungeonMapMarkers" in line and "{" in line:
                    in_table = True
                    continue
                if in_table:
                    if line.strip().startswith("}"):
                        break
                    match = re.search(r'\["([^"]+)"\]\s*=\s*"([^"]+)"', line)
                    if match:
                        markers[match.group(1)] = match.group(2)
    _LUA_MARKER_CACHE = markers
    return markers


def marker_for(dungeon: str, explicit: str = "") -> str:
    if explicit:
        return explicit
    return _load_lua_markers().get(dungeon, "")

NAMED_BOUNTIES = [
    {
        "dungeon": "Goblin Jim's Cave",
        "display": "Goblin Jim",
        "bp": "BP_GoblinJim_C",
        "marker": "GoblinJimsCaveMapMarker",
    },
    {
        "dungeon": "Derelict Mine",
        "display": "Sharp Tooth War Chief",
        "bp": "BP_Goblin_TribeLeaderG_C",
        "marker": "DerelictMineMapMarker",
    },
    {
        "dungeon": "Barren Mine",
        "display": "Dust Eater War Chief",
        "bp": "BP_Goblin_TribeLeaderE_C",
        "marker": "BarrenMineMapMarker",
    },
    {
        "dungeon": "Plundered Mine",
        "display": "Three Feather War Chief",
        "bp": "BP_Goblin_TribeLeader",
        "marker": "PlunderedMineMapMarker",
    },
    {
        "dungeon": "Fort Strand",
        "display": "Bjalfi the Contemptible",
        "bp": "BP_BjalfitheContemptible_C",
        "marker": "FortStrandMapMarker",
    },
]

WILDLIFE_HUNTS = [
    {
        "display": "Hunt: Deer",
        "target": "BP_DeerDoe_C,BP_DeerBuck_C",
        "cull": 6,
    },
    {
        "display": "Hunt: Mudcrab",
        "target": "BP_Generic_Mudcrab_C",
        "cull": 8,
    },
]

# Boss contracts are NPC *boss EDIDs and Vampire Patriarchs.
NPC_BOSS_TYPES = {"Bandit", "Marauder", "Necromancer", "Conjurer", "Vampire"}

# Occupant counts for bounty rolls. Includes caves that are not AP dungeon checks for this seed.
# Boss contracts need bosses >= 1. Cull contracts need enough enemies (including 0-boss caves).

DUNGEON_OCCUPANTS = {
    "Abandoned Mine": {"type": "Bandit", "enemies": 8, "bosses": 1},
    "Amelion Tomb": {"type": "Undead", "enemies": 4, "bosses": 1},
    "Anutwyll": {"type": "Monster", "enemies": 7, "bosses": 1},
    "Arrowshaft Cavern": {"type": "Monster", "enemies": 5, "bosses": 1},
    "Atatar": {"type": "Bandit", "enemies": 9, "bosses": 0},
    "Barren Cave": {"type": "Vampire", "enemies": 4, "bosses": 2},
    "Barren Mine": {"type": "Goblin", "enemies": 6, "bosses": 0},
    "Bawn": {"type": "Undead", "enemies": 11, "bosses": 1},
    "Belda": {"type": "Conjurer", "enemies": 4, "bosses": 1},
    "Beldaburo": {"type": "Conjurer", "enemies": 5, "bosses": 1},
    "Belletor's Folly": {"type": "Bandit", "enemies": 21, "bosses": 0},
    "Black Rock Caverns": {"type": "Bandit", "enemies": 4, "bosses": 1},
    "Bleak Flats Cave": {"type": "Undead", "enemies": 7, "bosses": 0},
    "Bleak Mine": {"type": "Bandit", "enemies": 6, "bosses": 0},
    "Bloodcrust Cavern": {"type": "Vampire", "enemies": 10, "bosses": 0},
    "Bloodrun Cave": {"type": "Necromancer", "enemies": 5, "bosses": 1},
    "Bramblepoint Cave": {"type": "Monster", "enemies": 20, "bosses": 1},
    "Breakneck Cave": {"type": "Monster", "enemies": 0, "bosses": 1},
    "Broken Promises Cave": {"type": "Bandit", "enemies": 8, "bosses": 0},
    "Capstone Cave": {"type": "Bandit", "enemies": 10, "bosses": 0},
    "Ceyatatar": {"type": "Conjurer", "enemies": 0, "bosses": 1},
    "Charcoal Cave": {"type": "Bandit", "enemies": 7, "bosses": 1},
    "Collapsed Mine": {"type": "Bandit", "enemies": 13, "bosses": 0},
    "Cracked Wood Cave": {"type": "Goblin", "enemies": 12, "bosses": 0},
    "Crayfish Cave": {"type": "Monster", "enemies": 22, "bosses": 3},
    "Crowhaven": {"type": "Vampire", "enemies": 0, "bosses": 1},
    "Crumbling Mine": {"type": "Bandit", "enemies": 6, "bosses": 1},
    "Culotte": {"type": "Undead", "enemies": 6, "bosses": 0},
    "Cursed Mine": {"type": "Bandit", "enemies": 25, "bosses": 1},
    "Dark Fissure": {"type": "Necromancer", "enemies": 12, "bosses": 1},
    "Dasek Moor": {"type": "Marauder", "enemies": 6, "bosses": 1},
    "Derelict Mine": {"type": "Goblin", "enemies": 23, "bosses": 0},
    "Deserted Mine": {"type": "Monster", "enemies": 16, "bosses": 1},
    "Desolate Mine": {"type": "Goblin", "enemies": 9, "bosses": 1},
    "Doomed Mine": {"type": "Bandit", "enemies": 8, "bosses": 0},
    "Dzonot Cave": {"type": "Bandit", "enemies": 5, "bosses": 1},
    "Echo Cave": {"type": "Necromancer", "enemies": 11, "bosses": 1},
    "Echo Mine": {"type": "Bandit", "enemies": 8, "bosses": 0},
    "Elenglynn": {"type": "Necromancer", "enemies": 1, "bosses": 1},
    "Exhausted Mine": {"type": "Goblin", "enemies": 26, "bosses": 1},
    "Fallen Rock Cave": {"type": "Undead", "enemies": 13, "bosses": 0},
    "Fanacas": {"type": "Vampire", "enemies": 4, "bosses": 1},
    "Fanacasecul": {"type": "Undead", "enemies": 5, "bosses": 1},
    "Fatback Cave": {"type": "Goblin", "enemies": 21, "bosses": 1},
    "Fathis Aren's Tower": {"type": "Conjurer", "enemies": 1, "bosses": 1},
    "Felgageldt Cave": {"type": "Bandit", "enemies": 8, "bosses": 0},
    "Fieldhouse Cave": {"type": "Conjurer", "enemies": 0, "bosses": 1},
    "Fingerbowl Cave": {"type": "Undead", "enemies": 11, "bosses": 2},
    "Forsaken Mine": {"type": "Monster", "enemies": 9, "bosses": 0},
    "Fort Alessia": {"type": "Marauder", "enemies": 7, "bosses": 1},
    "Fort Ash": {"type": "Goblin", "enemies": 8, "bosses": 1},
    "Fort Black Boot": {"type": "Conjurer", "enemies": 1, "bosses": 1},
    "Fort Blueblood": {"type": "Marauder", "enemies": 12, "bosses": 1},
    "Fort Bulwark": {"type": "Conjurer", "enemies": 10, "bosses": 2},
    "Fort Carmala": {"type": "Vampire", "enemies": 1, "bosses": 1},
    "Fort Cedrian": {"type": "Marauder", "enemies": 7, "bosses": 1},
    "Fort Chalman": {"type": "Undead", "enemies": 4, "bosses": 1},
    "Fort Coldcorn": {"type": "Monster", "enemies": 3, "bosses": 1},
    "Fort Cuptor": {"type": "Necromancer", "enemies": 6, "bosses": 0},
    "Fort Dirich": {"type": "Undead", "enemies": 4, "bosses": 1},
    "Fort Doublecross": {"type": "Necromancer", "enemies": 12, "bosses": 0},
    "Fort Empire": {"type": "Monster", "enemies": 7, "bosses": 2},
    "Fort Entius": {"type": "Conjurer", "enemies": 1, "bosses": 1},
    "Fort Facian": {"type": "Undead", "enemies": 7, "bosses": 2},
    "Fort Farragut": {"type": "Undead", "enemies": 6, "bosses": 0},
    "Fort Flecia": {"type": "Goblin", "enemies": 4, "bosses": 1},
    "Fort Gold-Throat": {"type": "Goblin", "enemies": 3, "bosses": 1},
    "Fort Hastrel": {"type": "Vampire", "enemies": 1, "bosses": 1},
    "Fort Homestead": {"type": "Marauder", "enemies": 7, "bosses": 1},
    "Fort Horunn": {"type": "Monster", "enemies": 14, "bosses": 1},
    "Fort Irony": {"type": "Goblin", "enemies": 8, "bosses": 0},
    "Fort Istirus": {"type": "Necromancer", "enemies": 14, "bosses": 1},
    "Fort Linchal": {"type": "Necromancer", "enemies": 13, "bosses": 1},
    "Fort Magia": {"type": "Undead", "enemies": 9, "bosses": 1},
    "Fort Naso": {"type": "Vampire", "enemies": 1, "bosses": 1},
    "Fort Nikel": {"type": "Bandit", "enemies": 4, "bosses": 0},
    "Fort Nomore": {"type": "Monster", "enemies": 10, "bosses": 1},
    "Fort Ontus": {"type": "Necromancer", "enemies": 14, "bosses": 0},
    "Fort Pale Pass": {"type": "Undead", "enemies": 24, "bosses": 1},
    "Fort Rayles": {"type": "Conjurer", "enemies": 1, "bosses": 2},
    "Fort Redman": {"type": "Vampire", "enemies": 4, "bosses": 1},
    "Fort Redwater": {"type": "Vampire", "enemies": 1, "bosses": 1},
    "Fort Scinia": {"type": "Marauder", "enemies": 5, "bosses": 0},
    "Fort Strand": {"type": "Marauder", "enemies": 7, "bosses": 1},
    "Fort Sutch": {"type": "Marauder", "enemies": 11, "bosses": 0},
    "Fort Teleman": {"type": "Necromancer", "enemies": 7, "bosses": 1},
    "Fort Urasek": {"type": "Goblin", "enemies": 7, "bosses": 1},
    "Fort Variela": {"type": "Necromancer", "enemies": 9, "bosses": 0},
    "Fort Virtue": {"type": "Undead", "enemies": 7, "bosses": 1},
    "Fort Wariel": {"type": "Marauder", "enemies": 5, "bosses": 1},
    "Fort Wooden Hand": {"type": "Marauder", "enemies": 9, "bosses": 1},
    "Fyrelight Cave": {"type": "Monster", "enemies": 13, "bosses": 0},
    "Garlas Agea": {"type": "Necromancer", "enemies": 6, "bosses": 1},
    "Goblin Jim's Cave": {"type": "Goblin", "enemies": 20, "bosses": 0},
    "Grayrock Cave": {"type": "Monster", "enemies": 16, "bosses": 0},
    "Greenmead Cave": {"type": "Monster", "enemies": 15, "bosses": 0},
    "Gutted Mine": {"type": "Vampire", "enemies": 5, "bosses": 0},
    "Hame": {"type": "Necromancer", "enemies": 5, "bosses": 1},
    "Haunted Mine": {"type": "Goblin", "enemies": 11, "bosses": 0},
    "Haynote Cave": {"type": "Monster", "enemies": 10, "bosses": 0},
    "Horn Cave": {"type": "Bandit", "enemies": 12, "bosses": 0},
    "Howling Cave": {"type": "Necromancer", "enemies": 9, "bosses": 0},
    "Hrota Cave": {"type": "Monster", "enemies": 7, "bosses": 1},
    "Hrotanda Vale": {"type": "Bandit", "enemies": 12, "bosses": 1},
    "Infested Mine": {"type": "Marauder", "enemies": 20, "bosses": 1},
    "Kemen": {"type": "Undead", "enemies": 12, "bosses": 0},
    "Kindred Cave": {"type": "Necromancer", "enemies": 14, "bosses": 1},
    "Kingscrest Cavern": {"type": "Monster", "enemies": 21, "bosses": 0},
    "Leafrot Cave": {"type": "Undead", "enemies": 5, "bosses": 0},
    "Lindai": {"type": "Undead", "enemies": 14, "bosses": 1},
    "Lipsand Tarn": {"type": "Vampire", "enemies": 11, "bosses": 1},
    "Lost Boy Cavern": {"type": "Undead", "enemies": 9, "bosses": 1},
    "Mackamentain": {"type": "Necromancer", "enemies": 2, "bosses": 1},
    "Malada": {"type": "Undead", "enemies": 10, "bosses": 1},
    "Memorial Cave": {"type": "Vampire", "enemies": 12, "bosses": 1},
    "Mingo Cave": {"type": "Monster", "enemies": 5, "bosses": 0},
    "Miscarcand": {"type": "Undead", "enemies": 30, "bosses": 1},
    "Mongrel's Tooth Cave": {"type": "Monster", "enemies": 8, "bosses": 0},
    "Morahame": {"type": "Monster", "enemies": 7, "bosses": 0},
    "Moranda": {"type": "Monster", "enemies": 16, "bosses": 0},
    "Moss Rock Cavern": {"type": "Necromancer", "enemies": 4, "bosses": 2},
    "Nagastani": {"type": "Monster", "enemies": 9, "bosses": 1},
    "Narfinsel": {"type": "Monster", "enemies": 8, "bosses": 1},
    "Nenalata": {"type": "Undead", "enemies": 18, "bosses": 1},
    "Nenyond Twyll": {"type": "Necromancer", "enemies": 6, "bosses": 1},
    "Newt Cave": {"type": "Monster", "enemies": 10, "bosses": 0},
    "Niryastare": {"type": "Undead", "enemies": 9, "bosses": 1},
    "Nisin Cave": {"type": "Monster", "enemies": 5, "bosses": 0},
    "Nonungalo": {"type": "Monster", "enemies": 15, "bosses": 1},
    "Nonwyll Cavern": {"type": "Monster", "enemies": 13, "bosses": 0},
    "Nornal": {"type": "Undead", "enemies": 8, "bosses": 1},
    "Nornalhorst": {"type": "Vampire", "enemies": 3, "bosses": 2},
    "Ondo": {"type": "Monster", "enemies": 5, "bosses": 1},
    "Onyx Caverns": {"type": "Bandit", "enemies": 14, "bosses": 1},
    "Outlaw Endre's Cave": {"type": "Bandit", "enemies": 11, "bosses": 0},
    "Pillaged Mine": {"type": "Goblin", "enemies": 19, "bosses": 0},
    "Piukanda": {"type": "Undead", "enemies": 16, "bosses": 2},
    "Plundered Mine": {"type": "Goblin", "enemies": 18, "bosses": 0},
    "Pothole Caverns": {"type": "Necromancer", "enemies": 7, "bosses": 0},
    "Quickwater Cave": {"type": "Monster", "enemies": 7, "bosses": 0},
    "Redguard Valley Cave": {"type": "Monster", "enemies": 7, "bosses": 1},
    "Redwater Slough": {"type": "Vampire", "enemies": 3, "bosses": 1},
    "Reedstand Cave": {"type": "Monster", "enemies": 7, "bosses": 1},
    "Rickety Mine": {"type": "Bandit", "enemies": 13, "bosses": 1},
    "Rielle": {"type": "Undead", "enemies": 17, "bosses": 1},
    "Robber's Glen Cave": {"type": "Monster", "enemies": 12, "bosses": 1},
    "Rock Bottom Caverns": {"type": "Goblin", "enemies": 8, "bosses": 1},
    "Rockmilk Cave": {"type": "Bandit", "enemies": 14, "bosses": 2},
    "Sage Glen Hollow": {"type": "Conjurer", "enemies": 0, "bosses": 1},
    "Sancre Tor": {"type": "Marauder", "enemies": 31, "bosses": 0},
    "Sandstone Cavern": {"type": "Monster", "enemies": 8, "bosses": 0},
    "Sardavar Leed": {"type": "Conjurer", "enemies": 6, "bosses": 1},
    "Sedor": {"type": "Monster", "enemies": 7, "bosses": 0},
    "Sercen": {"type": "Bandit", "enemies": 5, "bosses": 1},
    "Serpent Hollow Cave": {"type": "Monster", "enemies": 10, "bosses": 1},
    "Serpent's Trail": {"type": "Monster", "enemies": 4, "bosses": 0},
    "Shadow's Rest Cavern": {"type": "Monster", "enemies": 8, "bosses": 0},
    "Shattered Mine": {"type": "Bandit", "enemies": 16, "bosses": 0},
    "Shattered Scales Cave": {"type": "Monster", "enemies": 18, "bosses": 0},
    "Shinbone Cave": {"type": "Goblin", "enemies": 14, "bosses": 0},
    "Sideways Cave": {"type": "Monster", "enemies": 12, "bosses": 2},
    "Silorn": {"type": "Necromancer", "enemies": 14, "bosses": 1},
    "Silver Tooth Cave": {"type": "Goblin", "enemies": 23, "bosses": 1},
    "Sinkhole Cave": {"type": "Bandit", "enemies": 6, "bosses": 0},
    "Smoke Hole Cave": {"type": "Undead", "enemies": 21, "bosses": 1},
    "Squandered Mine": {"type": "Bandit", "enemies": 22, "bosses": 0},
    "Sundercliff Watch": {"type": "Vampire", "enemies": 20, "bosses": 1},
    "Swampy Cave": {"type": "Monster", "enemies": 15, "bosses": 0},
    "Talos Plaza Sewers": {"type": "Goblin", "enemies": 2, "bosses": 1},
    "Talwinque": {"type": "Bandit", "enemies": 17, "bosses": 1},
    "The Beast's Maw": {"type": "Monster", "enemies": 5, "bosses": 0},
    "The Elven Garden Sewers": {"type": "Bandit", "enemies": 5, "bosses": 0},
    "The Old Way": {"type": "Undead", "enemies": 51, "bosses": 1},
    "Timberscar Hollow": {"type": "Goblin", "enemies": 10, "bosses": 0},
    "Toadstool Hollow": {"type": "Undead", "enemies": 7, "bosses": 0},
    "Trumbe": {"type": "Undead", "enemies": 9, "bosses": 1},
    "Underpall Cave": {"type": "Necromancer", "enemies": 19, "bosses": 1},
    "Undertow Cavern": {"type": "Bandit", "enemies": 6, "bosses": 0},
    "Vahtacen": {"type": "Undead", "enemies": 10, "bosses": 1},
    "Varondo": {"type": "Conjurer", "enemies": 14, "bosses": 1},
    "Veyond": {"type": "Monster", "enemies": 21, "bosses": 0},
    "Vilverin": {"type": "Bandit", "enemies": 17, "bosses": 1},
    "Welke": {"type": "Undead", "enemies": 19, "bosses": 1},
    "Wellspring Cave": {"type": "Necromancer", "enemies": 6, "bosses": 0},
    "Wendelbek": {"type": "Necromancer", "enemies": 10, "bosses": 1},
    "Wenderbek Cave": {"type": "Goblin", "enemies": 8, "bosses": 1},
    "Wendir": {"type": "Undead", "enemies": 18, "bosses": 1},
    "Wenyandawik": {"type": "Undead", "enemies": 14, "bosses": 1},
    "Wind Cave": {"type": "Monster", "enemies": 35, "bosses": 1},
}


def cull_target(low: int) -> Optional[int]:
    if low < 4:
        return None
    if low >= 15:
        return low - 2
    return low - 1


def check_location_names(display: str, checks: int) -> List[str]:
    if checks <= 1:
        return [display]
    return [f"{display} ({n}/{checks})" for n in range(1, checks + 1)]


def location_names_for_index(index: int, checks: int) -> List[str]:
    return check_location_names(f"Bounty {index}", checks)


def all_bounty_location_names() -> List[str]:
    names: List[str] = []
    seen = set()

    def add(display: str, checks: int) -> None:
        for name in check_location_names(display, checks):
            if name not in seen:
                seen.add(name)
                names.append(name)

    for entry in NAMED_BOUNTIES:
        add(f"{entry['display']} ({entry['dungeon']})", 3)
    for entry in WILDLIFE_HUNTS:
        add(f"{entry['display']} ({entry['cull']})", 1)
    for dungeon, occ in DUNGEON_OCCUPANTS.items():
        occ_type = occ.get("type") or "Bandit"
        if occ_type in NPC_BOSS_TYPES and (occ.get("bosses") or 0) >= 1:
            add(occupant_boss_display(occ_type, dungeon), 3)
        target = cull_target(occ.get("enemies") or 0)
        if target:
            add(occupant_cull_display(occ_type, dungeon, target), 2)
    for dungeon in BOUNTY_MAP_MARKERS:
        if dungeon in DUNGEON_OCCUPANTS:
            continue
        add(occupant_cull_display("Bandit", dungeon, 6), 2)
    return names


def occupant_boss_display(occ_type: str, dungeon: str) -> str:
    """Occupant type is known at generation."""
    return f"{occ_type} Boss ({dungeon})"


def occupant_cull_display(occ_type: str, dungeon: str, count: int = 0) -> str:
    if occ_type == "Undead":
        plural = "Undead"
    elif occ_type.endswith("s"):
        plural = occ_type
    else:
        plural = occ_type + "s"
    if count > 0:
        return f"Cull {count} {plural} ({dungeon})"
    return f"Cull {plural} ({dungeon})"


def generate_bounties(
    random,
    count: int,
    selected_dungeons: List[str],
) -> List[Dict[str, Any]]:
    """Build contracts. selected_dungeons is this seed's dungeon-check list only.

    Bounties are a separate pool: any region, including DUNGEON_REGIONS caves that
    were not picked as checks. Block only this seed's selected dungeons plus SKIP_DUNGEONS.
    """
    if count <= 0:
        return []
    count = min(count, MAX_BOUNTIES)
    blocked: Set[str] = set(selected_dungeons) | SKIP_DUNGEONS
    occupants = DUNGEON_OCCUPANTS

    named_pool = [entry for entry in NAMED_BOUNTIES if entry["dungeon"] not in blocked]
    named_dungeons = {entry["dungeon"] for entry in named_pool}

    boss_pool = [
        {"name": name, **data}
        for name, data in occupants.items()
        if data["bosses"] >= 1
        and data.get("type") in NPC_BOSS_TYPES
        and name not in blocked
        and name not in named_dungeons
    ]
    cull_pool = [
        {"name": name, **data}
        for name, data in occupants.items()
        if cull_target(data["enemies"]) is not None and name not in blocked
    ]

    wildlife_pool = [dict(entry) for entry in WILDLIFE_HUNTS]
    used: Set[str] = set()
    contracts: List[Dict[str, Any]] = []

    # Adjust here if I want to weight a specific bounty type.
    tickets: List[Dict[str, Any]] = []
    for entry in named_pool:
        tickets.append({"kind": "named", "entry": entry})
    for row in boss_pool:
        tickets.append({"kind": "boss", "entry": row})
    for row in cull_pool:
        tickets.append({"kind": "cull", "entry": row})
    for extra_name, extra_marker in BOUNTY_MAP_MARKERS.items():
        if extra_name not in blocked and extra_name not in occupants:
            tickets.append({"kind": "extra", "entry": extra_name, "marker": extra_marker})
    if wildlife_pool:
        tickets.append({"kind": "wildlife"})

    def make_wildlife() -> Optional[Dict[str, Any]]:
        if not wildlife_pool:
            return None
        pick = wildlife_pool.pop(random.randrange(len(wildlife_pool)))
        wildlife_pool.clear()
        return {
            "type": "wildlife",
            "display": f"{pick['display']} ({pick['cull']})",
            "dungeon": "",
            "marker": "",
            "target": pick["target"],
            "occupant": "Wildlife",
            "cull": int(pick.get("cull") or 6),
            "checks": 1,
        }

    def make_extra_marker() -> Optional[Dict[str, Any]]:
        extras = [
            name for name in BOUNTY_MAP_MARKERS
            if name not in blocked and name not in used
        ]
        if not extras:
            return None
        name = extras[random.randrange(len(extras))]
        used.add(name)
        occ = occupants.get(name)
        if occ and occ.get("bosses", 0) >= 1 and occ.get("type") in NPC_BOSS_TYPES:
            occ_type = occ.get("type") or "Bandit"
            return {
                "type": "boss",
                "display": occupant_boss_display(occ_type, name),
                "dungeon": name,
                "marker": marker_for(name, BOUNTY_MAP_MARKERS[name]),
                "target": "Boss",
                "occupant": occ_type,
                "cull": 0,
                "checks": 3,
            }
        occ_type = (occ or {}).get("type") or "Bandit"
        target_kills = cull_target((occ or {}).get("enemies") or 8) or 6
        return {
            "type": "cull",
            "display": occupant_cull_display(occ_type, name, target_kills),
            "dungeon": name,
            "marker": marker_for(name, BOUNTY_MAP_MARKERS[name]),
            "target": occ_type,
            "occupant": occ_type,
            "cull": target_kills,
            "checks": 2,
        }

    def contract_from_ticket(ticket: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        kind = ticket["kind"]
        if kind == "wildlife":
            return make_wildlife()
        if kind == "named":
            pick = ticket["entry"]
            if pick["dungeon"] in used:
                return None
            used.add(pick["dungeon"])
            return {
                "type": "named",
                "display": f"{pick['display']} ({pick['dungeon']})",
                "dungeon": pick["dungeon"],
                "marker": pick["marker"],
                "target": pick["bp"],
                "occupant": "Named",
                "cull": 0,
                "checks": 3,
            }
        if kind == "boss":
            pick = ticket["entry"]
            if pick["name"] in used:
                return None
            used.add(pick["name"])
            return {
                "type": "boss",
                "display": occupant_boss_display(pick["type"], pick["name"]),
                "dungeon": pick["name"],
                "marker": marker_for(pick["name"]),
                "target": "Boss",
                "occupant": pick["type"],
                "cull": 0,
                "checks": 3,
            }
        if kind == "cull":
            pick = ticket["entry"]
            if pick["name"] in used:
                return None
            used.add(pick["name"])
            target_kills = cull_target(pick["enemies"]) or pick["enemies"]
            return {
                "type": "cull",
                "display": occupant_cull_display(pick["type"], pick["name"], target_kills),
                "dungeon": pick["name"],
                "marker": marker_for(pick["name"]),
                "target": pick["type"],
                "occupant": pick["type"],
                "cull": target_kills,
                "checks": 2,
            }
        if kind == "extra":
            return make_extra_marker()
        return None

    while len(contracts) < count and tickets:
        ticket = tickets.pop(random.randrange(len(tickets)))
        contract = contract_from_ticket(ticket)
        if contract is not None:
            contracts.append(contract)

    for index, contract in enumerate(contracts, start=1):
        contract["index"] = index
        display = contract.get("display") or f"Bounty {index}"
        names = check_location_names(display, contract["checks"])
        contract["locations"] = names
        contract["location_names"] = names
    return contracts


def settings_lines(contracts: List[Dict[str, Any]]) -> List[str]:
    lines = [f"bounty_count={len(contracts)}"]
    for contract in contracts:
        lines.append(
            "bounty_{index}={type}|{dungeon}|{marker}|{target}|{cull}|{checks}|{display}|{occupant}".format(
                **contract
            )
        )
    return lines


if __name__ == "__main__":
    import random as _random
    from pathlib import Path

    locations_text = Path(__file__).with_name("Locations.py").read_text(encoding="utf-8")
    match = re.search(r"DUNGEON_REGIONS = \{(.+?)\n\}", locations_text, re.S)
    if not match:
        raise SystemExit("Could not read DUNGEON_REGIONS")
    ap_dungeons = set(re.findall(r'"([^"]+)"\s*:', match.group(1)))
    leftover_boss = [
        name for name, data in DUNGEON_OCCUPANTS.items()
        if data["bosses"] >= 1 and name not in ap_dungeons and name not in SKIP_DUNGEONS
    ]
    leftover_cull = [
        name for name, data in DUNGEON_OCCUPANTS.items()
        if cull_target(data["enemies"]) is not None and name not in ap_dungeons and name not in SKIP_DUNGEONS
    ]
    selected = sorted(ap_dungeons)[:20]
    contracts = generate_bounties(_random.Random(1), 10, selected)
    used = {contract["dungeon"] for contract in contracts if contract.get("dungeon")}
    overlap = used & set(selected)
    print(f"occupants={len(DUNGEON_OCCUPANTS)} leftover_boss={len(leftover_boss)} leftover_cull={len(leftover_cull)}")
    print(f"subset-check seed: {len(contracts)} contracts {[c['display'] for c in contracts]}")
    if len(contracts) != 10:
        raise SystemExit(f"expected 10 contracts, got {len(contracts)}")
    if overlap:
        raise SystemExit(f"bounty dungeons overlapped this seed's checks: {sorted(overlap)}")
    print("ok")
