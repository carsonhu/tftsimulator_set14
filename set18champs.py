import math

from role import Role
from set18buffs import (AdaptorInnate, ApheliosOnslaught, AriseBuff, AsheTrail,
                        AttunedInnate, CaitlynHeadshotBuff,
                        CinderlingScarletBuff, GrompPurpleBuff,
                        KayleAscensions, MasterYiUlt, NidaleeUlt,
                        PebblesChannel, SivirBounces, TinyBeaksBuff,
                        XayahFeathers)

import status
from champion import Champion

champ_list = [
    "Varus",
    "Yunara",
    "LeBlanc",
    "MamaBeak",
    "Cassiopeia",
    "Zyra",
    "Azir",
    "Caitlyn",
    "Ahri",
    "Gromp",
    "Karma",
    "MasterYi",
    "Akali",
    "Ezreal",
    "Warwick",
    "Alune",
    "Camille",
    "Nidalee",
    "Sivir",
    "Ashe",
    "Cinderling",
    "Teemo",
    "Pebbles",
    "Aphelios",
    "Kayle",
    "Xayah",
]


def create_ability_scaling(ad_values, ap_values, func_name="abilityScaling"):
    """
    Factory function to create ability scaling functions.

    Args:
        ad_values: List of 3 AD scaling values [level1, level2, level3]
        ap_values: List of 3 AP scaling values [level1, level2, level3]
        func_name: The name of the function to be created (must match attribute name for pickling)

    Returns:
        A function that calculates ability damage based on level, AD, and AP
    """

    def scaling(_self, level, AD, AP):
        return ap_values[level - 1] * AP + ad_values[level - 1] * AD

    scaling.__name__ = func_name
    # Hung on the function so the numbers stay readable after the closure
    # swallows them: patch_check.py needs to compare these against the values
    # recorded in patch_pin.json, and a closure it cannot see into is a number
    # nothing can ever check.
    scaling.ad_values = list(ad_values)
    scaling.ap_values = list(ap_values)
    return scaling


class BaseChamp(Champion):
    def __init__(self, level):
        hp = 1000
        atk = 70
        curMana = 10
        fullMana = 100
        aspd = 0.85
        armor = 0
        mr = 0
        super().__init__(
            "Base Champ", hp, atk, curMana, fullMana, aspd, armor, mr, level
        )
        self.ap_scale = 1
        self.castTime = 0.5

    def abilityScaling(self, level, AD, AP):
        # Dynamic AP scaling based on self.ap_scale
        base_scaling = create_ability_scaling(
            [0, 0, 0], [self.ap_scale, self.ap_scale, self.ap_scale]
        )
        return base_scaling(None, level, AD, AP)

    def performAbility(self, opponents, items, time):
        self.multiTargetSpell(opponents, items, time, 1, self.abilityScaling, "magical")


class ZeroResistance(Champion):
    def __init__(self, level):
        hp = 1000
        atk = 70
        curMana = 10
        fullMana = 100
        aspd = 0.85
        armor = 0
        mr = 0
        super().__init__("Tankman", hp, atk, curMana, fullMana, aspd, armor, mr, level)
        self.castTime = 0.5

    def performAbility(self, opponents, items, time):
        return 0


class DummyTank(Champion):
    def __init__(self, level):
        hp = 1000
        atk = 70
        curMana = 10
        fullMana = 100
        aspd = 0.85
        armor = 100
        mr = 100
        super().__init__("Tankman", hp, atk, curMana, fullMana, aspd, armor, mr, level)
        self.castTime = 0.5

    def performAbility(self, opponents, items, time):
        return 0


class SuperDummyTank(Champion):
    def __init__(self, level):
        hp = 2000
        atk = 70
        curMana = 10
        fullMana = 100
        aspd = 0.85
        armor = 200
        mr = 200
        super().__init__("Tankman", hp, atk, curMana, fullMana, aspd, armor, mr, level)
        self.castTime = 0.5

    def performAbility(self, opponents, items, time):
        return 0


class Varus(Champion):
    def __init__(self, level):
        hp = 500
        atk = 40
        curMana = 30
        fullMana = 120
        aspd = 0.7
        armor = 25
        mr = 25
        super().__init__(
            "Varus",
            hp,
            atk,
            curMana,
            fullMana,
            aspd,
            armor,
            mr,
            level,
            Role.ATTACK_CASTER,
        )
        self.default_traits = ["Rapidfire"]
        self.castTime = 2.0
        self.num_targets = 2

    abilityScaling = create_ability_scaling([415, 625, 1000], [30, 45, 70])

    def performAbility(self, opponents, items, time):
        # Piercing Arrow: hits the first num_targets enemies in line; damage is
        # reduced by 40% for each enemy already pierced (minimum 40% of base).
        pierce_multiplier = 1.0
        for opponent in opponents[: self.num_targets]:
            mult = pierce_multiplier

            def pierce_scaling(level, AD, AP, mult=mult):
                return mult * self.abilityScaling(level, AD, AP)

            self.multiTargetSpell([opponent], items, time, 1, pierce_scaling, "physical")
            pierce_multiplier = max(0.4, pierce_multiplier * 0.6)


class Yunara(Champion):
    def __init__(self, level):
        hp = 550
        atk = 42
        curMana = 0
        fullMana = 35
        aspd = 0.75
        armor = 30
        mr = 30
        super().__init__(
            "Yunara",
            hp,
            atk,
            curMana,
            fullMana,
            aspd,
            armor,
            mr,
            level,
            Role.ATTACK_CASTER,
        )
        self.default_traits = ["Blossom", "Executioner"]
        # Full dash + orb-throw duration: maps directly to the real
        # cast-trigger-to-next-attack gap (no separate windup on top -- see
        # champion.py's post-cast attack_progress reset). Measured ~1.27-1.49s
        # for near-zero-distance dashes and ~1.8s for a full-board dash;
        # 1.8s assumes medium/long dashes are the common case. Revisit if
        # short dashes turn out to be more frequent in practice.
        self.castTime = 1.8

    abilityScaling = create_ability_scaling([160, 240, 370], [10, 15, 25])
    splash_ratio = 0.35
    splash_targets = 2

    def performAbility(self, opponents, items, time):
        # Cultivation of Spirit: dash, then launch an orb dealing physical
        # damage to the current target, splitting 35% of that damage to
        # splash_targets nearby enemies. Always 1 main target + 2 splash --
        # not user-adjustable, so no num_targets/num_extra_targets here.
        # numAttacks=1 on the main hit makes the cast count as an attack for
        # on-attack effects (e.g. Rapidfire's per-attack AS stacking),
        # without a redundant basic-attack hit or extra manaPerAttack
        # generation (the cast's own mana reset already handles that).
        if not opponents:
            return
        self.multiTargetSpell(
            opponents[:1], items, time, 1, self.abilityScaling, "physical", numAttacks=1
        )

        def splash_scaling(level, AD, AP):
            return self.splash_ratio * self.abilityScaling(level, AD, AP)

        self.multiTargetSpell(
            opponents[1:], items, time, self.splash_targets, splash_scaling, "physical"
        )


