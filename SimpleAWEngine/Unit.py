# from SimpleAWEngine.DamageTable import DAMAGE_TABLE 
from DamageTable import DAMAGE_TABLE

import random
import copy

class UnitType:
    def __init__(self, unitName, moveType, movement, vision, fuel, ammo, value, rangeMin, rangeMax, fuelBurn, transportsUnits=False, stealthable=False, stealthBurn=0, tranCapac=0):
        self.unitName = unitName
        self.moveType = moveType
        self.maxMovement = movement
        self.vision       = vision        # sight range
        self.baseVision = vision
        self.fuel         = fuel       # remaining fuel
        self.fuelMax = fuel
        self.ammo         = ammo        # remaining ammo
        self.ammoMax = ammo
        self.value        = value     # cost/value for AI evaluation
        self.minRange = rangeMin
        self.maxRange = rangeMax
        self.staticMax = rangeMax
        self.fuelBurn = fuelBurn
        self.stealthable = stealthable
        self.isStealthed = False
        self.stealthBurn = stealthBurn
        self.transportsUnits = transportsUnits
        self.transportCapacity = tranCapac
        self.captureBonus = 0 
        self.damageTable = DAMAGE_TABLE[unitName] # DAMAGE_TABLE is a dict mapping (attacker, defender) → base damage

unitTypes = {
    "AIR": UnitType("AIR", "TREAD", 6, 2, 60, 9, 8000, 0, 0, 0),
    "APC": UnitType("APC", "TREAD", 6, 1, 70, 0, 5000, 0, 0, 0, transportsUnits=True, tranCapac=1),
    "ART": UnitType("ART", "TREAD", 5, 1, 50, 9, 6000, 2, 3, 0),
    "BCP": UnitType("BCP", "AIR", 6, 3, 99, 6, 9000, 0, 0, 2),
    "BAT": UnitType("BAT", "SEA", 5, 2, 99, 9, 28000, 2, 6, 1),
    "BLK": UnitType("BLK", "LANDER", 7, 1, 60, 0, 7500, 0, 0, 1, transportsUnits=True, tranCapac=2),
    "BLB": UnitType("BLB", "AIR", 9, 1, 45, 0, 25000, 0, 0, 5),
    "BOM": UnitType("BOM", "AIR", 7, 2, 99, 9, 22000, 0, 0, 5),
    "CAR": UnitType("CAR", "SEA", 5, 4, 99, 9, 30000, 3, 8, 1, transportsUnits=True, tranCapac=2),
    "CRS": UnitType("CRS", "SEA", 6, 3, 99, 9, 18000, 0, 0, 1, transportsUnits=True, tranCapac=2),
    "FIG": UnitType("FIG", "AIR", 9, 2, 99, 9, 20000, 0, 0, 5),
    "INF": UnitType("INF", "INF", 3, 2, 99, 99, 1000, 0, 0, 0),
    "LAN": UnitType("LAN", "LANDER", 6, 1, 99, 0, 12000, 0, 0, 1, transportsUnits=True, tranCapac=2),
    "MED": UnitType("MED", "TREAD", 5, 1, 50, 8, 16000, 0, 0, 0),
    "MEC": UnitType("MEC", "MEC", 2, 2, 70, 99, 3000, 0, 0, 0),
    "MEG": UnitType("MEG", "TREAD", 4, 1, 50, 3, 28000, 0, 0, 0),
    "MIS": UnitType("MIS", "TIRE", 4, 5, 50, 6, 12000, 3, 5, 0),
    "NEO": UnitType("NEO", "TREAD", 6, 1, 99, 9, 22000, 0, 0, 0),
    "PRN": UnitType("PRN", "PIPE", 9, 4, 99, 9, 20000, 2, 5, 0),
    "REC": UnitType("REC", "TIRE", 8, 5, 80, 99, 4000, 0, 0, 0),
    "ROC": UnitType("ROC", "TIRE", 5, 1, 50, 6, 15000, 3, 5, 0),
    "STE": UnitType("STE", "AIR", 6, 4, 60, 6, 24000, 0, 0, 5, stealthable=True, stealthBurn=8),
    "SUB": UnitType("SUB", "SEA", 5, 5, 60, 6, 20000, 0, 0, 1, stealthable=True, stealthBurn=5),
    "TCP": UnitType("TCP", "AIR", 6, 2, 99, 0, 5000, 0, 0, 2, transportsUnits=True, tranCapac=1),
    "TNK": UnitType("TNK", "TREAD", 6, 3, 70, 9, 7000, 0, 0, 0),
}

