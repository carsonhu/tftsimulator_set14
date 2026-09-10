# ...existing code...
import ast
from collections import deque

from item import Item
from role import Role
from stats import Attack, JhinBonusAD
from utils import lucky_chance

import status


def get_classes_from_file(file_path):
    with open(file_path, "r") as file:
        file_content = file.read()

    # Parse the file content into an AST
    tree = ast.parse(file_content)

    # Extract all class definitions
    classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    return classes


class_buffs = [
    "Rapidfire",
    "Blossom",
    "Fae",
    "Executioner",
    "Riftbeast",
    "Summoner",
    "Spellweaver",
    "Adaptor",
    "Ravager",
    "Blackthorn",
    "Lunar",
    "Solar",
    "Primal",
    "Greenfather",
    "Hunter",
    "Invoker",
]

augments = [
    "Shred30",
    "Shred20",
    "TinyButDeadly",
    "StandUnitedI",
    "Ascension",
    "HoldTheLine5",
    "HoldTheLine7",
    "TonsOfStats",
    "TonsOfStatsPris",
    "JeweledLotusI",
    "JeweledLotusII",
    "SeraphimsStaff",
    "Retribution",
    "GlassCannonI",
    "GlassCannonII",
    "ItsMeBaby",
    "NoScoutNoPivot",
    "SoulAwakening",
    "FocusedFire",
    "Corrosion",
    "CryMeARiver",
    "WarlordsHonor",
    "Kahunahuna",
    "ClockworkAccelerator",
    "BaronsLair",
    "PartialAscension",
    "EarlyLearnings",
]

stat_buffs = ["ASBuff"]

no_buff = ["NoBuff"]

wisps = [
    "Flow",
    "ProlificPower",
    "UltraAscension",
    "CrystalBall",
    "Hummingbird",
    "Rain",
    "Downpour",
    "TatteredArmor",
    "MarksmensGale",
    "Supercritical",
    "BackrowStar",
]


class ChampionAbilityScaling:
    """Picklable wrapper for champion ability scaling."""

    def __init__(self, champion):
        self.champion = champion

    def __call__(self, level, AD, bonusAD, AP):
        return self.champion.abilityScaling(level, bonusAD, AP)


class ScaledChampionAbilityScaling:
    """Picklable wrapper for scaled champion ability scaling."""

    def __init__(self, champion, scale_factor):
        self.champion = champion
        self.scale_factor = scale_factor

    def __call__(self, level, AD, bonusAD, AP):
        return self.scale_factor * self.champion.abilityScaling(level, bonusAD, AP)


class ScaledChampionAbilityScaling2:
    """Picklable wrapper for scaled champion ability scaling.
    we'll fix this lmao"""

    def __init__(self, champion, scale_factor):
        self.champion = champion
        self.scale_factor = scale_factor

    def __call__(self, level, bonusAD, AP):
        return self.scale_factor * self.champion.abilityScaling(level, bonusAD, AP)


class ChampionEmpoweredAbilityScaling:
    """Picklable wrapper for a champion's empoweredScaling (its second damage
    row), for attack replacements whose empowered hit isn't a constant
    multiple of abilityScaling (so ScaledChampionAbilityScaling can't
    express it)."""

    def __init__(self, champion):
        self.champion = champion

    def __call__(self, level, AD, bonusAD, AP):
        return self.champion.empoweredScaling(level, bonusAD, AP)


class Buff(Item):
    levels = [0]

    def __init__(self, name, level, params, phases):
        super().__init__(name, phases=phases)
        self.level = level
        self.params = params

    def performAbility(self, phase, time, champion, input_=0):
        raise NotImplementedError("Please Implement this method")

    def ability(self, phase, time, champion, input_=0):
        # if it's level 0 of an ability
        if self.level == 0:
            return input_
        if self.phases and phase in self.phases:
            return self.performAbility(phase, time, champion, input_)
        return input_

    def extraParameters():
        return 0

    def hashFunction(self):
        # Hash function used for caching;
        # (name, level, params)
        init_tuple = (self.name, str(self.level))
        if isinstance(self.params, int):
            param_tuple = (self.params,)
        else:
            param_tuple = tuple(self.params)
        return init_tuple + param_tuple

    def __hash__(self):
        return hash(self.hashFunction())


class NoBuff(Buff):
    levels = [0]
    display_name = "NoItem"

    def __init__(self, level, params):
        # params is number of stacks
        super().__init__(self.display_name, level, params, phases=None)

    def performAbility(self, phase, time, champion, input_=0):
        return 0


class ASBuff(Buff):
    levels = [1]
    display_name = "Attack Speed Buff"

    def __init__(self, level, params):
        # params is number of stacks
        super().__init__(
            f"{self.display_name} {level}", level, params, phases=["preCombat"]
        )
        self.as_buff = 0
        self.extraBuff(params)

    def performAbility(self, phase, time, champion, input_=0):
        champion.aspd.addStat(self.as_buff)
        return 0

    def extraParameters():
        # defining the parameters for the extra shit
        return {"Title": "AS", "Min": 0, "Max": 100, "Default": 0}

    def extraBuff(self, as_buff):
        self.as_buff = as_buff


# CLASS BUFFS


class Rapidfire(Buff):
    levels = [0, 2, 3, 4, 5]
    display_name = "Rapidfire"

    def __init__(self, level, params):
        super().__init__(
            f"{self.display_name} {level}",
            level,
            params,
            phases=["preCombat", "postAttack"],
        )
        # 18.2 (official notes, not on PBE): (4)/(5) went 9/15 -> 8/12.
        # The cdragon pbe dump still reads 9/15 -- acknowledged in
        # patch_pin.json rather than followed.
        self.per_attack_scaling = {0: 0, 2: 3, 3: 5, 4: 8, 5: 12}
        self.max_stacks = 10
        # Named rather than written into performAbility as a literal 10, so
        # patch_check can point a hook at it. An unnamed constant is one no
        # patch check can ever see.
        self.team_as = 10
        self.stacks = 0

    def extraParameters():
        return {"Title": "Is Rapidfire", "Min": 0, "Max": 1, "Default": 1}

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "preCombat":
            # Team gains 10% Attack Speed
            champion.aspd.addStat(self.team_as)
        if phase == "postAttack":
            # Rapidfire champions gain more on every attack, up to 10 stacks.
            # extraParams ("Is Rapidfire") == 1 flags this holder as a full
            # trait member rather than just a teammate benefiting from the
            # flat 10% aura.
            if self.stacks < self.max_stacks and self.params == 1:
                self.stacks += 1
                champion.aspd.addStat(self.per_attack_scaling[self.level])
        return 0


class Blossom(Buff):
    levels = [0, 3, 5, 7, 9, 11]
    display_name = "Blossom"

    def __init__(self, level, params):
        super().__init__(
            f"{self.display_name} {level}", level, params, phases=["preCombat"]
        )
        # "After combat, your Wisps are empowered" and the shop-side Wisp
        # mechanics are out of scope for a combat simulator -- only the
        # AD/AP grant is modeled.
        self.scaling = {0: 0, 3: 12, 5: 30, 7: 45, 9: 50, 11: 100}

    def extraParameters():
        return {"Title": "Is Blossom", "Min": 0, "Max": 1, "Default": 1}

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "preCombat":
            # The AD/AP is the members' half. The Wisp upgrade below is not:
            # a Wisp is held by a champion, and the board's Blossom count is
            # what empowers it, so a non-member holding one still gets the
            # upgraded version. That split is the whole reason this trait can
            # sit in Team Traits -- at params 0 the stats stay off and the
            # Wisps still read the level.
            #
            # Team Traits shows this as a checkbox, not a level picker, and
            # that is right: what a non-member gets is a threshold
            # (_is_blossom_upgraded, 3+), and every active breakpoint clears
            # it, so 3 and 11 hand a non-member exactly the same thing. The
            # 11-Blossom wisps that would break the tie are not modeled here.
            if self.params == 1:
                amt = self.scaling[self.level]
                champion.bonus_ad.addStat(amt)
                champion.ap.addStat(amt)
            # Wisps (below) read this during postPreCombat to decide whether
            # their Blossom-upgraded values apply -- postPreCombat runs after
            # every item's preCombat phase, so it's the earliest point a Wisp
            # can reliably see this regardless of item ordering.
            champion.blossom_level = self.level
        return 0


class Executioner(Buff):
    levels = [0, 2, 3, 4]
    display_name = "Executioner"

    def __init__(self, level, params):
        super().__init__(
            f"{self.display_name} {level}",
            level,
            params,
            phases=["preCombat", "PostOnDealDamage"],
        )
        self.crit_bonus = 0.15
        # (2) grants Precision + crit only; bleed starts at (3)
        self.bleed_scaling = {0: 0, 2: 0, 3: 0.30, 4: 0.40}
        self.bleed_duration = 3.0

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "preCombat":
            if self.level >= 2:
                champion.crit.addStat(self.crit_bonus)
                champion.addPrecision()
        if phase == "PostOnDealDamage":
            bleed_pct = self.bleed_scaling.get(self.level, 0)
            target = champion.lastDamagedOpponent
            if bleed_pct > 0 and target is not None and input_:
                target.applyStatus(
                    status.ExecutionerBleedStatus(),
                    champion,
                    time,
                    self.bleed_duration,
                    input_[0] * bleed_pct,
                )
        return 0


class Riftbeast(Buff):
    levels = [0, 3, 7]
    display_name = "Riftbeast"
    # "Is Alpha" is which single champion holds the Alpha Mark, not team
    # membership, so this trait must not be offered in the Team Traits panel
    # despite carrying a 0/1 parameter (see sim_entry's team_buffs discovery).
    team_trait = False

    def __init__(self, level, params):
        alpha_label = "Alpha" if params == 1 else "Not Alpha"
        super().__init__(
            f"{self.display_name} {level} ({alpha_label})",
            level,
            params,
            phases=["preCombat", "onUpdate"],
        )
        # (5) shop-overrun and (10) +2 team size are meta/shop mechanics,
        # out of scope for a combat simulator -- only (3) and (7) are modeled.
        self.stat_scaling = 5  # AD/AS/AP %
        self.resist_scaling = 5  # Armor/MR
        self.hp_scaling = 50
        self.mana_regen_scaling = 1
        self.interval = 5
        self.next_bonus = 0

    def extraParameters():
        return {"Title": "Is Alpha", "Min": 0, "Max": 1, "Default": 1}

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "preCombat":
            if self.level >= 3 and self.params == 1:
                # (3) Alpha Mark grants its holder a champion-specific unique
                # buff. Only the boolean flag is modeled here -- the actual
                # unique buffs (e.g. Mama Beak's Orange Buff armor shred) are
                # unimplemented for now (see set18champs.MamaBeak).
                champion.riftbeast_alpha_mark = True
        elif phase == "onUpdate":
            if self.level >= 7 and time >= self.next_bonus:
                self.next_bonus += self.interval
                champion.bonus_ad.addStat(self.stat_scaling)
                champion.aspd.addStat(self.stat_scaling)
                champion.ap.addStat(self.stat_scaling)
                champion.armor.addStat(self.resist_scaling)
                champion.mr.addStat(self.resist_scaling)
                champion.hp.addStat(self.hp_scaling)
                champion.manaRegen.addStat(self.mana_regen_scaling)
        return 0


class Summoner(Buff):
    levels = [0, 2, 3]
    display_name = "Summoner"

    def __init__(self, level, params):
        super().__init__(
            f"{self.display_name} {level}", level, params, phases=["preCombat"]
        )
        # Yorick (+30% Health) is unimplemented for now -- Zyra's extra
        # plant attacks and Mama Beak's/Azir's Damage are modeled.
        self.zyra_bonus_attacks = {0: 0, 2: 4, 3: 6}
        # (3) improves (2)'s bonus by 50% -> x1.5, not a flat doubling.
        #
        # The two summons used to share one multiplier. PBE 18.2 split them:
        # DamageMult (0.45) is now Mama Beak's alone and Azir's soldiers read
        # their own AzirDamageMult (0.20), so they need separate rows.
        self.dmg_mult = {0: 1.0, 2: 1.45, 3: 1 + 0.45 * 1.5}
        self.azir_dmg_mult = {0: 1.0, 2: 1.20, 3: 1 + 0.20 * 1.5}

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "preCombat":
            champion.summoner_bonus_attacks = self.zyra_bonus_attacks.get(self.level, 0)
            champion.summoner_dmg_mult = self.dmg_mult.get(self.level, 1.0)
            champion.summoner_azir_dmg_mult = self.azir_dmg_mult.get(self.level, 1.0)
        return 0


