# from collections import deque
import re
from item import Item
import set14buffs
import status
# from champion import Stat

offensive_craftables = ['Rabadons', 'Bloodthirster', 'HextechGunblade',
                        'Archangels', 'HoJ', 'InfinityEdge', 'LastWhisper',
                        'Shojin', 'Titans', 'GS', 'GSNoGiant', 'Nashors', 'StrikersFlail',
                        'Deathblade', 'QSS', 'JeweledGauntlet', 'Red', 'SteraksGage',
                        'Blue', 'Morellos', 'TacticiansCrown', 'Adaptive', 'GuinsoosRageblade', 'VoidStaff', 'KrakensFury',
                        'DynamoEmblem', 'TechieEmblem']

artifacts = ['InfinityForce', 'Fishbones', 'RFC', 'Mittens', 'GamblersBlade',
             'WitsEnd', 'LichBane', 'GoldCollector', 'Flickerblade', 'ShivArtifact']

radiants = ['RadiantBlue', 'RadiantVoidStaff',
            'RadiantArchangels', 'RadiantKrakensFury',
            'RadiantLastWhisper', 'RadiantGS', 'RadiantRabadons', 'RadiantJeweledGauntlet',
            'RadiantNashors', 'RadiantShojin', 'RadiantInfinityEdge',
            'RadiantDeathblade', 'RadiantTitans', 'RadiantStrikersFlail',
            'RadiantHoJ', 'RadiantRed', 'RadiantMorellos', 'RadiantQSS',
            'RadiantAdaptive', 'RadiantSteraksGage', 'RadiantGuinsoosRageblade']

exotech = ['Holobow', 'PulseStabilizer']

no_item = ['NoItem']


# class Item(object):
#     def __init__(self, name, hp=0, ad=0, ap=0, 
#                  aspd=0, armor=0, mr=0, crit=0,
#                  dodge=0, mana=0, omnivamp=0, has_radiant=False, item_type='Craftable', phases=None):
#         self.name = name
#         self.hp = hp
#         self.ad = ad
#         self.ap = ap
#         self.aspd = aspd
#         self.armor = armor
#         self.mr = mr
#         self.crit = crit
#         self.dodge = dodge
#         self.mana = mana
#         self.omnivamp = omnivamp
#         self.has_radiant = has_radiant
#         self.phases = phases


#     def performAbility(self, phases, time, champion, input_=0):
#         raise NotImplementedError("Please Implement this method for {}".format(self.name))       

#     def ability(self, phase, time, champion, input_=0):
#         if self.phases and phase in self.phases:
#             return self.performAbility(phase, time, champion, input_)
#         return input_

#     def hashFunction(self):
#         return (self.name,)

#     def __hash__(self):
#         return hash(self.hash_function())

class NoItem(Item):
    def __init__(self):
        super().__init__("NoItem", phases=None)

class Rabadons(Item):
    def __init__(self):
        super().__init__("Rabadon's Deathcap", ap=50, dmgMultiplier = .15, has_radiant=True, phases=None)

class Bloodthirster(Item):
    def __init__(self):
        super().__init__("Bloodthirster", ad=15, ap=15, omnivamp=.20, phases=None)

class HextechGunblade(Item):
    def __init__(self):
        super().__init__("Gunblade", ad=20, ap=20, omnivamp=.15, phases=None)

class GuinsoosRagebladeOld(Item):
    def __init__(self):
        super().__init__("Guinsoo's Rageblade (Old)", aspd=10, ap=10, has_radiant=True, phases=["postAttack"])

    def performAbility(self, phase, time, champion, input_=0):
        if champion.aspd.stat <= 5:
            champion.aspd.add += 5
        return 0

class GuinsoosRageblade(Item):
    def __init__(self):
        super().__init__("Guinsoo's Rageblade", aspd=10, ap=10, has_radiant=True, phases=["onUpdate"])
        self.next_bonus = 1
        self.aspd_bonus = 7

    def performAbility(self, phase, time, champion, input_=0):
        if time > self.next_bonus:
            if champion.aspd.stat <= 5:
                champion.aspd.add += self.aspd_bonus
            self.next_bonus += 1
        return 0

class Archangels(Item):
    def __init__(self):
        super().__init__("Archangels", mana=15, ap=20, has_radiant=True, phases=["onUpdate"])
        self.nextAP = 5

    def performAbility(self, phase, time, champion, input_=0):
        if time > self.nextAP:
            champion.ap.add += 30
            self.nextAP += 5
        return 0


