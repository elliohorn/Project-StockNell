import torch
from PVN import PVN, DummyNet, DummyTTTState
from MCTS import MCTS
import sys, os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, PROJECT_ROOT)
from SimpleAWEngine.Game import Game
from SimpleAWEngine.Unit import Unit, unitTypes
from SimpleAWEngine.Board import terrain_types
from SimpleAWEngine.CO import COs

batchSize = 5
# numChannels = numTerrainTypes + (2 * numUnitTypes) + HP + Fuel + Ammo (all 1) + PlayerToMove
inChannels = 18 + (25 * 2) + 1 + 1 + 1 + 1
boardSize = (1,4)
numActionsAWBW = 8 * 8 * 10  
numActionsTTT = 9

network = PVN(inChannels, boardSize, numActionsAWBW)
mctsSimple = MCTS(DummyNet(), cPuct=1.0, numSims=1000, numActions=9)
mctsComplex = MCTS(network, cPuct=1.0, numSims=10, numActions=numActionsAWBW)
initialTTTState = DummyTTTState()
counts = mctsSimple.run(initialTTTState, initialTTTState.board)

terrain_codes = [[('HQ',1),('P',0),('P', 0), ('HQ', -1)]]
startingUnits = [(Unit(1,unitTypes.get('INF')), 0, 0), 
                 (Unit(-1,unitTypes.get('INF')), 3, 0)]

game = Game(terrain_codes, terrain_types, player1CO=COs.get("Andy"), player2CO=COs.get("Andy"), startingUnits=startingUnits)
ex = mctsComplex.runSelfPlay(game=game, numGames=1)
print(ex)
s, pi, z, mask = ex[0]
print(s.shape)
print(pi.shape)
print(mask.shape)
print (z in (-1, 0, 1))


dummyState = torch.randn(batchSize, inChannels, *boardSize)

policy, value = network(dummyState)

print(f"{policy.shape} compared to {(batchSize, numActionsAWBW)}")
print(f"{value.shape} compared to {(batchSize)}")
print(f"Sum: {sum(counts.values())}")
print(counts)