class Spellweaver(Buff):
    levels = [0, 2, 4, 6]
    display_name = "Spellweaver"

    def __init__(self, level, params):
        super().__init__(
            f"{self.display_name} {level}",
            level,
            params,
            phases=["preCombat", "postAbility"],
        )
        # The team-wide half doesn't scale with the breakpoint: everyone gets a
        # flat 10 AP at every tier. Only the Spellweavers' own grant scales,
        # and it stacks on top of the aura -- a Spellweaver at (4) holds
        # 10 + 30 = 40, not 30.
        self.team_ap = 10
        # extraParams ("Is Spellweaver") == 1 flags this holder as an actual
        # Spellweaver unit rather than a teammate benefiting from the aura.
        self.spellweaver_ap = {0: 0, 2: 10, 4: 30, 6: 55}
        self.ap_per_cast = {0: 0, 2: 1, 4: 1, 6: 2}

    def extraParameters():
        return {"Title": "Is SWeaver", "Min": 0, "Max": 1, "Default": 1}

    def performAbility(self, phase, time, champion, input_=0):
        is_spellweaver = self.params == 1
        if phase == "preCombat":
            champion.ap.addStat(self.team_ap)
            if is_spellweaver:
                champion.ap.addStat(self.spellweaver_ap.get(self.level, 0))
        elif phase == "postAbility" and is_spellweaver:
            champion.ap.addStat(self.ap_per_cast.get(self.level, 0))
        return 0


def resolveAdaptorVersion(champion):
    """Decide (once) whether an Adaptor unit is on its AD or AP version.

    Cached on the champion so the Adaptor trait's stat grant and the unit's own
    ability can never disagree, whichever of them runs first within
    postPreCombat. The grant can't flip the answer anyway -- it always feeds
    whichever stat is already ahead -- but pinning it keeps that guarantee from
    depending on item ordering.

    Which version an untouched Adaptor starts on is per-unit, not a single
    rule: Gromp and Nidalee tie to AP, Master Yi, Kog'Maw and Akali tie to AD.
    Units advertise it as adaptor_ties_to_ad; anything that doesn't set the
    attribute gets the AD default.
    """
    if not getattr(champion, "adaptor_resolved", False):
        if champion.bonus_ad.stat == champion.ap.stat:
            champion.ad_version = getattr(champion, "adaptor_ties_to_ad", True)
        else:
            champion.ad_version = champion.bonus_ad.stat > champion.ap.stat
        champion.adaptor_resolved = True
    return champion.ad_version


class Adaptor(Buff):
    """Adaptor: gain AP or AD, whichever of the two is already higher.

    The innate half of the trait (which version of the ability an Adaptor
    casts) is handled by AdaptorInnate, which sits on the unit rather than
    here -- an Adaptor unit switches its ability based on its own stats
    whether or not enough Adaptors are fielded to hit a breakpoint.

    Runs on postPreCombat, not preCombat: every other trait/item/augment AD and
    AP grant lands in preCombat, so postPreCombat is the earliest phase where
    the comparison sees final combat-start stats regardless of item order --
    the same reasoning the Wisps use for reading blossom_level.
    """

    levels = [0, 2, 3, 4]
    display_name = "Adaptor"

    def __init__(self, level, params):
        super().__init__(
            f"{self.display_name} {level}", level, params, phases=["postPreCombat"]
        )
        self.scaling = {0: 0, 2: 25, 3: 35, 4: 50}

    def performAbility(self, phase, time, champion, input_=0):
        # No "Is Adaptor" param: unlike Rapidfire/Spellweaver there's no
        # team-wide half of this trait, so only Adaptors ever hold it.
        amount = self.scaling.get(self.level, 0)
        if amount:
            if resolveAdaptorVersion(champion):
                champion.bonus_ad.addStat(amount)
            else:
                champion.ap.addStat(amount)
        return 0


class Ravager(Buff):
    """Ravager: flat bonus damage, multiplicative with damage amplification.

    Ravager-only, like Adaptor -- there's no team-wide half, so no
    "Is Ravager" param.

    The bonus lands on extraDmgMultiplier rather than dmgMultiplier because
    it's a separate multiplier in game: dmgMultiplier is the additive amp pool
    every item and augment feeds (Giant Slayer, Rabadon's, Glass Cannon...),
    and Ravager multiplies against the total of that pool instead of joining
    it. extraDmgMultiplier was unused before this, so nothing else competes
    for the slot -- worth knowing that two sources sharing it WOULD be
    additive with each other, so a second multiplicative amp needs its own
    multiplier rather than this one.

    The "doubled against units below 50% Health" half is not modeled: the
    sim's opponents are damage sponges whose HP the frame loop never
    decrements, so there's no health percentage to threshold on.
    """

    levels = [0, 2, 4, 6]
    display_name = "Ravager"

    def __init__(self, level, params):
        super().__init__(
            f"{self.display_name} {level}", level, params, phases=["preCombat"]
        )
        self.scaling = {0: 0, 2: 0.12, 4: 0.25, 6: 0.40}
        # Cosmetic here -- omnivamp is tracked and displayed but heals nothing,
        # since nothing in the sim damages the champion being measured.
        self.omnivamp_bonus = 0.10

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "preCombat":
            champion.extraDmgMultiplier.addStat(self.scaling.get(self.level, 0))
            champion.omnivamp.addStat(self.omnivamp_bonus)
        return 0


class Lunar(Buff):
    """Lunar: Attack Speed and Ability Power, doubled on Lunar champions.

    "Lunar champions and adjacent allies gain..." is a single aura, not one
    per neighbour -- you get it once whether it came from yourself or from the
    unit beside you. So the trait level only selects which row of the table
    applies; it does not multiply. What "Lunar champions gain 100% more" buys
    is the x2, which is what the Is Lunar param picks out (1 = the holder is
    itself Lunar, 0 = it is an adjacent ally riding the aura).

    Both halves are the same number, and both are additive with every other
    source: aspd.addStat is percentage points of base AS, ap.addStat is AP
    points against the 100 base, so "7%" is +7 to each.
    """

    levels = [0, 2, 3, 4, 5]
    display_name = "Lunar"

    def __init__(self, level, params):
        super().__init__(
            f"{self.display_name} {level}", level, params, phases=["preCombat"]
        )
        self.scaling = {0: 0, 2: 7, 3: 10, 4: 14, 5: 18}
        self.lunar_multiplier = 2

    def extraParameters():
        return {"Title": "Is Lunar", "Min": 0, "Max": 1, "Default": 1}

    def performAbility(self, phase, time, champion, input_=0):
        if phase != "preCombat":
            return 0
        amount = self.scaling.get(self.level, 0)
        if self.params == 1:
            amount *= self.lunar_multiplier
        champion.aspd.addStat(amount)
        champion.ap.addStat(amount)
        return 0


class Solar(Buff):
    """Solar: bonus magic damage on everything, scaled by 3-star Solars.

    Solar has a single breakpoint, (3), so its level is on/off and the real
    dial is how many unique 3-star Solar champions the board runs. That is the
    parameter -- and it is what the Trait slice sweeps, since sweeping a
    one-breakpoint level answers nothing.

    The bonus is a share of the damage that triggered it, taken PRE-mitigation
    and dealt as its own magic instance: 8% of a 100-damage hit is 8 magic
    damage, which the target's Magic Resist then reduces. That is not the same
    thing as an 8% damage amp, and the difference is not small -- an amp would
    be reduced by the *Armor* an attack was already being reduced by. The two
    only agree when a target's Armor and Magic Resist are equal, which is why
    this splits the hit in two rather than adding to dmgMultiplier.

    Two rows of the card are deliberately not modeled. The 5% max Health
    shield protects the champion being measured, and nothing in this sim
    damages it, so it would price at exactly zero. And the 8-three-star row (a
    3-star ascending to 4-star every 4s) is out of reach on purpose: the
    parameter stops at 5, and 4-star ascension is not modeled anywhere.
    """

    levels = [0, 3]
    display_name = "Solar"
    # The Trait slice varies the parameter instead of the level. Solar has one
    # breakpoint, so its level rows are just on and off, while "how many
    # 3-stars" is the question the tab exists to answer.
    sweep_params = True

    # The parameter's options. They are the count itself, so params indexes
    # straight in and `int(params)` is the number of 3-stars.
    three_star_counts = ["0", "1", "2", "3", "4", "5"]

    # Team-wide, at every breakpoint: a share of damage dealt, again as damage.
    bonus_magic_damage = 0.08
    # Added to that share (and to the shield) by each unique 3-star Solar.
    per_three_star = 0.01
    # 3-stars needed for the Attack Speed and resist row...
    threshold1 = 3
    threshold1_aspd = 15
    # 18.2 (official notes, not on PBE): 15 -> 12. cdragon still says 15;
    # acknowledged in patch_pin.json.
    threshold1_resists = 12
    # ...and for 40% of the bonus to become true damage.
    threshold2 = 5
    threshold2_true_conversion = 0.4
    # Not modeled (see the class docstring); named so patch_check can still
    # see the number and report it moving.
    shield_ratio = 0.05

    def __init__(self, level, params):
        # The count is meaningless with the trait off, and six identical
        # "off" rows differing only in a name that claims otherwise would be
        # worse than one.
        name = (
            f"{self.display_name} {level}"
            if level == 0
            else f"{self.display_name} {level} ({self.threeStars(params)}x 3-star)"
        )
        super().__init__(
            name,
            level,
            params,
            phases=["preCombat", "onDealDamage", "PostOnDealDamage"],
        )
        # Set on onDealDamage, spent on PostOnDealDamage -- see performAbility.
        self.pending = 0.0

    @classmethod
    def threeStars(cls, params):
        try:
            return max(0, min(int(params), len(cls.three_star_counts) - 1))
        except (TypeError, ValueError):
            return 0

    def extraParameters():
        return {
            "Title": "# of 3-stars",
            "Min": 0,
            "Max": len(Solar.three_star_counts) - 1,
            "Default": 0,
            "Options": Solar.three_star_counts,
        }

    def bonusRatio(self):
        """The share of each hit that comes back as bonus damage."""
        return self.bonus_magic_damage + self.per_three_star * self.threeStars(
            self.params
        )

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "preCombat":
            if self.threeStars(self.params) >= self.threshold1:
                champion.aspd.addStat(self.threshold1_aspd)
                champion.armor.addStat(self.threshold1_resists)
                champion.mr.addStat(self.threshold1_resists)
            return 0

        if phase == "onDealDamage":
            # input_ is the damage BEFORE resists, which is the base the card
            # takes its percentage of. Only remembered here: the target of
            # this instance is not known until doDamage records it, one line
            # further down, so the payout waits for PostOnDealDamage.
            self.pending = input_ * self.bonusRatio()
            return input_

        # PostOnDealDamage: lastDamagedOpponent is now this instance's target.
        bonus, self.pending = self.pending, 0.0
        target = champion.lastDamagedOpponent
        if bonus <= 0 or target is None:
            return 0
        # Above the second threshold half of it arrives as true damage
        # instead, which is a different mitigation, not a bigger number.
        true_share = (
            self.threshold2_true_conversion
            if self.threeStars(self.params) >= self.threshold2
            else 0.0
        )
        for amount, dtype in (
            (bonus * (1 - true_share), "magical"),
            (bonus * true_share, "true"),
        ):
            if amount <= 0:
                continue
            # No items: this is damage caused by a damage instance, and
            # letting it back through the on-damage phases would have it
            # trigger itself. Same reason SoulAwakening passes [] here.
            champion.doDamage(target, [], 0, amount, amount, dtype, time)
        return 0


class Fae(Buff):
    """Fae: Attack Damage and Ability Power per Pixie, for Fae champions.

    The level picks the rate and the Pixie count multiplies it, which is why
    the count is the parameter: Pixies are attracted by the whole team's
    damage, healing and shielding, so how many are out is a fact about the
    board's fight rather than something this simulator can derive from the one
    champion in front of it. It defaults to 7 because that is where the count
    stops buying stats -- past 7 the Pixies turn Golden and grant gold instead.

    There is no Team Traits row for this. The stats go to Fae champions only,
    so a board running Fae hands a non-Fae champion nothing at all, and a
    trait with no team-wide half has no membership to disclaim. The parameter
    shape (0-7 rather than a 0/1 flag) keeps it out of that panel on its own.

    The heal -- 2%/4% per Pixie once below 50% Health -- is not modeled:
    nothing in this sim damages the champion being measured, so it would price
    at exactly zero, same as Solar's shield.
    """

    levels = [0, 2, 4]
    display_name = "Fae"

    # % Attack Damage and Ability Power per Pixie.
    scaling = {0: 0, 2: 5, 4: 8}
    max_pixies = 7

    def __init__(self, level, params):
        # The count buys nothing with the trait off, so an off row says so
        # once rather than seven times over.
        name = (
            f"{self.display_name} {level}"
            if level == 0
            else f"{self.display_name} {level} ({self.pixies(params)} Pixies)"
        )
        super().__init__(name, level, params, phases=["preCombat"])

    @classmethod
    def pixies(cls, params):
        try:
            return max(0, min(int(params), cls.max_pixies))
        except (TypeError, ValueError):
            return 0

    def extraParameters():
        return {"Title": "Pixies", "Min": 0, "Max": Fae.max_pixies, "Default": 7}

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "preCombat":
            # Both halves are the same number and both are additive with every
            # other source: bonus_ad and ap are each read as (100 + add) / 100,
            # so "8% per Pixie" at 7 Pixies is +56 to each.
            amount = self.scaling.get(self.level, 0) * self.pixies(self.params)
            champion.bonus_ad.addStat(amount)
            champion.ap.addStat(amount)
        return 0


