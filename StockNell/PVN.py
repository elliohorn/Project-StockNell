import torch
import numpy as np
import torch.nn.functional as F
import copy
from torch import nn
from torchrl.envs.libs.gym import GymEnv


# Hyperparameters
device = "mps" if torch.mps.is_available() else "cpu"

#baseEnv = GymEnv("StockNellAISimulation-v0", device) # This is a reinforcement learning environment

channels = 18 + (25 * 2) + 1 + 1 + 1 + 1 # Num terrain types + (Num Units * Players) + HP/Fuel/Ammo Channel + Current Player Channel
# A sample state of the AW board would be the product of the channels (all possible needed inputs) * board height * board width
emptyState = torch.zeros(channels * 8 * 8)
# This state would be filled with all of the necessary data on the boad

class PVN(nn.Module):
    def __init__(self, inChannels, boardSize, numActions, hiddenDim=128):
        super().__init__()
        height, width = boardSize
        flattenedSize = height * width * 64 # Height * width * outChannels to flatten into a 1D tensor
        
        self.convTrunk = nn.Sequential(
            nn.Conv2d(in_channels=inChannels, out_channels=64, kernel_size=3, padding=1),
            nn.Conv2d(in_channels=64, out_channels=64, kernel_size=3, padding=1),
        )  
            # Policy Head
        self.policyHead = nn.Linear(in_features=flattenedSize, out_features=numActions)

            # Value Head
        self.valueHead = nn.Sequential(
            nn.Linear(in_features=flattenedSize, out_features=hiddenDim),
            nn.Linear(in_features=hiddenDim, out_features=1)
        )
        

    def forward(self, state, legalMask=None):
        state = F.relu(self.convTrunk(state))
        batch, chnls, h, w = state.shape

        flatten = state.view(batch, chnls * h * w)

        # Policy
        logits = self.policyHead(flatten)
        # This makes sure that the softmax gives a zero for the probability of illegal moves 
        if legalMask is not None:
            logits = logits.masked_fill(~legalMask, float("-inf")) 
        policy = F.softmax(logits, dim=-1)
        
        value = F.relu(self.valueHead(flatten))
        value = torch.tanh(value).squeeze(-1) # Removes the Batch in B, C, H, W

        return policy, value
    
## TODO: Finish State class (including board.getLegalMovesForPlayer). The state encoding is most important
class State:
    def __init__(self, game, currentPlayer):
        self.game = game
        self.board = copy.deepcopy(game.board)
        self.currentPlayer = currentPlayer

    def getLegalActions(self):
        moves, _ = self.board.getLegalMovesForPlayer(self.currentPlayer)
        return list(range(len(moves)))
    
    def getLegalMask(self):
        moves, _ = self.board.getLegalMovesForPlayer(self.currentPlayer)
        mask = torch.zeros(self.numActions(), dtype=torch.bool)
        mask[list(range(len(moves)))] = True
        return mask
    
    def applyAction(self, actionIndex):
        moves, costs = self.board.getLegalMovesForPlayer(self.currentPlayer)
        x0,y0, x1,y1 = moves[actionIndex]
        newBoard = copy.deepcopy(self.board)
        newBoard.moveUnit(x0, y0, x1, y1, moves, costs, self.game)

        return State(newBoard, -self.currentPlayer)
    
    # Checks for a win condition and returns the winner
    def isTerminal(self):
        return self.game.checkVictory()

    def toTensor(self):
        # This will be the encoding of the board.
        pass
    