class LeBlanc(Champion):
    def __init__(self, level):
        hp = 550
        atk = 30
        curMana = 0
        fullMana = 40
        aspd = 0.7
        armor = 30
        mr = 30
        super().__init__(
            "LeBlanc",
            hp,
            atk,
            curMana,
            fullMana,
            aspd,
            armor,
            mr,
            level,
            Role.MAGIC_CASTER,
        )
        self.default_traits = ["Elderwood", "Spellweaver"]
        # Measured directly off video frames in 2026-08-04 14-01-14.mkv:
        # mana hits 0 (cast start) at 05:34.166, next attack-windup twirl
        # starts at 05:35.266 -- a 1.1s raw gap, with the extra ~0.1s inside
        # attack-windup/frame-rounding slop rather than the cast itself.
        # Matches the standard 1.0s TFT mage cast time. Supersedes the
        # earlier 1.2s estimate from 5fps OCR sampling (see
        # verify_leblanc_mana.py) -- that was undersampled, this is exact.
        self.castTime = 1.0
        self.num_targets = 2

    abilityScaling = create_ability_scaling([0, 0, 0], [260, 390, 615])
    splashScaling = create_ability_scaling(
        [0, 0, 0], [100, 150, 230], func_name="splashScaling"
    )

    def performAbility(self, opponents, items, time):
        # Mirror Image: full damage to current target, reduced damage to
        # num_targets-1 adjacent enemies. Passive (ally clone on takedown)
        # ignored per request -- board-composition dependent, out of scope.
        if not opponents:
            return
        self.multiTargetSpell(opponents[:1], items, time, 1, self.abilityScaling, "magical")
        self.multiTargetSpell(
            opponents[1:], items, time, self.num_targets - 1, self.splashScaling, "magical"
        )


class MamaBeak(Champion):
    def __init__(self, level):
        hp = 650
        atk = 55
        curMana = 20
        fullMana = 60
        aspd = 0.75
        armor = 35
        mr = 35
        super().__init__(
            "Mama Beak",
            hp,
            atk,
            curMana,
            fullMana,
            aspd,
            armor,
            mr,
            level,
            Role.ATTACK_MARKSMAN,
        )
        self.default_traits = ["Riftbeast", "Summoner", "Rapidfire"]
        # Tentative, needs investigating.
        self.castTime = 0
        # Always-on (not an opt-in buff-bar selection): every attack while
        # active summons Tiny Beak hits, which is core to her kit rather
        # than a togglable ultimate.
        self.items.append(TinyBeaksBuff())

    beakScaling = create_ability_scaling([22, 33, 48], [0, 0, 0], func_name="beakScaling")

    def performAbility(self, opponents, items, time):
        # Flock Family: the cast itself deals no damage -- it just opens the
        # Tiny Beaks window, handled by TinyBeaksBuff (see __init__) via
        # postAbility/postAttack. Riftbeast's Orange Buff (armor shred on
        # physical damage) is unimplemented for now.
        return 0


class Cassiopeia(Champion):
    def __init__(self, level):
        hp = 650
        atk = 30
        curMana = 0
        fullMana = 30
        aspd = 0.75
        armor = 35
        mr = 35
        super().__init__(
            "Cassiopeia",
            hp,
            atk,
            curMana,
            fullMana,
            aspd,
            armor,
            mr,
            level,
            Role.MAGIC_CASTER,
        )
        # Coven ignored per request.
        self.default_traits = ["Spellweaver"]
        self.castTime = 1
        self.poison_duration = 15

    abilityScaling = create_ability_scaling([0, 0, 0], [400, 600, 950])

    def performAbility(self, opponents, items, time):
        # Noxious Blast: poison target 1 and target 2 for total magic damage
        # over poison_duration, ticking once per second. Real ability picks
        # "nearest non-poisoned enemy" for the 2nd target; per request this
        # always uses opponents[1] instead. Poisons stack, so each cast gets
        # its own uniquely named status (see CassiopeiaPoisonStatus) rather
        # than refreshing/replacing whatever's already ticking.
        #
        # The scaling function goes down instead of a damage number: each
        # tick re-reads Cass's AP at tick time, so AP gained mid-poison
        # raises the remaining ticks.
        for i, opponent in enumerate(opponents[:2]):
            opponent.applyStatus(
                status.CassiopeiaPoisonStatus(
                    f"Cassiopeia Poison {id(self)} {self.numCasts} {i}"
                ),
                self,
                time,
                self.poison_duration,
                self.abilityScaling,
            )


class Zyra(Champion):
    def __init__(self, level):
        hp = 850
        atk = 40
        curMana = 0
        fullMana = 45
        aspd = 0.75
        armor = 40
        mr = 40
        super().__init__(
            "Zyra",
            hp,
            atk,
            curMana,
            fullMana,
            aspd,
            armor,
            mr,
            level,
            Role.MAGIC_CASTER,
        )
        self.default_traits = ["Thornmaiden", "Summoner"]
        # Measured from 2026-08-04 14-01-14.mkv, t=715-736s: 5/5 clean
        # cast-reset-to-next-attack gaps all landed at exactly 1.2s (no
        # variance), overriding the 1.0s tentative guess. Frame-perfect
        # verification (like LeBlanc got) would sharpen this further.
        self.castTime = 1.2
        self.num_plants = 2
        self.plant_attacks = 10
        self.plant_interval = 0.8

    plantScaling = create_ability_scaling([0, 0, 0], [35, 53, 225], func_name="plantScaling")

    def performAbility(self, opponents, items, time):
        # Rampant Growth: spawn num_plants plants, each independently
        # attacking the caster's current first target every plant_interval
        # seconds for plant_attacks hits (+ Summoner's bonus, see
        # set18buffs.Summoner). Modeled as self-applied ticking statuses
        # (DoTEffect-style: the caster deals damage to its own current
        # first target each tick) rather than tracking plants as separate
        # entities.
        total_attacks = self.plant_attacks + getattr(self, "summoner_bonus_attacks", 0)
        duration = self.plant_interval * total_attacks + self.plant_interval
        for i in range(self.num_plants):
            self.applyStatus(
                status.ZyraPlantStatus(f"Zyra Plant {id(self)} {self.numCasts} {i}"),
                self,
                time,
                duration,
                (self.plantScaling, self.plant_interval, total_attacks),
            )