class Hunter(Buff):
    """Hunter: the Attack Damage half only.

    The trait's other half -- 10% Damage Amp once a Hunter has held the same
    target for 4 seconds -- is not modeled, per request. It would be nearly
    free here anyway: this sim points a champion at a dummy that never dies
    and never moves, so the condition would be met at t=4 in every single run
    and the "if" would price as an unconditional amp handed out on a timer.
    That is a fact about the test harness, not about the trait.

    No extraParameters, and so no row in Team Traits: the AD goes to Hunters,
    with nothing left over for the rest of the board. A champion who is not a
    Hunter gets nothing from a team running Hunter, which is exactly what an
    absent row says.
    """

    levels = [0, 2, 3, 4, 5]
    display_name = "Hunter"

    def __init__(self, level, params):
        super().__init__(
            f"{self.display_name} {level}", level, params, phases=["preCombat"]
        )
        self.scaling = {0: 0, 2: 20, 3: 30, 4: 45, 5: 65}

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "preCombat":
            champion.bonus_ad.addStat(self.scaling[self.level])
        return 0


class Invoker(Buff):
    """Invoker: Mana Regen for the whole team, more for Invokers.

    "increased for Invokers" is instead-of, not on-top-of: the card's two
    numbers ("1 | 3") are what a teammate gets and what an Invoker gets, so
    an Invoker at (2) regens 3, not 1 + 3. The Is Invoker param picks which
    half the holder is on.

    Both halves step with the breakpoint, so the trait's level is a real
    question even for a non-Invoker -- which is why it earns a level row in
    Team Traits rather than a bare on/off.
    """

    levels = [0, 2, 3, 4, 5]
    display_name = "Invoker"

    def __init__(self, level, params):
        super().__init__(
            f"{self.display_name} {level}", level, params, phases=["preCombat"]
        )
        # (2) 1 | 3, (3) 1 | 4, (4) 2 | 6, (5) 2 | 9
        self.team_mana_regen = {0: 0, 2: 1, 3: 1, 4: 2, 5: 2}
        self.invoker_mana_regen = {0: 0, 2: 3, 3: 4, 4: 6, 5: 9}

    def extraParameters():
        return {"Title": "Is Invoker", "Min": 0, "Max": 1, "Default": 1}

    def performAbility(self, phase, time, champion, input_=0):
        if phase != "preCombat":
            return 0
        table = (
            self.invoker_mana_regen if self.params == 1 else self.team_mana_regen
        )
        champion.manaRegen.addStat(table.get(self.level, 0))
        return 0


class Primal(Buff):
    """Primal: Blessing of the Tiger only.

    In game the trait is (0/2/4) and each breakpoint hands out blessings, but
    most of them are non-combat; the only one a DPS sim can price is the
    Blessing of the Tiger's delayed Attack Speed, so the trait collapses to
    on/off ([0, 1]) here. The Is Primal param picks which half of the blessing
    the holder gets (1 = a Primal champion's 35%, 0 = a teammate's 15% --
    "instead", not stacked).
    """

    levels = [0, 1]
    # Named for the blessing rather than the trait: Primal hands out several,
    # and the Tiger's Attack Speed is the only one this prices. Seeing which
    # one is on the row matters more than matching the trait's in-game name.
    display_name = "Primal (Tiger)"

    def __init__(self, level, params):
        super().__init__(
            f"{self.display_name} {level}", level, params, phases=["onUpdate"]
        )
        self.trigger_time = 6
        self.primal_as = 35
        self.team_as = 15
        self.triggered = False

    def extraParameters():
        return {"Title": "Is Primal (Tiger)", "Min": 0, "Max": 1, "Default": 1}

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "onUpdate" and not self.triggered and time >= self.trigger_time:
            self.triggered = True
            champion.aspd.addStat(
                self.primal_as if self.params == 1 else self.team_as
            )
        return 0


class Greenfather(Buff):
    """Greenfather: the bonus the grown hex gives whoever stands on it.

    Ivern spends seeds to grow one hex, and its type decides which stat the
    occupant gets. Only one hex exists at a time, so this is one buff with a
    Hex parameter rather than three that could all be ticked at once -- the
    choice is the point.

    The level is Ivern's star level, not a trait breakpoint: Greenfather is a
    one-unit trait, and how much the hex gives depends on how big he is.

    Rocks (Armor/MR) and Trees (Health) are the other two hex types and are
    not offered here: nothing in this sim damages the champion being measured,
    so both would price at exactly zero.
    """

    levels = [0, 1, 2, 3]
    display_name = "Greenfather"

    # Ordered as the parameter's options, so params indexes straight in.
    hexes = ["Flower", "Mushroom", "Water"]
    # The stat each hex grants, for the icon the Team Traits panel draws
    # beside the picker. Declared here rather than hardcoded in the frontend:
    # which stat a Flower gives is a fact about this trait, not about the UI.
    option_stats = ["scaleAS", "scaleDA", "scaleManaRegen"]
    # Per Ivern star. The 3-star row really is that much larger than the
    # 2-star; that is what the champion card says.
    flower_aspd = [10, 15, 200]  # % Attack Speed
    mushroom_amp = [0.08, 0.12, 2.00]  # damage amp
    water_mana_regen = [1, 2, 30]

    def __init__(self, level, params):
        super().__init__(
            f"{self.display_name} {level} ({self.hexName(params)})",
            level,
            params,
            phases=["preCombat"],
        )

    @classmethod
    def hexName(cls, params):
        try:
            return cls.hexes[int(params)]
        except (IndexError, TypeError, ValueError):
            return cls.hexes[0]

    def extraParameters():
        return {
            "Title": "Hex",
            "Min": 0,
            "Max": 2,
            "Default": 0,
            "Options": Greenfather.hexes,
        }

    def performAbility(self, phase, time, champion, input_=0):
        if phase != "preCombat":
            return 0
        star = self.level - 1
        hex_type = self.hexName(self.params)
        if hex_type == "Flower":
            champion.aspd.addStat(self.flower_aspd[star])
        elif hex_type == "Mushroom":
            champion.dmgMultiplier.addStat(self.mushroom_amp[star])
        else:
            champion.manaRegen.addStat(self.water_mana_regen[star])
        return 0


class Blackthorn(Buff):
    """Blackthorn: the ally on the Blackthorn hex is sacrificed before combat.

    Two halves: a flat Health grant, plus the stat package the sacrifice hands
    over. Which package that is depends on its Role, and how big it is depends
    on its Star Level and Cost -- all three read off the champion
    (blackthorn_role/_star/_cost, set by the sidebar's Blackthorn selector),
    like the set-17 Arbiter's cause/effect. The final number is

        base value  x  sacrifice_scaling[cost][star]  x  bonus_scaling[level]

    An empty hex (role "None", the default) is no sacrifice at all, so neither
    half applies.

    A Tank sacrifice (17% Health, 17 Armor/MR) is not modeled: it does nothing
    to a DPS number here, since nothing in the sim damages the champion being
    measured, and sacrificing a Tank is rare enough not to be worth a row.

    The reference bin used to disagree with the champion card -- (4) at a 0.25
    StatMultiplier, (6) at 350 Health with a whole different effect ("the
    sacrifice doesn't die") -- and the card's numbers were used instead. As of
    PBE 18.1g the bin has caught up and agrees with the card, so patch_check
    hooks them; PBE 18.2 moved the Health rows to 175/350/600. The sacrifice
    base values and the star/cost scaling table are still not in the bin at
    all. The official 18.2 notes (not on PBE) moved the AD sacrifice's
    Attack Speed 12 -> 14% and the AP sacrifice's Mana Regen 1.7 -> 2.
    """

    levels = [0, 2, 4, 6]
    display_name = "Blackthorn"

    # Health granted to your whole team.
    team_health = {0: 0, 2: 175, 4: 350, 6: 600}
    # "Bonus is X% stronger" -- multiplies the sacrifice's stats only.
    bonus_scaling = {0: 1.0, 2: 1.0, 4: 1.3, 6: 1.6}

    ROLE_NONE = "None"
    ROLE_MAGIC = "Magic"
    ROLE_ATTACK = "Attack"
    # Roles a sacrifice can actually have. ROLE_NONE is the empty hex -- no
    # sacrifice, so no Health and no stat package, whatever star level and
    # cost are set to. It is a selectable option, not a role, hence the two
    # lists.
    roles = [ROLE_MAGIC, ROLE_ATTACK]
    selectable_roles = [ROLE_NONE, ROLE_MAGIC, ROLE_ATTACK]

    # Sacrifice base values, before either scaling.
    magic_mana_regen = 2.0
    magic_amp = 0.14  # damage amp
    attack_ad = 24  # % AD
    attack_aspd = 14  # % Attack Speed

    star_levels = [1, 2, 3, 4]
    # Every sacrifice on a real board has a cost tier, so there is no untiered
    # row: a "No Tier" sacrifice scaled at a flat 1.0 and sat in the middle of
    # the table looking like a fifth option, without being anything you could
    # put on the hex. Per request. sacrificeScaling still falls back to 1.0
    # for a cost it does not know, so nothing depends on the row existing.
    costs = [1, 2, 3, 4, 5]
    sacrifice_scaling = {
        1: {1: 0.6, 2: 1.0, 3: 1.75, 4: 2.5},
        2: {1: 0.7, 2: 1.4, 3: 2.8, 4: 5.0},
        3: {1: 0.8, 2: 1.8, 3: 3.3, 4: 8.0},
        4: {1: 1.1, 2: 2.25, 3: 50.0, 4: 500.0},
        5: {1: 1.5, 2: 3.0, 3: 100.0, 4: 999.0},
    }
    # Only a 1-cost realistically reaches 3 or 4 stars, so the rest of the
    # table's high-star rows (the 50/500/100/999 placeholders included) are
    # kept as data but never offered. Per request.
    max_star_by_cost = {1: 4}
    default_max_star = 2

    def __init__(self, level, params):
        super().__init__(
            f"{self.display_name} {level}", level, params, phases=["preCombat"]
        )

    @classmethod
    def costLabel(cls, cost):
        return f"{cost} cost"

    @classmethod
    def starLabel(cls, star):
        return f"{star}*"

    @classmethod
    def starLevels(cls, cost):
        """Star levels a sacrifice of this cost can actually turn up at."""
        cap = cls.max_star_by_cost.get(cost, cls.default_max_star)
        return [star for star in cls.star_levels if star <= cap]

    def sacrificeScaling(self, champion):
        """Star/cost multiplier for the sacrifice sitting on the hex."""
        cost = getattr(champion, "blackthorn_cost", 1)
        star = getattr(champion, "blackthorn_star", 1)
        return self.sacrifice_scaling.get(cost, {}).get(star, 1.0)

    def performAbility(self, phase, time, champion, input_=0):
        if phase != "preCombat":
            return 0
        role = getattr(champion, "blackthorn_role", self.ROLE_NONE)
        if role == self.ROLE_NONE:
            # Nothing on the hex: no sacrifice, so not even the Health.
            return 0
        champion.hp.addStat(self.team_health.get(self.level, 0))
        scale = self.sacrificeScaling(champion) * self.bonus_scaling.get(self.level, 1.0)
        if role == self.ROLE_ATTACK:
            champion.bonus_ad.addStat(self.attack_ad * scale)
            champion.aspd.addStat(self.attack_aspd * scale)
        else:
            champion.manaRegen.addStat(self.magic_mana_regen * scale)
            champion.dmgMultiplier.addStat(self.magic_amp * scale)
        return 0


# WISPS
#
# Single-copy combat buffs from the Wisp bag (as opposed to the Blossom
# trait's own count-scaled levels above). Several of them get stronger
# values once the holder's Blossom trait is at level 3+ ("blossom_level",
# set by Blossom.performAbility). All of them read that on postPreCombat --
# by the time that phase runs, every item's preCombat phase (including
# Blossom's) has already resolved, so this doesn't depend on item order.


def _is_blossom_upgraded(champion):
    return getattr(champion, "blossom_level", 0) >= 3


class Flow(Buff):
    levels = [1]
    display_name = "Flow"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["postPreCombat"])
        # Unstoppable (CC immunity) is out of scope -- this simulator doesn't
        # model crowd control.
        self.as_bonus = 15
        self.duration = 10
        self.duration_upgraded = 15

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "postPreCombat":
            duration = (
                self.duration_upgraded
                if _is_blossom_upgraded(champion)
                else self.duration
            )
            champion.applyStatus(
                status.ASModifier("Flow"), champion, time, duration, self.as_bonus
            )
        return 0


