from Unit import Unit, unitTypes
from Game import Game
from Board import Board, TerrainType, terrain_codes, terrain_types
from CO import COs

# minimal terrain_types & map

#board = Board(terrain_codes, terrain_types, False)
# create two units
terrain_codes = [[('P',0),('P',0),('P',0),('P',0),('P',0), ('P',0), ('P',0), ('P',0)], 
                     [('P',0),('P',0),('P',0),('P',0),('P',0), ('P',0), ('P',0), ('P',0)], 
                     [('P',0),('P',0),('P',0),('P',0),('P',0), ('P',0), ('P',0), ('P',0)], 
                     [('P',0),('P',0),('P',0),('P',0),('P',0), ('P',0), ('P',0), ('P',0)], 
                     [('CM',1),('P',0),('P',0),('P',0),('C',1), ('P',0), ('P',0), ('P',0)]]
startingUnits = [(Unit(1,unitTypes.get('INF')), 0, 0), 
                     (Unit(-1,unitTypes.get('INF')), 1, 0),
                     (Unit(1,unitTypes.get('INF')), 3, 0), 
                     (Unit(-1,unitTypes.get('INF')), 4, 0),
                     (Unit(1,unitTypes.get('INF')), 6, 0), 
                     (Unit(-1,unitTypes.get('INF')), 7, 0),
                     (Unit(1,unitTypes.get('TNK')), 0, 2),
                     (Unit(-1,unitTypes.get('TNK')), 1, 2),
                     (Unit(1,unitTypes.get('TNK')), 3, 2),
                     (Unit(-1,unitTypes.get('TNK')), 4, 2),
                     (Unit(1,unitTypes.get('TNK')), 6, 2),
                     (Unit(-1,unitTypes.get('TNK')), 7, 2),
                     (Unit(1,unitTypes.get('TNK')), 7, 3),
                     (Unit(-1,unitTypes.get('INF')), 7, 4)]
game = Game(terrain_codes, terrain_types, player1CO=COs.get("Kanbei"), player2CO=COs.get("Max"), startingUnits=startingUnits)
game.funds[1] = 50000
game.getCO(1).gainMeter(200000)
game.getCO(-1).gainMeter(30000)
#game.board.units[(3,0)].health = 50
board = game.board

print(board)

game.playTurn(1)
game.playTurn(1)
game.playTurn(1)

print(board)

### FUNCTIOING BASIC PARTS:
# Attack increases
# Movement increases
# Range increases
# Global Healing, Damage
# Luck increases.
# Value changes

#### THINGS TO TEST (TODO):
# 1. Test CO behavior
# 2. Test weather effects

#### THINGS LEFT TO IMPLEMENT:
# 1. Modify the random input to include all the cases that Manual has










# for turn in range(1, 11):
#     print(f"\n=== Turn {turn:2d}, Player {game.currentPlayer:+d} ===")
#     print(game.board)           # uses your __repr__ to show the board
#     victory = game.playTurn(0)  # plays one full turn and prints captures
#     if victory:
#         print(f"Game over: Player {victory} wins on turn {turn}")
#         break
#     else:
#         print("\n=== Simulation complete (no victor) ===")
        # print(game.board)

# board.addUnit(u1, 0, 0)
# board.addUnit(u2, 2, 2)
# board.addUnit(u3, 3, 3)
# board.addUnit(u4, 6, 6)
# board.addUnit(u5, 6, 7)
# board.addUnit(u6, 7, 6)
# board.addUnit(u7, 7, 7)
# board.addUnit(u8, 4, 4)



### TESTING NEEDS TO BE DONE!!!!!!!!!!!!!!!

# u1.capture(board)
# board.nextTurn()
# u1.capture(board)
# board.moveUnit(2, 2, 1, 0, "TREAD")
# u2.attack(u1, board)
# board.nextTurn()
# u2.attack(u1, board)
# board.moveUnit(3, 3, 3, 5, "MEC")
# board.moveUnit(7, 7, 5, 7, "MEC")
# board.moveUnit(4, 4, 5, 4, "MEC")

#board.moveUnit(0, 0, 1, 0, "INF")
#print(board.units)
#print(u1)  # should show updated x,y and movement reduced