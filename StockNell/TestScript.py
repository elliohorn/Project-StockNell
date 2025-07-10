import torch
from PVN import PVN, DummyNet, DummyTTTState
from MCTS import MCTS

batchSize = 5
inChannels = 72
boardSize = (8,8)
numActionsAWBW = 8 * 8 * 4   # 4 directional moves per cell
numActionsTTT = 9

network = PVN(inChannels, boardSize, numActionsAWBW)
mcts = MCTS(DummyNet(), cPuct=1.0, numSims=1000, numActions=9)
initialTTTState = DummyTTTState()
counts = mcts.run(initialTTTState)

dummyState = torch.randn(batchSize, inChannels, *boardSize)

policy, value = network(dummyState)

print(f"{policy.shape} compared to {(batchSize, numActionsAWBW)}")
print(f"{value.shape} compared to {(batchSize)}")
print(f"Sum: {sum(counts.values())}")
print(counts)
