import torch
import torch.nn as nn
from PVN import PVN, DummyNet, DummyTTTState, ALL_ACTIONS
from torch.optim.lr_scheduler import StepLR
from MCTS import MCTS
import sys, os
from Training import accuracyFNPolicy, accuracyFNValue, trainModel, MODEL_SAVE_PATH, loadTrainingCheckpoint


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, PROJECT_ROOT)
from SimpleAWEngine.Game import Game
from SimpleAWEngine.Unit import Unit, unitTypes
from SimpleAWEngine.Board import terrain_types
from SimpleAWEngine.CO import COs

batchSize = 5
# numChannels = numTerrainTypes + (2 * numUnitTypes) + HP + Fuel + Ammo (all 1) + PlayerToMove
inChannels = 18 + (25 * 2) + 1 + 1 + 1 + 1
numActionsAWBW = len(ALL_ACTIONS)
numActionsTTT = 9

terrain_codes = [[('BA',1),('HQ',1),('HQ', -1), ('BA', -1)]]
#terrain_codes = [
    #      0      1      2      3      4      5      6       7
#     [('A', 1), ('CM', -1), ('P', 0), ('F', 0), ('S', 0), ('S', 0), ('H', -1), ('HQ', -1)],
#     [('P', 0), ('M', 0), ('P', 0), ('F', 0), ('SH', 0), ('S', 0), ('M', 0),  ('P', 0 )],
#     [('P', 0), ('P', 0), ('P', 0), ('P', 0), ('P', 0), ('P', 0), ('P', 0),  ('BA', -1)],
#     [('C', 0), ('P', 0), ('P', 0), ('C', 0), ('C', 0), ('R', 0), ('R', 0),  ('R', 0 )],
#     [('R', 0), ('R', 0), ('R', 0), ('C', 0), ('C', 0), ('P', 0), ('P', 0),  ('C', 0 )],
#     [('BA', 1), ('P', 0), ('P', 0), ('P', 0), ('P', 0), ('P', 0), ('P', 0),  ('P', 0 )],
#     [('P', 0), ('M', 0), ('S', 0), ('SH',0), ('F', 0), ('P', 0), ('M', 0),  ('P', 0 )],
#     [('HQ',1), ('H', 1), ('S', 0), ('S', 0), ('F', 0), ('P', 0), ('P', 0),  ('A', -1)]
# ]
boardSize = (len(terrain_codes), len(terrain_codes[0]))

network = PVN(inChannels, boardSize, numActionsAWBW)
mctsSimple = MCTS(DummyNet(), cPuct=1.0, numSims=1000, numActions=9)
mctsComplex = MCTS(network, cPuct=1.0, numSims=2, numActions=numActionsAWBW)
# initialTTTState = DummyTTTState()
# counts = mctsSimple.run(initialTTTState, initialTTTState.board, initialTTTState.getLegalMask())


# startingUnits = [(Unit(1,unitTypes.get('INF')), 0, 7), 
#                  (Unit(-1,unitTypes.get('INF')), 7, 0)]
startingUnits = [(Unit(1,unitTypes.get('INF')), 0, 0), 
                 (Unit(-1,unitTypes.get('INF')), 3, 0)]

game = Game(terrain_codes, terrain_types, player1CO=COs.get("Sami"), player2CO=COs.get("Andy"), startingUnits=startingUnits)
# ex = mctsComplex.runSelfPlay(game=game, numGames=1)
optimizer = torch.optim.Adam(network.parameters(), lr=1e-3)
scheduler = StepLR(optimizer, step_size=10, gamma=0.5)

startEpoch = 1
bestVal = float('inf')
if os.path.exists(MODEL_SAVE_PATH):
    startEpoch, bestVal = loadTrainingCheckpoint(
        MODEL_SAVE_PATH,
        network,
        optimizer,
        scheduler
    )
    print(f"Resuming from epoch {startEpoch} with best_val={bestVal:.4f}")

trainModel(network, optimizer, "mps", scheduler, accuracyFNPolicy, accuracyFNValue, mctsComplex, game, 2, startEpoch, endEpoch=100)

# s, pi, z, mask = ex[0]
# print(s.shape)
# print(pi.shape)
# print(mask.shape)
# print (z in (-1, 0, 1))


# dummyState = torch.randn(batchSize, inChannels, *boardSize)

# policy, value = network(dummyState)

# print(f"{policy.shape} compared to {(batchSize, numActionsAWBW)}")
# print(f"{value.shape} compared to {(batchSize)}")
# print(f"Sum: {sum(counts.values())}")
# print(counts)