class Azir(Champion):
    def __init__(self, level):
        hp = 650
        atk = 30
        curMana = 0
        fullMana = 35
        aspd = 0.75
        armor = 35
        mr = 35
        super().__init__(
            "Azir",
            hp,
            atk,
            curMana,
            fullMana,
            aspd,
            armor,
            mr,
            level,
            Role.MAGIC_MARKSMAN,
        )
        self.default_traits = ["Blackthorn", "Executioner", "Summoner"]
        self.castTime = 0.5
        self.items.append(AriseBuff())

    abilityScaling = create_ability_scaling([0, 0, 0], [43, 65, 103])

    def performAbility(self, opponents, items, time):
        # Arise!: no direct cast damage -- AriseBuff (see __init__) handles
        # the AS gain, the manalock-until-6-attacks gate, and replacing the
        # next 6 attacks with 2-target magic soldier commands.
        return 0


class Caitlyn(Champion):
    def __init__(self, level):
        hp = 550
        atk = 50
        curMana = 0
        # -1 disables casting entirely (canCast() requires fullMana.stat >
        # -1) -- her 3rd attack is a passive attack replacement, not a real
        # spell cast, per request.
        fullMana = -1
        aspd = 0.7
        armor = 30
        mr = 30
        super().__init__(
            "Caitlyn",
            hp,
            atk,
            curMana,
            fullMana,
            aspd,
            armor,
            mr,
            level,
            Role.ATTACK_SPECIALIST,
        )
        # Coven ignored per request.
        self.default_traits = ["Hunter"]
        self.items.append(CaitlynHeadshotBuff())

    # Physical damage row: 190/285/450 AD-scaled + 20/30/45 AP-scaled.
    abilityScaling = create_ability_scaling([190, 285, 470], [20, 30, 45])

    def performAbility(self, opponents, items, time):
        # Never actually called -- fullMana=-1 keeps canCast() False.
        # Headshot triggers off attack count (CaitlynHeadshotBuff, see
        # __init__), not mana.
        return 0


class Ahri(Champion):
    def __init__(self, level):
        hp = 850
        atk = 40
        curMana = 20
        fullMana = 100
        aspd = 0.8
        armor = 40
        mr = 40
        super().__init__(
            "Ahri",
            hp,
            atk,
            curMana,
            fullMana,
            aspd,
            armor,
            mr,
            level,
            Role.MAGIC_CASTER,
        )
        self.default_traits = ["Blossom", "Spellweaver"]
        # Measured from 2026-08-04 14-01-14.mkv, t=872-911s: 7/7 clean
        # cast-reset-to-next-attack gaps all landed at exactly 1.8s (no
        # variance) -- matches the tentative guess exactly.
        self.castTime = 1.8
        self.num_targets = 5

    abilityScaling = create_ability_scaling([0, 0, 0], [455, 685, 3500])
    # "reduced by X% per hex away from the epicenter". 18.2: 20% -> 21%.
    falloff_per_hex = 0.21

    def performAbility(self, opponents, items, time):
        # Spirit Bomb: 1 target at the epicenter (full damage), the next 2
        # one hex out, everyone else two hexes out -- including any beyond
        # the base 5 (overflow just extends the outer ring). Fewer than num_targets
        # enemies truncates this list from the end (outermost ring drops
        # first), which falls out naturally from only iterating over
        # however many opponents actually exist.
        for i, opponent in enumerate(opponents[: self.num_targets]):
            if i == 0:
                mult = 1.0
            elif i <= 2:
                mult = 1 - self.falloff_per_hex
            else:
                mult = 1 - 2 * self.falloff_per_hex

            def scaling(level, AD, AP, mult=mult):
                return mult * self.abilityScaling(level, AD, AP)

            self.multiTargetSpell([opponent], items, time, 1, scaling, "magical")


class Gromp(Champion):
    # Gromp's two versions do not share a base AD. He is built from the AP
    # version's, since that is the one he defaults to and the one the set's
    # data records (DA_Gromp18_AP); the AD version's 45 is swapped in by
    # AdaptorInnate, same as Master Yi and Akali but mirrored, because their
    # card stats are the AD version's and his are the AP version's.
    AD_VERSION_ATK = 45
    AP_VERSION_ATK = 30

    def __init__(self, level):
        hp = 550
        atk = self.AP_VERSION_ATK
        curMana = 0
        fullMana = 45
        aspd = 0.7
        armor = 30
        mr = 30
        super().__init__(
            "Gromp",
            hp,
            atk,
            curMana,
            fullMana,
            aspd,
            armor,
            mr,
            level,
            Role.MAGIC_CASTER,
        )
        self.default_traits = ["Riftbeast", "Adaptor"]
        self.castTime = 1
        self.num_targets = 2
        self.splash_duration = 3
        # Set at combat start by AdaptorInnate; True = the physical version.
        self.ad_version = False
        self.adaptor_resolved = False
        # Gromp is one of the two Adaptors (with Nidalee) that starts on its
        # AP version when nothing has pushed either stat ahead.
        self.adaptor_ties_to_ad = False
        # Star-scaled off the AP base already in atk.base, so the ratio holds
        # at every star level rather than pinning the AD version to 1-star.
        self.ad_base_atk = self.atk.base * self.AD_VERSION_ATK / self.AP_VERSION_ATK
        # Always-on rather than opt-in buff-bar picks: Belchy Bubble adapts
        # on every Gromp, and the Purple Buff no-ops on its own unless
        # Riftbeast (3) has set the Alpha Mark flag.
        self.items.append(AdaptorInnate())
        self.items.append(GrompPurpleBuff())
        self.notes = "Defaults AP"

    # AP version: burst on the current target, 3s splash DoT on the rest.
    apAbilityScaling = create_ability_scaling(
        [0, 0, 0], [225, 340, 535], func_name="apAbilityScaling"
    )
    apSplashScaling = create_ability_scaling(
        [0, 0, 0], [160, 240, 360], func_name="apSplashScaling"
    )
    # AD version: burst on the current target, instant splash on the rest.
    adAbilityScaling = create_ability_scaling(
        [305, 460, 725], [30, 45, 70], func_name="adAbilityScaling"
    )
    adSplashScaling = create_ability_scaling(
        [100, 150, 240], [0, 0, 0], func_name="adSplashScaling"
    )

    def performAbility(self, opponents, items, time):
        # Belchy Bubble: full damage to the current target, splash to
        # num_targets-1 enemies within a hex of the explosion. Which of the
        # two versions fires was pinned at combat start by AdaptorInnate.
        if not opponents:
            return 0
        num_splash = self.num_targets - 1
        if self.ad_version:
            self.multiTargetSpell(
                opponents[:1], items, time, 1, self.adAbilityScaling, "physical"
            )
            self.multiTargetSpell(
                opponents[1:], items, time, num_splash, self.adSplashScaling, "physical"
            )
        else:
            self.multiTargetSpell(
                opponents[:1], items, time, 1, self.apAbilityScaling, "magical"
            )
            # Splash is a DoT, so it goes out as a status on each victim
            # (see status.GrompBubbleStatus) rather than an instant hit. The
            # scaling function goes down instead of a damage number: AP DoT
            # ticks re-read the caster's AP (and amps) at tick time.
            for opponent in opponents[1 : 1 + num_splash]:
                opponent.applyStatus(
                    status.GrompBubbleStatus(),
                    self,
                    time,
                    self.splash_duration,
                    self.apSplashScaling,
                )
        return 0


