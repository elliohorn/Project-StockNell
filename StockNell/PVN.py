import torch
import numpy as np
import torch.nn.functional as F
import copy
from torch import nn
#from torchrl.envs.libs.gym import GymEnv
from Action import Action, ActionType

import sys, os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, PROJECT_ROOT)
from SimpleAWEngine.Board import terrain_types
from SimpleAWEngine.Unit import unitTypes


# Hyperparameters
device = "mps" if torch.mps.is_available() else "cpu"
WIDTH = 8
HEIGHT = 8

#baseEnv = GymEnv("StockNellAISimulation-v0", device) # This is a reinforcement learning environment

channels = 18 + (25 * 2) + 1 + 1 + 1 + 1 # Num terrain types + (Num Units * Players) + HP/Fuel/Ammo Channel + Current Player Channel
# A sample state of the AW board would be the product of the channels (all possible needed inputs) * board height * board width
emptyState = torch.zeros(channels * WIDTH * HEIGHT)
# This state would be filled with all of the necessary data on the boad

# TODO Make a numActions function
ALL_ACTIONS = Action.buildAllActions(WIDTH, HEIGHT)
actionToIndex = {act: i for i, act in enumerate(ALL_ACTIONS)}
END_TURN_IDX = len(ALL_ACTIONS) - 1

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

        # Normalization step that is needed since both 3D and 4D tensors (with and without the batch)
        # are passed into this function (3D in self play, 4D in training loop)
        singleExample = False
        if state.dim() == 3:           # [C, H, W]
            state = state.unsqueeze(0) # [1, C, H, W]
            singleExample = True

            if legalMask is not None and legalMask.dim() == 1:
                legalMask = legalMask.unsqueeze(0)
        
        #print(state.shape)
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

        if singleExample:
            policy = policy.squeeze(0)   # [A]
            value  = value.squeeze(0) 

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
    def __init__(self, game, currentPlayer, numActions, applyDailyEffects=False):
        self.game = game
        self.board = copy.deepcopy(game.board)
        self.currentPlayer = currentPlayer
        self.numActions = numActions
        if applyDailyEffects:
            self.game.dailyEffects()

    def getLegalActions(self):
        actions = []

        # Failsafe: If there aren't any units that can move, then there are no legal moves
        for (x0, y0), unit in self.board.units.items():
            if unit.movement > 0 or unit.attackAvailable == True:
                break
            return actions

        moves, _ = self.board.getLegalMovesForPlayer(self.currentPlayer)
        for x0, y0, legalDests in moves:
            for dest in legalDests:
                actions.append(Action(ActionType.MOVE, (x0, y0), (dest[0], dest[1])))
        
        for (x0, y0), unit in self.board.units.items():
            if unit.owner != self.currentPlayer or (unit.movement == 0 and unit.attackAvailable == False):
                continue

            for target in self.board.getAttackTargets(unit):
                actions.append(Action(ActionType.ATTACK, (x0, y0), (target.x, target.y)))

            if self.board.captureTargets(unit):
                actions.append(Action(ActionType.CAPTURE, (x0, y0), None))
            
            if unit.unitType.stealthable:
                actions.append(Action(ActionType.STEALTH, (x0, y0), None))
            
            if unit.unitType.transportCapacity > 0 and unit.loaded:
                for (unlX, unlY) in self.board.getAdjacentPositions(unit, 0):
                    actions.append(Action(ActionType.UNLOAD, (x0, y0), (unlX, unlY)))

            if unit.attackAvailable == True and unit.movement > 0:
                actions.append(Action(ActionType.WAIT, (x0, y0), (x0, y0)))
        
        for (x0, y0), terrain in self.board.buildings.items():
            if (x0,y0) not in self.board.units and terrain.canProduce() and terrain.owner == self.currentPlayer:
                match terrain.name:
                    case "Base":
                        for ut in unitTypes:
                            if (unitTypes.get(ut).moveType != "Sea" and unitTypes.get(ut).moveType != "Air" and unitTypes.get(ut).value <= self.game.funds[self.currentPlayer]): 
                                actions.append(Action(ActionType.BUILD_UNIT, (x0, y0), (ut,)))
                    case "Airport":
                        for ut in unitTypes:
                            if (unitTypes.get(ut).moveType == "Air" and unitTypes.get(ut).value <= self.game.funds[self.currentPlayer]): 
                                actions.append(Action(ActionType.BUILD_UNIT, (x0, y0), (ut,)))
                    case "Harbor":
                        for ut in unitTypes:
                            if (unitTypes.get(ut).moveType == "Sea" and unitTypes.get(ut).value <= self.game.funds[self.currentPlayer]): 
                                actions.append(Action(ActionType.BUILD_UNIT, (x0, y0), (ut,)))


        if self.game.getCO(self.currentPlayer).copAvailable():
            actions.append(Action(ActionType.ACTIVATE_POWER, None, None))

        if self.game.getCO(self.currentPlayer).scopAvailable():
            actions.append(Action(ActionType.ACTIVATE_SUPER, None, None))
        

        return actions

        # moves, _ = self.board.getLegalMovesForPlayer(self.currentPlayer)
        # return list(range(len(moves)))
    
    def getLegalMask(self):
        # moves, _ = self.board.getLegalMovesForPlayer(self.currentPlayer)
        # mask = torch.zeros(self.numActions, dtype=torch.bool)
        # mask[list(range(len(moves)))] = True
        mask = torch.zeros(self.numActions, dtype=torch.bool)

        legal = set(self.getLegalActions())
        for idx, action in enumerate(ALL_ACTIONS):
            if action in legal:
                mask[idx] = True

        if not legal:
            mask[END_TURN_IDX] = True
    
        return mask
    
    def applyAction(self, action):
        # actions = self.getLegalActions()
        # act = actions[action]
        act = ALL_ACTIONS[action]

        ### TODO: The error is caused by CO powers always being legal, so it never appends end turn.
        ### Either find a way to append end turn, or figure out why the algorithm isn't using its power.
        legal = set(self.getLegalActions())
        #print(legal)
        # If there are no legal moves, you must end your turn
        if legal is None or len(legal) == 0:
            act = Action(ActionType.END_TURN, None, None)
        elif act not in legal:
            return self

        newGame = copy.deepcopy(self.game)
        newBoard = copy.deepcopy(self.board)
        newGame.board = newBoard  
        x0, y0, x1, y1, unitCode = [None] * 5   
        
        if act.actor is not None:
            x0, y0 = act.actor
        if act.target is not None:
            if act.type != ActionType.BUILD_UNIT:
                x1, y1 = act.target
            else:
                unitCode = act.target[0]

        match act.type:
            case ActionType.MOVE:
                moves, costs = newBoard.get_legal_moves(newBoard.units[(x0,y0)])
                newBoard.moveUnit(x0,y0,x1,y1, moves, costs, newGame)

            case ActionType.ATTACK:
                attacker = newBoard.units[(x0,y0)]
                defender = newBoard.units[(x1,y1)]
                fundsToAdd = attacker.attack(defender, newGame,  newGame.getCO(attacker.owner).luckLowerBound, newGame.getCO(attacker.owner).luckUpperBound, newGame.getCO(defender.owner).luckLowerBound, newGame.getCO(defender.owner).luckUpperBound)
                if newGame.getCO(self.currentPlayer).name == "Sasha" and newGame.getCO(self.currentPlayer).powerStage == 2 and fundsToAdd is not None:
                    newGame.funds[self.currentPlayer] += 0.50 * fundsToAdd

            case ActionType.CAPTURE:
                newBoard.units[(x0,y0)].capture(newBoard)

            case ActionType.STEALTH:
                unit = newBoard.units[(x0, y0)]
                if unit.unitType.isStealthed:
                    unit.unitType.isStelathed = False
                else:
                    unit.unitType.isStelathed = True

            case ActionType.UNLOAD:
                transport = newBoard.units[x0,y0]
                newBoard.unloadUnit(transport, x1, y1)

            case ActionType.BUILD_UNIT:
                newGame.productionStep(inputType=0, unitCode=unitCode)

            case ActionType.ACTIVATE_POWER:
                newGame.getCO(self.currentPlayer).activateCO(newGame)

            case ActionType.ACTIVATE_SUPER:
                newGame.getCO(self.currentPlayer).activateSuper(newGame)

            # Wait does nothing, but for completeness I left it in here
            case ActionType.WAIT:
                moves, costs = newBoard.get_legal_moves(newBoard.units[(x0,y0)])
                newBoard.moveUnit(x0,y0,x0,y0, moves, costs, newGame)

            case ActionType.END_TURN:
                # print("Applied action AttackType.END_TURN")
                finalGame = copy.deepcopy(newGame)
                finalGame.board = copy.deepcopy(newBoard)
                finalGame.endTurn()
                finalGame.weatherStep(finalGame.weather != "CLEAR")
                # print(f"The weather is currently {finalGame.weather} with {finalGame.weatherTimer} turns left")
                # print(f"Player 1: {finalGame.funds[1]}, Player 2: {finalGame.funds[-1]}")
                return State(finalGame, -self.currentPlayer, self.numActions, applyDailyEffects=True)

            case _:
                raise ValueError(f"Unknown action type {act.type}")
            
        # if x1 is not None: print(f"Applied action {act.type}, actor is unit on {(x0, y0)} which targets {x1, y1}")
        # elif unitCode is not None: print(f"Applied action {act.type}, actor is unit on {(x0, y0)} which built {unitCode}")
        #elif act.type == ActionType.ATTACK:print(f"Applied action {act.type}, actor is unit {newBoard.units[(x0,y0)].unitType.unitName} on {(x0, y0)} which targets {x1, y1}")
        #print(newBoard)
        finalGame = copy.deepcopy(newGame)
        finalGame.board = copy.deepcopy(newBoard)
        return State(finalGame, self.currentPlayer, self.numActions)
                
    # The old apply action that can only handle movement
    # def applyAction(self, action):
    #     moves, costs = self.board.getLegalMovesForPlayer(self.currentPlayer)

    #     # Flattening the moves and costs arrays into arrays of (x0,y0,x1,y1) 4-Tuples
    #     flatMoves = []
    #     flatCosts = []
    #     for (x0, y0, destList), costList in zip(moves, costs):
    #         if not destList:
    #             flatMoves.append((x0, y0, x0, y0))
    #             flatCosts.append(0)
    #         else:
    #             for (x1, y1), cost in zip(destList, costList):
    #                 flatMoves.append((x0, y0, x1, y1))
    #                 flatCosts.append(cost)


    #     x0, y0, x1, y1 = flatMoves[action]

    #     newBoard = copy.deepcopy(self.board)
    #     newBoard.moveUnit(x0, y0, x1, y1, moves[action][2], costs, self.game)

    #     game = copy.deepcopy(self.game)
    #     game.board = copy.deepcopy(newBoard)
    #     return State(game, -self.currentPlayer, self.numActions)
    
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