class VoidStaff(Item):
    def __init__(self):
        super().__init__("Void Staff", mana=15, ap=35, aspd=15, has_radiant=True, phases=["preCombat"])

    def performAbility(self, phase, time, champion, input_=0):
        for opponent in champion.opponents:
            opponent.mr.mult = .7
        return 0



class Warmogs(Item):
    def __init__(self):
        super().__init__("Warmogs", hp=1000, phases=None)

    def performAbility(self, phase, time, champion, input_=0):
        return 0


class HoJ(Item):
    def __init__(self):
        super().__init__("Hand of Justice", mana=10, crit=20, ad=30, ap=30, omnivamp=.12, has_radiant=True, phases=None)

    def performAbility(self, phase, time, champion, input_=0):
        return 0

class TacticiansCrown(Item):
    def __init__(self):
        super().__init__("Tacticians' Crown (Coronation)", aspd=20, ad=25, ap=30, phases=None)

    def performAbility(self, phase, time, champion, input_=0):
        return 0


class StrikersFlail(Item):
    def __init__(self):
        super().__init__("StrikersFlail", crit=20, aspd=20, dmgMultiplier = 0.1, has_radiant=True, phases=["onCrit"])
        self.current_buff = 0
        self.buff_duration = 5
        self.dmg_amp_value = .05

    def performAbility(self, phase, time, champion, input_=0):
        champion.applyStatus(status.DmgAmpModifier("StrikersFlail {} {}".format(id(self), self.current_buff)),
                            self, time, self.buff_duration, self.dmg_amp_value)
        self.current_buff = (self.current_buff + 1) % 4   
        return 0

class Guardbreaker(Item):
    def __init__(self):
        super().__init__("Guardbreaker", crit=20, ap=10, aspd=20, has_radiant=True, phases=["preCombat"])

    def performAbility(self, phase, time, champion, input_=0):
        champion.dmgMultiplier.add += .25
        return 0

class GuardbreakerNoGuard(Item):
    def __init__(self):
        super().__init__("Guardbreaker (no shield)", crit=20, ap=10, aspd=20, has_radiant=True, phases=["preCombat"])

    def performAbility(self, phase, time, champion, input_=0):
        champion.dmgMultiplier.add += .1
        return 0

class InfinityEdge(Item):
    def __init__(self):
        super().__init__("Infinity Edge", ad=35, crit=35, has_radiant=True, phases=["postPreCombat"])

    def performAbility(self, phase, time, champion, input_=0):
        if champion.canSpellCrit:
            champion.critDmg.add += 0.1
        champion.canSpellCrit = True
        return 0

class LastWhisper(Item):
    def __init__(self):
        super().__init__("Last Whisper", aspd=20, crit=20, ad=15, has_radiant=True, phases=["preAttack"])

    def performAbility(self, phase, time, champion, opponents):
        # NOTE: LW usually applies AFTER attack but we want to calculate w/ reduced armor
        for opponent in champion.opponents:
            opponent.armor.mult = .7
        return 0

class Shojin(Item):
    def __init__(self):
        super().__init__("Spear of Shojin", ad=15, mana=15, ap=15, has_radiant=True, phases=["preCombat"])
        self.counter = 0

    def performAbility(self, phase, time, champion, input_=0):
        champion.manaPerAttack.add += 5
        return 0

class Titans(Item):
    def __init__(self):
        super().__init__("Titan's Resolve", aspd=10, armor=20, has_radiant=True, phases="preAttack")
        self.stacks = 0

    def performAbility(self, phase, time, champion, input_=0):
        if self.stacks < 25:
            champion.atk.addStat(2)
            champion.ap.addStat(2)
        self.stacks += 1
        if self.stacks == 25:
            champion.armor.addStat(20)
            champion.mr.addStat(20)
        return 0

class Nashors(Item):
    def __init__(self):
        super().__init__("Nashor's Tooth", aspd=10, ap=10, has_radiant=True, phases=["postAbility", "onUpdate"])
        self.active = False
        self.wearoffTime = 9999
        self.base_duration = 5
        self.aspdBoost = 60
        # we just dont treat it as a sttus

    def performAbility(self, phase, time, champion, input_=0):
        duration = champion.castTime + self.base_duration # add cast time
        if phase == "postAbility":
            if not self.active:
                # if not active, give the AS bonus
                champion.aspd.addStat(self.aspdBoost)
            self.active = True
            self.wearoffTime = time + duration
        elif phase == "onUpdate":
            if time > self.wearoffTime and self.active:
                # wearing off
                self.active = False
                champion.aspd.addStat(self.aspdBoost * -1)
        return 0

