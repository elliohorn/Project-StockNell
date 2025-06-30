from SimpleAWEngine.Board import Board
from SimpleAWEngine.Unit import unitTypes
import csv
import re
import heapq
import random
from pathlib import Path

HERE = Path(__file__).parent   # directory this .py file lives in
POWERS_CSV = (HERE / "powers.csv").resolve()


POWERS_LOOKUP = {}
class CO:
    def __init__(self, name, cop_stars, scop_stars, dayToDay, d2dKey, co_power, copKey, super_power, scopKey, player=0):
        self.name = name
        self.player = player
        self.coMeter = 0            # current meter [0 to CO max]
        self.coStars = 0            
        self.copStars = cop_stars
        self.scopStars = scop_stars
        self.powerStage = 0         # 0=none, 1=CO Power, 2=Super Power
        self.d2d = dayToDay
        self.d2dKey = d2dKey
        self.coPower = co_power     # function(game) → applies CO Power
        self.copKey = copKey
        self.superPower = super_power
        self.scopKey = scopKey
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
            self.powerStage = 1
            self.coPower(game)
    
    def activate_super(self, game):
        if self.coStars > self.scopStars:
            self.co_meter = 0
            self.powerStage = 2
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
    
    @classmethod
    def basicPower(self, values, game):
        board = game.board
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
        for y in range(game.board.height):
            for x in range(game.board.width):
                terrain = game.board.getTerrain(x, y)
                if terrain.name == "City" and terrain.owner == self.player:
                    terrain.unitType.produces = True

    @classmethod
    def goldRush(self, game):
        game.funds[self.player] *= 1.5

    @classmethod
    def powerOfMoney(self, game):
        firepowerBoost = -10 + (3 * (game.funds[self.player]/1000))
        colin = POWERS_LOOKUP.get("colin")
        colin[3] = f"{firepowerBoost},0,0,'ALL')" # Modify the data line to change the firepower boost
        self.basicPower(colin, game.board)
    
    @classmethod
    def marketCrash(self, game):
        powerCrashPercent = (10 * (game.funds(self.player) / 5000))/100
        p2 = game.player2CO
        if powerCrashPercent > 1: powerCrashPercent = 1
        p2.gainMeter(-1 * (1-powerCrashPercent) * (p2.scopStars * 5000))
    
    @classmethod
    def tsunami(self, game):
        self.basicPower(POWERS_LOOKUP.get("tsunami"))
        enemyUnits = [u for u in game.board.units.values()
                    if u.owner != self.player]
        for unit in enemyUnits: unit.unitType.fuel = 0.50 * unit.unitType.fuel
    
    @classmethod
    def typhoon(self, game):
        self.basicPower(POWERS_LOOKUP.get("typhoon"))
        enemyUnits = [u for u in game.board.units.values()
                    if u.owner != self.player]
        for unit in enemyUnits: unit.unitType.fuel = 0.50 * unit.unitType.fuel
        game.setWeather("RAIN")

    @classmethod
    def blizzard(self, game):
        game.setWeather("SNOW")
    
    @classmethod
    def winterFury(self, game):
        self.basicPower(POWERS_LOOKUP.get("winterFury"))
        game.setWeather("SNOW")

    @classmethod
    def lightningStrike(self, game):
        self.basicPower(POWERS_LOOKUP.get("lightningDrive"))
        myUnits = [u for u in game.board.units.values()
                    if u.owner == self.player]
        for unit in myUnits:
            unit.movement = unit.unitType.maxMovement
            unit.attackAvailable = True
    
    @classmethod
    def turboCharge(self, game):
        self.basicPower(POWERS_LOOKUP.get("turboCharge"))
        myUnits = [u for u in game.board.units.values()
                    if u.owner == self.player]
        for unit in myUnits: unit.resupply(game)
    
    @classmethod
    def overdrive(self, game):
        self.basicPower(POWERS_LOOKUP.get("overdrive"))
        myUnits = [u for u in game.board.units.values()
                    if u.owner == self.player]
        for unit in myUnits: unit.resupply(game)
    
    @classmethod
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

    def copterCommand(self, game):
        for y in range(game.board.height):
            for x in range(game.board.width):
                terrain = game.board.getTerrain(x, y)
                if terrain.name == "City" and terrain.owner == self.player and (y, x) not in game.board.units:
                    game.board.addUnit(unitTypes.get("INF"), x, y)
                    game.board.setUnitHP(x, y, 90)

    def airborneAssault(self, game):
        for y in range(game.board.height):
            for x in range(game.board.width):
                terrain = game.board.getTerrain(x, y)
                if terrain.name == "City" and terrain.owner == self.player and (y, x) not in game.board.units:
                    game.board.addUnit(unitTypes.get("MEC"), x, y)
                    game.board.setUnitHP(x, y, 90)


    def sonja(self, game):
        myUnits = [u for u in game.board.units.values()
                    if u.owner == self.player]
        for unit in myUnits: unit.unitType.vision = unit.unitType.baseVision + 1
    
    @classmethod
    def enhancedVision(self, game):
        myUnits = [u for u in game.board.units.values()
                    if u.owner == self.player]
        for unit in myUnits: unit.unitType.vision = unit.unitType.baseVision + 2
        # SEE INTO HIDING PLACES SHOULD BE ADDED WHEN FOG IS WANTED
    
    @classmethod
    def urbanBlight(self, game):
        enemyUnits = [u for u in game.board.units.values()
                    if u.owner != self.player
                    and game.board.getTerrain(u.x,u.y).name in ("City","Base","Aiport","Harbor","HQ")]
        for unit in enemyUnits: 
            if unit.health > 30:
                unit.health -= 30
            else:
                unit.health = 1 
    
    @classmethod
    def highSociety(self, game):
        for (x,y), b in game.board.buildings.items():
            if b.owner == game.currentPlayer and b.name in ("City","Base","Aiport","Harbor","HQ"):
                firepowerBonus += 3
        powerList = ['','','',f"({firepowerBonus},0,0,'ALL')",'']
        self.basicPower(powerList, game.board)

    @classmethod
    def perfectMovement(self, game):
        if game.weather != "SNOW":
            game.board.flatMoveCost = True

    def sturmsSpecialLittleFunction(self, game):
        """
        Fuck you for making me make this Sturm. You're the ONLY FUCKING EDGE CASE IN THIS WHOLE GAME
        WHO REQUIRES BOTH A UNIQUE FUNCTION AND MY BASIC POWER FUNCTION
        """
        if game.weather != "SNOW":
            game.board.flatMoveCost = True
        self.basicPower(POWERS_LOOKUP["sturm"], game)

    @classmethod
    def missilePowers(self, game):
        match self.name:
            case "Rachel":
                self.missileHelper(game, "FTHP", 3)
                self.missileHelper(game, "VAL", 3)
                self.missileHelper(game, "HP", 3)
            case "Sturm":
                match random.randint(1, 3):
                    case 1: self.missileHelper("HP", 4 * self.powerStage)
                    case 2: self.missileHelper("VAL", 4 * self.powerStage)
                    case 3: self.missileHelper("INDIRVAL", 4 * self.powerStage) 
            case "Von Bolt":
                self.missileHelper("VAL", 3)

    def missileHelper(self, game, type, damageAmount):
        largestTotal = 0
        targetedSquare = (0,0)
        for y in range(game.board.height):
            for x in range(game.board.width):
                totalHere = self.searchRange(x, y, game.board, type)
                if totalHere > largestTotal:
                    largestTotal = totalHere
                    targetedSquare = (y,x)
        if self.name == "Von Bolt":
            self.searchRange(targetedSquare[1], targetedSquare[0], game.board, "DISABLE", damageAmount)
        else:
            self.searchRange(targetedSquare[1], targetedSquare[0], game.board, "DAMAGE", damageAmount)
        

    def searchRange(x, y, board, searchType, damage=0):
        start = (x,y)
        frontier = [(0, start)]
        distanceSearched = 0
        searchTotal = 0
        while frontier:
            dist, (x, y) = heapq.heappop(frontier)
            # Explore neighbors
            for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                nx, ny = x + dx, y + dy
                distanceSearched = dist + 1
                if distanceSearched > 2:
                    continue
                heapq.heappush(frontier, (distanceSearched, (nx, ny)))
                if (nx, ny) not in board.units:
                    continue
                match searchType:
                    case "FTHP":
                        unitName =  board.units[(nx, ny)].unitType.unitName == "INF"
                        if unitName == "INF" or unitName == "MEC":
                            searchTotal += board.units[(nx, ny)].health
                    case "HP":
                        searchTotal += board.units[(nx,ny)].health
                    case "VAL":
                        searchTotal += board.units[(nx,ny)].unitType.value
                    case "INDIRVAL":
                        if board.units[(nx,ny)].minRange != 0:
                            searchTotal += board.units[(nx,ny)].unitType.value * 2
                        else:
                            searchTotal += board.units[(nx,ny)].unitType.value
                    case "DAMAGE":
                        board.units[(nx,ny)].health -= damage
                    case "DISABLE":
                        board.units[(nx,ny)].health -= damage
                        board.units[(nx,ny)].disable()
        return searchTotal

            