class Karma(Champion):
    def __init__(self, level):
        hp = 500
        atk = 25
        curMana = 0
        fullMana = 40
        aspd = 0.7
        armor = 25
        mr = 25
        super().__init__(
            "Karma",
            hp,
            atk,
            curMana,
            fullMana,
            aspd,
            armor,
            mr,
            level,
            Role.MAGIC_CASTER,
        )
        self.default_traits = ["Blossom", "Spellweaver"]
        # Per request. Longer than the 1.5s tether, so a recast can never
        # land while the previous tether is still ticking.
        self.castTime = 3.0
        self.num_targets = 2
        self.tether_duration = 1.5
        self.tether_interval = 0.5

    tetherScaling = create_ability_scaling(
        [0, 0, 0], [280, 420, 630], func_name="tetherScaling"
    )
    burstScaling = create_ability_scaling(
        [0, 0, 0], [120, 180, 270], func_name="burstScaling"
    )

    def performAbility(self, opponents, items, time):
        # Karmic Bond: tether the current target for tether_duration, dealing
        # the tether total to it alone in even ticks, then burst on it and
        # the enemies within a hex -- num_targets counts the tethered target
        # itself, so the default 2 is "target + 1 neighbour". The tether and
        # the delayed burst both live in KarmaTetherStatus (see status.py).
        if not opponents:
            return 0
        ticks = max(1, round(self.tether_duration / self.tether_interval))
        opponents[0].applyStatus(
            # Unique per cast, like Cassiopeia's poison: refreshing a shared
            # status would drop a burst that hadn't fired yet if castTime
            # were ever lowered below the tether's duration.
            status.KarmaTetherStatus(f"Karma Tether {id(self)} {self.numCasts}"),
            self,
            time,
            self.tether_duration,
            (
                self.tetherScaling,
                self.tether_interval,
                ticks,
                self.burstScaling,
                self.num_targets,
            ),
        )
        return 0


class MasterYi(Champion):
    # The AD version's base AD; the AP version is a much weaker autoattacker.
    # 18.2 (official notes): 65 -> 60. The cdragon pbe dump reads 62 and lags
    # the live build; acknowledged in patch_pin.json.
    AD_VERSION_ATK = 60
    AP_VERSION_ATK = 15

    def __init__(self, level):
        hp = 850
        atk = self.AD_VERSION_ATK
        curMana = 0
        # -1 disables casting entirely (canCast() requires fullMana.stat >
        # -1) -- the third-attack Double Strike is a passive, not a cast, so
        # it lives in MasterYiUlt instead.
        fullMana = -1
        aspd = 0.8
        armor = 55
        mr = 55
        super().__init__(
            "Master Yi",
            hp,
            atk,
            curMana,
            fullMana,
            aspd,
            armor,
            mr,
            level,
            Role.ATTACK_SPECIALIST,
        )
        self.default_traits = ["Blossom", "Adaptor"]
        # Base AD to switch to if the AP version wins the Adaptor comparison.
        # Scaled off self.atk.base so the star-level multiplier Champion
        # already applied carries over instead of being re-derived here.
        self.ap_base_atk = self.atk.base * self.AP_VERSION_ATK / self.AD_VERSION_ATK
        # Set at combat start by AdaptorInnate; True = the physical version,
        # which is also where an untouched one lands (unlike Gromp).
        self.ad_version = False
        self.adaptor_resolved = False
        self.adaptor_ties_to_ad = True
        self.items.append(AdaptorInnate())
        self.items.append(MasterYiUlt())

    # AP version: bonus magic damage on each of the two Double Strike hits.
    # 18.2 (official notes): 140/210/335 -> 125/190/285. The card itself
    # prints no number for this line, so the notes are the only source.
    abilityScaling = create_ability_scaling([0, 0, 0], [125, 190, 285])

    def performAbility(self, opponents, items, time):
        # Never actually called -- fullMana=-1 keeps canCast() False. Wuju
        # Style triggers off attack count (MasterYiUlt, see __init__).
        return 0


class Akali(Champion):
    # The AD version's base AD; the AP version trades 10 of it away.
    AD_VERSION_ATK = 40
    AP_VERSION_ATK = 30

    def __init__(self, level):
        hp = 650
        atk = self.AD_VERSION_ATK
        curMana = 0
        fullMana = 25
        aspd = 0.75
        armor = 35
        mr = 35
        super().__init__(
            "Akali",
            hp,
            atk,
            curMana,
            fullMana,
            aspd,
            armor,
            mr,
            level,
            Role.ATTACK_FIGHTER,
        )
        # Inferno isn't in the buff list yet, so it isn't preselected.
        self.default_traits = ["Adaptor", "Ravager"]
        # Guess: Kunai Strike is still a bin placeholder (its 0.25s is the
        # unauthored-spell template default, shared by every other unauthored
        # set-18 spell), so this uses the 1.0s the set's other single-target
        # casters measured out at.
        self.castTime = 1.0
        # Base AD to switch to if the AP version wins the Adaptor comparison.
        # Scaled off self.atk.base so the star-level multiplier Champion
        # already applied carries over instead of being re-derived here.
        self.ap_base_atk = self.atk.base * self.AP_VERSION_ATK / self.AD_VERSION_ATK
        # Set at combat start by AdaptorInnate; True = the physical version,
        # which is also where an untouched one lands (unlike Gromp).
        self.ad_version = False
        self.adaptor_resolved = False
        self.adaptor_ties_to_ad = True
        self.items.append(AdaptorInnate())
        # Inferno's Burn is what makes a target Burning, and Inferno is
        # unimplemented, so the AD version's Burning rider is assumed live
        # rather than driven by it. Flip this off to price the dry case.
        self.assume_burning = True

    # AD version, assuming Burning: 145/220/345 AD + 10/15/25 AP for the
    # volley, plus 35/52/80 AD for the Burning rider. Kept as separate rows
    # (as the card shows them) but summed into one damage instance -- same
    # target, same damage type, so splitting would only double-count spell
    # crit rolls.
    adAbilityScaling = create_ability_scaling(
        [145, 220, 380], [10, 15, 25], func_name="adAbilityScaling"
    )
    adBurningScaling = create_ability_scaling(
        [35, 52, 80], [0, 0, 0], func_name="adBurningScaling"
    )
    # AP version: pure AP, no AD row on the card.
    apAbilityScaling = create_ability_scaling(
        [0, 0, 0], [140, 210, 340], func_name="apAbilityScaling"
    )
    # "Increased by if they're a Tank" -- the exact number isn't published, so
    # per request this is a flat 1.5x against a Tank-archetype target.
    ap_tank_multiplier = 1.5

    def performAbility(self, opponents, items, time):
        # Kunai Strike: single target either way. Which of the two versions
        # fires was pinned at combat start by AdaptorInnate.
        if not opponents:
            return 0
        if self.ad_version:
            burning = self.assume_burning

            def ad_scaling(level, AD, AP, burning=burning):
                total = self.adAbilityScaling(level, AD, AP)
                if burning:
                    total += self.adBurningScaling(level, AD, AP)
                return total

            self.multiTargetSpell(
                opponents[:1], items, time, 1, ad_scaling, "physical"
            )
        else:
            # The ChampionSelector's enemy is a DummyTank, so this is the
            # normal case there rather than the exception.
            mult = (
                self.ap_tank_multiplier
                if opponents[0].role.archetype == "Tank"
                else 1.0
            )

            def ap_scaling(level, AD, AP, mult=mult):
                return mult * self.apAbilityScaling(level, AD, AP)

            self.multiTargetSpell(
                opponents[:1], items, time, 1, ap_scaling, "magical"
            )
        return 0