class Adaptive(Item):
    def __init__(self):
        super().__init__("Adaptive Helm", mana=15, ap=25, has_radiant=True, phases=["onUpdate", "postAbility"])
        self.nextMana = 3
        self.mana_gained = 10

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "onUpdate":
            if time > self.nextMana:
                if champion.manalockTime > time:
                    # if currently manalocked, add until non-manalocked
                    self.nextMana += 1/30
                else:
                    champion.addMana(self.mana_gained)
                    # champion.addMana(time, 10)
                    self.nextMana += 3
        elif phase == "postAbility":
            # post-ability because of variable cast time (mel)
            self.nextMana += champion.castTime
        return 0

class RunaansHurricane(Item):
    def __init__(self):
        super().__init__("Runaan's Hurricane", aspd=10, ad=20, has_radiant=True, phases="preAttack")

    def performAbility(self, phase, time, champion, input_=0):
        baseDmg = champion.atk.stat * .5
        if len(champion.opponents) > 1:
            champion.doDamage(champion.opponents[1], [], 0, baseDmg, baseDmg,'physical', time)             

        return 0

class KrakensFury(Item):
    def __init__(self):
        super().__init__("Kraken's Fury", aspd=10, ad=15, has_radiant=True, phases="preAttack")

    def performAbility(self, phase, time, champion, input_=0):
        champion.atk.addStat(3)
        return 0

class Deathblade(Item):
    def __init__(self):
        super().__init__("Deathblade", ad=55, has_radiant=True, phases="preCombat")

    def performAbility(self, phase, time, champion, input_=0):
        champion.dmgMultiplier.add += .1
        return 0


class SteraksGage(Item):
    def __init__(self):
        super().__init__("Sterak's Gage", ad=40, has_radiant=True, phases=None)
    

class QSS(Item):
    def __init__(self):
        super().__init__("Quicksilver", aspd=30, crit=20, phases="onUpdate")
        self.nextAS = 2
        self.asGain = 3
        self.procs_left = 9

    def performAbility(self, phase, time, champion, input_=0):
        if time >= self.nextAS and self.procs_left > 0:
            champion.aspd.addStat(self.asGain)
            self.nextAS += 2
            self.procs_left -= 1
        return 0

class JeweledGauntlet(Item):
    def __init__(self):
        super().__init__("Jeweled Gauntlet", crit=35, ap=35, has_radiant=True, phases=["postPreCombat"])

    def performAbility(self, phase, time, champion, input_=0):
        if champion.canSpellCrit:
            champion.critDmg.add += 0.1
        champion.canSpellCrit = True
        return 0

class Red(Item):
    def __init__(self):
        super().__init__("Red (no burn yet)", aspd=35, dmgMultiplier = .06, phases=None)


class Morellos(Item):
    def __init__(self):
        super().__init__("Morellos (no burn yet)", aspd=10, ap=25, phases=None)

    def performAbility(self, phase, time, champion, input_=0):
        return 0

class Shiv(Item):
    def __init__(self):
        super().__init__("Statikk Shiv", ap=15, aspd=15, mana=15, has_radiant=True, phases=["preAttack"])
        self.shivDmg = 30
        self.shivTargets = 4
        self.counter = 0

    def performAbility(self, phase, time, champion, input_=0):
        # here, we'll just preset certain times where you get the deathblade stacks.
        self.counter += 1
        if self.counter == 3:
            self.counter = 0
            baseDmg = self.shivDmg
            # only consider dmg to primary target
            # champion.doDamage(champion.opponents[0], [], 0, baseDmg, baseDmg,'magical', time)
            for opponent in champion.opponents[0:self.shivTargets]:
                champion.doDamage(opponent, [], 0, baseDmg, baseDmg,'magical', time)
                opponent.applyStatus(status.MRReduction("MR"), champion, time, 5, .7)
        return 0

