"""Where every simulated number comes from.

This is the index that answers "the code says 45 -- says who?". Each hook ties
one constant in set18champs/set18buffs to the exact place in
reference/tft_data.json it was read from, so `python patch_check.py` can
re-read all of them after a patch instead of a person re-reading them by eye.

patch_check.py never edits anything. It prints a list; changing a number is
always a human decision, because "PBE moved" and "I want to follow PBE" are
different questions -- see patch_pin.json.


Three kinds of number, and only one of them is checkable
-------------------------------------------------------
CommunityDragon does not carry the whole game, and the parts it is missing are
exactly the parts this simulator cares most about:

  TRAIT      trait breakpoint variables. Real, complete, and trustworthy.
             Checked automatically, every value, every breakpoint.
  STAT       champion base stats (Health, AD, Attack Speed, Armor, MR, Mana).
             Also real. Also checked automatically.
  CARD       ability damage, cast times, and every per-star spell number.
             NOT checkable: at the time of writing, 2 of the 99 champions in
             the set have real spell DataValues and the rest still ship the
             bin template's placeholders (0/1/2/10...). These numbers were read
             off the champion card or a patch-notes site, so all the checker
             can do is notice that the code still says what we recorded, and
             remind you to look again when the patch moves.

A CARD hook is therefore not a weaker TRAIT hook. It is a different claim:
"a human read this off a card on patch X". Keep them honest and the checker
stays useful; let them rot and it becomes a list of numbers nobody believes.
"""

# --------------------------------------------------------------------------
# Champion base stats: code name -> the set's apiName for that unit.
#
# Adaptors ship as two records (DA_18_Akali_AD / _AP) with different base
# stats; the suffix here names the one the class is actually built from.
# --------------------------------------------------------------------------

CHAMPION_API = {
    "Ahri": "DA_18_Ahri",
    "Aphelios": "DA_18_Aphelios",
    "Akali": "DA_18_Akali_AD",
    "Alune": "DA_18_Alune",
    "Ashe": "DA_18_Ashe",
    "Azir": "DA_18_Azir",
    "Caitlyn": "DA_18_Caitlyn",
    "Camille": "DA_18_Camille",
    "Cassiopeia": "DA_18_Cassiopeia",
    "Cinderling": "DA_Cinderling18",
    "Ezreal": "DA_18_Ezreal",
    "Gromp": "DA_Gromp18_AP",
    "Karma": "DA_Karma18",
    "Kayle": "DA_18_Kayle",
    "LeBlanc": "DA_18_LeBlanc",
    "MamaBeak": "DA_CrimsonRaptor18",
    "MasterYi": "DA_18_MasterYi_AD",
    "Nidalee": "DA_Nidalee18_AP",
    # Riot files him under "Sentry", not his display name.
    "Pebbles": "DA_18_Sentry",
    "Sivir": "DA_18_Sivir",
    "Teemo": "DA_18_Teemo",
    "Varus": "DA_18_Varus",
    "Warwick": "DA_18_Warwick",
    "Xayah": "DA_18_Xayah",
    "Yunara": "DA_18_Yunara",
    "Zyra": "DA_18_Zyra",
}

# champion attribute -> reference stats field. Read off a level-1 instance,
# and off .base rather than .stat so items and traits cannot colour the answer.
STAT_FIELDS = {
    "hp": "hp",
    "atk": "ad",
    "aspd": "attackSpeed",
    "armor": "armor",
    "mr": "mr",
    "fullMana": "maxMana",
}


# --------------------------------------------------------------------------
# Traits.
#
#   attr      the code's {breakpoint: value} dict, or a plain number
#   variable  the name inside the breakpoint's variables
#   scale     multiply the reference value by this to get the code's units.
#             100 where the code stores 20 for a reference 0.20.
#   note      why a hook is shaped oddly, when it is
# --------------------------------------------------------------------------

