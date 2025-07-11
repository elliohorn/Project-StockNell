import torch
import numpy as np
import torch.nn.functional as F
import copy
from torch import nn
from torchrl.envs.libs.gym import GymEnv

import sys, os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, PROJECT_ROOT)
from SimpleAWEngine.Board import terrain_types
from SimpleAWEngine.Unit import unitTypes


# Hyperparameters
device = "mps" if torch.mps.is_available() else "cpu"

#baseEnv = GymEnv("StockNellAISimulation-v0", device) # This is a reinforcement learning environment

channels = 18 + (25 * 2) + 1 + 1 + 1 + 1 # Num terrain types + (Num Units * Players) + HP/Fuel/Ammo Channel + Current Player Channel
# A sample state of the AW board would be the product of the channels (all possible needed inputs) * board height * board width
emptyState = torch.zeros(channels * 8 * 8)
# This state would be filled with all of the necessary data on the boad

# TODO Make a numActions function
#ALL_ACTIONS = get

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
        chnls, h, w = state.shape

        flatten = state.view(chnls * h * w)

        # Policy
        logits = self.policyHead(flatten)
        # This makes sure that the softmax gives a zero for the probability of illegal moves 
        if legalMask is not None:
            logits = logits.masked_fill(~legalMask, float("-inf")) 
        policy = F.softmax(logits, dim=-1)
        
        value = F.relu(self.valueHead(flatten))
        value = torch.tanh(value).squeeze(-1) # Removes the Batch in B, C, H, W

        return policy, value

# Dummy network used for testing the MCTS
class DummyNet:
    def __call__(self, x, mask):
        # uniform priors, value=0
        p = mask.float() / mask.sum(dim=-1, keepdim=True)
        v = torch.zeros(x.shape[0])
        return p, v
    
## TODO: Finish State class (including board.getLegalMovesForPlayer). The state encoding is most important
class State:
    def __init__(self, game, currentPlayer, numActions):
        self.game = game
        self.board = copy.deepcopy(game.board)
        self.currentPlayer = currentPlayer
        self.numActions = numActions

    def getLegalActions(self):
        moves, _ = self.board.getLegalMovesForPlayer(self.currentPlayer)
        return list(range(len(moves)))
    
    def getLegalMask(self):
        moves, _ = self.board.getLegalMovesForPlayer(self.currentPlayer)
        mask = torch.zeros(self.numActions, dtype=torch.bool)
        mask[list(range(len(moves)))] = True
        return mask
    
    def applyAction(self, action):
        moves, costs = self.board.getLegalMovesForPlayer(self.currentPlayer)
        moveTuple = moves[action]
        x0 = moveTuple[0]
        y0 = moveTuple[1]
        x1 = moveTuple[2][0]
        y1 = moveTuple[2][1]
        newBoard = copy.deepcopy(self.board)
        newBoard.moveUnit(x0, y0, x1, y1, moves, costs, self.game)

        return State(newBoard, -self.currentPlayer)
    
    # Checks for a win condition and returns the winner
    def isTerminal(self):
        return self.game.checkVictory()

    def stateToTensor(self, board):
        channels = []
        H = board.height
        W = board.width
        # This will be the encoding of the board.
        
        # Terrain Encoding, 1 plane for each type
        for terrainType in terrain_types:
            x = terrainType
            mask = (board.grid == terrainType)
            planeData = [[1.0 if board.grid[y][x] is terrainType else 0.0
                            for x in range(W)]
                                for y in range(H)]
            
            plane = torch.tensor(planeData, dtype=torch.float32)
            channels.append(plane)

        # Unit encoding, 1 plane per unit per player
        for unitType in unitTypes:
            for owner in (1, -1):
                mask = torch.zeros(H, W)
                for (x,y), u in board.units.items():
                    if u.unitType == unitType and u.owner == owner:
                        mask[y,x] = 1.0
                channels.append(mask)

        # HP, Fuel, and Ammo planes, normalized to [0,1]
        hpPlane = torch.zeros(H, W)
        fuelPlane = torch.zeros(H, W)
        ammoPlane = torch.zeros(H, W)
        for (x,y), u in board.units.items():
            hpPlane[y, x] = u.health / 100
            fuelPlane[y, x] = u.unitType.fuel / u.unitType.fuelMax
            ammoPlane[y, x] = u.unitType.ammo / u.unitType.ammoMax
        channels.append(hpPlane)
        channels.append(fuelPlane)
        channels.append(ammoPlane)

        # Player to Move plane, so the AI knows who's turn it is
        ptmPlane = torch.full((H,W), 1.0 if self.currentPlayer == 1 else 0.0)
        channels.append(ptmPlane)
        # Return the final tensor
        return torch.stack(channels, dim=0)

# Dummy Tic-Tac-Toe State used to test MCTS
class DummyTTTState:
    def __init__(self, board=None, currentPlayer=1):
        if board is None:
            self.board = np.array([[0, 0, 0],
                        [0, 0, 0],
                        [0, 0, 0]])
        else:
            self.board = copy.deepcopy(board)
        self.currentPlayer = currentPlayer

    def getLegalMask(self):
        moves = self.board[self.board == 0]
        mask = torch.zeros(len(moves), dtype=torch.bool)
        mask[list(range(len(moves)))] = True

        return mask

    def applyAction(self, action):
        moves = self.board[self.board == 0]
        chosenSquare = moves[action]
        newBoard = copy.deepcopy(self.board)
        newBoard[chosenSquare] = self.currentPlayer

        return DummyTTTState(newBoard, -self.currentPlayer)
    
    def isTerminal(self):
        # Returns winner, 0 for draw, None for still playing
        for row in self.board:
            if row[0] != 0 and (row[0] == row[1] == row[2]):
                return row[0]
        
        for col in range(3):
            if self.board[0][col] != 0 and (self.board[0][col] == self.board[1][col] == self.board[2][col]):
                return self.board[0][col]
        
        if self.board[0][0] != 0 and (self.board[0][0] == self.board[1][1] == self.board[2][2]):
            return self.board[0][0]
        if self.board[0][2] != 0 and (self.board[0][2] == self.board[1][1] == self.board[2][0]):
            return self.board[0][2]
        
        if self.board[self.board == 0] is None:
            return 0
        
        return None
    
    def stateToTensor(self, board=None):
        return self.board.flatten()
