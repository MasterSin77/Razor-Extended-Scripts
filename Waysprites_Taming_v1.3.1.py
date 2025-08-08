# Waysprites_Taming_v1.3
# -----------------------------------------------------------------------------
# This file combines the pet healing/cure logic from AutoPetHealandCure_v12.py
# with the taming trainer from Waysprites_Taming_v1.2.3.py.  In addition to
# merging these functionalities, it updates the tameables list to include
# additional animals (e.g. Gaman) identified during research【346623078249504†L115-L150】.
# Future 1.3x revisions will further integrate tank-pet commands and kiting logic.

from System.Collections.Generic import List
from System import Byte, Int32
import re
import time

# ---------------------------------------------------------------------------
# === USER CONFIGURATION ===
#
# Customize these settings for your shard and playstyle.  These variables
# control naming, targeting, healing preferences, timers, and clean-up.
# ---------------------------------------------------------------------------

# ----- General taming options -----
# Rename all newly tamed pets to this name.  Must be a single-word string.
renameTamedAnimalsTo = "WayPet"

# Names of pets that should never be targeted or renamed.  Always include
# the renameTamedAnimalsTo value so your training pets are ignored.
petsToIgnore = [
    renameTamedAnimalsTo, "Magmaguard", "Saphira", "Your Worst Nightmare", "Murder Pony", "Toothless"
]

# Keep this many followers after taming; if exceeded, the pet will be released.
numberOfFollowersToKeep = 0

# Maximum taming attempts per animal (0 means unlimited)
maximumTameAttempts = 0

# Minimum taming difficulty to consider for training.  Animals below this
# difficulty will be ignored.
minimumTamingDifficulty = 30

# When True, selects the hardest tameable nearby (even above your skill)
# rather than only those you can currently tame.
prioritizeHardestNearby = True

# ----- Healing options -----
# Enable or disable various healing methods.  The heal_pets routine and
# heal_player function will check these flags.
healUsingMagery = False
healUsingBandages = False
healUsingChivalry = False
healUsingSpiritSpeak = False
healUsingMysticism = False
healUsingSpellweaving = False
healUsingPotions = False
healUsingBushido = False

# Heal when the player's health is below this fraction of max HP. 0.5 is 50% health. 
healThreshold = 0.5

# ----- Behaviour toggles -----
enablePeacemaking = False     # Use Peacemaking to calm animals (not yet implemented)
enableFollowAnimal = True     # Follow animals when out of range
purgeLeftoverPets = True      # Kill leftover training pets near you
autoDefendAgainstAggro = True # Cast Lightning on aggressive mobs (hostiles only)

# ----- Timer configuration (milliseconds) -----
noAnimalsToTrainTimerMilliseconds = 10000
playerStuckTimerMilliseconds = 5000
catchUpToAnimalTimerMilliseconds = 20000
animalTamingTimerMilliseconds = 13000
targetClearDelayMilliseconds = 100

# ----- Cleanup configuration -----
# Names of tamed pets we should kill on sight (usually just the training name).
# This list is derived from the renameTamedAnimalsTo value so that any pet
# renamed to your chosen training name will be purged automatically.
killOnSightPetNames = [renameTamedAnimalsTo, "Trainooo"]

# ----- Pet healing configuration -----
# Serial numbers of your pets that should be healed by the heal_pets routine.
PET_SERIALS = [
    0x002C8540, 0x01BBD306, 0x09B7D605,
    0x09B7DAD4, 0x095FCE87, 0x0A135ACA,
]

# Item ID for veterinary bandages (0x0E21 is standard bandage)
BANDAGE_TYPE = 0x0E21

# Percentage thresholds for resurrecting or healing pets
VET_REZ_THRESHOLD = 0.00   # Resurrect pets when HP < 0%
PET_HEAL_THRESHOLD = 0.75  # Heal pets when HP < 75%

# Message intervals (ms) for reminders and distance checks
REMINDER_INTERVAL = 60000        # Remind about bandages every 60 seconds
DISTANCE_MSG_INTERVAL = 30000    # Notify if pet is too far every 30 seconds
MSG_INTERVAL = 30000             # Generic message interval for unspecified alerts

# Maximum distances for magery heal and bandage use (in tiles)
MAGE_HEAL_RANGE = 10.0
VET_RANGE = 2.0

# ============================== enemies.py ===================================
class Notoriety:
    byte = Byte(0)
    color = ''
    description = ''

    def __init__(self, byte, color, description):
        self.byte = byte
        self.color = color
        self.description = description

notorieties = {
    'innocent':   Notoriety(Byte(1), 'blue',  'innocent'),
    'ally':       Notoriety(Byte(2), 'green', 'guilded/ally'),
    'attackable': Notoriety(Byte(3), 'gray',  'attackable but not criminal'),
    'criminal':   Notoriety(Byte(4), 'gray',  'criminal'),
    'enemy':      Notoriety(Byte(5), 'orange','enemy'),
    'murderer':   Notoriety(Byte(6), 'red',   'murderer'),
    'npc':        Notoriety(Byte(7), '',      'npc'),
}

def _GetNotorietyList(nots):
    notorietyList = []
    for n in nots:
        notorietyList.append(n.byte)
    return List[Byte](notorietyList)

def GetEnemyNotorieties(minRange = 0, maxRange = 12):
    return _GetNotorietyList([
        notorieties['attackable'],
        notorieties['criminal'],
        notorieties['enemy'],
        notorieties['murderer'],
    ])

def GetEnemies(Mobiles, minRange = 0, maxRange = 12, notorieties = GetEnemyNotorieties(), IgnorePartyMembers = False):
    if Mobiles is None:
        raise ValueError('Mobiles was not passed to GetEnemies')
    enemyFilter = Mobiles.Filter()
    enemyFilter.Enabled = True
    enemyFilter.RangeMin = minRange
    enemyFilter.RangeMax = maxRange
    enemyFilter.Notorieties = notorieties
    enemyFilter.CheckIgnoreObject = True
    enemyFilter.Friend = False
    enemies = Mobiles.ApplyFilter(enemyFilter)
    if IgnorePartyMembers:
        partyMembers = [enemy for enemy in enemies if enemy.InParty]
        for partyMember in partyMembers:
            enemies.Remove(partyMember)
    return enemies

# ============================= tameables.py ==================================
class Animal:
    name = ''
    mobileID = 0
    color = 0
    minTamingSkill = -1
    maxTamingSkill = -1
    packType = None
    def __init__(self, name, mobileID, color, minTamingSkill, maxTamingSkill, packType):
        self.name = name
        self.mobileID = mobileID
        self.color = color
        self.minTamingSkill = minTamingSkill
        self.maxTamingSkill = maxTamingSkill
        self.packType = packType

