from Board import Board

class CO:
    def __init__(self, name, cop_stars, scop_stars, dayToDay, co_power, super_power, boostAmount=100, boostType=None, player=0):
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
        self.luckModifier = 9

    def gain_meter(self, gain):
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
            self.superPower(game)

def hyperRepair(self, board):
    board.globalHPChange(self.player, 2)

def hyperUpgrade(self, board):
    board.globalHPChange(self.player, 5)
    board.globalUnitModifier(self.player, 10, 1, 0, "ALL")

def hachi(self, board):
    board.globalValueChange(self.player, 0.9)

def barter(self, board):
    board.globalValueChange(self.player, 0.5)

def merchantUnion(self, board):
    board.globalValueChange(self.player, 0.5)
    for y in range(self.board.height):
        for x in range(self.board.width):
            terrain = self.board.getTerrain(x, y)
            if terrain.name == "City" and terrain.owner == self.player:
                terrain.unitType.produces = True

def jake(self, board):
    board.globalUnitModifier(self.player, 10, 0, 0, "PLAINS")

def beatDown(self, board):
    board.globalUnitModifier(self.player, 20, 0, 0, "PLAINS", indirBonus=1)

def blockRock(self, board):
    board.globalUnitModifier(self.player, 40, 0, 0, "PLAINS", indirBonus=1)
    board.globalMovementChange(self.player, 2)

def max(self, board):
    board.globalUnitModifier(self.player, 20, 0, 0, "DIRECT")
    board.globalUnitModifier(self.player, -10, 0, 0, "INDIRECT", indirBonus=-1)

def maxForce(self, board):
    board.globalUnitModifier(self.player, 30, 1, 0, "DIRECT")

def maxBlast(self, board):
    board.globalUnitModifier(self.player, 50, 2, 0, "DIRECT")

def nell(self):
    self.luckModifier = 19

def luckyStar(self):
    self.luckModifier = 59

def ladyLuck(self):
    self.luckModifier = 99

def luckyLass(self):
    self.luckModifier = 39

# Handle missiles later. I don't give a shit right now
def coveringFire(self, board):
    pass

def sami(self, board):
    board.globalUnitModifier(self.player, 30, 0, 0, "INF", captureBonus = 0.50)
    board.globalUnitModifier(self.player, -10, 0, 0, "DIRECT")
    board.globalUnitModifier(self.player, 0, 1, 0, "TRANSPORT")

def doubleTime(self, board):
    board.globalUnitModifier(self.player, 50, 1, 0, "INF")

def victoryMarch(self, board):
    board.globalUnitModifier(self.player, 70, 2, 0, "INF", captureBonus = 999)
    
COs = {
    "Andy": CO("Andy", 3, 6, None, hyperRepair, hyperUpgrade),
    "Hachi": CO("Hachi", 3, 5, hachi, barter, merchantUnion),
    "Jake": CO("Jake", 3, 6, jake, beatDown, blockRock),
    "Max": CO("Max", 3, 6, hachi, barter, merchantUnion),
    "Nell": CO("Nell", 3, 6, nell, luckyStar, ladyLuck),
    "Rachel": CO("Rachel", 3, 6, None, luckyLass, coveringFire),
    "Sami": CO("Sami", 3, 8, sami, doubleTime, victoryMarch)
}