class Ezreal(Champion):
    # Forest's Flurry: three blinks, then a piercing blast on the fourth cast.
    blink_cast_time = 1.0
    blast_cast_time = 2.25
    casts_per_blast = 4

    def __init__(self, level):
        hp = 850
        atk = 45
        curMana = 0
        fullMana = 30
        aspd = 0.75
        armor = 40
        mr = 40
        super().__init__(
            "Ezreal",
            hp,
            atk,
            curMana,
            fullMana,
            aspd,
            armor,
            mr,
            level,
            Role.ATTACK_CASTER,
        )
        self.default_traits = ["Elderwood", "Executioner"]
        # Swapped to blast_cast_time on the blast cast itself (see
        # performAbility) -- update() reads castTime after performAbility
        # returns, so setting it there applies to the cast that just fired.
        self.castTime = self.blink_cast_time
        # Enemies the blast passes through, per request.
        self.num_targets = 4
        # Running total of the Attack Speed handed out by the blinks, so the
        # blast can hand exactly that much back.
        self.natures_wrath_aspd = 0.0

    abilityScaling = create_ability_scaling([250, 375, 1200], [0, 0, 0])
    blastScaling = create_ability_scaling(
        [385, 580, 2500], [0, 0, 0], func_name="blastScaling"
    )
    # Attack Speed per blink at 100 AP; scaled by the AP ratio at cast time.
    aspd_per_blink = [25, 25, 100]
    # The blast loses 25% of its damage per enemy pierced, floored at 50%.
    # Multiplicative per enemy, matching Varus's Piercing Arrow.
    blast_falloff = 0.75
    blast_minimum = 0.5

    def performAbility(self, opponents, items, time):
        if not opponents:
            return 0
        # numCasts is incremented before performAbility runs, so this is the
        # 1-indexed number of the cast being fired.
        if self.numCasts % self.casts_per_blast == 0:
            self.castTime = self.blast_cast_time
            # Blast through the largest group of enemies, damage reduced for
            # each one already pierced.
            pierce_multiplier = 1.0
            for opponent in opponents[: self.num_targets]:
                mult = pierce_multiplier

                def pierce_scaling(level, AD, AP, mult=mult):
                    return mult * self.blastScaling(level, AD, AP)

                self.multiTargetSpell(
                    [opponent], items, time, 1, pierce_scaling, "physical"
                )
                pierce_multiplier = max(
                    self.blast_minimum, pierce_multiplier * self.blast_falloff
                )
            # The blast consumes the Attack Speed the blinks granted.
            self.aspd.addStat(-self.natures_wrath_aspd)
            self.natures_wrath_aspd = 0.0
        else:
            self.castTime = self.blink_cast_time
            self.multiTargetSpell(
                opponents[:1], items, time, 1, self.abilityScaling, "physical"
            )
            gained = self.aspd_per_blink[self.level - 1] * self.ap.stat
            self.aspd.addStat(gained)
            self.natures_wrath_aspd += gained
        return 0


class Warwick(Champion):
    def __init__(self, level):
        hp = 750
        atk = 45
        curMana = 0
        fullMana = 40
        aspd = 0.75
        armor = 45
        mr = 45
        super().__init__(
            "Warwick",
            hp,
            atk,
            curMana,
            fullMana,
            aspd,
            armor,
            mr,
            level,
            Role.ATTACK_FIGHTER,
        )
        self.default_traits = ["Blackthorn", "Ravager"]
        # Recomputed per cast in performAbility; this is the value at his base
        # Attack Speed, which is what the first cast gets.
        self.castTime = self.cast_time_slow

    abilityScaling = create_ability_scaling([215, 325, 500], [0, 0, 0])
    # Flat on the card -- the only AP-scaled number on it is the heal.
    aspd_per_cast = 20

    # Cast time scales with his own Attack Speed: 1.0s at base, falling
    # linearly to 0.8s and stopping there. The stopping point is +25% Attack
    # Speed, which off his 0.75 base is 0.9375 -- the card's "0.94".
    cast_time_slow = 1.0
    cast_time_fast = 0.8
    cast_time_as_cap = 0.25

    def castTimeForAspd(self, aspd):
        """Cast time at a given total Attack Speed."""
        # Measured against his own base rather than a hardcoded 0.75, so the
        # cap stays "+25%" if that base is ever rebalanced. Bonus AS in TFT is
        # always a fraction of base, so this is the same quantity the card
        # means by 25%.
        bonus = aspd / self.aspd.base - 1 if self.aspd.base else 0
        progress = min(max(bonus, 0.0), self.cast_time_as_cap) / self.cast_time_as_cap
        return self.cast_time_slow + progress * (self.cast_time_fast - self.cast_time_slow)

    def performAbility(self, opponents, items, time):
        # Set before the bite, for two reasons. The cast time is read straight
        # after performAbility returns (see Champion.update), so this is the
        # only place it can be set for *this* cast rather than the next one --
        # the same idiom Alune and Ezreal use. And it has to be read before the
        # Attack Speed this cast grants, since a cast cannot be sped up by its
        # own buff.
        self.castTime = self.castTimeForAspd(self.aspd.stat)
        # Bite the current target, then keep the Attack Speed for good.
        if not opponents:
            return 0
        self.multiTargetSpell(
            opponents[:1], items, time, 1, self.abilityScaling, "physical"
        )
        self.aspd.addStat(self.aspd_per_cast)
        return 0