#
# Tameable animals with minimum difficulty thresholds.  This list merges
# the original tameables.py entries with additional creatures (e.g. Gaman) from
# research.  Values reflect approximate minimum skill as documented on the
# Taming Archive【346623078249504†L115-L150】.  Body IDs come from standard
# UO macros where available.
#
animals = {
    # beginner animals
    'dog': Animal('dog', 0x00D9, 0x0000, 0, 10, ['canine']),
    'gorilla': Animal('gorilla', 0x001D, 0x0000, 0, 10, None),
    'parrot': Animal('parrot', 0x033F, 0x0000, 0, 10, None),
    'rabbit (brown)': Animal('rabbit', 0x00CD, 0x0000, 0, 10, None),
    'rabbit (black)': Animal('rabbit', 0x00CD, 0x090E, 0, 10, None),
    'jack rabbit': Animal('jack rabbit', 0x00CD, 0x01BB, 0, 10, None),
    'skittering hopper': Animal('skittering hopper', 0x012E, 0x0000, 0, 10, None),
    'squirrel': Animal('squirrel', 0x0116, 0x0000, 0, 10, None),
    'mongbat': Animal('mongbat', 0x0027, 0x0000, 0, 20, None),
    'chickadee': Animal('chickadee', 0x0006, 0x0840, 10, 20, None),
    'crossbill': Animal('crossbill', 0x0006, 0x083A, 10, 20, None),
    'crow': Animal('crow', 0x0006, 0x0901, 10, 20, None),
    'finch': Animal('finch', 0x0006, 0x0835, 10, 20, None),
    'hawk': Animal('hawk', 0x0006, 0x0835, 10, 20, None),
    'kingfisher': Animal('kingfisher', 0x0006, 0x083F, 10, 20, None),
    'lapwing': Animal('lapwing', 0x0006, 0x0837, 10, 20, None),
    'magpie': Animal('magpie', 0x0006, 0x0901, 10, 20, None),
    'nuthatch': Animal('nuthatch', 0x0006, 0x0851, 10, 20, None),
    'plover': Animal('plover', 0x0006, 0x0847, 10, 20, None),
    'raven': Animal('raven', 0x0006, 0x0901, 10, 20, None),
    'skylark': Animal('skylark', 0x0006, 0x083C, 10, 20, None),
    'starling': Animal('starling', 0x083E, 0x0845, 10, 20, None),
    'swift': Animal('swift', 0x0006, 0x0845, 10, 20, None),
    'tern': Animal('tern', 0x0006, 0x0847, 10, 20, None),
    'towhee': Animal('towhee', 0x0006, 0x0847, 10, 20, None),
    'woodpecker': Animal('woodpecker', 0x0006, 0x0851, 10, 20, None),
    'wren': Animal('wren', 0x0006, 0x0850, 10, 20, None),
    'cat': Animal('cat', 0x00C9, 0x0000, 10, 20, ['feline']),
    'chicken': Animal('chicken', 0x00D0, 0x0000, 10, 20, None),
    'mountain goat': Animal('mountain goat', 0x0058, 0x0000, 10, 20, None),
    'rat': Animal('rat', 0x00EE, 0x0000, 10, 20, None),
    'sewer rat': Animal('sewer rat', 0x00EE, 0x0000, 10, 20, None),
    # novice
    'cow (brown)': Animal('cow', 0x00E7, 0x0000, 20, 30, None),
    'cow (black)': Animal('cow', 0x00D8, 0x0000, 20, 30, None),
    'goat': Animal('goat', 0x00D1, 0x0000, 20, 30, None),
    'pig': Animal('pig', 0x00CB, 0x0000, 20, 30, None),
    'sheep': Animal('sheep', 0x00CF, 0x0000, 20, 30, None),
    'giant beetle': Animal('giant beetle', 0x0317, 0x0000, 20, 50, None),
    'slime': Animal('slime', 0x0033, 0x0000, 20, 50, None),
    'eagle': Animal('eagle', 0x0005, 0x0000, 30, 40, None),
    # mid-level
    'boar': Animal('boar', 0x0122, 0x0000, 40, 50, None),
    'bullfrog': Animal('bullfrog', 0x0051, 0x0000, 40, 50, None),
    'ferret': Animal('ferret', 0x0117, 0x0000, 40, 50, None),
    'giant rat': Animal('giant rat', 0x00D7, 0x0000, 40, 50, None),
    'hind': Animal('hind', 0x00ED, 0x0000, 40, 50, None),
    'horse': Animal('horse', 0x00C8, 0x0000, 40, 50, None),
    'horse2': Animal('horse', 0x00E2, 0x0000, 40, 50, None),
    'horse3': Animal('horse', 0x00CC, 0x0000, 40, 50, None),
    'horse4': Animal('horse', 0x00E4, 0x0000, 40, 50, None),
    'horsePack': Animal('pack horse', 0x0123, 0x0000, 40, 50, None),
    'pack llama': Animal('pack llama', 0x0124, 0x0000, 40, 50, None),
    'ostard': Animal('desert ostard', 0x00D2, 0x0000, 40, 50, ['ostard']),
    'forest ostard (green)': Animal('forest ostard', 0x00DB, 0x88A0, 40, 50, ['ostard']),
    'forest ostard (red)': Animal('forest ostard', 0x00DB, 0x889D, 40, 50, ['ostard']),
    'timber wolf': Animal('timber wolf', 0x00E1, 0x0000, 40, 50, ['canine']),
    'rideable wolf': Animal('rideable wolf', 0x0115, 0x0000, 40, 50, ['canine']),
    'black bear': Animal('black bear', 0x00D3, 0x0000, 50, 60, ['bear']),
    'polar bear': Animal('polar bear', 0x00D5, 0x0000, 50, 60, ['bear']),
    'llama': Animal('llama', 0x00DC, 0x0000, 50, 60, None),
    'walrus': Animal('walrus', 0x00DD, 0x0000, 50, 60, None),
    'alligator': Animal('alligator', 0x00CA, 0x0000, 60, 70, None),
    'brown bear': Animal('brown bear', 0x00A7, 0x0000, 60, 70, ['bear']),
    'cougar': Animal('cougar', 0x003F, 0x0000, 60, 70, ['feline']),
    'scorpion': Animal('scorpion', 0x0030, 0x0000, 60, 70, None),
    # high-mid
    'rideable polar bear': Animal('rideable polar bear', 0x00D5, 0x0000, 70, 80, ['bear']),
    'grizzly bear': Animal('grizzly bear', 0x00D4, 0x0000, 70, 80, ['bear']),
    'young dragon': Animal('young dragon', 0x003C, 0x0000, 70, 80, None),
    'great hart': Animal('great hart', 0x00EA, 0x0000, 70, 80, None),
    'snow leopard': Animal('snow leopard', 0x0040, 0x0000, 70, 80, ['feline']),
    'snow leopard2': Animal('snow leopard', 0x0041, 0x0000, 70, 80, ['feline']),
    'panther': Animal('panther', 0x00D6, 0x0000, 70, 80, ['feline']),
    'snake': Animal('snake', 0x0034, 0x0000, 70, 80, None),
    'giant spider': Animal('giant spider', 0x001C, 0x0000, 70, 80, None),
    'grey wolf (light grey)': Animal('grey wolf', 0x0019, 0x0000, 70, 80, ['canine']),
    'grey wolf (dark grey)': Animal('grey wolf', 0x001B, 0x0000, 70, 80, ['canine']),
    'white wolf (dark grey)': Animal('white wolf', 0x0022, 0x0000, 80, 90, ['canine']),
    'white wolf (light grey)': Animal('white wolf', 0x0025, 0x0000, 80, 90, ['canine']),
    # high
    'bull (solid, brown)': Animal('bull', 0x00E8, 0x0000, 90, 100, ['bull']),
    'bull (solid, black)': Animal('bull', 0x00E8, 0x0901, 90, 100, ['bull']),
    'bull (spotted, brown)': Animal('bull', 0x00E9, 0x0000, 90, 100, ['bull']),
    'bull (spotted, black)': Animal('bull', 0x00E9, 0x0901, 90, 100, ['bull']),
    'hellcat (small)': Animal('hellcat', 0x00C9, 0x0647, 90, 100, ['feline']),
    'frenzied ostard': Animal('frenzied ostard', 0x00DA, 0x0000, 90, 100, ['ostard']),
    'frost spider': Animal('frost spider', 0x0014, 0x0000, 90, 100, None),
    'giant toad': Animal('giant toad', 0x0050, 0x0000, 90, 100, None),
    'giant ice worm': Animal('giant ice worm', 0x0050, 0x0000, 90, 100, None),
    # very high
    'drake (brown)': Animal('drake', 0x003C, 0x0000, 100, 110, None),
    'drake (red)': Animal('drake', 0x003D, 0x0000, 100, 110, None),
    'hellcat (large)': Animal('hellcat', 0x007F, 0x0000, 100, 110, ['feline']),
    'hellhound': Animal('hellhound', 0x0062, 0x0000, 100, 110, ['canine']),
    'imp': Animal('imp', 0x004A, 0x0000, 100, 110, ['daemon']),
    'lava lizard': Animal('lava lizard', 0x00CE, 0x0000, 100, 110, None),
    'ridgeback': Animal('ridgeback', 0x00BB, 0x0000, 100, 110, None),
    'savage ridgeback': Animal('savage ridgeback', 0x00BC, 0x0000, 100, 110, None),
    'dire wolf': Animal('dire wolf', 0x0017, 0x0000, 100, 110, ['canine']),
    'rune beetle': Animal('rune beetle', 0x00F4, 0x0000, 110, 120, None),
    'dragon': Animal('dragon', 0x003B, 0x0000, 110, 120, None),
    'dread spider': Animal('dread spider', 0x000B, 0x0000, 110, 120, None),
    'white wyrm': Animal('white wyrm', 0x00B4, 0x0000, 110, 120, None),
    'shadow wyrm': Animal('shadow wyrm', 0x006A, 0x0000, 120, 120, None),
    # new
    'gaman': Animal('gaman', 0x00F8, 0x0000, 68, 80, None),
}

