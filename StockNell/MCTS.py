import torch
import numpy
import math

class MCTS:
    def __init__(self, model, cPuct, numSims):
        self.model = model      # This is the PVN
        self.cPuct = cPuct      # The exploration coefficent (higher means more, lower means less)
        self.numSims = numSims  # Number of loops of the MCTS algorithm


    ### This is the MCTS Algorithm: Selection -> Expansion -> Simulation -> Backpropagation
    def run(self, rootState):
        self.root = TreeNode()
        for _ in range(self.numSims):
            node, state = self.select(self.root, rootState)
            value = self.expandAndEval(node, state)
            self.backup(node, value)
        # Return all children's visit counts
        return {a: child.visCount for a, child in self.root.children.items()}
    
    ## MCTS Step 1: Selection
    def select(self, node, state):
        current = node
        currentState = state

        while current.children:
            totalVisCount = sum(child.visCount for child in current.children.values())
            bestScore = -float('inf')
            bestAction = None
            bestChild = None

            for action, child in current.children.items():
                Q = child.meanVal
                P = child.prior
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
    def expandAndEval(self, node, state):
        legalMask = state.getLegalMask()
        policy, value = self.model(torch.tensor(state), legalMask)

        for action, prior in enumerate(policy):
            if legalMask[action]: # Check if the move is legal
                # I think this is supposed to be a K-V Pair. Key: Action, Value: Node that action leads to
                node.children[action] = TreeNode(parent=node, prior=prior) 
        return value.item()
        

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
        