class Alune(Champion):
    # Moonfall: four rains of moonshards, then the moon itself on the fifth.
    casts_per_cycle = 5
    normal_cast_time = 2.0
    full_moon_cast_time = 4.0
    moonshards = 9
    # "the 3 nearest enemies" -- fixed by the spell, so no num_targets slider.
    targets = 3

    def __init__(self, level):
        hp = 900
        atk = 40
        curMana = 0
        fullMana = 35
        aspd = 0.8
        armor = 45
        mr = 45
        super().__init__(
            "Alune",
            hp,
            atk,
            curMana,
            fullMana,
            aspd,
            armor,
            mr,
            level,
            Role.MAGIC_CASTER,
        )
        # Attuned is deliberately absent: it is a one-unit trait and a
        # permanent part of her kit, so it rides along as an item below rather
        # than being something you would toggle in the buff bar.
        self.default_traits = ["Lunar", "Spellweaver"]
        self.castTime = self.normal_cast_time
        self.items.append(AttunedInnate())

    # Per moonshard, before the 9x and the split.
    #
    # Alune is the one modeled champion whose bin is authored rather than
    # placeholder, and it disagrees with her card anyway -- it carries
    # PrimaryMagicDamage 160/240/380 and MagicDamage 380/570/900, which match
    # neither of these rows at any patch. The card wins; see
    # patch_pin.json's spell_data_published. Authored is not the same as
    # correct, which is worth remembering when the rest of the set's bins land.
    moonshardScaling = create_ability_scaling(
        [0, 0, 0], [55, 83, 500], func_name="moonshardScaling"
    )
    # The whole moon, before the split.
    fullMoonScaling = create_ability_scaling(
        [0, 0, 0], [2350, 3600, 7500], func_name="fullMoonScaling"
    )

    def performAbility(self, opponents, items, time):
        if not opponents:
            return 0
        # Split across however many are actually there, so a short bench does
        # not quietly lose the missing shards' damage.
        split = min(self.targets, len(opponents))
        # numCasts is incremented before performAbility, so this is the
        # 1-indexed cast; every 5th is the Full Moon one. AttunedInnate has
        # already advanced the phase (and applied its amp) in preAbility.
        if self.numCasts % self.casts_per_cycle == 0:
            self.castTime = self.full_moon_cast_time

            def moon_scaling(level, AD, AP, split=split):
                return self.fullMoonScaling(level, AD, AP) / split

            scaling = moon_scaling
        else:
            self.castTime = self.normal_cast_time

            def shard_scaling(level, AD, AP, split=split):
                return (
                    self.moonshards * self.moonshardScaling(level, AD, AP) / split
                )

            scaling = shard_scaling

        self.multiTargetSpell(opponents, items, time, split, scaling, "magical")
        return 0


class Camille(Champion):
    def __init__(self, level):
        hp = 700
        atk = 40
        curMana = 0
        fullMana = 25
        aspd = 0.75
        armor = 40
        mr = 40
        super().__init__(
            "Camille",
            hp,
            atk,
            curMana,
            fullMana,
            aspd,
            armor,
            mr,
            level,
            Role.ATTACK_FIGHTER,
        )
        self.default_traits = ["Ravager"]
        self.castTime = 1.1

    abilityScaling = create_ability_scaling([160, 240, 410], [10, 15, 25])

    def performAbility(self, opponents, items, time):
        if not opponents:
            return 0
        self.multiTargetSpell(
            opponents[:1], items, time, 1, self.abilityScaling, "physical"
        )
        return 0


class Nidalee(Champion):
    def __init__(self, level):
        hp = 850
        atk = 35
        curMana = 0
        # 0/45. The set's data still says 40 -- cdragon's PBE dump lags the
        # live PBE build on this one, so it is acknowledged in patch_pin.json
        # rather than followed.
        fullMana = 45
        aspd = 0.8
        armor = 30
        mr = 30
        super().__init__(
            "Nidalee",
            hp,
            atk,
            curMana,
            fullMana,
            aspd,
            armor,
            mr,
            level,
            Role.MAGIC_MARKSMAN,
        )
        self.default_traits = ["Primal", "Adaptor"]
        self.castTime = 0.5  # per request
        # Set at combat start by AdaptorInnate; True = the physical version.
        # Nidalee is one of the two Adaptors (with Gromp) that starts on its
        # AP version when nothing has pushed either stat ahead.
        self.ad_version = False
        self.adaptor_resolved = False
        self.adaptor_ties_to_ad = False
        # The AD version (Cougar Form) is uncoded, so it's a deliberate stub:
        # 0 base AD and a no-op ability (NidaleeUlt bails when ad_version),
        # so the collapsed numbers flag that stacking AD at combat start
        # turns her into AD Nidalee rather than silently mispricing it.
        self.ad_base_atk = 0
        self.items.append(AdaptorInnate())
        self.items.append(NidaleeUlt())
        self.notes = (
            "Defaults AP. AD Adaptor (Cougar Form) is uncoded -- resolving to "
            "the AD version zeroes her out on purpose."
        )

    # Javelins 1-2, pure AP.
    abilityScaling = create_ability_scaling([0, 0, 0], [170, 255, 2000])
    # The 3rd javelin's bigger row; NidaleeUlt picks it via
    # ChampionEmpoweredAbilityScaling.
    empoweredScaling = create_ability_scaling(
        [0, 0, 0], [300, 450, 3000], func_name="empoweredScaling"
    )

    def performAbility(self, opponents, items, time):
        # Javelin Toss: no direct cast damage -- NidaleeUlt (see __init__)
        # handles the +150% AS, the manalock-until-3-attacks gate, and
        # replacing the next 3 attacks with javelins.
        return 0


class Sivir(Champion):
    def __init__(self, level):
        hp = 850
        atk = 50
        curMana = 0
        fullMana = 40
        aspd = 0.8
        armor = 40
        mr = 40
        super().__init__(
            "Sivir",
            hp,
            atk,
            curMana,
            fullMana,
            aspd,
            armor,
            mr,
            level,
            Role.ATTACK_CASTER,
        )
        self.default_traits = ["Primal", "Hunter"]
        self.castTime = 1.0  # per request
        self.items.append(SivirBounces())
        self.notes = (
            "The 8 bounces land at +1s through "
            "+2.75s rather than on the cast. The 3 extra bounces on a kill "
            "are not modeled -- nothing dies in this sim."
        )

    # The card's 205/305/1150 is one row, but its breakdown is two: an
    # AD-scaled part and an AP-scaled part (190 + 15 = 205, 285 + 20 = 305,
    # 1050 + 100 = 1150). Note the 3-star row is a spike, not the usual x1.5
    # step -- that is what the card says.
    abilityScaling = create_ability_scaling([190, 285, 1050], [15, 20, 100])
    # Each bounce is 20%/20%/40% of that, taken off both halves so the split
    # stays proportional: 38 + 3 = 41, 57 + 4 = 61, 420 + 40 = 460, which is
    # the card's bounce row exactly.
    bounceScaling = create_ability_scaling(
        [38, 57, 420], [3, 4, 40], func_name="bounceScaling"
    )

    def performAbility(self, opponents, items, time):
        if not opponents:
            return 0
        # The blade's own hit. SivirBounces (see __init__) schedules the 8
        # bounces off postAbility, which fires immediately after this.
        self.multiTargetSpell(
            opponents[:1], items, time, 1, self.abilityScaling, "physical"
        )
        return 0