def GetAnimalIDsAtOrOverTamingDifficulty(minimumTamingDifficulty):
    animalList = List[Int32]()
    for k in animals:
        a = animals[k]
        if (a is not None and
            not animalList.Contains(a.mobileID) and
            a.minTamingSkill >= minimumTamingDifficulty):
            animalList.Add(a.mobileID)
    return animalList

def GetAnimalIDsAtOrUnderTamingSkill(maxTamingSkill):
    animalList = List[Int32]()
    for k in animals:
        a = animals[k]
        if a is not None and not animalList.Contains(a.mobileID) and a.minTamingSkill <= maxTamingSkill:
            animalList.Add(a.mobileID)
    return animalList

def GetTameableAnimalsForSkill(skillLevel):
    eligible = []
    for a in animals.values():
        if a is not None and a.minTamingSkill <= skillLevel:
            eligible.append(a)
    eligible.sort(key=lambda x: x.minTamingSkill, reverse=True)
    return eligible

def GetTameableAnimalsAboveDifficulty(minDifficulty):
    eligible = []
    for a in animals.values():
        if a is not None and a.minTamingSkill >= minDifficulty:
            eligible.append(a)
    eligible.sort(key=lambda x: x.minTamingSkill)
    return eligible

# =========================== taming_advice.py ================================
from typing import Optional, List as _List, Dict, Any

class AdviceEntry(Dict[str, Any]):
    pass