class GS(Item):
    # needs reworking
    def __init__(self):
        super().__init__("Giant Slayer", aspd=10, ad=25, ap=25, has_radiant=True, phases="preCombat")

    def performAbility(self, phase, time, champion, input_):
        # input_ is target
        champion.dmgMultiplier.add += .05
        if len(champion.opponents) > 0:
            vsGiants = champion.opponents[0].hp.stat >= 1750
            if vsGiants:
                champion.dmgMultiplier.add += .2
        return 0

class GSNoGiant(Item):
    # needs reworking
    def __init__(self):
        super().__init__("Giant Slayer (no Giant)", aspd=10, ad=25, ap=25, has_radiant=True, phases="preCombat")

    def performAbility(self, phase, time, champion, input_):
        champion.dmgMultiplier.add += .05
        return 0

class Bramble(Item):
    def __init__(self):
        super().__init__("Bramble Vest", armor=55, phases=None)

class Blue(Item):
    def __init__(self):
        super().__init__("Blue Buff", mana=30, ap=15, ad=15, has_radiant=True, phases=["postAbility", "onUpdate"])
        self.has_activated = False

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "postAbility":
            champion.addMana(10)

        if phase == "onUpdate":
            if time > champion.first_takedown and not self.has_activated:
                champion.dmgMultiplier.add += .05 # we actually want this only after 5s or so
                self.has_activated = True
        return 0


class DynamoEmblem(Item):
    def __init__(self):
        super().__init__("Dynamo Emblem", mana=15, phases=["preCombat", "preAbility"])

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "preCombat":
            pattern = re.compile(r'Dynamo \d+')
            matches = [item for item in champion.items if re.fullmatch(r'Dynamo \d+', item.name)]
            if len(matches) == 0:
                champion.items.append(set14buffs.Dynamo(2, 1))
            elif len(matches) == 1:
                matches[0].is_dynamo = True
                keys = sorted(matches[0].scaling.keys())
                index = keys.index(matches[0].level)
                if index < len(keys) - 1:
                    matches[0].level = keys[index + 1]
        elif phase == "preAbility":
            champion.dmgMultiplier.addStat(champion.fullMana.stat / 1000 * 1)
        return 0


class TechieEmblem(Item):
    def __init__(self):
        super().__init__("Techie Emblem", ap=15, phases="preCombat")

    def performAbility(self, phase, time, champion, input_=0):
        champion.ap.addMultiplier += .15
        return 0

### ARTIFACTS

class InfinityForce(Item):
    def __init__(self):
        super().__init__("Infinity Force", ad=25, ap=25, aspd=25, mana=25, item_type='Artifact', phases=None)

class Fishbones(Item):
    def __init__(self):
        super().__init__("Fishbones", aspd=50, ad=20, phases=None)

    def performAbility(self, phase, time, champion, input_):
        return 0

class RFC(Item):
    def __init__(self):
        super().__init__("Rapid Firecannon", aspd=66, phases=None)

    def performAbility(self, phase, time, champion, input_):
        return 0

class Mittens(Item):
    def __init__(self):
        super().__init__("Mittens", aspd=60, phases=None)

    def performAbility(self, phase, time, champion, input_):
        return 0

class GamblersBlade(Item):
    def __init__(self):
        super().__init__("Gambler's Blade (30g)", aspd=65, ap=10, phases=None)

    def performAbility(self, phase, time, champion, input_):
        return 0

class GoldCollector(Item):
    def __init__(self):
        super().__init__("Gold Collector", ad=25, crit=30, phases=None)

    def performAbility(self, phase, time, champion, input_):
        return 0


class LichBane(Item):
    def __init__(self):
        super().__init__("Lich Bane", ap=30, aspd=30, phases=["preAbility", "preAttack"])
        self.dmg = {2: 240, 3: 320, 4: 400, 5: 480, 6: 540}
        self.enhancedAuto = False

    def performAbility(self, phase, time, champion, input_=0):
            if phase == "preAbility":
                self.enhancedAuto = True
            elif phase == "preAttack":
                if self.enhancedAuto:
                    dmg = self.dmg[champion.stage]
                    champion.doDamage(champion.opponents[0], [], 0, dmg,
                                      dmg, 'magical', time)
                    self.enhancedAuto = False
            return 0    


class WitsEnd(Item):
    def __init__(self):
        super().__init__("Wit's End", aspd=30, mr=30, phases="preAttack")
        self.dmg = {2: 42, 3: 60, 4: 75, 5: 90, 6: 100}

    def performAbility(self, phase, time, champion, input_=0):
        baseDmg = self.dmg[champion.stage]
        champion.doDamage(champion.opponents[0], [], 0, baseDmg, baseDmg,'magical', time)
        return 0        
   