class Ashe(Champion):
    def __init__(self, level):
        hp = 900
        atk = 75
        curMana = 20
        fullMana = 80
        aspd = 0.8
        armor = 45
        mr = 45
        super().__init__(
            "Ashe",
            hp,
            atk,
            curMana,
            fullMana,
            aspd,
            armor,
            mr,
            level,
            Role.ATTACK_CASTER,
        )
        self.default_traits = ["Blossom", "Hunter"]
        self.castTime = 1.0  # per request
        # The arrow pierces 5 by default; the trail catches num_targets - 1.
        self.num_targets = 5
        self.items.append(AsheTrail())
        self.notes = (
            "The trail's damage arrives 1s at a time over the 4s after each "
            "cast, not on the cast, and a recast refreshes it rather than "
            "stacking it. Its 2% max Health part reads off the enemy HP above, "
            "so raising that raises Ashe's damage."
        )

    abilityScaling = create_ability_scaling([465, 700, 1000], [0, 0, 0])
    # The card's 7/11/220 trail row is two halves, same as Sivir's: 5 + 2 = 7,
    # 8 + 3 = 11, 200 + 20 = 220. The 2% max Health rides on top of this and is
    # added per-target in AsheTrail, since it depends on who is being hit.
    trailScaling = create_ability_scaling(
        [5, 8, 200], [2, 3, 20], func_name="trailScaling"
    )

    def performAbility(self, opponents, items, time):
        # Spirit Rift: the arrow pierces num_targets enemies in a line. "-80%
        # per enemy hit, minimum 20%" bottoms out on the very first reduction
        # (1.0 -> 0.2, and 0.2 is the floor), so it is full damage on the
        # first target and a flat 20% for everyone behind it.
        for i, opponent in enumerate(opponents[: self.num_targets]):
            mult = 1.0 if i == 0 else 0.2

            def arrow_scaling(level, AD, AP, mult=mult):
                return mult * self.abilityScaling(level, AD, AP)

            self.multiTargetSpell(
                [opponent], items, time, 1, arrow_scaling, "physical"
            )
        # AsheTrail (see __init__) handles the 4s trail off postAbility, which
        # fires immediately after this.
        return 0


class Cinderling(Champion):
    def __init__(self, level):
        hp = 500
        atk = 40
        curMana = 0
        fullMana = 50
        aspd = 0.7
        armor = 25
        mr = 25
        super().__init__(
            "Cinderling",
            hp,
            atk,
            curMana,
            fullMana,
            aspd,
            armor,
            mr,
            level,
            Role.ATTACK_CASTER,
        )
        self.default_traits = ["Riftbeast", "Hunter"]
        self.castTime = 1.5
        self.items.append(CinderlingScarletBuff())
        self.notes = "Wound and Burn are not modeled."

    abilityScaling = create_ability_scaling([310, 465, 700], [30, 45, 70])

    def performAbility(self, opponents, items, time):
        # Razor Leaves: five leaves converge on the current target; modeled as
        # a single hit for their combined total, per request. The 20% Wound
        # and 1% Burn are not modeled (see notes).
        if not opponents:
            return 0
        self.multiTargetSpell(
            opponents[:1], items, time, 1, self.abilityScaling, "physical"
        )
        return 0


class Teemo(Champion):
    def __init__(self, level):
        hp = 550
        atk = 35
        curMana = 0
        fullMana = 50
        aspd = 0.75
        armor = 30
        mr = 30
        super().__init__(
            "Teemo",
            hp,
            atk,
            curMana,
            fullMana,
            aspd,
            armor,
            mr,
            level,
            Role.MAGIC_CASTER,
        )
        # His other trait is Sprykin, which is unimplemented for now; leaving
        # it out keeps it from eating a buff bar slot that can't be filled
        # (same as Camille's Coven).
        self.default_traits = ["Invoker"]
        self.castTime = 1.5  # per request
        self.num_targets = 3
        self.notes = (
            "Foraging is not modeled: the rerolls, Tactician Health and XP a "
            "foraged mushroom gives are all out of combat."
        )

    # The mushroom clusters, on the nearest num_targets.
    abilityScaling = create_ability_scaling([0, 0, 0], [60, 90, 135])
    # The giant mushroom that follows, on the current target only.
    giantScaling = create_ability_scaling(
        [0, 0, 0], [135, 200, 310], func_name="giantScaling"
    )

    def performAbility(self, opponents, items, time):
        # Fungus Among Us: mushroom clusters on the 3 nearest enemies, then a
        # giant mushroom on the current target. The card's "2 clusters" is not
        # two applications of the 60/90/135 row -- in game that row is split
        # between the pair -- so the clusters go out as a single hit for the
        # card's number, per request.
        if not opponents:
            return 0
        self.multiTargetSpell(
            opponents, items, time, self.num_targets, self.abilityScaling, "magical"
        )
        self.multiTargetSpell(
            opponents[:1], items, time, 1, self.giantScaling, "magical"
        )
        return 0


class Pebbles(Champion):
    def __init__(self, level):
        hp = 500
        atk = 35
        curMana = 30
        fullMana = 70
        aspd = 0.80
        armor = 25
        mr = 25
        super().__init__(
            "Pebbles",
            hp,
            atk,
            curMana,
            fullMana,
            aspd,
            armor,
            mr,
            level,
            Role.MAGIC_CASTER,
        )
        self.default_traits = ["Riftbeast", "Invoker"]
        # Not a real cast time: Azure Laser is a channel whose length is
        # emergent (mana divided by the net drain), so PebblesChannel owns the
        # attack lockout and releases it when the channel empties. Leaving
        # this at 0 keeps update()'s own lockout from fighting it.
        self.castTime = 0
        self.items.append(PebblesChannel())
        self.notes = (
            "Azure Laser channels rather than casting: PebblesChannel drains "
            "35% max mana a second and ticks damage once a second until he is "
            "empty. The 3 flat Magic Resist per tick is not modeled, and the "
            "first tick's timing is the card read literally, not measured."
        )

    # Per damage tick. The card also carries a 4th row (615) that this
    # simulator has nowhere to put -- levels stop at 3 stars.
    abilityScaling = create_ability_scaling([0, 0, 0], [160, 240, 360])

    def performAbility(self, opponents, items, time):
        # The cast itself deals nothing: it opens the channel, and
        # PebblesChannel (see __init__) meters out every point of damage and
        # every point of mana from there.
        return 0