skill_advice: _List[AdviceEntry] = [
    AdviceEntry(min_skill=0.0, max_skill=10.0,
        animals=["bird","cat","chicken","dog","mountain goat","gorilla","rabbit","rat","mongbat","sewer rat"],
        locations=["Britain and Moonglow farm animals and woods","Windemere Wood/Sacrifice","North Britain Woods"],
        note=("Start by buying skill to 30 from an NPC. For gains up to 10 skill, "
              "tame any small animal you come across — birds, cats, dogs and other "
              "farm animals are plentiful around Britain and Moonglow and in the "
              "Windemere Wood area.")),
    AdviceEntry(min_skill=10.1, max_skill=20.0,
        animals=["goat","cow","sheep","eagle"],
        locations=["Britain farms","Moonglow farms","Windemere Wood/Sacrifice"],
        note=("Continue taming farm animals. Goats, cows and sheep have higher "
              "difficulty than chickens and yield better gains; you can also try "
              "eagles if you venture into the woods.")),
    AdviceEntry(min_skill=20.1, max_skill=30.0,
        animals=["bullfrog","timber wolf","boar","rideable llama","forest ostard","horse","desert ostard","eagle"],
        locations=["Ice Island (Dagger Isle)","Delucia pens and farms","Crossroads and Minoc Woods"],
        note=("Ice Island has a variety of tameables and is an excellent place to "
              "tame up to 40 skill. Timber wolves and boars provide good gains, "
              "while rideable llamas and ostards offer a little extra challenge. "
              "Delucia’s pens also provide bulls and other farm animals with minimal danger.")),
    AdviceEntry(min_skill=30.1, max_skill=40.0,
        animals=["boar","rideable llama","forest ostard","desert ostard","black bear","polar bear","llama","walrus","brown bear","cougar"],
        locations=["Ice Island for polar bears and walrus","Covetous Woods","Minoc and North Britain Woods"],
        note=("Make circuits of Ice Island to tame polar bears, snow leopards and white wolves. "
              "Forest and desert ostards, along with black and brown bears, can be found in the woods near Vesper and "
              "Britain. Cougars also begin to yield gains in this range.")),
    AdviceEntry(min_skill=40.1, max_skill=50.0,
        animals=["brown bear","cougar","alligator","scorpion","black bear","polar bear","llama","walrus"],
        locations=["Shame dungeon levels 1–2 (scorpions)","Jhelom bull pen and surrounding farms","Hopper’s Bog for alligators and bullfrogs"],
        note=("Level 1–2 of Shame is packed with scorpions and provides rapid gains; alligator spawns around "
              "Jhelom and Hopper’s Bog offer variety. Continue to tame bears and cougars in the forests.")),
    AdviceEntry(min_skill=50.1, max_skill=60.0,
        animals=["brown bear","cougar","alligator","scorpion","black bear","polar bear","llama","walrus","grey wolf","great hart","snake","giant spider","grizzly bear","panther","snow leopard"],
        locations=["Shame levels 1–2 for scorpions","Minoc and Moonglow moongates","Ice Island and Covetous Woods"],
        note=("Continue working scorpions in Shame. As you approach 60 skill you can add grey wolves, great harts and grizzlies "
              "to your circuit. Giant spiders and panthers appear in deeper woods and provide slightly higher difficulty.")),
    AdviceEntry(min_skill=60.1, max_skill=70.0,
        animals=["cougar","alligator","scorpion","black bear","polar bear","llama","walrus","grey wolf","great hart","snake","giant spider","grizzly bear","panther","snow leopard","white wolf"],
        locations=["Shame levels 1–2 (scorpions still best)","Ice Island and Kos Heb Icelands","Jhelom bull pen and Covetous Woods"],
        note=("Scorpions remain excellent through 70 skill. Alternatively hunt in the snowy regions for grey and white wolves, "
              "snakes, snow leopards and polar bears. Great harts and grizzlies in the woods near Britain and Vesper continue to yield gains.")),
    AdviceEntry(min_skill=70.1, max_skill=80.0,
        animals=["alligator","scorpion","black bear","polar bear","walrus","grey wolf","great hart","snake","giant spider","grizzly bear","panther","snow leopard","white wolf","bull","hellcat (small)","frenzied ostard","giant toad","frost spider"],
        locations=["Shame (scorpions) and Minoc/Vesper woods","Jhelom bull pen (bulls)","Fire dungeon for small hellcats","Hopper’s Bog for giant toads and alligators"],
        note=("At 70 skill you can begin taming bulls and even small hellcats; bulls are plentiful at the Jhelom pens. "
              "Continue working scorpions for quick gains or venture into Fire dungeon to hunt small hellcats, frenzied ostards and giant toads.")),
    AdviceEntry(min_skill=80.1, max_skill=90.0,
        animals=["alligator","scorpion","black bear","polar bear","walrus","great hart","snake","giant spider","grizzly bear","panther","snow leopard","white wolf","bull","hellcat (small)","frenzied ostard","giant toad","frost spider","lava lizard","imp","hell hound","dire wolf"],
        locations=["Delucia Passage and Vesper south road (small hellcats)","Fire dungeon Level 1 (hellcats, hell hounds, lava lizards)","Jhelom bull pen and Delucia farms"],
        note=("Small hellcats become the premier tamables between 80–90 skill—Delucia Passage has clusters of them. "
              "Lava lizards begin to yield gains around 80.7 skill and appear in Fire dungeon. Hell hounds and imps in Fire or Hythloth provide "
              "additional challenge, while bulls remain an accessible option.")),
    AdviceEntry(min_skill=90.1, max_skill=100.0,
        animals=["great hart","snake","giant spider","grizzly bear","panther","snow leopard","white wolf","bull","hellcat (small)","frenzied ostard","giant toad","frost spider","lava lizard","imp","hell hound","dire wolf","hellcat (large)","dragon","drake","nightmare","white wyrm","ki-rin","unicorn"],
        locations=["Fire dungeon Levels 1–2 (lava lizards, hell hounds, large hellcats)","Hythloth dungeon (hell hounds and imps)","Destard, Fire Isle and Wind for drakes and dragons","Ice Dungeon for frost spiders and white wyrms"],
        note=("Continue taming small hellcats, bulls and lava lizards until about 95 skill, then begin adding hell hounds and large hellcats. "
              "At the high end of this bracket you can attempt dragons, drakes, nightmares and white wyrms in dungeons such as Fire, Destard or Wind.")),
    AdviceEntry(min_skill=100.1, max_skill=120.0,
        animals=["lava lizard","hell hound","hellcat (large)","dragon","drake","nightmare","white wyrm","dread spider","rune beetle","shadow wyrm"],
        locations=["Fire dungeon Levels 1–2 (hellcats and hell hounds)","Delucia Passage (lava lizards)","Destard and Wind (dragons and drakes)","Ice Dungeon (white wyrms and dread spiders)"],
        note=("Above 100 skill, gains slow dramatically. Continue taming lava lizards until about 107, then focus on hell hounds and large hellcats in Fire. "
              "Dragons, drakes, nightmares and white wyrms require 93.9–120 skill and reside in dungeons like Destard, Wind and Ice.")),
]

def get_advice(skill_level: float) -> Optional[AdviceEntry]:
    for entry in skill_advice:
        if entry["min_skill"] <= skill_level <= entry["max_skill"]:
            return entry
    return None

# ============================ healing_module.py ===============================
#
# Player and pet healing utilities.  This section integrates basic self-healing
# from the original taming trainer with pet heal/cure logic from
# AutoPetHealandCure_v12.py.  The pet healing code has been converted from an
# infinite loop into a single-call function (heal_pets) suitable for invocation
# during each iteration of the taming loop.  It respects cooldowns and
# thresholds, and uses Veterinary or Magery as appropriate.  Use PET_SERIALS
# below to identify your pets.

# === CONFIGURATION ===
# Define the serials of your regular pets.  When healing, the script will
# iterate over these serials to find the pet with the lowest health and heal
# or cure it as necessary.  Note: Serial values are hexadecimal literals
# accepted by Razor Enhanced.
PET_SERIALS = [
    0x002C8540,
    0x01BBD306,
    0x09B7D605,
    0x09B7DAD4,
    0x095FCE87,
    0x0A135ACA,
]
BANDAGE_TYPE = 0x0E21
VET_REZ_THRESHOLD = 50  # minimum Veterinary skill to attempt resurrection
PET_HEAL_THRESHOLD = 50  # percent at which to cast heal spells
CHECK_INTERVAL = 500  # ms between iterations when called in a loop; unused here
REMINDER_INTERVAL = 60
DISTANCE_MSG_INTERVAL = 2
MSG_INTERVAL = 2
MAGE_HEAL_RANGE = 10
VET_RANGE = 2

# === STATE TRACKING ===
lastPetPercent = -1
lastPlayerHits = -1
lastReminderTime = time.time()
lastDistance = -1
lastDistanceTime = 0
lastMessageTime = 0
lastBandageCount = -1
activePetSerial = None

def find_bandage_item(container):
    for item in container.Contains:
        if item.ItemID == BANDAGE_TYPE:
            return item
        if item.IsContainer:
            nested = find_bandage_item(item)
            if nested:
                return nested
    return None

def count_bandages(container):
    count = 0
    for item in container.Contains:
        if item.ItemID == BANDAGE_TYPE:
            count += item.Amount
        elif item.IsContainer:
            count += count_bandages(item)
    return count

