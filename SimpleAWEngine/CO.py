from SimpleAWEngine.Board import Board
import csv
import re
from pathlib import Path

HERE = Path(__file__).parent   # directory this .py file lives in
POWERS_CSV = (HERE / "powers.csv").resolve()

POWERS_LOOKUP = {}
class CO:
    def __init__(self, name, cop_stars, scop_stars, dayToDay, co_power, super_power, player=0):
        self.name = name
        self.player = player
        self.coMeter = 0            # current meter [0 to CO max]
        self.coStars = 0            
        self.copStars = cop_stars
        self.scopStars = scop_stars
        self.powerStage = 0         # 0=none, 1=CO Power, 2=Super Power
        self.d2d = dayToDay
        self.coPower = co_power     # function(game) → applies CO Power
        self.superPower = super_power
        self.luckUpperBound = 9
        self.luckLowerBound = 0

    def gainMeter(self, gain):
        self.coMeter = self.coMeter + gain
        self.coStars = self.coMeter / 5000
        if self.coStars > self.copStars:
            print("COP Available")
            if self.copStars > self.scopStars:
                print("SCOP Available")
    
    def activate_co(self, game):
        if self.coStars > self.copStars:
            self.co_meter -= self.copStars * 5000
            self.coPower(game)
    
    def activate_super(self, game):
        if self.coStars > self.scopStars:
            self.co_meter = 0
            self.superPower(game.board)

    def parsePowers():
        powers = {}
        with POWERS_CSV.open("r") as f:
            reader = csv.reader(f)
            header = next(reader)
            for row in reader:
                powers[row[0]] = f"{row[1]}, {row[2]}, {row[3]}, {row[4]}, {row[5]}"
        #print(powers.get("jake"))
        POWERS_LOOKUP = powers
        return powers
    
    def basicPower(self, values, board):
        indivValues = re.split(r',\s*(?![^()]*\))', values)
        luckModifier = indivValues[0]
        globalHPChange = indivValues[1]
        globalMoveChange = indivValues[2]
        unitModifiers = indivValues[3]
        modifierTuples = []
        print(indivValues)
        if ";" in unitModifiers:
            for modifier in unitModifiers.split(";"):
                modifierTuples.append(tuple(modifier.split(",")))
        else:
            modifierTuples.append(tuple(unitModifiers.split(",")))
        globalValueChange = indivValues[4]

        if len(luckModifier) > 0: 
            if "(" in luckModifier:
                luckBounds = luckModifier.strip().split(",")
                self.luckLowerBound = int(luckBounds[0])
                self.luckUpperBound = int(luckBounds[1])
            else:
                self.luckUpperBound = int(luckModifier)

        if len(globalHPChange) > 0:
            if "(" in globalHPChange:
                hpBounds = globalHPChange.strip().split(",")
                board.globalHPChange(self.player * -1, int(hpBounds[0]))
                board.globalHPChange(self.player, int(hpBounds[1]))
            else:
                if int(globalHPChange) > 0:
                    board.globalHPChange(self.player, int(globalHPChange))
                else:
                    board.globalHPChange(self.player * -1, int(globalHPChange))

        if len(globalMoveChange) > 0:
            board.globalMovementChange(self.player, int(globalMoveChange))

        for value in modifierTuples:
            board.globalUnitModifier(self.player, value)
        
        if len(globalValueChange) > 0:
            board.globalValueChange(self.player, float(globalValueChange))


    # TEST ALL OF THESE TODO

    def merchantUnion(self, game):
        game.board.globalValueChange(self.player, 0.5)
        for y in range(self.board.height):
            for x in range(self.board.width):
                terrain = self.board.getTerrain(x, y)
                if terrain.name == "City" and terrain.owner == self.player:
                    terrain.unitType.produces = True

    def goldRush(self, game):
        game.funds[self.player] *= 1.5

    def powerOfMoney(self, game):
        firepowerBoost = -10 + (3 * (game.funds[self.player]/1000))
        colin = POWERS_LOOKUP.get("colin")
        colin[4] = f"{firepowerBoost},0,0,'ALL')" # Modify the data line to change the firepower boost
        self.basicPower(colin, game.board)
    
    def marketCrash(self, game):
        powerCrashPercent = (10 * (game.funds(self.player) / 5000))/100
        p2 = game.player2CO
        if powerCrashPercent > 1: powerCrashPercent = 1
        p2.gainMeter(-1 * (1-powerCrashPercent) * (p2.scopStars * 5000))
    
    def tsunami(self, game):
        self.basicPower(POWERS_LOOKUP.get("tsunami"))
        enemyUnits = [u for u in game.board.units.values()
                    if u.owner != self.player]
        for unit in enemyUnits: unit.unitType.fuel = 0.50 * unit.unitType.fuel
    
    def typhoon(self, game):
        self.basicPower(POWERS_LOOKUP.get("typhoon"))
        enemyUnits = [u for u in game.board.units.values()
                    if u.owner != self.player]
        for unit in enemyUnits: unit.unitType.fuel = 0.50 * unit.unitType.fuel
        game.setWeather("RAIN")

    def blizzard(self, game):
        game.setWeather("SNOW")
    
    def winterFury(self, game):
        self.basicPower(POWERS_LOOKUP.get("winterFury"))
        game.setWeather("SNOW")

    def lightningStrike(self, game):
        self.basicPower(POWERS_LOOKUP.get("lightningDrive"))
        myUnits = [u for u in game.board.units.values()
                    if u.owner == self.player]
        for unit in myUnits:
            unit.movement = unit.unitType.maxMovement
            unit.attackAvailable = True
    
    def turboCharge(self, game):
        self.basicPower(POWERS_LOOKUP.get("turboCharge"))
        myUnits = [u for u in game.board.units.values()
                    if u.owner == self.player]
        for unit in myUnits: unit.resupply(game)
    
    def overdrive(self, game):
        self.basicPower(POWERS_LOOKUP.get("overdrive"))
        myUnits = [u for u in game.board.units.values()
                    if u.owner == self.player]
        for unit in myUnits: unit.resupply(game)
    
    def javierAndPowers(self, game):
        myUnits = [u for u in game.board.units.values()
                    if u.owner == self.player]
        for unit in myUnits: unit.defenseModifier = unit.getComBoost(game.board) / 100
    
    def samuraiSpirit(self, game):
        self.basicPower(POWERS_LOOKUP.get("samuraiSpirit"))
        myUnits = [u for u in game.board.units.values()
                    if u.owner == self.player]
        for unit in myUnits: unit.counterModifier = 1.50
    
    # The hidden HP thing is probably just going to be not feeding the AI knowledge about
    # a unit's HP, so we can handle that later.
    def sonja(self, game):
        myUnits = [u for u in game.board.units.values()
                    if u.owner == self.player]
        for unit in myUnits: unit.unitType.vision = unit.unitType.baseVision + 1
    
    def enhancedVision(self, game):
        myUnits = [u for u in game.board.units.values()
                    if u.owner == self.player]
        for unit in myUnits: unit.unitType.vision = unit.unitType.baseVision + 2
        # SEE INTO HIDING PLACES SHOULD BE ADDED WHEN FOG IS WANTED

    
        

    # POWERS THAT REQUIRE SPECIAL FUNCTIONS:
    # Covering Fire TODO
    # All of Sonja TODO
    # Urban Blight, High Society TODO
    # All of Lash TODO
    # Meteor Strike TODO
    # Ex Machina TODO
    
    
        
    

    

    