TRAIT_HOOKS = [
    # (trait class, code attribute, apiName, variable, scale)
    ("Rapidfire", "per_attack_scaling", "DA_18_Rapidfire", "ASperAttack", 100),
    ("Rapidfire", "team_as", "DA_18_Rapidfire", "TeamAS", 100),
    ("Rapidfire", "max_stacks", "DA_18_Rapidfire", "MaxStacks", 1),
    ("Blossom", "scaling", "DA_18_Blossom", "ADAP", 100),
    ("Fae", "scaling", "DA_18_Fae", "ADAP", 1),
    ("Hunter", "scaling", "DA_18_Hunter", "HunterAD", 100),
    ("Invoker", "team_mana_regen", "DA_18_Invoker", "TeamManaRegen", 1),
    ("Invoker", "invoker_mana_regen", "DA_18_Invoker", "InvokerManaBonus", 1),
    ("Executioner", "crit_bonus", "DA_18_Executioner", "CritChance", 1),
    ("Executioner", "bleed_scaling", "DA_18_Executioner", "BonusBleedPercent", 1),
    ("Executioner", "bleed_duration", "DA_18_Executioner", "BleedDuration", 1),
    ("Adaptor", "scaling", "DA_18_Adaptor", "ADAPGain", 100),
    ("Spellweaver", "spellweaver_ap", "DA_18_Spellweaver", "SpellweaverAP", 100),
    ("Spellweaver", "team_ap", "DA_18_Spellweaver", "TeamwideAP", 100),
    ("Spellweaver", "ap_per_cast", "DA_18_Spellweaver", "APPerCast", 100),
    ("Lunar", "scaling", "DA_18_Lunar", "AttackSpeed", 100),
    ("Solar", "bonus_magic_damage", "DA_18_Solar", "BonusMagicDamage", 1),
    ("Solar", "per_three_star", "DA_18_Solar", "PercentIncreasePer3Star", 1),
    ("Solar", "shield_ratio", "DA_18_Solar", "ShieldRatio", 1),
    ("Solar", "threshold1", "DA_18_Solar", "NumThreeStarThreshold1", 1),
    ("Solar", "threshold1_aspd", "DA_18_Solar", "Threshold1AttackSpeed", 100),
    ("Solar", "threshold1_resists", "DA_18_Solar", "Threshold1ArmorMagicResist", 1),
    ("Solar", "threshold2", "DA_18_Solar", "NumThreeStarThreshold2", 1),
    ("Solar", "threshold2_true_conversion", "DA_18_Solar",
     "Threshold2TrueDamageConversion", 1),
    ("Ravager", "scaling", "DA_18_Slayer", "BonusDamagePercentBase", 1),
    ("Ravager", "omnivamp_bonus", "DA_18_Slayer", "Omnivamp", 1),
    ("Blackthorn", "team_health", "DA_18_Blackthorn", "Health", 1),
    ("Riftbeast", "stat_scaling", "DA_Riftbeast18", "CapstoneAD", 100),
    ("Riftbeast", "resist_scaling", "DA_Riftbeast18", "CapstoneArmor", 1),
    ("Riftbeast", "hp_scaling", "DA_Riftbeast18", "CapstoneHealth", 1),
    ("Riftbeast", "mana_regen_scaling", "DA_Riftbeast18", "CapstoneManaRegen", 1),
]

# Hooks whose code value is a rule applied to the reference value rather than
# a copy of it. Checked the same way, with the rule spelled out.
#
#   Blackthorn's bonus_scaling stores the multiplier (1.3), the reference the
#   bonus (0.3). Summoner's (3) row is the (2) row +50%, applied by the trait
#   rather than written into the data -- both breakpoints carry the same
#   variables, so a naive check would demand the code repeat them.
DERIVED_TRAIT_HOOKS = [
    ("Blackthorn", "bonus_scaling", "DA_18_Blackthorn", "StatMultiplier",
     lambda ref: 1.0 + ref, "code stores 1+x, data stores x"),
    ("Summoner", "zyra_bonus_attacks", "DA_18_Summoner", "NumExtraAttacks",
     None, "(3) is (2) +50%, applied by the trait -- data repeats the (2) row"),
    ("Summoner", "dmg_mult", "DA_18_Summoner", "DamageMult",
     None, "(3) is (2) +50%, applied by the trait -- data repeats the (2) row"),
    ("Summoner", "azir_dmg_mult", "DA_18_Summoner", "AzirDamageMult",
     None, "as dmg_mult; PBE 18.2 split Azir's summons onto their own variable"),
]


# --------------------------------------------------------------------------
# Trait values with no reference at all: the trait exists, but the numbers the
# simulator needs are not in its breakpoint variables. Listed so the checker
# can report them as unbacked rather than silently checking nothing.
# --------------------------------------------------------------------------

TRAIT_CARD_ONLY = {
    "Primal": ("primal_as", "team_as", "trigger_time"),
    "Greenfather": ("flower_aspd", "mushroom_amp", "water_mana_regen"),
}