def heal_pets():
    """
    Heal or cure pets and the player.  This function examines the health of the
    player and all pets listed in PET_SERIALS and takes appropriate actions.
    It performs a single pass (no infinite loop) and should be called
    periodically from the main taming loop.  State variables track the last
    reported health and message timings to avoid spamming.
    """
    global lastPetPercent, lastPlayerHits, lastReminderTime, lastDistance
    global lastDistanceTime, lastMessageTime, lastBandageCount, activePetSerial
    # Check bandage count
    try:
        bandage_count = count_bandages(Player.Backpack)
    except Exception:
        bandage_count = 0
    current_time = time.time()
    if bandage_count != lastBandageCount:
        Misc.SendMessage("Bandages Available: {}".format(bandage_count), 1100)
        lastBandageCount = bandage_count
    # Periodic reminder
    if current_time - lastReminderTime >= REMINDER_INTERVAL:
        Misc.SendMessage("Healing Script Active", 1100)
        lastReminderTime = current_time
    # Player HP display
    playerHP = Player.Hits
    playerMaxHP = Player.HitsMax
    playerPercent = int((100 * playerHP) / playerMaxHP) if playerMaxHP > 0 else 0
    if playerHP != lastPlayerHits:
        Misc.SendMessage("Player HP: {}%".format(playerPercent), 1100)
        lastPlayerHits = playerHP
    # Cure player poison
    if Player.Poisoned:
        Misc.SendMessage("Player is poisoned! Casting Cure...", 66)
        try:
            Spells.Cast("Cure")
            if Target.WaitForTarget(2000, False):
                Target.TargetExecute(Player.Serial)
        except Exception:
            pass
        Misc.Pause(500)
        return
    # Select pet with lowest HP percent
    activePetSerial = None
    lowest_hp_percent = 101
    pet = None
    for serial in PET_SERIALS:
        petCandidate = Mobiles.FindBySerial(serial)
        if petCandidate and petCandidate.HitsMax > 0:
            percent = int((100 * petCandidate.Hits) / petCandidate.HitsMax)
            if percent < lowest_hp_percent:
                lowest_hp_percent = percent
                activePetSerial = serial
                pet = petCandidate
    # If no pet found, heal player if necessary and return
    if not pet:
        if playerPercent < 99:
            Misc.SendMessage("Healing Player with Greater Heal...", 1100)
            try:
                Spells.Cast("Greater Heal")
                if Target.WaitForTarget(2000, False):
                    Target.TargetExecute(Player.Serial)
            except Exception:
                pass
            Misc.Pause(500)
        return
    # Distance message
    try:
        petDistance = Misc.Distance(Player.Position.X, Player.Position.Y, pet.Position.X, pet.Position.Y)
    except Exception:
        petDistance = 99
    if petDistance != lastDistance and current_time - lastDistanceTime > DISTANCE_MSG_INTERVAL:
        Misc.SendMessage("Distance to pet: {}".format(petDistance), 1100)
        lastDistance = petDistance
        lastDistanceTime = current_time
    # Pet HP percent
    petHP = pet.Hits
    petMaxHP = pet.HitsMax
    petPercent = int((100 * petHP) / petMaxHP) if petMaxHP > 0 else 0
    if petPercent != lastPetPercent:
        Misc.SendMessage("Pet HP: {}%".format(petPercent), 1100)
        lastPetPercent = petPercent
    # Dead pet
    if petHP <= 0:
        if Player.GetSkillValue("Veterinary") >= VET_REZ_THRESHOLD and bandage_count > 0 and petDistance <= VET_RANGE:
            if current_time - lastMessageTime > MSG_INTERVAL:
                Misc.SendMessage("Pet dead! Attempting Veterinary rez...", 66)
                lastMessageTime = current_time
            bandage_item = find_bandage_item(Player.Backpack)
            if bandage_item:
                Items.UseItem(bandage_item)
                if Target.WaitForTarget(2000, False):
                    Target.TargetExecute(pet.Serial)
            Misc.Pause(500)
        else:
            if current_time - lastMessageTime > MSG_INTERVAL:
                Misc.SendMessage("Pet dead. Cannot rez (Vet too low or no bandages).", 33)
                lastMessageTime = current_time
        return
    # Heal player if necessary and pet is stable (>25%)
    # We prioritise healing the player if they are below threshold and the pet is not critically low.
    if playerPercent < 99 and petPercent > 25:
        Misc.SendMessage("Healing Player with Greater Heal...", 1100)
        try:
            Spells.Cast("Greater Heal")
            if Target.WaitForTarget(2000, False):
                Target.TargetExecute(Player.Serial)
        except Exception:
            pass
        Misc.Pause(500)
        return

    # ---- Pet-specific healing begins here ----
    # Cure pet poison if within spell range.  We cast Cure on the pet if they are poisoned.
    if pet.Poisoned and petDistance <= MAGE_HEAL_RANGE:
        if current_time - lastMessageTime > MSG_INTERVAL:
            Misc.SendMessage("Pet is poisoned! Casting Cure...", 66)
            lastMessageTime = current_time
        try:
            Spells.Cast("Cure")
            if Target.WaitForTarget(2000, False):
                Target.TargetExecute(activePetSerial)
        except Exception:
            pass
        Misc.Pause(500)
        return

    # Healing logic: decide whether to use Magery or Veterinary to heal the pet.
    if petDistance <= MAGE_HEAL_RANGE:
        # Critical heal threshold: use Greater Heal via Magery when pet is very low.
        if petPercent <= PET_HEAL_THRESHOLD:
            if current_time - lastMessageTime > MSG_INTERVAL:
                Misc.SendMessage("Pet critically injured! Casting Greater Heal...", 66)
                lastMessageTime = current_time
            try:
                Spells.Cast("Greater Heal")
                if Target.WaitForTarget(2000, False):
                    Target.TargetExecute(activePetSerial)
            except Exception:
                pass
            Misc.Pause(500)
            return
        # Pet is hurt but not critical.  Prefer bandages if in range and bandages are available.
        elif petPercent < 100:
            if petDistance <= VET_RANGE and bandage_count > 0:
                bandage_item = find_bandage_item(Player.Backpack)
                if bandage_item:
                    if current_time - lastMessageTime > MSG_INTERVAL:
                        Misc.SendMessage("Pet slightly injured. Using Veterinary (Bandages)...", 1100)
                        lastMessageTime = current_time
                    Items.UseItem(bandage_item)
                    if Target.WaitForTarget(2000, False):
                        Target.TargetExecute(pet.Serial)
                    Misc.Pause(500)
                    return
            # Out of bandage range or no bandages; fall back to Greater Heal via Magery.
            if current_time - lastMessageTime > MSG_INTERVAL:
                Misc.SendMessage("Pet slightly injured but out of bandage range. Casting Greater Heal...", 66)
                lastMessageTime = current_time
            try:
                Spells.Cast("Greater Heal")
                if Target.WaitForTarget(2000, False):
                    Target.TargetExecute(activePetSerial)
            except Exception:
                pass
            Misc.Pause(500)
            return

    # If none of the above conditions triggered, no healing was required on this pass.
    return

# -----------------------------------------------------------------------------
# Healing utilities copied from the 1.2.x version of the script.  These
# functions implement a variety of ways to heal the player using different
# schools (Magery, Bandages, Chivalry, Mysticism, Spellweaving, Potions,
# Bushido).  The heal_player() function coordinates them based on the
# configured toggles defined below.  These utilities were omitted in the
# initial v1.3 merge, leading to a NameError when heal_player() was called.
# -----------------------------------------------------------------------------

def _hm_find_item_by_name(name_substring):
    """
    Search the player's backpack for an item whose name contains the given
    substring (case-insensitive).  Returns the first matching item or None.
    """
    items = Items.FindBySerial(Player.Backpack.Serial).Items
    if items is None:
        return None
    substring = name_substring.lower()
    for item in items:
        try:
            if item.Name and substring in item.Name.lower():
                return item
        except Exception:
            continue
    return None

def heal_with_bandage():
    """
    Attempt to heal the player with a bandage.  Returns True on success,
    False if no bandages were found or the heal did not proceed.
    """
    bandage = _hm_find_item_by_name("bandage")
    if bandage:
        Items.UseItem(bandage)
        Target.WaitForTarget(2000, False)
        Target.TargetExecute(Player.Serial)
        Misc.Pause(1000)
        return True
    return False