# COs = {
#     "Andy": CO("Andy", 3, 6, None, hyperRepair, hyperUpgrade),
#     "Hachi": CO("Hachi", 3, 5, hachi, barter, merchantUnion),
#     "Jake": CO("Jake", 3, 6, jake, beatDown, blockRock),
#     "Max": CO("Max", 3, 6, max, maxForce, maxBlast),
#     "Nell": CO("Nell", 3, 6, nell, luckyStar, ladyLuck),
#     "Rachel": CO("Rachel", 3, 6, None, luckyLass, coveringFire),
#     "Sami": CO("Sami", 3, 8, sami, doubleTime, victoryMarch)
# }
                



# def hyperRepair(self, board):
#     board.globalHPChange(self.player, 2)

# def hyperUpgrade(self, board):
#     board.globalHPChange(self.player, 5)
#     board.globalUnitModifier(self.player, 10, 1, 0, "ALL")

# def hachi(self, board):
#     board.globalValueChange(self.player, 0.9)

# def barter(self, board):
#     board.globalValueChange(self.player, 0.5)


# def power(self, luck_modifier, global_hp_change, global_movement_change, global_unit_modifier, global_value_change):
    
#     if luck_modifier:
#         self.luckModifier = luck_modifier

#     if global_hp_change:
#         board.globalHPChange(self.player, 5)