class ProlificPower(Buff):
    levels = [1]
    display_name = "Prolific Power"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["postPreCombat"])
        self.scaling = 4
        self.scaling_upgraded = 6

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "postPreCombat":
            amt = (
                self.scaling_upgraded
                if _is_blossom_upgraded(champion)
                else self.scaling
            )
            champion.bonus_ad.addStat(amt)
            champion.ap.addStat(amt)
        return 0


class UltraAscension(Buff):
    levels = [1]
    display_name = "Ultra Ascension"

    def __init__(self, level=1, params=0):
        super().__init__(
            self.display_name, level, params, phases=["postPreCombat", "onUpdate"]
        )
        self.dmg_bonus = 3.0
        self.trigger_time = 25
        self.trigger_time_upgraded = 23
        self.next_bonus = None

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "postPreCombat":
            self.next_bonus = (
                self.trigger_time_upgraded
                if _is_blossom_upgraded(champion)
                else self.trigger_time
            )
        elif phase == "onUpdate":
            if self.next_bonus is not None and time >= self.next_bonus:
                self.next_bonus = None
                champion.dmgMultiplier.addStat(self.dmg_bonus)
        return 0


class CrystalBall(Buff):
    levels = [1]
    display_name = "Crystal Ball"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["postPreCombat"])
        # Revealing the next opponent has no effect on a 1v1 combat sim.
        self.as_bonus = 12
        self.as_bonus_upgraded = 18

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "postPreCombat":
            amt = (
                self.as_bonus_upgraded
                if _is_blossom_upgraded(champion)
                else self.as_bonus
            )
            champion.aspd.addStat(amt)
        return 0


class Hummingbird(Buff):
    levels = [1]
    display_name = "Hummingbird"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["postPreCombat"])
        self.as_bonus = 20
        self.as_bonus_upgraded = 35

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "postPreCombat":
            amt = (
                self.as_bonus_upgraded
                if _is_blossom_upgraded(champion)
                else self.as_bonus
            )
            champion.aspd.addStat(amt)
        return 0


class Rain(Buff):
    levels = [1]
    display_name = "Rain"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["postPreCombat"])
        self.mana_regen = 1
        self.mana_regen_upgraded = 2

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "postPreCombat":
            amt = (
                self.mana_regen_upgraded
                if _is_blossom_upgraded(champion)
                else self.mana_regen
            )
            champion.manaRegen.addStat(amt)
        return 0


class Downpour(Buff):
    levels = [1]
    display_name = "Downpour"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["postPreCombat"])
        self.mana_regen = 2
        self.mana_regen_upgraded = 3

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "postPreCombat":
            amt = (
                self.mana_regen_upgraded
                if _is_blossom_upgraded(champion)
                else self.mana_regen
            )
            champion.manaRegen.addStat(amt)
        return 0


class TatteredArmor(Buff):
    levels = [1]
    display_name = "Tattered Armor"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["postPreCombat"])
        # Shred = Armor reduction, Sunder = MR reduction.
        self.shred_mult = 0.7
        self.duration = 10
        self.duration_upgraded = 15

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "postPreCombat":
            duration = (
                self.duration_upgraded
                if _is_blossom_upgraded(champion)
                else self.duration
            )
            for opponent in champion.opponents:
                opponent.applyStatus(
                    status.ArmorReduction("Tattered Armor - Armor"),
                    champion,
                    time,
                    duration,
                    self.shred_mult,
                )
                opponent.applyStatus(
                    status.MRReduction("Tattered Armor - MR"),
                    champion,
                    time,
                    duration,
                    self.shred_mult,
                )
        return 0


class MarksmensGale(Buff):
    levels = [1]
    display_name = "Marksmen's Gale"

    def __init__(self, level=1, params=0):
        super().__init__(
            self.display_name, level, params, phases=["postPreCombat", "postAttack"]
        )
        self.as_per_attack = 3
        self.as_per_attack_upgraded = 5
        # Role can still change during postPreCombat (e.g. Kaisa's ult
        # swapping to ATTACK_MARKSMAN), so this is checked there rather than
        # preCombat, same as the blossom-upgrade check.
        self.is_marksman = False

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "postPreCombat":
            self.is_marksman = champion.role.archetype == "Marksman"
        elif phase == "postAttack" and self.is_marksman:
            amt = (
                self.as_per_attack_upgraded
                if _is_blossom_upgraded(champion)
                else self.as_per_attack
            )
            champion.aspd.addStat(amt)
        return 0


class Supercritical(Buff):
    levels = [1]
    display_name = "Supercritical"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["postPreCombat"])
        # "Allies with Precision" -- Precision is modeled in this simulator
        # as champion.canSpellCrit (set by addPrecision(), see Executioner/
        # JeweledLotusI/II above).
        self.crit_dmg_bonus = 0.25
        self.crit_dmg_bonus_upgraded = 0.40

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "postPreCombat" and champion.canSpellCrit:
            amt = (
                self.crit_dmg_bonus_upgraded
                if _is_blossom_upgraded(champion)
                else self.crit_dmg_bonus
            )
            champion.critDmg.addStat(amt)
        return 0


class BackrowStar(Buff):
    levels = [1]
    display_name = "Backrow Star"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["postPreCombat"])
        # Ignoring the "random back row champion" targeting -- applies
        # directly to the buff holder.
        self.as_bonus = 85
        self.as_bonus_upgraded = 115
        self.duration = 7
        self.duration_upgraded = 8

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "postPreCombat":
            upgraded = _is_blossom_upgraded(champion)
            as_bonus = self.as_bonus_upgraded if upgraded else self.as_bonus
            duration = self.duration_upgraded if upgraded else self.duration
            champion.applyStatus(
                status.ASModifier("Backrow Star"), champion, time, duration, as_bonus
            )
        return 0


# Unit buffs


class AdaptorInnate(Buff):
    """Adaptor's innate: lock in the AD or AP version of the unit's ability.

    Lives on the unit rather than on the Adaptor trait buff so it still fires
    when the trait isn't fielded at all (or sits at level 0) -- an Adaptor's
    ability always adapts, the trait levels only add the stat grant.

    postPreCombat for the same reason as the Adaptor trait: it's the first
    phase where every preCombat AD/AP source has resolved.

    Also applies the base-AD swap for the Adaptors whose two versions don't
    share a base AD (Master Yi 70/15, Akali 40/30). They advertise it as
    ap_base_atk, already star-scaled; units whose versions share a base AD
    just don't set the attribute. ad_base_atk is the mirror image, for units
    whose card stats are the AP version (Nidalee, whose AD version is a
    0-AD stub for now).
    """

    levels = [1]
    display_name = "Adaptor Innate"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["postPreCombat"])

    def performAbility(self, phase, time, champion, input_=0):
        if resolveAdaptorVersion(champion):
            if hasattr(champion, "ad_base_atk"):
                champion.atk.base = champion.ad_base_atk
        elif hasattr(champion, "ap_base_atk"):
            champion.atk.base = champion.ap_base_atk
        return 0


class GrompPurpleBuff(Buff):
    """Gromp's Riftbeast unique buff: every 5s, +25% of his adaptive stat.

    Unlocked by Riftbeast (3)'s Alpha Mark, so this checks the
    riftbeast_alpha_mark flag that Riftbeast.performAbility sets on preCombat
    (which runs before any onUpdate frame) instead of being appended
    conditionally. Which stat it feeds follows the same AD-vs-AP split as the
    ability itself.
    """

    levels = [1]
    display_name = "Purple Buff"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["onUpdate"])
        self.interval = 5.0
        self.amount = 25
        self.next_tick = 5.0

    def performAbility(self, phase, time, champion, input_=0):
        if not getattr(champion, "riftbeast_alpha_mark", False):
            return 0
        if time >= self.next_tick:
            self.next_tick += self.interval
            if getattr(champion, "ad_version", False):
                champion.bonus_ad.addStat(self.amount)
            else:
                champion.ap.addStat(self.amount)
        return 0


class CinderlingScarletBuff(Buff):
    """Cinderling's Riftbeast unique buff: +22% Attack Damage each cast.

    Unlocked by Riftbeast (3)'s Alpha Mark, so like GrompPurpleBuff this
    checks the riftbeast_alpha_mark flag and no-ops without it. postAbility:
    "gains ... each cast" is a reward for the cast, so the cast that earned
    the AD goes out at the old value and the next one benefits.
    """

    levels = [1]
    display_name = "Scarlet Buff"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["postAbility"])
        self.ad_per_cast = 22

    def performAbility(self, phase, time, champion, input_=0):
        if not getattr(champion, "riftbeast_alpha_mark", False):
            return 0
        champion.bonus_ad.addStat(self.ad_per_cast)
        return 0


class PebblesChannel(Buff):
    """Azure Laser: a channel that burns mana instead of spending it.

    Every other cast in this simulator is instantaneous -- update() drops mana
    to startingMana and moves on. Pebbles' does not: the cast opens a channel
    that drains 35% of his *max* mana per second until he is empty, dealing
    damage once a second while it runs. So the shape of the thing is a
    postAbility that takes the mana back over (update() has already applied
    the normal cast drain by then) and an onUpdate that meters it out.

    The numbers are measured, not guessed -- see
    replay_analysis/pebbles_channel_mana.py, which fits all of this against a
    30fps clip and lands 102 of 106 channel frames exactly:

      * the drain is 4 ticks a second, 0.35 * maxMana * 0.25 each. Scanning
        the fraction peaks hard at 0.350, so the card's 35% is literal.
      * mana regen keeps flowing the whole time. That is why nothing here
        manalocks: a manalock would gate addMana() and stall the regen that
        the clip plainly shows ticking through the channel.
      * the Teal Buff's "2 Mana Regen for every 4 seconds channeled" is not
        granted in 2-point lumps every 4 seconds. The rate climbs smoothly at
        +0.5/s of channeling; the panel's integer readout is what makes it
        look chunky, stepping 5 -> 6 -> 7 at exactly 2.000s intervals. The
        continuous model beats a 2s staircase 102 fits to 87, and the
        tooltip's literal 4s staircase 102 to 81.
      * the bonus is never removed. It survives the channel that earned it
        (the readout holds after mana bottoms out) and stacks across casts.

    Two things are deliberately left out. The 3 flat Magic Resist the laser
    shreds per tick is not modeled, per request. And the damage tick *phase*
    -- whether the first tick lands on the cast or a second into it -- is the
    one number the clip cannot settle, since the beam and the rest of the
    board wash out any attempt to time the damage popups. `first_tick` below
    takes the card's "each second while casting" literally, at one second in;
    it is a named constant precisely because it is the piece most likely to
    be wrong.

    A caution about the emergent case: net drain is 0.35*maxMana - regen, and
    the Teal Buff grows regen without bound while the channel runs. Give
    Pebbles enough starting regen and the drain never wins, so he channels
    for the rest of combat and never auto-attacks again. That is what the
    numbers say rather than a modelling artifact, but it makes his DPS curve
    turn discontinuous, so it is worth knowing before reading a result.
    """

    levels = [1]
    display_name = "Azure Laser"

    drain_fraction = 0.35  # of max mana, per second
    tick = 0.25  # both the drain and the Teal Buff grant land here
    damage_interval = 1.0
    first_tick = 1.0  # unverified -- see the class docstring
    # "2 Mana Regen for every 4 seconds channeled", as the per-second rate it
    # actually is.
    regen_growth_per_s = 0.5

    def __init__(self, level=1, params=0):
        super().__init__(
            self.display_name, level, params, phases=["postAbility", "onUpdate"]
        )
        self.active = False
        self.next_drain = 0.0
        self.next_damage = 0.0

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "postAbility":
            self.start(time, champion)
        elif phase == "onUpdate" and self.active:
            self.run(time, champion)
        return 0

    def start(self, time, champion):
        self.active = True
        self.next_drain = time
        self.next_damage = time + self.first_tick
        # update() has already run the ordinary cast drain
        # (curMana -= fullMana, += startingMana). The channel is what spends
        # this cast's mana, so hand it back and let the ticks below take it.
        champion.curMana = champion.fullMana.stat
        # No manalock: regen is observed running throughout the channel, and
        # addMana() refuses to pay out while manalockTime is ahead of now.
        champion.manalockTime = -1
        # He cannot auto-attack mid-channel. Pinned far ahead rather than
        # estimated, since the channel's length is emergent -- released in
        # finish() below, the same way NidaleeUlt releases its manalock.
        champion.nextAttackTime = time + 9999

    def run(self, time, champion):
        """Pay out whichever ticks this frame has reached, in time order.

        The two schedules collide constantly rather than occasionally: a
        damage tick is one second, which is exactly four drain ticks, so every
        damage tick lands on a drain tick. That makes their order a real
        decision and not a detail. Damage goes first, so a tick due at the
        instant the drain empties him still lands -- he was channelling right
        up to that instant. Draining first would silently eat that tick, and
        since the channel tends to end near a whole second it would eat it
        systematically, not rarely.
        """
        while self.active:
            due = min(self.next_drain, self.next_damage)
            if time < due:
                break
            if self.next_damage <= self.next_drain:
                self.next_damage += self.damage_interval
                if champion.opponents:
                    champion.multiTargetSpell(
                        champion.opponents[:1],
                        champion.items,
                        time,
                        1,
                        champion.abilityScaling,
                        "magical",
                    )
            else:
                self.next_drain += self.tick
                champion.curMana -= (
                    self.drain_fraction * champion.fullMana.stat * self.tick
                )
                if getattr(champion, "riftbeast_alpha_mark", False):
                    champion.manaRegen.addStat(self.regen_growth_per_s * self.tick)
                if champion.curMana <= 0:
                    self.finish(time, champion)

    def finish(self, time, champion):
        self.active = False
        champion.curMana = 0
        # The manalock ends with the channel, so he is free to attack and to
        # start banking mana again on the same frame.
        champion.nextAttackTime = time
        champion.attack_progress = 1.0