def heal_with_magery():
    """
    Heal the player with Magery.  Chooses Greater Heal if enough mana,
    otherwise falls back to Heal.  Returns True on success.
    """
    if Player.Mana >= 11:
        spell_name = "Greater Heal"
    elif Player.Mana >= 9:
        spell_name = "Heal"
    else:
        return False
    try:
        Spells.Cast(spell_name)
        Target.WaitForTarget(2000, True)
        Target.TargetExecute(Player.Serial)
        Misc.Pause(500)
        return True
    except Exception:
        return False

def heal_with_chivalry():
    """
    Heal the player using Chivalry (Close Wounds).  Returns True on success.
    """
    if Player.Mana < 10:
        return False
    try:
        Spells.Cast("Close Wounds")
        Target.WaitForTarget(2000, True)
        Target.TargetExecute(Player.Serial)
        Misc.Pause(500)
        return True
    except Exception:
        return False

def heal_with_spirit_speak():
    """
    Heal the player using Spirit Speak.  Returns True on success.
    """
    try:
        Player.UseSkill("Spirit Speak")
        Misc.Pause(1000)
        return True
    except Exception:
        return False

def heal_with_healing_stone():
    """
    Heal the player using a Mysticism Healing Stone.  If no healing stone is
    present and the player has enough mana, the spell is cast to create one.
    Returns True on success.
    """
    stone = _hm_find_item_by_name("healing stone")
    if not stone:
        if Player.Mana < 4:
            return False
        try:
            Spells.Cast("Healing Stone")
            Misc.Pause(1000)
            stone = _hm_find_item_by_name("healing stone")
        except Exception:
            return False
    if stone:
        Items.UseItem(stone)
        Misc.Pause(500)
        return True
    return False

def heal_with_cleansing_winds():
    """
    Heal and cure the player using Spellweaving (Cleansing Winds).  Returns
    True on success.
    """
    if Player.Mana < 20:
        return False
    try:
        Spells.Cast("Cleansing Winds")
        Target.WaitForTarget(2000, True)
        Target.TargetExecute(Player.Serial)
        Misc.Pause(500)
        return True
    except Exception:
        return False

def heal_with_potion(prefer_greater=True):
    """
    Heal the player using healing potions.  Optionally prefers Greater Heal
    potions over normal heal potions.  Returns True if a potion was used.
    """
    if prefer_greater:
        item = _hm_find_item_by_name("greater heal potion")
        if not item:
            item = _hm_find_item_by_name("heal potion")
    else:
        item = _hm_find_item_by_name("heal potion")
        if not item:
            item = _hm_find_item_by_name("greater heal potion")
    if item:
        Items.UseItem(item)
        Misc.Pause(500)
        return True
    return False

def heal_with_confidence():
    """
    Heal the player using Bushido's Confidence ability (requires a weapon and
    success in combat to trigger healing).  Returns True on success.
    """
    try:
        Player.UseSkill("Bushido")
        Spells.Cast("Confidence")
        Misc.Pause(500)
        return True
    except Exception:
        return False

def heal_player(threshold=0.5,
                use_magery=False,
                use_bandages=False,
                use_chivalry=False,
                use_spirit_speak=False,
                use_mysticism=False,
                use_spellweaving=False,
                use_potions=False,
                use_bushido=False):
    """
    Heal the player if their hit points drop below the given threshold.  The
    healing methods are attempted in order of priority: Magery, Potions,
    Chivalry, Mysticism, Spellweaving, Spirit Speak, Bandages, and Bushido.
    Returns True if any healing method was successfully used.
    """
    if Player.IsGhost:
        return False
    if Player.Hits >= Player.HitsMax * threshold:
        return False
    # Try each healing method in priority order
    if use_magery and heal_with_magery():
        return True
    if use_potions and heal_with_potion():
        return True
    if use_chivalry and heal_with_chivalry():
        return True
    if use_mysticism and heal_with_healing_stone():
        return True
    if use_spellweaving and heal_with_cleansing_winds():
        return True
    if use_spirit_speak and heal_with_spirit_speak():
        return True
    if use_bandages and heal_with_bandage():
        return True
    if use_bushido and heal_with_confidence():
        return True
    return False

# =========================== PetTamerCleanup.py ===============================
# Inlined from the original helper module.  These definitions were omitted
# during the merge, leading to a NameError for PurgeOtherPetsNearby and an
# undefined killOnSightPetNames.  killOnSightPetNames lists names of pets
# that should be killed on sight (typically training pets).  PurgeOtherPetsNearby
# scans for these pets within a certain range and kills them with a Lightning spell.

# Names of tamed pets we should immediately kill are defined in the
# configuration section (killOnSightPetNames).  See USER CONFIGURATION above.

def PurgeOtherPetsNearby(Spells, Mobiles, Target, Misc):
    """
    Search for nearby mobiles (within 10 tiles) with names in killOnSightPetNames
    and kill them using a Lightning spell.  This is used to clean up leftover
    training pets before selecting a new taming target.
    """
    f = Mobiles.Filter()
    f.Enabled = True
    f.RangeMax = 10
    f.CheckIgnoreObject = False
    f.IsHuman = False
    f.IsGhost = False
    mobs = Mobiles.ApplyFilter(f)
    for m in mobs:
        if m.Name in killOnSightPetNames and m.Hits > 0 and m.Hits <= m.HitsMax:
            try:
                Spells.Cast("Lightning")
                if Target.WaitForTarget(2000, False):
                    Target.TargetExecute(m)
                Misc.Pause(1000)
            except Exception:
                # If casting fails (e.g. insufficient mana), continue to next mob
                pass

# =========================== Main trainer ====================================
# Configuration variables are defined in the USER CONFIGURATION section near the
# top of this file.  Do not duplicate them here; see that section for
# renameTamedAnimalsTo, petsToIgnore, numberOfFollowersToKeep, maximumTameAttempts,
# minimumTamingDifficulty, prioritizeHardestNearby, healing flags, and behavior toggles.
#
# === Advice Tracking ===
currentAdvice = None

def send_taming_advice():
    global currentAdvice
    skill = Player.GetRealSkillValue("Animal Taming")
    advice = get_advice(skill)
    if advice is not None and advice != currentAdvice:
        animals_line = ", ".join(advice["animals"])
        cleaned_locations = [re.sub(r"【[^】]*】", "", loc).strip() for loc in advice["locations"]]
        locations_line = ", ".join(cleaned_locations)
        note = advice.get("note", "")
        clean_note = re.sub(r"【[^】]*】", "", note).strip()
        Misc.SendMessage(f"📘 Animal Taming Advice (Skill {skill:.1f})", 78)
        Misc.SendMessage(f"Animals: {animals_line}", 78)
        Misc.SendMessage(f"Locations: {locations_line}", 78)
        # Send the note text if present
        if clean_note:
            Misc.SendMessage(clean_note, 78)
        # Record that we’ve delivered this advice so we don't repeat it
        currentAdvice = advice

# Timer constants are defined in the USER CONFIGURATION section at the top of
# this file (noAnimalsToTrainTimerMilliseconds, playerStuckTimerMilliseconds,
# catchUpToAnimalTimerMilliseconds, animalTamingTimerMilliseconds,
# targetClearDelayMilliseconds).  They should not be redeclared here.