#     if global_movement_change:
#         board.globalMovementChange(self.player, 2)
    
#     if global_unit_modifier:
#         board.globalUnitModifier(self.player, 10, 0, 0, "PLAINS")
    
#     if global_value_change:
#         board.globalValueChange(self.player, 0.5)

# def jake(self, board):
#     board.globalUnitModifier(self.player, 10, 0, 0, "PLAINS")

# def beatDown(self, board):
#     board.globalUnitModifier(self.player, 20, 0, 0, "PLAINS", indirBonus=1)

# def blockRock(self, board):
#     board.globalUnitModifier(self.player, 40, 0, 0, "PLAINS", indirBonus=1)
#     board.globalMovementChange(self.player, 2)

# def max(self, board):
#     board.globalUnitModifier(self.player, 20, 0, 0, "DIRECT")
#     board.globalUnitModifier(self.player, -10, 0, 0, "INDIRECT", indirBonus=-1)

# def maxForce(self, board):
#     board.globalUnitModifier(self.player, 30, 1, 0, "DIRECT")

# def maxBlast(self, board):
#     board.globalUnitModifier(self.player, 50, 2, 0, "DIRECT")

# def nell(self, board):
#     self.luckModifier = 19

# def luckyStar(self, board):
#     self.luckModifier = 59

# def ladyLuck(self, board):
#     self.luckModifier = 99

# def luckyLass(self, board):
#     self.luckModifier = 39

# # Handle missiles later. I don't give a shit right now
# def coveringFire(self, board):
#     pass

# def sami(self, board):
#     board.globalUnitModifier(self.player, 30, 0, 0, "INF", captureBonus = 0.50)
#     board.globalUnitModifier(self.player, -10, 0, 0, "DIRECT")
#     board.globalUnitModifier(self.player, 0, 1, 0, "TRANSPORT")

# def doubleTime(self, board):
#     board.globalUnitModifier(self.player, 50, 1, 0, "INF")

# def victoryMarch(self, board):
#     board.globalUnitModifier(self.player, 70, 2, 0, "INF", captureBonus = 999)


# CO("Andy", 3, 6, None, hyperRepair, hyperUpgrade),

# name, cop_stars, scop_stars, dayToDay, co_power, super_power, player=0
# Andy,3,6,None,hyperRepair,hyperUpgrade
# Hachi,3,5,hachi,barter,merchantUnion

# name,luck_modifier,global_hp_change,global_movement_change,global_unit_modifier,global_value_change
# "hyperRepair",-1,3,-1,-1,-1
# "hyperUpgrade",-1,5,-1,(10,1,0,"ALL"),-1


# board.globalHPChange(self.player, 5)
# board.globalUnitModifier(self.player, 10, 1, 0, "ALL")