class AttunedInnate(Buff):
    """Attuned: the moon advances one phase before each of Alune's casts.

    A one-unit trait and a permanent part of her kit, so it lives on the unit
    (like AdaptorInnate) rather than being something you pick in the buff bar.

    preAbility, not postAbility, per request. The phase the cast lands under is
    the one it *arrives* at, and Moonfall's damage is instant -- so advancing
    first is what makes the Damage Amp apply to the cast that earned it.
    multiTargetSpell reads dmgMultiplier when it fires, and update() runs every
    item's preAbility before performAbility, so the ordering holds without any
    extra sequencing.

    The five phases cycle New Moon -> ... -> Full Moon and back. The first
    three are "at or below half full" and give Durability, which is not
    modeled: nothing in this simulator damages the champion being measured.
    The last two give Damage Amp, so casts 4 and 5 of every cycle are amped.
    Cast 5 is Full Moon, which is also the cast Alune crashes the moon on.
    """

    levels = [1]
    display_name = "Attuned"

    # Index in this list == (numCasts - 1) % 5, so cast 1 is New Moon.
    moon_phases = [
        "New Moon",
        "Waxing Crescent",
        "Half Moon",
        "Waxing Gibbous",
        "Full Moon",
    ]
    # "While above [half full]" -- the two phases that amp instead of shielding.
    amp_phases = ("Waxing Gibbous", "Full Moon")
    damage_amp = 0.07
    # Durability is the other half of the trait; unmodeled, kept for reference.
    durability = 0.07

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["preAbility"])
        # Whether damage_amp is currently added to dmgMultiplier. The amp is a
        # property of the current phase, not a stack, so leaving the amped
        # phases has to take it back off again.
        self.amp_applied = False

    def performAbility(self, phase, time, champion, input_=0):
        if phase != "preAbility":
            return 0
        # numCasts is incremented before preAbility runs, so this is the
        # 1-indexed number of the cast about to fire.
        index = (champion.numCasts - 1) % len(self.moon_phases)
        champion.moon_phase = self.moon_phases[index]

        wants_amp = champion.moon_phase in self.amp_phases
        if wants_amp != self.amp_applied:
            champion.dmgMultiplier.addStat(
                self.damage_amp if wants_amp else -self.damage_amp
            )
            self.amp_applied = wants_amp
        return 0


class TinyBeaksBuff(Buff):
    levels = [1]
    display_name = "Flock Family"

    def __init__(self, level=1, params=0):
        super().__init__(
            self.display_name, level, params, phases=["postAbility", "postAttack"]
        )
        self.num_beaks = 4
        self.duration = 5
        self.active_until = -1

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "postAbility":
            # Duration scales with AP the same way this file's other
            # ap_values do (ap.stat is ~1.0 at 0 bonus AP), per Mama Beak's
            # card ("5" shown with the AP-scaling droplet icon).
            self.active_until = time + self.duration * champion.ap.stat
        elif phase == "postAttack" and time < self.active_until:
            # Summoner (2)/(3): Tiny Beak damage is boosted +45%/+67.5%.
            mult = getattr(champion, "summoner_dmg_mult", 1.0)

            def scaling(level, AD, AP, mult=mult):
                return mult * champion.beakScaling(level, AD, AP)

            for _ in range(self.num_beaks):
                champion.multiTargetSpell(
                    champion.opponents,
                    champion.items,
                    time,
                    1,
                    scaling,
                    "physical",
                )
        return 0


class AriseBuff(Buff):
    levels = [1]
    display_name = "Arise!"

    def __init__(self, level=1, params=0):
        super().__init__(
            self.display_name,
            level,
            params,
            phases=["postAbility", "preAttack", "postAttack"],
        )
        self.as_bonus = 150
        self.num_soldier_attacks = 6
        self.num_targets = 2
        self.attacks_remaining = 0
        self.active = False

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "postAbility":
            champion.aspd.addStat(self.as_bonus)
            self.attacks_remaining = self.num_soldier_attacks
            self.active = True
            # Manalocked until all num_soldier_attacks land -- pinned far
            # ahead rather than duration-estimated, since the AS gain (and
            # so attack cadence) changes the instant this fires. Unlocked
            # explicitly in postAttack below once the count hits zero.
            champion.manalockTime = time + 9999
        elif phase == "preAttack" and self.active:
            # Replace the attack with a 2-target magic "soldier command",
            # matching how the rest of this file swaps an Attack's
            # scaling/canCrit/attackType from preAttack (see e.g.
            # DravenUlt/JhinUlt) rather than bypassing performAttack.
            input_.canOnHit = True
            input_.canCrit = champion.canSpellCrit
            input_.attackType = "magical"
            # Summoner (2)/(3): soldier damage is boosted +20%/+30%. Azir's
            # own variable since PBE 18.2 -- see Summoner.azir_dmg_mult.
            mult = getattr(champion, "summoner_azir_dmg_mult", 1.0)
            input_.scaling = (
                ChampionAbilityScaling(champion)
                if mult == 1.0
                else ScaledChampionAbilityScaling(champion, mult)
            )
            input_.numTargets = self.num_targets
        elif phase == "postAttack" and self.active:
            # Runs after performAttack's own mana-gen check for this same
            # attack, so ending Arise here (rather than in preAttack) means
            # the 6th empowered attack still generates no mana and only the
            # 7th (first normal attack after) does.
            self.attacks_remaining -= 1
            if self.attacks_remaining <= 0:
                self.active = False
                champion.aspd.addStat(-self.as_bonus)
                champion.manalockTime = time
                # startAttack() (caller of performAttack, still on the
                # stack above this hook) does
                # `attack_progress = max(0.0, attack_progress - 1.0)`
                # right after this returns, carrying any overshoot past
                # 1.0 into the next swing's timer -- that overshoot was
                # accrued while still under the +150% AS, in the frames
                # leading up to this attack. Clamping to 1.0 here (instead
                # of leaving the accrued value, which can be >1.0) zeroes
                # that carryover out so the wait for the 7th attack starts
                # fresh, fully under normal AS with no leftover head start.
                champion.attack_progress = min(champion.attack_progress, 1.0)
        return 0


class NidaleeUlt(Buff):
    """Javelin Toss (AP version): +150% Attack Speed for the next 3 attacks,
    each replaced with a javelin dealing magic damage; the 3rd javelin uses
    the bigger empoweredScaling row instead.

    Same shape as AriseBuff (gain AS, manalock, replace the next N attacks
    from preAttack), so the manalock/unlock and attack_progress handling
    mirror it exactly. The 3rd javelin's real targeting (furthest enemy with
    the least items) is meaningless against this sim's identical dummies, so
    it hits the current target like the other two.

    On AD-version Nidalee (see set18champs.Nidalee: currently a 0-AD,
    0-damage stub) the whole buff no-ops -- casts fire but do nothing.
    """

    levels = [1]
    display_name = "Javelin Toss"

    def __init__(self, level=1, params=0):
        super().__init__(
            self.display_name,
            level,
            params,
            phases=["postAbility", "preAttack", "postAttack"],
        )
        self.as_bonus = 150
        self.num_javelins = 3
        self.attacks_remaining = 0
        self.active = False

    def performAbility(self, phase, time, champion, input_=0):
        if getattr(champion, "ad_version", False):
            return 0
        if phase == "postAbility":
            champion.aspd.addStat(self.as_bonus)
            self.attacks_remaining = self.num_javelins
            self.active = True
            # Manalocked until all num_javelins land -- pinned far ahead
            # rather than duration-estimated, since the AS gain changes the
            # attack cadence the instant this fires. Unlocked explicitly in
            # postAttack below once the count hits zero (same as AriseBuff).
            champion.manalockTime = time + 9999
        elif phase == "preAttack" and self.active and input_.regularAuto:
            input_.canOnHit = True
            input_.canCrit = champion.canSpellCrit
            input_.attackType = "magical"
            # The last of the 3 javelins is the empowered one.
            input_.scaling = (
                ChampionEmpoweredAbilityScaling(champion)
                if self.attacks_remaining == 1
                else ChampionAbilityScaling(champion)
            )
        elif phase == "postAttack" and self.active:
            # Runs after performAttack's own mana-gen check for this same
            # attack, so ending the ult here means the 3rd javelin still
            # generates no mana and only the first normal attack after does.
            self.attacks_remaining -= 1
            if self.attacks_remaining <= 0:
                self.active = False
                champion.aspd.addStat(-self.as_bonus)
                champion.manalockTime = time
                # Zero out windup overshoot accrued under the +150% AS so the
                # next attack's wait starts fresh under normal AS -- see
                # AriseBuff's postAttack for the full walkthrough.
                champion.attack_progress = min(champion.attack_progress, 1.0)
        return 0


class SivirBounces(Buff):
    """Boomerang Blade's 8 bounces, which arrive after the cast, not with it.

    The blade's first hit lands on the cast like every other spell here. The
    bounces are a schedule instead: postAbility queues 8 of them at +1.0s,
    +1.25s ... +2.75s, and onUpdate pays each one out as the frame clock
    reaches it. That spread is the whole reason this is a buff rather than
    another line in performAbility -- eight hits dealt at cast time would put
    ~40% of a cast's damage two seconds early, which is most of the DPS
    question for a unit measured at 5 and 10 seconds.

    "When this kills an enemy, bounce 3 additional times" is deliberately not
    modeled: nothing dies in this sim, so the extra bounces would be a guess
    about a board rather than a property of the champion.
    """

    levels = [1]
    display_name = "Boomerang Blade"

    first_bounce = 1.0
    interval = 0.25
    bounces = 8

    def __init__(self, level=1, params=0):
        super().__init__(
            self.display_name, level, params, phases=["postAbility", "onUpdate"]
        )
        self.pending = []

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "postAbility":
            first = time + self.first_bounce
            self.pending.extend(
                first + step * self.interval for step in range(self.bounces)
            )
            # A recast before the last bounce lands leaves two blades in the
            # air; sorting keeps them paying out in the order they arrive.
            self.pending.sort()
        elif phase == "onUpdate":
            # A frame is 1/30s and the bounces are 0.25s apart, so this
            # normally fires at most one per frame -- the loop is for the
            # overlapping-blades case above.
            while self.pending and time >= self.pending[0]:
                self.pending.pop(0)
                champion.multiTargetSpell(
                    champion.opponents,
                    champion.items,
                    time,
                    1,
                    champion.bounceScaling,
                    "physical",
                )
        return 0