class ShivArtifact(Item):
    def __init__(self):
        super().__init__("Statikk Shiv (Artifact)", ap=40, aspd=40, has_radiant=True, phases=["preAttack"])
        self.shivDmg = 40
        self.shivTargets = 4
        self.counter = 0

    def performAbility(self, phase, time, champion, input_=0):
        # here, we'll just preset certain times where you get the deathblade stacks.
        self.counter += 1
        if self.counter == 3:
            self.counter = 0
            baseDmg = self.shivDmg + champion.ap.stat * 40
            # only consider dmg to primary target
            for opponent in champion.opponents[0:self.shivTargets]:
                champion.doDamage(opponent, [], 0, baseDmg, baseDmg,'magical', time)
        return 0


class Flickerblade(Item):
    def __init__(self):
        super().__init__("Flickerblade", aspd=15, ap=10,     phases=["postAttack"])
        self.counter = 0

    def performAbility(self, phase, time, champion, input_=0):
        self.counter += 1
        if champion.aspd.stat <= 5:
            champion.aspd.addStat(7)
        if self.counter == 5:
            champion.atk.addStat(4)
            champion.ap.addStat(5)
            self.counter = 0
        return 0

### EXOTECH

class PulseStabilizer(Item):
    def __init__(self):
        super().__init__("Pulse Stabilizer", crit=30, ad=30, phases="postPreCombat")

    def performAbility(self, phase, time, champion, input_=0):
        if champion.canSpellCrit:
            champion.critDmg.add += 0.1
        champion.canSpellCrit = True
        return 0    


class Holobow(Item):
    def __init__(self):
        super().__init__("Holobow", aspd=25, ap=30, mana=15, phases=["onCrit", "postAbility"])
        self.buff_duration = 5
        self.crit_value = .4

    def performAbility(self, phase, time, champion, input_=0):
        # it's an autoattack
        if phase == "onCrit" and not input_:
            champion.addMana(2)
        elif phase == "postAbility":
            champion.applyStatus(status.CritModifier("Holobow"),
                             self, time, self.buff_duration, self.crit_value)
        return 0    


class HyperFangs(Item):
    # usually these sorts of thigns dont count shiv/runaans
    def __init__(self):
        super().__init__("Hyper Fangs", ap=20, ad=30, omnivamp=.15, phases=["PostOnDealDamage", "onUpdate"])
        self.dmg_counter = 0
        self.next_dmg = 4

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "PostOnDealDamage":
            self.dmg_counter += input_[0] * .25
        elif phase == "onUpdate":
            if time > self.next_dmg:
                champion.doDamage(opponent=champion.opponents[0],
                                  items=[],
                                  critChance=0,
                                  damageIfCrit=0,
                                  damage=self.dmg_counter,
                                  dtype='physical',
                                  time=time,
                                  is_spell=True)
                champion.doDamage(opponent=champion.opponents[1],
                                  items=[],
                                  critChance=0,
                                  damageIfCrit=0,
                                  damage=self.dmg_counter,
                                  dtype='physical',
                                  time=time,
                                  is_spell=True)
                self.next_dmg += 4
                self.dmg_counter = 0
        return 0    


### RADIANTS


class RadiantSteraksGage(Item):
    def __init__(self):
        super().__init__("Radiant Sterak's Gage", ad=80, has_radiant=True, phases=None)


class RadiantStrikersFlail(Item):
    def __init__(self):
        super().__init__("Radiant Strikers' Flail", crit=35, aspd=35, dmgMultiplier = 0.2, has_radiant=True, phases=["preCombat", "onCrit"])
        self.current_buff = 0
        self.buff_duration = 8
        self.dmg_amp_value = .08

    def performAbility(self, phase, time, champion, input_=0):
        champion.applyStatus(status.DmgAmpModifier("RadiantStrikersFlail {} {}".format(id(self), self.current_buff)),
                            self, time, self.buff_duration, self.dmg_amp_value)
        self.current_buff = (self.current_buff + 1) % 4   
        return 0



class RadiantGuardbreaker(Item):
    def __init__(self):
        super().__init__("Radiant Guardbreaker", crit=20, ap=30, aspd=30, phases=["preCombat"])

    def performAbility(self, phase, time, champion, input_=0):
        champion.dmgMultiplier.add += .5
        return 0


