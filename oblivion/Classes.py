"""
Class definitions for Oblivion Remastered APWorld.

Each class has 7 major skills that determine which skill checks are valid.
When a class is selected, only these skills will be tracked for location checks.
"""

from typing import Dict, List, Optional

class ClassData:
    def __init__(self, name: str, skills: List[str]):
        self.name = name
        self.skills = skills

# All vanilla Oblivion classes with their 7 major skills
CLASSES = {
    "acrobat": ClassData("Acrobat", [
        "Acrobatics", "Blade", "Block", "Marksman", "Security", "Sneak", "Speechcraft"
    ]),
    "agent": ClassData("Agent", [
        "Acrobatics", "Illusion", "Marksman", "Mercantile", "Security", "Sneak", "Speechcraft"
    ]),
    "archer": ClassData("Archer", [
        "Armorer", "Blade", "Blunt", "Hand-to-Hand", "Light Armor", "Marksman", "Sneak"
    ]),
    "assassin": ClassData("Assassin", [
        "Acrobatics", "Alchemy", "Blade", "Light Armor", "Marksman", "Security", "Sneak"
    ]),
    "barbarian": ClassData("Barbarian", [
        "Armorer", "Athletics", "Blade", "Block", "Blunt", "Hand-to-Hand", "Light Armor"
    ]),
    "bard": ClassData("Bard", [
        "Alchemy", "Blade", "Block", "Illusion", "Light Armor", "Mercantile", "Speechcraft"
    ]),
    "battlemage": ClassData("Battlemage", [
        "Alchemy", "Alteration", "Blade", "Blunt", "Conjuration", "Destruction", "Mysticism"
    ]),
    "crusader": ClassData("Crusader", [
        "Athletics", "Blade", "Blunt", "Destruction", "Hand-to-Hand", "Heavy Armor", "Restoration"
    ]),
    "healer": ClassData("Healer", [
        "Alchemy", "Alteration", "Destruction", "Illusion", "Mercantile", "Restoration", "Speechcraft"
    ]),
    "knight": ClassData("Knight", [
        "Blade", "Block", "Blunt", "Hand-to-Hand", "Heavy Armor", "Illusion", "Speechcraft"
    ]),
    "mage": ClassData("Mage", [
        "Alchemy", "Alteration", "Conjuration", "Destruction", "Illusion", "Mysticism", "Restoration"
    ]),
    "monk": ClassData("Monk", [
        "Acrobatics", "Alteration", "Athletics", "Hand-to-Hand", "Marksman", "Security", "Sneak"
    ]),
    "nightblade": ClassData("Nightblade", [
        "Acrobatics", "Alteration", "Athletics", "Blade", "Destruction", "Light Armor", "Restoration"
    ]),
    "pilgrim": ClassData("Pilgrim", [
        "Armorer", "Block", "Blunt", "Light Armor", "Mercantile", "Security", "Speechcraft"
    ]),
    "rogue": ClassData("Rogue", [
        "Alchemy", "Athletics", "Blade", "Block", "Illusion", "Light Armor", "Mercantile"
    ]),
    "scout": ClassData("Scout", [
        "Acrobatics", "Alchemy", "Armorer", "Athletics", "Blade", "Block", "Light Armor"
    ]),
    "sorcerer": ClassData("Sorcerer", [
        "Alchemy", "Alteration", "Conjuration", "Destruction", "Heavy Armor", "Mysticism", "Restoration"
    ]),
    "spellsword": ClassData("Spellsword", [
        "Alteration", "Blade", "Block", "Heavy Armor", "Destruction", "Illusion", "Restoration"
    ]),
    "thief": ClassData("Thief", [
        "Acrobatics", "Light Armor", "Marksman", "Mercantile", "Security", "Sneak", "Speechcraft"
    ]),
    "warrior": ClassData("Warrior", [
        "Armorer", "Athletics", "Blade", "Block", "Blunt", "Hand-to-Hand", "Heavy Armor"
    ]),
    "witchhunter": ClassData("Witchhunter", [
        "Alchemy", "Athletics", "Conjuration", "Destruction", "Marksman", "Mysticism", "Security"
    ])
}

def get_class_data(class_name: str) -> Optional[ClassData]:
    """Get class data for a given class name."""
    return CLASSES.get(class_name.lower())

def get_all_class_names() -> List[str]:
    """Get list of all available class names."""
    return list(CLASSES.keys())

def get_class_skills(class_name: str) -> List[str]:
    """Get the skills associated with a given class."""
    class_data = get_class_data(class_name)
    return class_data.skills if class_data else []

def is_valid_class_skill(class_name: str, skill_name: str) -> bool:
    """Check if a skill is valid for a given class."""
    class_skills = get_class_skills(class_name)
    return skill_name in class_skills 