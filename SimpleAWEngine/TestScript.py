from Unit import Unit, unitTypes
from Game import Game
from Board import Board, TerrainType, terrain_codes, terrain_types

# minimal terrain_types & map

#board = Board(terrain_codes, terrain_types, False)
# create two units
startingUnits = [
    (Unit(1,unitTypes.get('APC')), 0, 3),# 'INF', 1, 3, 2, 100, 99, 1000)
    (Unit(-1,unitTypes.get('TNK')), 2, 2),#, 'TREAD', -1, 6, 3, 100, 9, 7000)
    (Unit(1,unitTypes.get('MEC')), 0, 0),# 'MEC', 1, 2, 2, 100, 99, 3000)
]#     (Unit(1,unitTypes.get('MEC')), 6, 6),# 'MEC', 1, 2, 2, 100, 99, 3000)
    #(Unit(-1,unitTypes.get('MEC')), 6, 7)]# 'MEC', 1, 2, 2, 100, 99, 3000)
#     (Unit(1,unitTypes.get('MEC')), 7, 6),# 'MEC', 1, 2, 2, 100, 99, 3000)
#     (Unit(1,unitTypes.get('MEC')), 7, 7),# 'MEC', 1, 2, 2, 100, 99, 3000)
#     (Unit(1,unitTypes.get('MEC')), 4, 4)# 'MEC', 1, 2, 2, 100, 99, 3000)
# ]

game = Game(terrain_codes, terrain_types, startingUnits)
board = game.board

print(board)

game.playTurn(1)
game.playTurn(1)

print(board)

#### THINGS TO TEST (TODO):
# 1. Transport loading, unloading, autoresupplying DONE
# 2. Resupply, both manual and automatic (including black boat healing) DONE
# 3. Presence of the boosting bug DONE
# 4. Fuel consumption is handled properly DONE
# 5. Test daily fuel burn DONE

#### THINGS LEFT TO IMPLEMENT:
# 1. Define all the COs (this may take a while) and test behavior
# 2. Modify the random input to include all the cases that Manual has
# 3. Allow for attack modifiers (this will come with CO implementation)
# 4. Healing needs to drain funds DONE
# 5. Weather effects
# 6. Terrain based attackers need to be checked at the time of attack, not the start of the turn










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