class RadiantShiv(Item):
    def __init__(self):
        super().__init__("Radiant Shiv", ap=50, aspd=20, mana=15, phases=["preAttack"])
        self.shivDmg = 95
        self.shivTargets = 8
        self.counter = 0

    def performAbility(self, phase, time, champion, input_=0):
        # here, we'll just preset certain times where you get the deathblade stacks.
        self.counter += 1
        if self.counter == 3:
            self.counter = 0
            baseDmg = self.shivDmg
            # only consider dmg to primary target
            # champion.doDamage(champion.opponents[0], [], 0, baseDmg, baseDmg,'magical', time)
            for opponent in champion.opponents[0:self.shivTargets]:
                champion.doDamage(opponent, [], 0, baseDmg, baseDmg,'magical', time)
                opponent.applyStatus(status.MRReduction("MR"), champion, time, 5, .7)
        return 0


class RadiantBlue(Item):
    def __init__(self):
        super().__init__("Radiant Blue", mana=30, ap=60, ad=60, phases=["postAbility", "onUpdate"])
        self.has_activated = False
    
    def performAbility(self, phase, time, champion, input_=0):
        # blue buff is the only multiplier so we just to flat -10
        if phase == "postAbility":
            champion.addMana(10)

        if phase == "onUpdate":
            if time > champion.first_takedown and not self.has_activated:
                champion.dmgMultiplier.add += .2 # we actually want this only after 5s or so
                self.has_activated = True
        return 0

class RadiantArchangels(Item):
    def __init__(self):
        super().__init__("Radiant Archangels", mana=15, ap=60, phases=["onUpdate"])
        self.nextAP = 4

    def performAbility(self, phase, time, champion, input_=0):
        if time > self.nextAP:
            champion.ap.add += 40
            self.nextAP += 4
        return 0

class RadiantRunaansHurricane(Item):
    def __init__(self):
        super().__init__("Radiant Runaan's", aspd=20, ad=40, phases="preAttack")

    def performAbility(self, phase, time, champion, input_=0):
        baseDmg = champion.atk.stat * 1
        if len(champion.opponents) > 1:
            champion.doDamage(champion.opponents[1], [], 0, baseDmg, baseDmg,'physical', time)
        return 0

class RadiantGuinsoosRageblade(Item):
    def __init__(self):
        super().__init__("Radiant Guinsoo's Rageblade", aspd=30, ap=30, phases=["onUpdate"])
        self.next_bonus = 1
        self.aspd_bonus = 14

    def performAbility(self, phase, time, champion, input_=0):
        if time > self.next_bonus:
            if champion.aspd.stat <= 5:
                champion.aspd.add += self.aspd_bonus
            self.next_bonus += 1
        return 0


class RadiantKrakensFury(Item):
    def __init__(self):
        super().__init__("Radiant Kraken's Fury", aspd=25, ad=30, has_radiant=True, phases="preAttack")

    def performAbility(self, phase, time, champion, input_=0):
        champion.atk.addStat(6)
        return 0


class RadiantHoJ(Item):
    def __init__(self):
        super().__init__("Radiant HoJ", mana=10, crit=40, ad=70, ap=70, omnivamp=.20, phases=None)

    def performAbility(self, phase, time, champion, input_=0):
        return 0


class RadiantLastWhisper(Item):
    def __init__(self):
        super().__init__("Radiant LW", aspd=25, crit=55, ad=45, phases=["preAttack"])

    def performAbility(self, phase, time, champion, opponents):
        # NOTE: LW usually applies AFTER attack but we want to calculate w/ reduced armor
        for opponent in champion.opponents:
            opponent.armor.mult = .7
        return 0


class RadiantGS(Item):
    # needs reworking
    def __init__(self):
        super().__init__("Radiant GS", aspd=10, ad=50, ap=50, phases="preCombat")

    def performAbility(self, phase, time, champion, input_):
        # input_ is target        
        champion.dmgMultiplier.add += .2
        if len(champion.opponents) > 0:
            vsGiants = champion.opponents[0].hp.stat >= 1750
            if vsGiants:
                champion.dmgMultiplier.add += .3
        return 0


class RadiantRabadons(Item):
    def __init__(self):
        super().__init__("Radiant Rab", ap=80, dmgMultiplier=.5, phases=None)