class AsheTrail(Buff):
    """Spirit Rift's trail: a 4s zone that ticks once a second after the cast.

    The arrow's own hit lands in performAbility like any other spell. The
    trail is a schedule instead -- postAbility keeps one expiry, onUpdate pays
    out a tick per second while the trail is still on the ground -- because
    four seconds of damage handed over at cast time would land most of a
    cast's trail damage before the trail exists, and this sim is read at 5 and
    10 seconds.

    A recast refreshes rather than stacks: there is only ever one trail, so a
    second cast pushes the expiry out and nothing else. The tick cadence
    deliberately keeps running across that refresh instead of restarting at
    +1s. The card promises damage every second for as long as the trail is
    down, and restarting the clock on each cast would pay a fast-casting Ashe
    *less* than one tick per second -- a recast at +0.9s would cancel a tick
    that was 0.1s from landing. Refreshing only the expiry keeps the rate at
    exactly one tick per second of uptime, which is the number the card
    describes.

    The 20% Slow is not modeled: the dummy never attacks, so slowing its
    attack speed changes nothing.
    """

    levels = [1]
    display_name = "Spirit Rift Trail"

    duration = 4.0
    interval = 1.0
    # "2% max Health" reads off the target's max HP, not Ashe's.
    health_ratio = 0.02

    def __init__(self, level=1, params=0):
        super().__init__(
            self.display_name, level, params, phases=["postAbility", "onUpdate"]
        )
        # No trail yet: -inf makes the first cast take the "nothing on the
        # ground" branch without a separate first-cast flag, and keeps the
        # onUpdate loop inert until then.
        self.expires = float("-inf")
        self.next_tick = 0.0

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "postAbility":
            if time > self.expires:
                # Nothing on the ground, so the new trail starts its own clock.
                self.next_tick = time + self.interval
            self.expires = time + self.duration
        elif phase == "onUpdate":
            # A frame is 1/30s and the ticks are 1s apart, so this pays out at
            # most one per frame; the loop is only for safety at low frame
            # rates. The epsilon is for the last tick, which is due at exactly
            # the expiry and would otherwise be lost to accumulated +1.0s.
            while time >= self.next_tick and self.next_tick <= self.expires + 1e-6:
                self.tick(champion, time)
                self.next_tick += self.interval
        return 0

    def tick(self, champion, time):
        # The arrow pierces num_targets enemies; the trail it leaves behind
        # catches one fewer.
        for opponent in champion.opponents[: max(0, champion.num_targets - 1)]:
            # The %max-HP part is per-target, so each one needs its own
            # scaling closure rather than a single multiTargetSpell call.
            flat = self.health_ratio * opponent.hp.stat

            def scaling(level, AD, AP, flat=flat):
                return champion.trailScaling(level, AD, AP) + flat

            champion.multiTargetSpell(
                [opponent], champion.items, time, 1, scaling, "physical"
            )


class ApheliosOnslaught(Buff):
    """Moonlight's Onslaught's schedule: two attack credits, then the blast.

    The swipes themselves are a DoT on the target
    (status.ApheliosSeverumStatus). What is left is Aphelios's own side of the
    cast, and both halves of it are a schedule rather than something that can
    happen at cast time -- which is why this is a buff and not more lines in
    performAbility.

      * The onslaught counts as 2 attacks, however many swipes it lands, and
        they are paid at +0.75s and +1.5s. Everything that reads an attack is
        a rate -- Rapidfire's stacks, Guinsoo's ramp, an on-hit item -- so
        handing both over on the cast would credit them up to 1.5s early on a
        unit measured at 5 and 10 seconds.
      * The blast fires "after the onslaught finishes", i.e. at the end of the
        2s swipe window, not at the end of the 3.5s cast. It re-reads his
        current opponents instead of the list captured at cast, for the same
        reason KarmaTetherStatus's burst does.
    """

    levels = [1]
    display_name = "Moonlight's Onslaught"

    # Offsets from the cast.
    attack_credits = (0.75, 1.5)
    blast_at = 2.0

    def __init__(self, level=1, params=0):
        super().__init__(
            self.display_name, level, params, phases=["postAbility", "onUpdate"]
        )
        self.pending_attacks = []
        self.pending_blasts = []

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "postAbility":
            self.pending_attacks.extend(
                time + offset for offset in self.attack_credits
            )
            self.pending_attacks.sort()
            self.pending_blasts.append(time + self.blast_at)
            self.pending_blasts.sort()
        elif phase == "onUpdate":
            # A frame is 1/30s and nothing here is closer together than
            # 0.5s, so these normally pay out at most one apiece per frame;
            # the loops are for the overlapping-cast case the sorts allow.
            while self.pending_attacks and time >= self.pending_attacks[0]:
                self.pending_attacks.pop(0)
                self.creditAttack(champion, time)
            while self.pending_blasts and time >= self.pending_blasts[0]:
                self.pending_blasts.pop(0)
                if champion.opponents:
                    champion.multiTargetSpell(
                        champion.opponents,
                        champion.items,
                        time,
                        1,
                        champion.blastScaling,
                        "physical",
                    )
        return 0

    def creditAttack(self, champion, time):
        # An attack for bookkeeping only. Its damage is already accounted for
        # -- it is one of the swipes the DoT is ticking out -- but it still has
        # to advance numAttacks and fire the pre/postAttack item phases, which
        # is what Rapidfire, Guinsoo and the on-hit items actually count.
        # multiTargetSpell with 0 targets is exactly that: the attack
        # bookkeeping with no second helping of damage.
        champion.multiTargetSpell(
            champion.opponents,
            champion.items,
            time,
            0,
            status.zero_scaling,
            "physical",
            numAttacks=1,
        )


class CaitlynHeadshotBuff(Buff):
    levels = [1]
    display_name = "Headshot"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["preAttack"])
        self.attack_count = 0

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "preAttack" and input_.regularAuto:
            self.attack_count += 1
            if self.attack_count % 3 == 0:
                input_.scaling = ChampionAbilityScaling(champion)
                input_.canCrit = champion.canSpellCrit
        return input_


class MasterYiUlt(Buff):
    """Wuju Style: every third attack is a Double Strike that hits twice.

    Not a real cast -- Master Yi is built with fullMana=-1 (canCast() is never
    true), so the whole passive lives here, counting attacks the same way
    CaitlynHeadshotBuff does.

    The two hits are the auto itself plus one replay of it (queued in
    preAttack, fired in postAttack so it lands after the original), and each
    Adaptor version then gets its own per-hit rider:
      AP: bonus magic damage per hit (the heal off it isn't modeled -- nothing
          in the sim damages the champion being measured).
      AD: stacking AS per Double Strike -- a flat 12% plus 3% that scales
          with AP, i.e. the 15% the card shows at Master Yi's 100 base AP.
          Once per strike, not once per hit: the card's subject is "Double
          Strikes grant ... stacking Attack Speed", so the replayed hit adds
          damage but no second stack.

    The AP version's much weaker base AD (15 instead of 70) is applied by
    AdaptorInnate, not here.
    """

    levels = [1]
    display_name = "Wuju Style"

    def __init__(self, level=1, params=0):
        super().__init__(
            self.display_name,
            level,
            params,
            phases=["preAttack", "postAttack"],
        )
        self.attack_count = 0
        self.attacks_per_strike = 3
        self.hits_per_strike = 2
        # AD version, per Double Strike: 12% AS flat + 3% AP-scaled.
        self.as_per_strike = 12
        self.as_per_strike_scaling = 3
        # Set in preAttack, consumed in postAttack; the Attack object it holds
        # is created fresh per performAttack, so replaying it can't outlive the
        # swing it belongs to.
        self.pending_strike = None

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "preAttack" and input_.regularAuto:
            self.attack_count += 1
            if self.attack_count % self.attacks_per_strike == 0:
                # Every other item's preAttack has already run (champion.items
                # sit last in the simulator's list), so this is the finished
                # attack -- replaying it in postAttack repeats it exactly.
                self.pending_strike = input_
        elif phase == "postAttack" and self.pending_strike is not None:
            attack = self.pending_strike
            self.pending_strike = None
            # Second hit. doAttack, not performAttack: a Double Strike is one
            # attack that lands twice, so this must not re-enter preAttack
            # (which would advance the count) or generate mana.
            champion.doAttack(attack, champion.items, time)
            if champion.ad_version:
                champion.aspd.addStat(
                    self.as_per_strike + self.as_per_strike_scaling * champion.ap.stat
                )
            else:
                for _ in range(self.hits_per_strike):
                    champion.multiTargetSpell(
                        champion.opponents,
                        champion.items,
                        time,
                        1,
                        champion.abilityScaling,
                        "magical",
                    )
        return input_


class KayleAscensions(Buff):
    """Solar Judgement: the ascensions Kayle's star level turns on.

    Not a cast -- Kayle has no mana at all, and fullMana = -1 keeps canCast()
    false -- so the whole ability lives here, the way MasterYiUlt and
    CaitlynHeadshotBuff do. The ascensions stack rather than replace: a 3-star
    has all three at once.

      1st (always)  every attack lands a second instance for the card's magic
                    damage. It goes out through multiTargetSpell rather than a
                    bare doDamage so it reads her live Ability Power, takes
                    amps, and is a real damage instance -- which for a champion
                    whose AD is 10 is not a detail, it is nearly all of her.
      2nd (2-star)  the card Shreds whoever the attack hit for 2 seconds. Per
                    request this is a flat 20% on every enemy from combat
                    start, which is where a champion attacking once a second
                    into a 2s Shred lands anyway, minus the first attack.
      3rd (3-star)  the attack also fires a wave for the card's flat secondary
                    damage. "All other units hit" is modeled as num_targets
                    units (default 2): every opponent in this sim is the same
                    dummy, so which of them the wave catches is not a
                    distinction it can make -- only how many.

    The 4th ascension (infinite range, every 3rd wave enlarged) is not modeled:
    it needs a 4-star, and nothing here ascends anyone past 3.
    """

    levels = [1]
    display_name = "Solar Judgement"

    # 2nd Ascension. The card's 2s duration is not used -- see the class
    # docstring; the status is applied once and never lapses.
    shred = 0.20
    shred_from = 2
    wave_from = 3

    def __init__(self, level=1, params=0):
        super().__init__(
            self.display_name, level, params, phases=["preCombat", "onAttack"]
        )

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "preCombat":
            if champion.level >= self.shred_from:
                for opponent in champion.opponents:
                    opponent.applyStatus(
                        status.MRReduction("Kayle Shred"),
                        champion,
                        time,
                        # Longer than any combat this sim runs: the Shred is
                        # permanent here, so an expiry would only be a bug
                        # waiting for someone to raise the duration slider.
                        9999,
                        1 - self.shred,
                    )
            return 0

        # onAttack: input_ is the attack's opponent list, and the bonus lands
        # on whoever it hit.
        opponents = input_ if input_ else champion.opponents
        if not opponents:
            return 0
        champion.multiTargetSpell(
            opponents, champion.items, time, 1, champion.ascensionScaling, "magical"
        )
        if champion.level >= self.wave_from and champion.num_targets > 0:
            champion.multiTargetSpell(
                opponents,
                champion.items,
                time,
                champion.num_targets,
                champion.waveScaling,
                "magical",
            )
        return 0


class XayahFeathers(Buff):
    """Deadly Plumage: +50% Attack Speed for the next 5 attacks, each replaced
    with a feather dealing the card's physical damage.

    Same shape as AriseBuff and NidaleeUlt -- gain AS, manalock until the
    count runs out, swap the Attack's scaling from preAttack -- so the
    manalock/unlock and attack_progress handling mirror them exactly.

    The feathers' "reduce Armor by 2" is not modeled, per request.
    """

    levels = [1]
    display_name = "Deadly Plumage"

    def __init__(self, level=1, params=0):
        super().__init__(
            self.display_name,
            level,
            params,
            phases=["postAbility", "preAttack", "postAttack"],
        )
        self.as_bonus = 50
        self.num_feathers = 5
        self.attacks_remaining = 0
        self.active = False

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "postAbility":
            champion.aspd.addStat(self.as_bonus)
            self.attacks_remaining = self.num_feathers
            self.active = True
            # Manalocked until all num_feathers land -- pinned far ahead
            # rather than duration-estimated, since the AS gain changes the
            # attack cadence the instant this fires. Unlocked explicitly in
            # postAttack below once the count hits zero (same as AriseBuff).
            champion.manalockTime = time + 9999
        elif phase == "preAttack" and self.active and input_.regularAuto:
            # A feather is still an attack for on-hit purposes, but its damage
            # is the ability's, so it crits only where spell damage would.
            input_.canOnHit = True
            input_.canCrit = champion.canSpellCrit
            input_.attackType = "physical"
            input_.scaling = ChampionAbilityScaling(champion)
        elif phase == "postAttack" and self.active:
            # Runs after performAttack's own mana-gen check for this same
            # attack, so ending the ult here means the 5th feather still
            # generates no mana and only the first normal attack after does.
            self.attacks_remaining -= 1
            if self.attacks_remaining <= 0:
                self.active = False
                champion.aspd.addStat(-self.as_bonus)
                champion.manalockTime = time
                # Zero out windup overshoot accrued under the +50% AS so the
                # next attack's wait starts fresh under normal AS -- see
                # AriseBuff's postAttack for the full walkthrough.
                champion.attack_progress = min(champion.attack_progress, 1.0)
        return 0


class RumbleUlt(Buff):
    levels = [1]
    display_name = "Artillery Barrage"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["onUpdate"])
        self.next_missile = 0

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "onUpdate":
            missiles = 3 + (champion.aspd.add // 33)
            if time >= self.next_missile:
                champion.multiTargetSpell(
                    champion.opponents,
                    champion.items,
                    time,
                    1,
                    champion.abilityScaling,
                    "magical",
                )
                self.next_missile = time + 1 / missiles


class ZoeUlt(Buff):
    levels = [1]
    display_name = "Double Trouble Bubble"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["preCombat"])

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "preCombat":
            # permashred everyone. Not exactly accurate but it'll do
            for opponent in champion.opponents:
                opponent.applyStatus(
                    status.MRReduction("Zoe MR 30"), champion, time, 30, 0.7
                )