def RetaliateAgainstHostile():
    f = Mobiles.Filter()
    f.Enabled = True
    f.RangeMax = 1
    f.CheckIgnoreObject = False
    f.IsHuman = False
    f.IsGhost = False
    f.Notorieties = List[Byte](bytes([4, 5, 6]))
    mobs = Mobiles.ApplyFilter(f)
    for m in mobs:
        if m.Hits > 0 and m.Hits <= m.HitsMax:
            try:
                Spells.Cast("Lightning")
                if Target.WaitForTarget(1500, False):
                    Target.TargetExecute(m)
                Misc.Pause(250)
            except:
                pass
            break

# Build a reverse index from body id -> Animal meta, used for hardest-nearby mode
_BODY_TO_ANIMAL = None
def _build_body_index():
    global _BODY_TO_ANIMAL
    if _BODY_TO_ANIMAL is None:
        _BODY_TO_ANIMAL = {}
        for a in animals.values():
            if a is not None:
                _BODY_TO_ANIMAL[a.mobileID] = a
    return _BODY_TO_ANIMAL

def FindAnimalToTame():
    if purgeLeftoverPets:
        PurgeOtherPetsNearby(Spells, Mobiles, Target, Misc)
    if autoDefendAgainstAggro:
        RetaliateAgainstHostile()
    if prioritizeHardestNearby:
        body_index = _build_body_index()
        f = Mobiles.Filter()
        f.Enabled = True
        f.RangeMin = 0
        f.RangeMax = 20
        f.IsHuman = False
        f.IsGhost = False
        f.CheckIgnoreObject = True
        nearby = Mobiles.ApplyFilter(f)
        candidates = []
        for m in nearby:
            a = body_index.get(m.Body, None)
            if a is None:
                continue
            if a.minTamingSkill < minimumTamingDifficulty:
                continue
            if m.Name in petsToIgnore:
                continue
            if m.Name in killOnSightPetNames:
                continue
            candidates.append((a.minTamingSkill, m))
        candidates.sort(key=lambda t: t[0], reverse=True)
        if candidates:
            return candidates[0][1]
        return None
    # original behaviour
    skill = Player.GetRealSkillValue("Animal Taming")
    all_eligible = GetTameableAnimalsForSkill(skill)
    for animal in all_eligible:
        if animal.minTamingSkill < minimumTamingDifficulty:
            continue
        f = Mobiles.Filter()
        f.Enabled = True
        f.Bodies = List[Int32]([animal.mobileID])
        f.RangeMin = 0
        f.RangeMax = 20
        f.IsHuman = False
        f.IsGhost = False
        f.CheckIgnoreObject = True
        mobs = Mobiles.ApplyFilter(f)
        if mobs:
            for m in mobs:
                if m.Name not in petsToIgnore and m.Name not in killOnSightPetNames:
                    return m
    return None

def PlayerWalk(direction):
    if Player.Direction == direction:
        Player.Walk(direction)
    else:
        Player.Walk(direction)
        Player.Walk(direction)

def FollowMobile(mobile, maxDistance=3):
    if not Timer.Check("catchUpToAnimalTimer"):
        return False
    playerPos = Player.Position
    targetPos = mobile.Position
    dx = targetPos.X - playerPos.X
    dy = targetPos.Y - playerPos.Y
    if dx > 0 and dy > 0:
        direction = "Down"
    elif dx < 0 and dy > 0:
        direction = "Left"
    elif dx > 0 and dy < 0:
        direction = "Right"
    elif dx < 0 and dy < 0:
        direction = "Up"
    elif dx > 0:
        direction = "East"
    elif dx < 0:
        direction = "West"
    elif dy > 0:
        direction = "South"
    else:
        direction = "North"
    Timer.Create("playerStuckTimer", playerStuckTimerMilliseconds)
    lastPos = Player.Position
    PlayerWalk(direction)
    Misc.Pause(100)
    newPos = Player.Position
    if lastPos == newPos and not Timer.Check("playerStuckTimer"):
        for _ in range(5):
            Player.Walk("Down" if direction == "Up" else "Up")
        Timer.Create("playerStuckTimer", playerStuckTimerMilliseconds)
    if Player.DistanceTo(mobile) > maxDistance:
        FollowMobile(mobile, maxDistance)
    return True

def TryReleasePet(animal):
    """
    Attempt to release a freshly tamed pet by invoking its context menu and
    responding to the confirmation gump appropriately.  Some shards display
    different gumps depending on location (e.g., stable vs. wilderness), so
    we inspect the gump text to decide which button to press.  We also
    verify that the pet has indeed been released by checking its serial or
    control status.
    """
    if animal is None:
        return
    # Small pause so the server updates pet status/name before we act
    Misc.Pause(250)

    # Helper to determine if the pet no longer belongs to us (despawned or
    # uncontrolled).  We check the Controlled flag if available, the
    # ControlMaster, and the pet's name (no longer our standardized name).
    renamed = renameTamedAnimalsTo
    def _release_succeeded():
        m = Mobiles.FindBySerial(animal.Serial)
        if not m:
            return True
        try:
            # On some shards Controlled becomes False when released
            if hasattr(m, "Controlled") and m.Controlled is False:
                return True
            # ControlMaster may be None or different when released
            if hasattr(m, "ControlMaster") and (not m.ControlMaster or m.ControlMaster.Serial != Player.Serial):
                return True
        except Exception:
            pass
        # Name check: released pets revert to their original name
        if m.Name and m.Name != renamed:
            return True
        return False

    # We may need to try multiple times to open the context menu and process
    # different gump types.  Try a few times before giving up.
    maxAttempts = 3
    for attempt in range(1, maxAttempts + 1):
        Misc.SendMessage(f"⚠️ Attempting to release pet ({attempt}/{maxAttempts})", 52)
        # Open the context menu on the pet.  If it does not appear, the pet may
        # already have been released; check and exit early.
        if not Misc.WaitForContext(animal.Serial, 2000):
            Misc.Pause(300)
            if _release_succeeded():
                Misc.SendMessage("✅ Pet released (context unavailable but pet is no longer ours).", 65)
                return
            # Otherwise, retry
            continue
        # Try both possible indices (9 and 8) because the Release entry can move
        # depending on follower slots or shard configuration.
        for idx in (9, 8):
            try:
                Misc.ContextReply(animal.Serial, idx)
                Misc.Pause(300)
            except Exception:
                continue
            # Wait briefly for a gump to appear
            # If no gump appears, we may have clicked the wrong entry or the pet was
            # released instantly.  Check and continue.
            if Gumps.CurrentGump() == 0:
                if _release_succeeded():
                    Misc.SendMessage("✅ Pet released successfully.", 65)
                    return
                continue
            # A gump has appeared.  Read its text to decide which button to press.
            gump_id = Gumps.CurrentGump()
            try:
                lines = Gumps.LastGumpGetLineList()
                lower_lines = [ln.lower() for ln in lines]
            except Exception:
                lower_lines = []
            # Determine gump type
            is_destruction_zone = any(
                ("permanently" in ln and "delete" in ln) or ("cannot" in ln and "be recovered" in ln)
                for ln in lower_lines
            )
            keywords = ["release", "abandon", "dismiss", "free", "are you sure"]
            is_safe_zone = any(any(kw in ln for kw in keywords) for ln in lower_lines)
            # Choose the first button to press based on the gump type.  Many shards
            # use button 1 for deletion and button 2 for safe release.  If we
            # cannot determine the type, start with button 1.
            if is_destruction_zone:
                preferred_buttons = [1, 2]
            elif is_safe_zone:
                preferred_buttons = [2, 1]
            else:
                preferred_buttons = [1, 2]
            # Try each preferred button in order until the gump closes or the pet
            # is released
            for btn in preferred_buttons:
                try:
                    Gumps.SendAction(gump_id, btn)
                    # Allow some time for the action to process
                    Misc.Pause(500)
                except Exception:
                    continue
                # If the gump has closed and the pet is no longer ours, we succeeded
                if Gumps.CurrentGump() == 0 and _release_succeeded():
                    Misc.SendMessage("✅ Pet released successfully.", 65)
                    return
            # If the gump is still open after trying the buttons, close it to avoid stacking
            if Gumps.CurrentGump() != 0:
                try:
                    Gumps.SendAction(Gumps.CurrentGump(), 0)  # attempt to close
                except Exception:
                    pass
            # Check again if the pet has been released before retrying the next index
            if _release_succeeded():
                Misc.SendMessage("✅ Pet released successfully.", 65)
                return
        # Short pause before trying again
        Misc.Pause(400)
        # Check once more if the pet has been released
        if _release_succeeded():
            Misc.SendMessage("✅ Pet released successfully.", 65)
            return
    # If we get here, we failed to release after all attempts
    Misc.SendMessage("❌ Failed to release pet after 3 attempts (leaving it alive).", 33)