#bp = lambda key: (lambda g: CO.basicPower(POWERS_LOOKUP[key], g))
bp = CO.basicPower
    
# TODO Add all COs to the LIST        

COs = {
    "Andy": CO("Andy", 3, 6, None, None, bp, "hyperRepair", bp, "hyperUpgrade"),
    "Hachi": CO("Hachi", 3, 5, bp, "hachi", bp, "barter", CO.merchantUnion, None),
    "Jake": CO("Jake", 3, 6, bp, "jake", bp, "beatDown", bp, "blockRock"),
    "Max": CO("Max", 3, 6, bp, "max", bp, "maxForce", bp, "maxBlast"),
    "Nell": CO("Nell", 3, 6, bp, "nell", bp, "luckyStar", bp, "ladyLuck"),
    "Rachel": CO("Rachel", 3, 6, None, None, bp, "luckyLass", CO.missilePowers),
    "Sami": CO("Sami", 3, 8, bp, "sami", bp, "doubleTime", bp, "victoryMarch"),
    "Colin": CO("Colin", 2, 6, bp, "colin", CO.goldRush, None, CO.powerOfMoney, None),
    "Grit": CO("Grit", 3, 6, bp, "grit", bp, "snipeAttack", bp, "superSnipe"),
    "Olaf": CO("Olaf", 3, 7, None, None, CO.blizzard, None, CO.winterFury, None),
    "Sasha": CO("Sasha", 2, 6, None, None, CO.marketCrash, None, None, None),
    "Drake": CO("Drake", 4, 7, bp, "drake", CO.typhoon, None, CO.tsunami, None),
    "Eagle": CO("Eagle", 3, 9, bp, "eagle", bp, "lightningDrive", CO.lightningStrike, None),
    "Javier": CO("Javier", 3, 6, CO.javierAndPowers, None, CO.javierAndPowers, None, CO.javierAndPowers, None),
    "Jess": CO("Jess", 3, 6, bp, "jess", CO.turboCharge, None, CO.overdrive, None),
    "Grimm": CO("Grimm", 3, 6, bp, "grimm", bp, "knuckleduster", bp, "haymaker"),
    "Kanbei": CO("Kanbei", 4, 7, bp, "kanbei", bp, "moraleBoost", CO.samuraiSpirit, None),
    "Sensei": CO("sensei", 2, 6, bp, "sensei", CO.copterCommand, None, CO.airborneAssault, None),
    "Sonja": CO("Sonja", 3, 5, CO.sonja, None, CO.enhancedVision, None, None, None),
    "Flak": CO("Flak", 3, 6, bp, "flak", bp, "bruteForce", bp, "barbaricBlow"),
    "Hawke": CO("Hawke", 5, 9, bp, "hawke", bp, "blackWave", bp, "blackStorm"),
    "Jugger": CO("Jugger", 3, 7, bp, "jugger", bp, "overclock", bp, "systemCrash"),
    "Kindle": CO("Kindle", 3, 6, None, None, CO.urbanBlight, None, CO.highSociety, None),
    "Koal": CO("Koal", 3, 5, None, None, None, None, None, None),
    "Lash": CO("Lash", 4, 7, None, None, CO.perfectMovement, None, CO.perfectMovement, None),
    "Sturm": CO("Sturm", 6, 10, CO.sturmsSpecialLittleFunction, None, CO.missilePowers, None, CO.missilePowers, None),
    "Von Bolt": CO("Von Bolt", 0, 10, bp, "vonBolt", None, None, CO.missilePowers, None)
}
                



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