class ApheliosUlt(Buff):
    levels = [1]
    display_name = "Incendiary Onslaught"

    def __init__(self, level=1, params=0):
        super().__init__(
            self.display_name,
            level,
            params,
            phases=["preCombat", "preAttack", "postAbility"],
        )

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "preCombat":
            # permashred everyone
            for opponent in champion.opponents:
                opponent.applyStatus(
                    status.ArmorReduction("Aph Armor 30"), champion, time, 30, 0.7
                )
        elif phase == "postAbility" and champion.severumActivated:
            # severum was activated, apply buff
            champion.severumActivated = False
            champion.aspd.addStat(200)
        elif phase == "preAttack":
            if champion.severumAttacksLeft == 0:
                # Infernum
                input_.numTargets = 3
            else:
                input_.canCrit = champion.canSpellCrit
                input_.scaling = ChampionAbilityScaling(champion)
                champion.severumAttacksLeft -= 1
                if champion.severumAttacksLeft == 0:
                    # deactivate
                    champion.aspd.addStat(-200)
                    champion.manalockTime = time + 0.01
        return 0


class JhinUlt(Buff):
    levels = [1]
    display_name = "Curtain Call"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["preAttack"])

    def performAbility(self, phase, time, champion, input_=0):
        if champion.ultAutos > 0:
            input_.canOnHit = True
            input_.canCrit = champion.canSpellCrit
            input_.attackType = "physical"
            input_.scaling = (
                ChampionAbilityScaling(champion)
                if champion.ultAutos > 1
                else ScaledChampionAbilityScaling(champion, 2.44)
            )
            champion.ultAutos -= 1
            if champion.ultAutos == 0:
                champion.manalockTime = time + 0.01
                champion.aspd.base = 0.7
                champion.aspd.as_cap = 5
        return 0


class DravenUlt(Buff):
    levels = [1]

    def __init__(self, level=1, params=0):
        super().__init__(
            "Spinning Axes", level, params, phases=["preAttack", "onUpdate"]
        )
        self.attack_queue = deque()
        self.axe_return_time = 1.3

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "preAttack":
            if champion.axes > 0:
                input_.canOnHit = True
                input_.canCrit = champion.canCrit
                input_.attackType = "physical"
                input_.scaling = ChampionAbilityScaling(champion)
                champion.axes -= 1
                self.attack_queue.append(time + self.axe_return_time)
        if phase == "onUpdate":
            if self.attack_queue and self.attack_queue[0] < time:
                if champion.axes < 2:
                    champion.axes += 1
                self.attack_queue.popleft()
        return 0


class KaisaUlt(Buff):
    levels = [1]

    def __init__(self, level=1, params=0):
        super().__init__(
            "Icathian Rain", level, params, phases=["postPreCombat", "preAttack"]
        )
        self.autoCount = 0  # separate counter for empowered autos
        # todo: fix so it resets on cast

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "postPreCombat":
            # check if champ's bonus AD or AP is higher
            if champion.bonus_ad.stat < champion.ap.stat:
                champion.ad_version = False
                # fix role stuff: hardcoded in, but caster is 7 mpA, 2 mana regen. Marksman is 10 mpA, 0 mana regen.
                champion.manaRegen.addStat(-2)
                champion.manaPerAttack.addStat(3)
                champion.manalockDuration = 5
                champion.role = Role.ATTACK_MARKSMAN
                champion.castTime = 0
                champion.curMana = 10  # need to change curmana to be a stat
                champion.fullMana.base = 30
                champion.atk.base = 25

        elif phase == "preAttack" and not champion.ad_version and champion.ultActive:
            if self.autoCount % 5 == 0:
                champion.multiTargetSpell(
                    champion.opponents,
                    champion.items,
                    time,
                    1,
                    champion.empoweredAbilityScaling2,
                    "magical",
                )
            else:
                champion.multiTargetSpell(
                    champion.opponents,
                    champion.items,
                    time,
                    1,
                    champion.empoweredAbilityScaling,
                    "magical",
                )
            self.autoCount += 1
        return 0


class TwistedFateUlt(Buff):
    levels = [1]
    display_name = "Stacked Deck"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["preAttack"])

    def performAbility(self, phase, time, champion, input_=0):
        # input_.canOnHit = True
        # input_.canCrit = champion.canSpellCrit
        # input_.attackType = 'magical'
        # input_.scaling = ChampionAbilityScaling(champion)
        # if champion.numAttacks % 3 == 0:
        #     champion.multiTargetSpell(
        #         champion.opponents,
        #         champion.items,
        #         time,
        #         champion.num_targets - 2,
        #         champion.extraAbilityScaling,
        #     "magical",
        # )
        return 0


class JinxUlt(Buff):
    levels = [1]
    display_name = "Switcheroo"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["preAttack"])

    def performAbility(self, phase, time, champion, input_=0):
        if champion.numAttacks >= champion.auto_threshold[champion.level - 1]:
            input_.canOnHit = True
            input_.canCrit = champion.canCrit
            input_.attackType = "physical"
            input_.scaling = ChampionAbilityScaling(champion)
            for i in range(2):
                champion.doAttack(input_, champion.items, time)
        return 0


class THexUlt(Buff):
    levels = [1]
    display_name = "Hextech Arsenal"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["onUpdate"])
        self.missiles_to_send = 0
        self.missile_count = 0
        self.mana_drain = 30

    def performAbility(self, phase, time, champion, input_=0):
        if champion.ultActive:
            if champion.firstMissile:
                champion.firstMissile = False
                champion.curMana = champion.fullMana.stat
            if champion.curMana > 0:
                if time > champion.nextDrain:
                    champion.nextDrain += 0.25
                    champion.curMana -= self.mana_drain / 4
                    for i in range(champion.num_targets):
                        scale_factor = 1.0
                        if i == 1:
                            scale_factor = 0.3
                        elif i >= 2:
                            scale_factor = 0.1

                        scaling_func = (
                            champion.abilityScaling
                            if scale_factor == 1.0
                            else ScaledChampionAbilityScaling2(champion, scale_factor)
                        )

                        champion.multiTargetSpell(
                            champion.opponents,
                            champion.items,
                            time,
                            1,
                            scaling_func,
                            "physical",
                        )

                    self.missiles_to_send += champion.missilesPerTick
                    while self.missiles_to_send > 1:
                        self.missile_count += 1
                        self.missiles_to_send -= 1
                        champion.multiTargetSpell(
                            champion.opponents,
                            champion.items,
                            time,
                            1,
                            champion.extraAbilityScaling,
                            "physical",
                        )

            if champion.curMana <= 0:
                champion.ultActive = False
                champion.nextAttackTime = time + 0.01
                champion.curMana = 0
        return 0


class VeigarUlt(Buff):
    levels = [1]
    display_name = "Dark Storm"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["preCombat"])
        self.multScaling = 0.5

    def performAbility(self, phase, time, champion, input_=0):
        champion.canSpellCrit = True
        champion.ap.addMultiplier += self.multScaling
        return 0


class ViegoUlt(Buff):
    levels = [1]
    display_name = "Blade of the Ruined King"

    def __init__(self, level=1, params=0):
        super().__init__(
            self.display_name, level, params, phases=["preCombat", "preAttack"]
        )

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "preCombat":
            champion.aspd.addStat(10 + champion.souls // 6)
        elif phase == "preAttack":
            if champion.numCasts > 0:
                champion.multiTargetSpell(
                    champion.opponents,
                    champion.items,
                    time,
                    1,
                    champion.extraAbilityScaling,
                    "magical",
                )

        return 0


class YoneUlt(Buff):
    levels = [1]
    display_name = "Kin of the Stained Blade"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["preAttack"])

    def performAbility(self, phase, time, champion, input_=0):
        if champion.numAttacks % 2 == 1:
            champion.multiTargetSpell(
                champion.opponents,
                champion.items,
                time,
                1,
                champion.adAutoAbilityScaling,
                "physical",
            )
        else:
            champion.multiTargetSpell(
                champion.opponents,
                champion.items,
                time,
                1,
                champion.apAutoAbilityScaling,
                "magical",
            )
        return 0


class MissFortuneUlt(Buff):
    levels = [1]
    display_name = "Heartbreaker"

    def __init__(self, level=1, params=0):
        super().__init__(
            self.display_name, level, params, phases=["preCombat", "preAttack"]
        )
        self.newAttack = Attack()

    def MFScaling(level, baseAD, AD, AP=0):
        return baseAD * AD * 0.5

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "preCombat":
            self.newAttack.opponents = champion.opponents
            self.newAttack.canCrit = champion.canCrit
            self.newAttack.canOnHit = True
            self.newAttack.numTargets = 1
            self.newAttack.attackType = "physical"
            self.newAttack.scaling = MissFortuneUlt.MFScaling
        elif phase == "preAttack":
            champion.doAttack(self.newAttack, champion.items, time)


class YunaraUlt(Buff):
    levels = [1]

    def __init__(self, level=1, params=0):
        super().__init__(
            "Transcendent State",
            level,
            params,
            phases=["preCombat", "preAttack", "onCrit", "PostOnDealDamage"],
        )
        self.newAttack = Attack()
        self.critBonus = False
        self.true_dmg_scaling = 0.33

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "preCombat":
            self.newAttack.opponents = champion.opponents
            self.newAttack.canCrit = champion.canSpellCrit
            self.newAttack.canOnHit = True
            self.newAttack.numTargets = 1
        if champion.ultActive:
            if phase == "preAttack":
                input_.canOnHit = True
                input_.canCrit = champion.canSpellCrit
                input_.attackType = "physical"
                input_.scaling = ChampionAbilityScaling(champion)
                for index in range(1, champion.num_targets):
                    # 1: .6
                    # 2: .36
                    self.newAttack.scaling = ScaledChampionAbilityScaling(
                        champion, 0.25**index
                    )
                    champion.doAttack(self.newAttack, champion.items, time)
            elif phase == "onCrit":
                self.critBonus = True
            elif phase == "PostOnDealDamage":
                if self.critBonus:
                    true_dmg = self.true_dmg_scaling * input_[0]
                    champion.doDamage(
                        champion.opponents[0],
                        [],
                        0,
                        true_dmg,
                        true_dmg,
                        "true",
                        time,
                    )
                self.critBonus = False
                # return input_
        return input_


# AUGMENTS


class Kahunahuna(Buff):
    levels = [1]
    display_name = "Kahunahuna"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["postAttack"])
        self.stacks = 0
        self.scaling = 1.25

    def performAbility(self, phase, time, champion, input_=0):
        self.stacks += 1
        if self.stacks % 5 == 0:
            baseDmg = self.scaling * champion.atk.stat * champion.bonus_ad.stat
            champion.doDamage(
                champion.opponents[0], [], 0, baseDmg, baseDmg, "true", time
            )
        return 0


class SeraphimsStaff(Buff):
    levels = [1]
    display_name = "Seraphim's Staff"

    def __init__(self, level=1, params=0):
        super().__init__(
            self.display_name,
            level,
            params,
            phases=["preCombat"],
        )

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "preCombat":
            champion.seraphim = True
        return 0


class Retribution(Buff):
    levels = [1]
    display_name = "Retribution"

    def __init__(self, level=1, params=0):
        super().__init__(
            self.display_name,
            level,
            params,
            phases=["preCombat"],
        )
        self.crit_scaling = 0.15

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "preCombat":
            champion.retribution = True
            champion.crit.addStat(self.crit_scaling)
        return 0


class JeweledLotusI(Buff):
    levels = [1]
    display_name = "Jeweled Lotus I"

    def __init__(self, level=1, params=0):
        super().__init__(
            self.display_name,
            level,
            params,
            phases=["preCombat"],
        )
        self.crit_scaling = 0.1

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "preCombat":
            champion.crit.addStat(self.crit_scaling)
            champion.addPrecision()
        return 0


class JeweledLotusII(Buff):
    levels = [1]
    display_name = "Jeweled Lotus II"

    def __init__(self, level=1, params=0):
        super().__init__(
            self.display_name,
            level,
            params,
            phases=["preCombat"],
        )
        self.crit_scaling = 0.25
        self.crit_dmg_scaling = 0.1

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "preCombat":
            champion.crit.addStat(self.crit_scaling)
            champion.critDmg.addStat(self.crit_dmg_scaling)
            champion.addPrecision()
        return 0


class HoldTheLine5(Buff):
    levels = [1]
    display_name = "Hold The Line (5 units)"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["preCombat"])
        self.ad_scaling = 9
        self.ap_scaling = 10
        self.frontliners = 5

    def performAbility(self, phase, time, champion, input_=0):
        champion.bonus_ad.addStat(self.ad_scaling * self.frontliners)
        champion.ap.addStat(self.ap_scaling * self.frontliners)
        return 0


