import torch
import numpy as np
import math
import random
import copy
from PVN import State

class MCTS:
    def __init__(self, model, cPuct, numSims, numActions):
        self.model = model      # This is the PVN
        self.cPuct = cPuct      # The exploration coefficent (higher means more, lower means less)
        self.numSims = numSims  # Number of loops of the MCTS algorithm
        self.numActions = numActions


    ### This is the MCTS Algorithm: Selection -> Expansion -> Simulation -> Backpropagation
    def run(self, rootState, board, legalMask):
        self.root = TreeNode()
        for _ in range(self.numSims):
            node, state = self.select(self.root, copy.deepcopy(rootState))
            if state.isTerminal() is not None:
                value = state.isTerminal()
            else:
                value = self.expandAndEval(node, state, board, legalMask)
            self.backup(node, value)
        # Return all children's visit counts        
        return {a: child.visCount for a, child in self.root.children.items()}
    
    def runSelfPlay(self, game, numGames):
        examples = []
        for _ in range(numGames):
            state = State(copy.deepcopy(game), currentPlayer=1, numActions=self.numActions)
            trajectory = []
            moveIdx = 0
        

            while not state.isTerminal():
                mask = state.getLegalMask()
                mcts = self
                counts = mcts.run(state, game.board, mask)

                total = sum(counts.values())
                piStar = torch.zeros_like(mask, dtype=torch.float32)
                for a, n in counts.items():
                    piStar[a] = n / total

                stateTensor = state.stateToTensor(copy.deepcopy(game.board))
                trajectory.append((stateTensor, piStar, mask))

                # Scales the temperature with the number of moves made (get greedier over time)
                if moveIdx < 10:
                    tau = 1.0
                elif moveIdx < 20:
                    tau = 0.5
                else:
                    tau = 0.0

                action = mcts.sampleFromPI(piStar, tau)

                state = state.applyAction(action)
                moveIdx += 1

            z = state.isTerminal()

            for (stateTensor, piStar, mask) in trajectory:
                examples.append((stateTensor, piStar, z, mask))
        
        print(f"Terminal state reached {state.isTerminal()}")
        return examples
    
    def sampleFromPI(self, piStar, temperature):
        if isinstance(piStar, torch.Tensor):
            pi = piStar.detach().cpu().numpy().astype(np.float64)
        else:
            pi = np.array(piStar, dtype=np.float64)


        if temperature <= 0:
            # Greedy exploitation
            return int(pi.argmax())
    
        # Exploration (scaling probabilities) using 1 / Temperature
        with np.errstate(divide='ignore', invalid='ignore'):
            scaled = np.power(pi, 1.0 / temperature)

        total = scaled.sum()

        if total <= 0 or not np.isfinite(total):
            # Fallback: uniform over all positive‐prob moves,
            # or over all moves if none positive
            mask = pi > 0
            if not mask.any():
                mask = np.ones_like(pi, dtype=bool)
            probs = mask.astype(np.float64)
            probs /= probs.sum()
        else:
            probs = scaled / total

        probsSum = probs.sum()
        if probsSum <= 0 or not np.isfinite(probsSum):
            raise RuntimeError(f"Cannot normalize probs, sum={probsSum}")
        probs /= probsSum

        return int(np.random.choice(len(probs), p=probs))

    ## MCTS Step 1: Selection
    def select(self, node, state):
        current = node
        currentState = state

        while current.children:
            totalVisCount = sum(child.visCount for child in current.children.values())
            bestScore = -float('inf')
            bestAction = None
            bestChild = None

            noise = np.random.dirichlet([0.3]*self.numActions)
            for action, child in current.children.items():
                Q = child.meanVal
                P = 0.75 * child.prior + 0.25*noise[action]
                N = child.visCount
    
                # PUCT Formula
                U = self.cPuct * P * (math.sqrt(totalVisCount) / (1 + N))
                score = Q + U

                if score > bestScore:
                    bestScore = score
                    bestAction = action
                    bestChild = child
            
            currentState = currentState.applyAction(action=bestAction)
            current = bestChild
        
        return current, currentState



    ## MCTS Step 2 + 3: Expansion and Simulation
    def expandAndEval(self, node, state, board, legalMask):
       #legalMask = state.getLegalMask()
        policy, value = self.model(state.stateToTensor(board), legalMask)

        for action, prior in enumerate(policy):
            if legalMask[action]: # Check if the move is legal
                # I think this is supposed to be a K-V Pair. Key: Action, Value: Node that action leads to
                node.children[action] = TreeNode(parent=node, prior=prior) 
        return value#.item()
        

    ## MCTS Step 4: Backpropagation
    def backup(self, node, value):
        while node:
            node.visCount += 1
            node.totalVal += value
            node.meanVal = node.visCount / node.totalVal
            node = node.parent
            value = -value      # This toggles perspective for a two player game




class TreeNode:
    def __init__(self, parent=None, prior=0.0):
        self.parent = parent
        self.children = {}
        self.visCount = 0
        self.totalVal = 0.0
        self.meanVal = 0.0      # Mean val = visCount/totalVal
        self.prior = prior      # Prior probability as given by the policy head
        

