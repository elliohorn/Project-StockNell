from DamageTable import DAMAGE_TABLE 
from Board import Board
import random

class UnitType:
    def __init__(self, unitName, moveType, movement, vision, fuel, ammo, value, rangeMin, rangeMax, fuelBurn, transportsUnits=False, stealthable=False, stealthBurn=0, tranCapac=0):
        self.unitName = unitName
        self.moveType = moveType
        self.maxMovement = movement
        self.vision       = vision        # sight range
        self.fuel         = fuel       # remaining fuel
        self.fuelMax = fuel
        self.ammo         = ammo        # remaining ammo
        self.ammoMax = ammo
        self.value        = value     # cost/value for AI evaluation
        self.minRange = rangeMin
        self.maxRange = rangeMax
        self.fuelBurn = fuelBurn
        self.stealthable = stealthable
        self.isStealthed = False
        self.stealthBurn = stealthBurn
        self.transportsUnits = transportsUnits
        self.transportCapacity = tranCapac
        self.damageTable = DAMAGE_TABLE[unitName] # DAMAGE_TABLE is a dict mapping (attacker, defender) → base damage

unitTypes = {
    "AIR": UnitType("AIR", "TREAD", 6, 2, 60, 9, 8000, 0, 0, 0),
    "APC": UnitType("APC", "TREAD", 6, 1, 70, 0, 5000, 0, 0, 0, transportsUnits=True, tranCapac=1),
    "ART": UnitType("ART", "TREAD", 5, 1, 50, 9, 6000, 2, 3, 0),
    "BCP": UnitType("BCP", "AIR", 6, 3, 99, 6, 9000, 0, 0, 2),
    "BAT": UnitType("BAT", "SEA", 5, 2, 99, 9, 28000, 2, 6, 1),
    "BLK": UnitType("BLK", "SEA", 7, 1, 60, 0, 7500, 0, 0, 1, transportsUnits=True, tranCapac=2),
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
        self.unitType = unitType
        self.movement = self.unitType.maxMovement        # movement points per turn
        self.attackAvailable = True
        self.turnOver = False
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

    def getComBoost(self, board):
        return 100 + 10 * sum(1 for b in board.buildings.values()
                        if b.owner == self.owner and b.name == "Com Tower")

    def attack(self, defender, board):
        print("Attacking!")
        if self.unitType.ammo <= 0:
            print("Unit is out of ammo!")
            return None
        if ((self.unitType.minRange == 0 and not board.get_attack_targets(self)) # Check within direct rane
            or (self.unitType.minRange != 0 and not board.get_attack_targets(self, defender))): # Check within indir range
            print("Unit out of range!")
            return None

        if self.attackAvailable == True:
            self.movement = 0
            self.attackAvailable = False
            base = self.damageAgainst(defender)
            defenseBonus = board.getDefenseBonus(defender.x, defender.y)
            attackBonus = self.getComBoost(board)
            print(attackBonus)
            damage = int((base * (attackBonus/100) * (self.health/100)) * ((100 - (10 * defenseBonus))/100)) + random.randint(0, 9)
            defender.health -= damage
            self.unitType.ammo -= 1
            if defender.health <= 0:
                print("Unit destroyed!")
                board.removeUnit(defender, defender.x, defender.y)
            elif self.unitType.minRange == 0 and defender.unitType.minRange == 0 and defender.unitType.ammo > 0: # Counter
                base = defender.damageAgainst(self)
                defenseBonus = board.getDefenseBonus(self.x, self.y)
                attackBonus = 100
                damage = int((base * (attackBonus/100) * (defender.health/100) + random.randint(0, 9)) * ((100 - (10 * defenseBonus))/100))
                self.health -= damage
                defender.unitType.ammo -= 1
            if self.health <= 0:
                print("Unit lost attacking!")
                board.removeUnit(self, self.x, self.y)
        else:
            print("Unit unable to attack!")
        print(f"Attacker: {self.health}, Defender: {defender.health}")

    def wait(self):
        self.movement = 0
        self.attackAvailable = False

    def resupply(self, game, healthToHeal=0):
        self.ammo = self.ammoMax
        self.fuel = self.fuelMax
        if game.funds[game.currentPlayer] >= (healthToHeal/100) * self.unitType.value:
            self.health += healthToHeal


    def __repr__(self):
        return f"<Unit {self.unitType} P{self.owner} @({self.x},{self.y}) HP={self.health}>"