class HoldTheLine7(Buff):
    levels = [1]
    display_name = "Hold The Line (7 units)"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["preCombat"])
        self.ad_scaling = 9
        self.ap_scaling = 10
        self.frontliners = 7

    def performAbility(self, phase, time, champion, input_=0):
        champion.bonus_ad.addStat(self.ad_scaling * self.frontliners)
        champion.ap.addStat(self.ap_scaling * self.frontliners)
        return 0


class GlassCannonI(Buff):
    levels = [1]
    display_name = "Glass Cannon I"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["preCombat"])

    def performAbility(self, phase, time, champion, input_=0):
        champion.dmgMultiplier.addStat(0.16)
        return 0


class KnowYourEnemy(Buff):
    levels = [1]
    display_name = "Know Your Enemy"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["preCombat"])

    def performAbility(self, phase, time, champion, input_=0):
        champion.dmgMultiplier.addStat(0.15)
        return 0


class GlassCannonII(Buff):
    levels = [1]
    display_name = "Glass Cannon II"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["preCombat"])

    def performAbility(self, phase, time, champion, input_=0):
        champion.dmgMultiplier.addStat(0.25)
        return 0


class ItsMeBaby(Buff):
    levels = [1]
    display_name = "It's Me Baby"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["preCombat"])

    def performAbility(self, phase, time, champion, input_=0):
        champion.dmgMultiplier.addStat(0.15)
        champion.aspd.addStat(15)
        return 0



class SoulAwakening(Buff):
    levels = [1]
    display_name = "Soul Awakening"

    def __init__(self, level=1, params=0):
        super().__init__(
            self.display_name, level, params, phases=["onUpdate", "onDealDamage"]
        )
        self.ad_ap_boost = 1.5
        self.next_boost = 1
        self.deal_true_damage = False
        self.true_dmg_boost = 0.12

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "onUpdate":
            if time > self.next_boost:
                self.next_boost += 1
                champion.bonus_ad.addStat(self.ad_ap_boost)
                champion.ap.addStat(self.ad_ap_boost)
            if self.next_boost == 10:
                self.next_boost = 999
                self.deal_true_damage = True
        elif phase == "onDealDamage":
            if self.deal_true_damage:
                dmg = (
                    input_ * self.true_dmg_boost
                )  # note: this may interact badly with other things
                champion.doDamage(champion.opponents[0], [], 0, dmg, dmg, "true", time)
            return input_
        return 0


class MacesWill(Buff):
    levels = [1]
    display_name = "Maces Will"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["preCombat"])

    def performAbility(self, phase, time, champion, input_=0):
        champion.crit.addStat(0.25)
        return 0


class TonsOfStats(Buff):
    levels = [1]
    display_name = "Tons of Stats"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["preCombat"])
        self.scaling = 4

    def performAbility(self, phase, time, champion, input_=0):
        champion.hp.addStat(self.scaling * 11)
        champion.bonus_ad.addStat(self.scaling)
        champion.ap.addStat(self.scaling)
        champion.aspd.addStat(self.scaling)
        champion.armor.addStat(self.scaling)
        champion.mr.addStat(self.scaling)
        # hacky
        if champion.curMana < champion.fullMana.stat:
            champion.curMana += self.scaling
        return 0


class TonsOfStatsPris(Buff):
    levels = [1]
    display_name = "Tons of Stats (Pris)"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["preCombat"])
        self.scaling = 8

    def performAbility(self, phase, time, champion, input_=0):
        champion.hp.addStat(self.scaling * 11)
        champion.bonus_ad.addStat(self.scaling)
        champion.ap.addStat(self.scaling)
        champion.aspd.addStat(self.scaling)
        champion.armor.addStat(self.scaling)
        champion.mr.addStat(self.scaling)
        # hacky
        if champion.curMana < champion.fullMana.stat:
            champion.curMana += self.scaling
        return 0


class BestFriendsI(Buff):
    levels = [1]
    display_name = "Best Friends I"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["preCombat"])

    def performAbility(self, phase, time, champion, input_=0):
        champion.aspd.addStat(10)
        champion.armor.addStat(9)
        champion.mr.addStat(9)
        return 0


class BestFriendsII(Buff):
    levels = [1]
    display_name = "Best Friends II"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["preCombat"])

    def performAbility(self, phase, time, champion, input_=0):
        champion.aspd.addStat(15)
        champion.armor.addStat(14)
        champion.armor.addStat(14)

        return 0


class TrifectaI(Buff):
    levels = [1]
    display_name = "Trifecta I"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["preCombat"])

    def performAbility(self, phase, time, champion, input_=0):
        champion.aspd.addStat(20)
        return 0


class TrifectaII(Buff):
    levels = [1]
    display_name = "Trifecta II"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["preCombat"])

    def performAbility(self, phase, time, champion, input_=0):
        champion.aspd.addStat(30)
        return 0


class TinyButDeadly(Buff):
    levels = [1]
    display_name = "Tiny But Deadly"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["preCombat"])

    def performAbility(self, phase, time, champion, input_=0):
        champion.aspd.addStat(33)
        return 0


class WarlordsHonor(Buff):
    levels = [1]
    display_name = "Warlord's Honor"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["preCombat"])

    def performAbility(self, phase, time, champion, input_=0):
        champion.bonus_ad.addStat(20)
        champion.ap.addStat(20)
        return 0


class StandUnitedI(Buff):
    levels = [1]
    display_name = "Stand United"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["preCombat"])
        self.scaling = 1.5

    def performAbility(self, phase, time, champion, input_=0):
        champion.bonus_ad.addStat(champion.num_traits * self.scaling)
        champion.ap.addStat(champion.num_traits * self.scaling)
        return 0


class PumpingUpI(Buff):
    levels = [1]
    display_name = "Pumping Up I"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["preCombat"])
        self.base_scaling = 6
        self.bonus_scaling = 0.5

    def performAbility(self, phase, time, champion, input_=0):
        champion.aspd.addStat(
            self.base_scaling + self.bonus_scaling * 6 * (champion.stage - 2)
        )
        return 0


class PumpingUpII(Buff):
    levels = [1]
    display_name = "Pumping Up II"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["preCombat"])
        self.base_scaling = 10
        self.bonus_scaling = 1

    def performAbility(self, phase, time, champion, input_=0):
        champion.aspd.addStat(
            self.base_scaling + self.bonus_scaling * 6 * (champion.stage - 2)
        )
        return 0


class PumpingUpIII(Buff):
    levels = [1]
    display_name = "Pumping Up III"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["preCombat"])
        self.base_scaling = 16
        self.bonus_scaling = 2

    def performAbility(self, phase, time, champion, input_=0):
        champion.aspd.addStat(
            self.base_scaling + self.bonus_scaling * 6 * (champion.stage - 2)
        )
        return 0


class NoScoutNoPivot(Buff):
    levels = [1]
    display_name = "No Scout no Pivot"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["preCombat"])
        self.ad_scaling = 1
        self.ap_scaling = 1

    def performAbility(self, phase, time, champion, input_=0):
        champion.bonus_ad.addStat(self.ad_scaling * 5 * (champion.stage - 2))
        champion.ap.addStat(self.ap_scaling * 5 * (champion.stage - 2))
        return 0


class EarlyLearnings(Buff):
    levels = [1]
    display_name = "Early Learnings (assume 1-cost)"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["preCombat"])
        self.base = 5
        self.ad_scaling = 2
        self.ap_scaling = 2

    def performAbility(self, phase, time, champion, input_=0):
        champion.bonus_ad.addStat(
            self.base + self.ad_scaling * 5 * (champion.stage - 2)
        )
        champion.ap.addStat(self.base + self.ap_scaling * 5 * (champion.stage - 2))
        return 0


class AccelerationHex(Buff):
    levels = [1]
    display_name = "Acceleration Hex"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["preCombat"])

    def performAbility(self, phase, time, champion, input_=0):
        champion.aspd.addStat(30)
        return 0


class AccelerationHexEmpowered(Buff):
    levels = [1]
    display_name = "Acceleration Hex (Empowered)"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["preCombat"])

    def performAbility(self, phase, time, champion, input_=0):
        champion.aspd.addStat(45)
        return 0


class StarlightHex(Buff):
    levels = [1]
    display_name = "Starlight Hex"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["preCombat"])

    def performAbility(self, phase, time, champion, input_=0):
        champion.manaRegen.addStat(3)
        return 0


class StarlightHexEmpowered(Buff):
    levels = [1]
    display_name = "Starlight Hex (Empowered)"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["preCombat"])

    def performAbility(self, phase, time, champion, input_=0):
        champion.manaRegen.addStat(4.5)
        return 0


class AdaptiveStyle(Buff):
    levels = [1]
    display_name = "AdaptiveStyle"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["preAttack"])
        self.stacks = 0
        self.max_stacks = 15

    def performAbility(self, phase, time, champion, input_=0):
        for item in champion.items:
            if "Duelist" in item.name and self.stacks < self.max_stacks:
                self.stacks += 1
                champion.bonus_ad.addStat(2)
                champion.ap.addStat(2)
                break
        return 0


class Ascension(Buff):
    levels = [1]
    display_name = "Ascension"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["onUpdate"])
        self.dmgBonus = 0.35
        self.nextBonus = 12

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "onUpdate":
            if time >= self.nextBonus:
                self.nextBonus += 99999
                champion.dmgMultiplier.addStat(self.dmgBonus)
        return 0


class PartialAscension(Buff):
    levels = [1]
    display_name = "Partial Ascension"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["onUpdate"])
        self.dmgBonus = 0.2
        self.nextBonus = 12

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "onUpdate":
            if time >= self.nextBonus:
                self.nextBonus += 99999
                champion.dmgMultiplier.addStat(self.dmgBonus)
        return 0


class ScopedWeaponsII(Buff):
    levels = [1]
    display_name = "ScopedWeaponsII"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["preCombat"])
        self.scaling = 25

    def performAbility(self, phase, time, champion, input_=0):
        champion.aspd.addStat(self.scaling)
        return 0


class BackupDancers(Buff):
    levels = [1]
    display_name = "Backup Dancers"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["onUpdate"])
        self.asBonus = 9
        self.nextBonus = 0

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "onUpdate":
            if time >= self.nextBonus:
                self.nextBonus += 3
                champion.aspd.addStat(self.asBonus)
        return 0


class FocusedFire(Buff):
    levels = [1]
    display_name = "Focused Fire"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["onUpdate"])
        self.adBonus = 10
        self.nextBonus = 0
        self.bonusInterval = 5

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "onUpdate":
            if time >= self.nextBonus:
                self.nextBonus += self.bonusInterval
                champion.bonus_ad.addStat(self.adBonus)
        return 0


class Shred30(Buff):
    levels = [1]
    display_name = "30% Armor/MR Shred"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["preCombat"])

    def performAbility(self, phase, time, champion, input_=0):
        for opponent in champion.opponents:
            opponent.applyStatus(
                status.ArmorReduction("Armor 30"), champion, time, 30, 0.7
            )
            opponent.applyStatus(status.MRReduction("MR 30"), champion, time, 30, 0.7)
        return 0


class Shred20(Buff):
    levels = [1]
    display_name = "20% Armor/MR Shred"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["preCombat"])

    def performAbility(self, phase, time, champion, input_=0):
        for opponent in champion.opponents:
            opponent.applyStatus(
                status.ArmorReduction("Armor 20"), champion, time, 30, 0.8
            )
            opponent.applyStatus(status.MRReduction("MR 20"), champion, time, 30, 0.8)
        return 0


class ClockworkAccelerator(Buff):
    levels = [1]
    display_name = "Clockwork Accelerator"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["onUpdate"])
        self.asBonus = 10
        self.nextBonus = 3

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "onUpdate":
            if time >= self.nextBonus:
                self.nextBonus += 3
                champion.aspd.addStat(self.asBonus)
        return 0


class BaronsLair(Buff):
    levels = [1]
    display_name = "Baron's Lair"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["onUpdate"])
        self.statBonus = 4
        self.nextBonus = 8

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "onUpdate":
            if time >= self.nextBonus:
                self.nextBonus += 1
                champion.bonus_ad.addStat(self.statBonus)
                champion.ap.addStat(self.statBonus)
        return 0


class Corrosion(Buff):
    levels = [1]
    display_name = "Corrosion"

    def __init__(self, level=1, params=0):
        super().__init__(self.display_name, level, params, phases=["preCombat"])

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "preCombat":
            for opponent in champion.opponents:
                opponent.applyStatus(status.CorrosionStatus(), champion, time, 30, 0)
        return 0


class CryMeARiver(Buff):
    levels = [1]
    display_name = "Cry Me A River"

    def __init__(self, level=1, params=0):
        super().__init__(
            self.display_name, level, params, phases=["preCombat", "onUpdate"]
        )
        self.stage_2_active = False

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "preCombat":
            champion.manaRegen.addStat(1)
        elif phase == "onUpdate":
            if not self.stage_2_active and time >= 12:
                # After 12 seconds, increase to 4 (so add 3 more)
                champion.manaRegen.addStat(3)
                self.stage_2_active = True
        return 0