class RadiantJeweledGauntlet(Item):
    def __init__(self):
        super().__init__("Radiant JG", crit=75, ap=70, phases=["postPreCombat"])

    def performAbility(self, phase, time, champion, input_=0):
        if champion.canSpellCrit:
            champion.critDmg.add += 0.1
        champion.canSpellCrit = True
        return 0


class RadiantNashors(Item):
    def __init__(self):
        super().__init__("Radiant Nashor's", aspd=20, ap=30, phases=["postAbility", "onUpdate"])
        self.active = False
        self.wearoffTime = 9999
        self.duration = 8
        self.aspdBoost = 120
        # we just dont treat it as a sttus

    def performAbility(self, phase, time, champion, input_=0):
        self.duration = champion.castTime + self.duration # add cast time
        if phase == "postAbility":
            if not self.active:
                # if not active, give the AS bonus
                champion.aspd.addStat(self.aspdBoost)
            self.active = True
            self.wearoffTime = time + self.duration
        elif phase == "onUpdate":
            if time > self.wearoffTime and self.active:
                # wearing off
                self.active = False
                champion.aspd.addStat(self.aspdBoost * -1)
        return 0


class RadiantShojin(Item):
    def __init__(self):
        super().__init__("Radiant Spear of Shojin", ad=35, mana=20, ap=35, phases=["preCombat"])
        self.counter = 0

    def performAbility(self, phase, time, champion, input_=0):
        champion.manaPerAttack.add += 10
        return 0


class RadiantVoidStaff(Item):
    def __init__(self):
        super().__init__("Radiant Void Staff", mana=30, ap=60, aspd=60, phases=["preCombat"])

    def performAbility(self, phase, time, champion, input_=0):
        for opponent in champion.opponents:
            opponent.mr.mult = .7
        return 0


class RadiantInfinityEdge(Item):
    def __init__(self):
        super().__init__("Radiant InfinityEdge", ad=70, crit=75, phases=["postPreCombat"])

    def performAbility(self, phase, time, champion, input_=0):
        if champion.canSpellCrit:
            champion.critDmg.add += 0.1
        champion.canSpellCrit = True
        return 0


class RadiantDeathblade(Item):
    def __init__(self):
        super().__init__("Radiant DB", ad=105, phases="preCombat")

    def performAbility(self, phase, time, champion, input_=0):
        champion.dmgMultiplier.add += .2
        return 0


class RadiantQSS(Item):
    def __init__(self):
        super().__init__("Radiant Quicksilver", aspd=50, crit=20, phases="onUpdate")
        self.nextAS = 2
        self.asGain = 9
        self.procs_left = 7

    def performAbility(self, phase, time, champion, input_=0):
        if time >= self.nextAS and self.procs_left > 0:
            champion.aspd.addStat(self.asGain)
            self.nextAS += 2
            self.procs_left -= 1
        return 0


class RadiantRed(Item):
    def __init__(self):
        super().__init__("Radiant Red (no burn yet)", aspd=60, phases=["preCombat"])

    def performAbility(self, phase, time, champion, input_=0):
        champion.dmgMultiplier.add += .1
        # champion.critDmg.add += 0.1
        return 0


class RadiantMorellos(Item):
    def __init__(self):
        super().__init__("RadiantMorellos (no burn yet)", aspd=25, ap=50, phases=None)

    def performAbility(self, phase, time, champion, input_=0):
        return 0


class RadiantAdaptive(Item):
    def __init__(self):
        super().__init__("Radiant Adaptive", mana=15, ap=65, phases=["onUpdate", "postAbility"])
        self.nextMana = 3
        self.mana_gained = 20

    def performAbility(self, phase, time, champion, input_=0):
        if phase == "onUpdate":
            if time > self.nextMana:
                if champion.manalockTime > time:
                    # if currently manalocked, add until non-manalocked
                    self.nextMana += 1/30
                else:
                    champion.addMana(self.mana_gained)
                    self.nextMana += 3
        elif phase == "postAbility":
            self.nextMana += champion.castTime
        return 0


class RadiantTitans(Item):
    def __init__(self):
        super().__init__("Radiant Titans", aspd=30, armor=35, phases="preAttack")
        self.stacks = 0

    def performAbility(self, phase, time, champion, input_=0):
        if self.stacks < 25:
            champion.atk.addStat(3)
            champion.ap.addStat(3)
        self.stacks += 1
        if self.stacks == 25:
            champion.armor.addStat(50)
            champion.mr.addStat(50)
        return 0