class Aphelios(Champion):
    """Moonlight's Onslaught: 2s of Severum swipes, then a blast.

    The cast is 3.5s, but almost nothing about it happens at cast time. The
    swipes are a DoT on the target (status.ApheliosSeverumStatus); the two
    attacks the onslaught counts as, and the blast that follows it, are a
    schedule on Aphelios (ApheliosOnslaught, see __init__).
    """

    # The onslaught's length, which is not the cast time.
    swipe_window = 2.0
    # Swipes at 0 bonus Attack Speed. The card's count is "%i:scaleAS%", i.e.
    # this many times (1 + bonus AS), floored, off the Attack Speed at the
    # START of the cast. The one reading available is 8 swipes at +65%, and 5
    # is the only whole number that produces it (5 x 1.65 = 8.25); +65% sits
    # in the middle of the [+60%, +80%) band that gives 8, so it is not a
    # near-miss for 4 or 6 either. A reading at some other Attack Speed is
    # what would settle it, and this is the constant to move if one disagrees.
    base_swipes = 5

    def __init__(self, level):
        hp = 850
        atk = 60
        curMana = 20
        fullMana = 70
        aspd = 0.8
        armor = 40
        mr = 40
        super().__init__(
            "Aphelios",
            hp,
            atk,
            curMana,
            fullMana,
            aspd,
            armor,
            mr,
            level,
            Role.ATTACK_MARKSMAN,
        )
        self.default_traits = ["Lunar", "Rapidfire"]
        self.castTime = 3.5
        self.items.append(ApheliosOnslaught())

    # Per swipe. Pure AD: the card's only AP row is on the blast.
    swipeScaling = create_ability_scaling(
        [70, 105, 850], [0, 0, 0], func_name="swipeScaling"
    )
    # The blast, as two halves like Sivir's and Ashe's: 450 + 40 = 490,
    # 675 + 60 = 735, 5000 + 225 = 5225, which is the card's row exactly. The
    # 3-star row is a spike rather than the usual step -- that is what the card
    # says.
    blastScaling = create_ability_scaling(
        [450, 675, 5000], [40, 60, 225], func_name="blastScaling"
    )

    def swipeCount(self):
        """Swipes this onslaught lands, off the current Attack Speed."""
        # Measured against his own base rather than a hardcoded 0.8, the same
        # way Warwick's cast time is, so this stays "bonus AS" if that base is
        # ever rebalanced. Reading .stat picks up both halves of Aspd (the
        # additive % and any multiplier), which is what the card means by
        # attack speed.
        ratio = self.aspd.stat / self.aspd.base if self.aspd.base else 1
        # One swipe is the floor: a slow can shorten the onslaught, but the
        # card promises swipes, so it can never zero it out.
        return max(1, math.floor(self.base_swipes * ratio))

    def performAbility(self, opponents, items, time):
        # Equip Severum: the swipes go on the current target as a DoT, spread
        # across the 2s window. The count is fixed here, at cast time, so
        # attack speed gained during the onslaught buys no extra swipes.
        #
        # Nothing else happens now -- ApheliosOnslaught (see __init__) pays the
        # two attack credits at +0.75s/+1.5s and fires the blast at +2s, off
        # postAbility, which runs immediately after this.
        if not opponents:
            return 0
        opponents[0].applyStatus(
            status.ApheliosSeverumStatus(),
            self,
            time,
            self.swipe_window,
            (self.swipeScaling, self.swipeCount()),
        )
        return 0


class Kayle(Champion):
    """Solar Judgement: a passive that grows with her own star level.

    Nothing about Kayle is a cast -- her card reads 0/0 mana -- so fullMana is
    -1 (canCast() needs fullMana > -1) and KayleAscensions owns the whole
    ability. Her 10 base AD is not a typo either: the attack is a delivery
    mechanism for the magic damage bolted to it.
    """

    # 3rd Ascension only: how many units the wave catches. Left at 0 below
    # 3-star so the page does not offer a slider for a wave that does not
    # exist yet.
    wave_targets = 2

    def __init__(self, level):
        hp = 550
        atk = 10
        curMana = 0
        # The card says 0/0 mana. 0 would make canCast() true on the first
        # frame and every frame after (curMana >= fullMana, and fullMana > -1);
        # -1 is this simulator's way of saying "never casts", the same as
        # Caitlyn and Master Yi. See patch_pin.json's acknowledged list.
        fullMana = -1
        aspd = 0.75
        armor = 30
        mr = 30
        super().__init__(
            "Kayle",
            hp,
            atk,
            curMana,
            fullMana,
            aspd,
            armor,
            mr,
            level,
            Role.MAGIC_SPECIALIST,
        )
        self.default_traits = ["Solar", "Rapidfire"]
        self.num_targets = self.wave_targets if level >= KayleAscensions.wave_from else 0
        self.items.append(KayleAscensions())
        self.notes = (
            "Her ascensions come from her star level and stack: every Kayle "
            "gets the bonus magic damage on attacks, a 2-star adds the Shred, "
            "a 3-star adds the wave. The Shred is modeled as a flat 20% Magic "
            "Resist reduction on every enemy from combat start rather than a "
            "2s window re-applied per attack. The 4th ascension needs a "
            "4-star and is not modeled."
        )

    # 1st Ascension: the magic damage every attack carries, at every star.
    ascensionScaling = create_ability_scaling(
        [0, 0, 0], [62, 92, 105], func_name="ascensionScaling"
    )
    # 3rd Ascension: the wave, per unit it catches. Flat across stars -- the
    # card really does say 35/35/35 (18.2; was 40/40/40).
    waveScaling = create_ability_scaling(
        [0, 0, 0], [35, 35, 35], func_name="waveScaling"
    )

    def performAbility(self, opponents, items, time):
        # Never actually called -- fullMana = -1 keeps canCast() False. Solar
        # Judgement is a passive, handled by KayleAscensions (see __init__).
        return 0


class Xayah(Champion):
    def __init__(self, level):
        hp = 450
        atk = 45
        curMana = 0
        fullMana = 50
        aspd = 0.7
        armor = 25
        mr = 25
        super().__init__(
            "Xayah",
            hp,
            atk,
            curMana,
            fullMana,
            aspd,
            armor,
            mr,
            level,
            Role.ATTACK_MARKSMAN,
        )
        # Elderwood is deliberately absent: it grants placeable plants, which
        # are separate units on the board and nothing this simulator can
        # price. Leaving it out keeps it from eating a buff bar slot that
        # can't be filled (same as Teemo's Sprykin and Camille's Coven).
        self.default_traits = ["Fae", "Rapidfire"]
        self.castTime = 0.7  # per request
        self.items.append(XayahFeathers())
        self.notes = (
            "The feathers' 2 Armor reduction is not modeled, and neither is "
            "Elderwood -- its plants are separate units."
        )

    # Per feather.
    abilityScaling = create_ability_scaling([72, 108, 165], [0, 0, 0])

    def performAbility(self, opponents, items, time):
        # Deadly Plumage: no direct cast damage -- XayahFeathers (see
        # __init__) handles the +50% Attack Speed, the manalock-until-5-
        # attacks gate, and replacing the next 5 attacks with feathers.
        return 0