class Unit:
    def __init__(self, owner, unitType, x=None, y=None):
        self.owner = owner
        self.health       = 100       # current HP
        self.maxHealth   = 100
        self.x, self.y = x,y
        self.unitType = copy.deepcopy(unitType)
        self.movement = self.unitType.maxMovement        # movement points per turn
        self.attackAvailable = True
        self.turnOver = False
        self.attackModifier = 0
        self.defenseModifier = 0
        self.counterModifier = 1
        self.disabled = False
        if self.unitType.transportsUnits:
            self.loaded = []

    def damageAgainst(self, otherUnit):
        return self.unitType.damageTable[otherUnit.unitType.unitName]
    
    def capture(self, board):
        if not board.captureTargets(self):
            raise ValueError("Cannot capture here")
        self.movement = 0
        print("Capturing!")
        board.reduceCapturePoints(self)

    def getComBoost(self, game):
        if (game.getCO(self.owner).name == "Javier" and game.getCO(self.owner).powerStage != 0):
            if game.getCO(self.owner).powerStage == 1:
                return 2 * 10 * sum(1 for b in game.board.buildings.values()
                        if b.owner == self.owner and b.name == "Com Tower")
            elif game.getCO(self.owner).powerStage == 2:
                return 3 * 10 * sum(1 for b in game.board.buildings.values()
                        if b.owner == self.owner and b.name == "Com Tower")
        else:
            return 10 * sum(1 for b in game.board.buildings.values()
                        if b.owner == self.owner and b.name == "Com Tower")

    def terrainDependentBoosts(self, x, y, game):
        tileOn = game.board.getTerrain(x,y)
        match game.getCO(self.owner).name:
            case "Jake":
                if tileOn.name == "Plains":
                    match game.getCO(self.owner).powerStage:
                        case 0: return 10
                        case 1: return 20
                        case 2: return 40
            case "Kindle":
                if tileOn.name in ("City","Base","Aiport","Harbor","HQ"):
                    match game.getCO(self.owner).powerStage:
                        case 0: return 40
                        case 1: return 80
                        case 2: return 130
            case "Koal":
                if tileOn.name in ("Road", "Bridge"): return 10 + 10 * game.getCO(self.owner).powerStage
            case "Lash":
                if game.getCO(self.owner).powerStage != 2:
                    return 10 * tileOn.defenseBonus
                elif game.getCO(self.owner).powerStage == 2:
                    return 10 * tileOn.defenseBonus * 2
            case _:
                return 0
        return 0


    def getAttackBoost(self, game):
        return 100 + self.getComBoost(game) + self.attackModifier + self.terrainDependentBoosts(self.x, self.y, game) + (10 if game.getCO(self.owner).powerStage in (1, 2) else 0)

    def attack(self, defender, game, minLuck=0, maxLuck=9):
        board = game.board
        attacker = self
        x = game.getCO(self.owner).name
        if game.getCO(self.owner * -1).name == "Sonja" and game.getCO(self.owner * -1).powerStage == 2:
            # If counter break is active, we switch who is attacking
            temp = defender
            defender = attacker
            attacker = temp
        print("Attacking!")
        if attacker.unitType.ammo <= 0:
            print("Unit is out of ammo!")
            return None
        # if ((attacker.unitType.minRange == 0 and not board.get_attack_targets(attacker)) # Check within direct rane
        #     or (attacker.unitType.minRange != 0 and not board.get_attack_targets(attacker, defender))): # Check within indir range
        #     print("Unit out of range!")
        #     return None

        if attacker.attackAvailable == True:

            attacker.movement = 0
            attacker.attackAvailable = False
            base = attacker.damageAgainst(defender)
            defenseBonus = board.getDefenseBonus(defender, defender.x, defender.y, game) + (1 if game.getCO(defender.owner).powerStage in (1, 2) else 0)
            attackBonus = attacker.getAttackBoost(game)
            #damage = int(((base * attackBonus)/100 + random.randint(minLuck, maxLuck)) * attacker.health/100  *  (200 - (defender.defenseModifier + (10 * defenseBonus) * (defender.health/10)))/100) #((100 - (10 * defenseBonus + defender.defenseModifier))/100))
            damage = int((base * (attackBonus/100) * (attacker.health/100) + random.randint(minLuck, maxLuck)) * ((100 - (10 * defenseBonus + defender.defenseModifier))/100))
            defender.health -= damage
            attacker.unitType.ammo -= 1
            
            defenderValueLost = (damage/100) * defender.unitType.value
            attackerValueDamaged = defenderValueLost * 0.5
            defender.unitType.value -= defenderValueLost
            if game.getCO(defender.owner).powerStage == 0: game.getCO(defender.owner).gainMeter(defenderValueLost)
            if game.getCO(attacker.owner).powerStage == 0: game.getCO(attacker.owner).gainMeter(attackerValueDamaged)

            if defender.health <= 0:
                print("Unit destroyed!")
                board.removeUnit(defender, defender.x, defender.y)
            elif attacker.unitType.minRange == 0 and defender.unitType.minRange == 0 and defender.unitType.ammo > 0: # Counter

                base = defender.damageAgainst(attacker)
                defenseBonus = board.getDefenseBonus(attacker, attacker.x, attacker.y, game) + (1 if game.getCO(attacker.owner).powerStage in (1, 2) else 0)
                attackBonus = defender.getAttackBoost(game)
                #damage = int(((base * attackBonus * defender.counterModifier)/100 + random.randint(minLuck, maxLuck)) * defender.health/100  *  (200 - (attacker.defenseModifier + (10 * defenseBonus) * (attacker.health/10)))/100)
                damage = int((base * (attackBonus/100) * (defender.health/100) * defender.counterModifier + random.randint(minLuck, maxLuck)) * ((100 - (10 * defenseBonus + attacker.defenseModifier))/100))
                attacker.health -= damage
                defender.unitType.ammo -= 1

                attackerValueLost = (damage/100) * attacker.unitType.value
                defenderValueDamaged = attackerValueLost * 0.5
                attacker.unitType.value -= attackerValueLost
                if game.getCO(attacker.owner).powerStage == 0: game.getCO(attacker.owner).gainMeter(attackerValueLost)
                if game.getCO(defender.owner).powerStage == 0: game.getCO(defender.owner).gainMeter(defenderValueDamaged)

            if attacker.health <= 0:
                print("Unit lost attacking!")
                board.removeUnit(attacker, attacker.x, attacker.y)
            print(f"Attacker: {attacker.health}, Defender: {defender.health}")
            return attackerValueDamaged
        else:
            print("Unit unable to attack!")
        
    def joinUnits(self, destUnit, game):
        unitToJoin = self
        if unitToJoin.unitType.unitName != destUnit.unitType.unitName:
            return
        if unitToJoin.health + destUnit.health > 100:
            surplus = unitToJoin.health + destUnit.health - 100
            surplusValue = (surplus/100) * unitToJoin.unitType.value
            game.funds[game.currentPlayer] += surplusValue

        destUnit.health += unitToJoin.health
        destUnit.unitType.ammo += unitToJoin.unitType.ammo
        destUnit.unitType.fuel += unitToJoin.unitType.fuel

        if destUnit.health > 100: destUnit.health = 100
        if destUnit.unitType.ammo > destUnit.unitType.ammoMax:
            destUnit.unitType.ammo = destUnit.unitType.ammoMax
        if destUnit.unitType.fuel > destUnit.unitType.fuelMax:
            destUnit.unitType.fuel = destUnit.unitType.fuelMax

        game.board.units[(destUnit.x, destUnit.y)].movement = 0
        game.board.units[(destUnit.x, destUnit.y)].attackAvailable = False
        game.board.removeUnit(unitToJoin, unitToJoin.x, unitToJoin.y)


    def disable(self):
        self.movement = 0
        self.attackAvailable = False
        self.disabled = True

    def resupply(self, game, healthToHeal=0):
        self.unitType.ammo = self.unitType.ammoMax
        self.unitType.fuel = self.unitType.fuelMax
        if game.funds[game.currentPlayer] >= (healthToHeal/100) * self.unitType.value and self.health < 100:
            self.health += healthToHeal
            if self.health > 100: self.health == 100
            game.funds[game.currentPlayer] -= (healthToHeal/100) * self.unitType.value 


    def __repr__(self):
        return f"<Unit {self.unitType} P{self.owner} @({self.x},{self.y}) HP={self.health}>"