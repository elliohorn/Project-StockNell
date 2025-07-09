import torch
from PVN import PVN

batchSize = 5
inChannels = 72
boardSize = (8,8)
numActions = 8 * 8 * 4   # 4 directional moves per cell

network = PVN(inChannels, boardSize, numActions)

dummyState = torch.randn(batchSize, inChannels, *boardSize)

policy, value = network(dummyState)

print(f"{policy.shape} compared to {(batchSize, numActions)}")
print(f"{value.shape} compared to {(batchSize)}")