def TrainAnimalTaming():
    Journal.Clear()
    Misc.ClearIgnore()
    Player.SetWarMode(True)
    Player.SetWarMode(False)
    animal = None
    timesTried = 0
    tameOngoing = False
    tameHandled = False
    Timer.Create("animalTamingTimer", 1)
    send_taming_advice()
    while not Player.IsGhost and Player.GetRealSkillValue("Animal Taming") < Player.GetSkillCap("Animal Taming"):
        heal_player(
            threshold=healThreshold,
            use_magery=healUsingMagery,
            use_bandages=healUsingBandages,
            use_chivalry=healUsingChivalry,
            use_spirit_speak=healUsingSpiritSpeak,
            use_mysticism=healUsingMysticism,
            use_spellweaving=healUsingSpellweaving,
            use_potions=healUsingPotions,
            use_bushido=healUsingBushido
        )
        # Call pet healing routine once per loop.  This will heal pets and cure poison as needed.
        heal_pets()
        send_taming_advice()
        if animal and not Mobiles.FindBySerial(animal.Serial):
            animal = None
        if maximumTameAttempts and timesTried > maximumTameAttempts:
            Mobiles.IgnoreObject(animal)
            animal = None
            timesTried = 0
        if animal is None:
            animal = FindAnimalToTame()
            if animal is None:
                Misc.Pause(1000)
                continue
            else:
                Mobiles.Message(animal, 90, "Found animal to tame")
        if Player.DistanceTo(animal) > 30:
            animal = None
            continue
        elif Player.DistanceTo(animal) > 3:
            if enableFollowAnimal:
                Timer.Create("catchUpToAnimalTimer", catchUpToAnimalTimerMilliseconds)
                if not FollowMobile(animal, 3):
                    Player.HeadMessage(1100, "Player stuck!")
                    return
        # If we are not currently in a taming attempt and the taming timer has expired,
        # begin a new taming attempt on the current animal.  Always set a timer
        # and mark tameOngoing so that we can detect timeouts even if no journal
        # message is produced (e.g., line of sight issues).
        if not tameOngoing and not Timer.Check("animalTamingTimer"):
            # Clear any pending targets and small pause before starting
            Target.ClearLastandQueue()
            Misc.Pause(targetClearDelayMilliseconds)
            # Use the Animal Taming skill on the selected animal
            Player.UseSkill("Animal Taming")
            # Wait up to 2 seconds for the targeting cursor and then target the animal
            Target.WaitForTarget(2000, True)
            Target.TargetExecute(animal)
            # Start the taming timer immediately to avoid getting stuck; if a journal
            # message indicates we actually started taming, timesTried will be
            # incremented below in the journal checks.
            Timer.Create("animalTamingTimer", animalTamingTimerMilliseconds)
            tameOngoing = True
            # Check if we saw the standard prompt indicating a valid taming attempt.
            if Journal.Search("Tame which animal?"):
                timesTried += 1
            # Whether or not we see the prompt, proceed to journal handling on the
            # next iteration; do not continue here so that timeout handling can run
        # If we are currently taming, check for success, failure, or timeout
        if tameOngoing:
            if Journal.SearchByName("It seems to accept you as master.", animal.Name) or \
               Journal.Search("That wasn't even challenging."):
                # If taming succeeds, rename if necessary and optionally release.  Only
                # attempt rename/release on a valid animal reference.
                if animal is not None:
                    if animal.Name != renameTamedAnimalsTo:
                        Misc.PetRename(animal, renameTamedAnimalsTo)
                    if Player.Followers > numberOfFollowersToKeep:
                        TryReleasePet(animal)
                    # Ignore the animal so it is not re-targeted in future
                    try:
                        Misc.IgnoreObject(animal)
                    except:
                        pass
                animal = None
                timesTried = 0
                tameHandled = True
            elif Journal.Search("You fail to tame the creature.") or \
                 Journal.Search("You must wait a few moments to use another skill."):
                tameHandled = True
            elif Journal.Search("That is too far away.") or \
                 Journal.Search("You are too far away to continue taming.") or \
                 Journal.Search("Someone else is already taming this"):
                animal = None
                timesTried = 0
                Timer.Create("animalTamingTimer", 1)
                tameHandled = True
            elif Journal.Search("You have no chance of taming this creature") or \
                 Journal.Search("Target cannot be seen") or \
                 Journal.Search("This animal has had too many owners") or \
                 Journal.Search("That animal looks tame already.") or \
                 Journal.Search("You do not have a clear path"):
                # This animal is not worth taming; ignore it if valid
                if animal is not None:
                    try:
                        Misc.IgnoreObject(animal)
                    except:
                        pass
                animal = None
                timesTried = 0
                Timer.Create("animalTamingTimer", 1)
                tameHandled = True

            # Timeout handling: if the taming timer has expired and none of the
            # above journal messages have appeared, assume the attempt failed due
            # to a stall (e.g., target inaccessible, stuck behind terrain).  In
            # this case, clear the journal and reset state so that we can
            # identify a new target or re-attempt.  We also ignore this
            # creature so we don't repeatedly get stuck on it.
            if tameOngoing and not Timer.Check("animalTamingTimer"):
                # Consider this a failed attempt due to timeout
                Misc.SendMessage("⌛ Taming attempt timed out, moving on.", 33)
                # Only ignore the object if we still have a valid reference
                if animal is not None:
                    Misc.IgnoreObject(animal)
                animal = None
                timesTried = 0
                tameHandled = True
            if tameHandled:
                # Clear the journal so we don't re-trigger previous messages
                Journal.Clear()
                tameHandled = False
                tameOngoing = False
        Misc.Pause(50)

# Auto-run
TrainAnimalTaming()