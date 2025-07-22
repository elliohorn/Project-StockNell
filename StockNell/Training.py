import torch
import tqdm
from torch.utils.data import Dataset, DataLoader
from PVN import PVN, ALL_ACTIONS
from MCTS import MCTS

import os, sys
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, PROJECT_ROOT)
from SimpleAWEngine.Game import Game
from SimpleAWEngine.Unit import Unit, unitTypes
from SimpleAWEngine.Board import terrain_types
from SimpleAWEngine.CO import COs



class AWBWDataset(Dataset):
    def __init__(self, example):
        self.example = example

    def __len__(self):
        return len(self.example)
    
    def __getitem__(self, index):
        s, piStar, z, mask = self.example[index]
        return {
            "state" : s,        # FloatTensor[C,H,W]
            "piStar": piStar,   # FloatTensor[numActions]
            "value": torch.tensor(z, dtype=torch.float32),
            "legalMask": mask   # BoolTensor[numActions]
        }


# From the tutorial I used to learn PyTorch
def accuracy_fn(y_true, y_pred):
    """Calculates accuracy between truth labels and predictions.

    Args:
        y_true (torch.Tensor): Truth labels for predictions.
        y_pred (torch.Tensor): Predictions to be compared to predictions.

    Returns:
        [torch.float]: Accuracy value between y_true and y_pred, e.g. 78.45
    """
    correct = torch.eq(y_true, y_pred).sum().item()
    acc = (correct / len(y_pred)) * 100
    return acc


def train(model: torch.nn.Module,
        trainDataLoader: torch.utils.data.DataLoader, 
        testDataLoader: torch.utils.data.DataLoader,
        lossFN: torch.nn.Module,
        opt: torch.optim.Optimizer,
        device,
        accuracyFN = accuracy_fn, 
        epochs: int = 5,):
        
    results = {"train_loss": [], "train_acc": [], "test_loss": [], "test_acc": []}
    for epoch in tqdm(range(epochs)):
        trainLoss, trainAcc = trainStep(model, trainDataLoader, lossFN, opt, accuracyFN, device)
       # testLoss, testAcc = testStep(model, testDataLoader, lossFN, accuracyFN, device)

        print(f"Epoch: {epoch+1} | "
            f"train_loss: {trainLoss:.4f} | "
            f"train_acc: {trainAcc:.4f} | ")
            # f"test_loss: {testLoss:.4f} | "
            # f"test_acc: {testAcc:.4f}")
        # 5. Update results dictionary
        # Ensure all data is moved to CPU and converted to float for storage
        results["train_loss"].append(trainLoss.item() if isinstance(trainLoss, torch.Tensor) else trainLoss)
        results["train_acc"].append(trainAcc.item() if isinstance(trainAcc, torch.Tensor) else trainAcc)
        # results["test_loss"].append(testLoss.item() if isinstance(testLoss, torch.Tensor) else testLoss)
        # results["test_acc"].append(testAcc.item() if isinstance(testAcc, torch.Tensor) else testAcc)
    
    return results

def trainStep(model, dataLoader, lossFN, opt, accuracyFN, device):
    model.train()
    trainAcc, totalPolicy, totalValue, totalExamples = 0, 0, 0, 0
    for batch in dataLoader:
        states = batch["state"].to(device)
        piStar = batch["piStar"].to(device)
        valuesTrue = batch["value"].to(device)
        legalMask = batch["legalMask"].to(device)

        opt.zero_grad()
        policyPreds, valuePreds = model(states, legalMask)
        
        # Compute loss. Policy is the actual direct form of CrossEntropyLoss, but
        # we can't use the function directly
        logProbs = torch.log(policyPreds + 1e-8)
        policyLoss = -torch.sum(piStar * logProbs, dim=1).mean()
        valueLoss = lossFN(valuePreds, valuesTrue)
        loss = policyLoss + valueLoss
        trainAcc += accuracyFN(valuesTrue, valuePreds.argmax(dim=1))

        loss.backward()
        opt.step()

        batchSize = states.size(0)
        totalPolicy += policyLoss.item() * batchSize
        totalValue += valueLoss.item() * batchSize
        totalExamples += batchSize

def testStep():
    pass

# numChannels = numTerrainTypes + (2 * numUnitTypes) + HP + Fuel + Ammo (all 1) + PlayerToMove
inChannels = 18 + (25 * 2) + 1 + 1 + 1 + 1
numActionsAWBW = len(ALL_ACTIONS)
numActionsTTT = 9

# terrain_codes = [
#     #      0      1      2      3      4      5      6       7
#     [('A', 1), ('CM', -1), ('P', 0), ('F', 0), ('S', 0), ('S', 0), ('H', -1), ('HQ', -1)],
#     [('P', 0), ('M', 0), ('P', 0), ('F', 0), ('SH', 0), ('S', 0), ('M', 0),  ('P', 0 )],
#     [('P', 0), ('P', 0), ('P', 0), ('P', 0), ('P', 0), ('P', 0), ('P', 0),  ('BA', -1)],
#     [('C', 0), ('P', 0), ('P', 0), ('C', 0), ('C', 0), ('R', 0), ('R', 0),  ('R', 0 )],
#     [('R', 0), ('R', 0), ('R', 0), ('C', 0), ('C', 0), ('P', 0), ('P', 0),  ('C', 0 )],
#     [('BA', 1), ('P', 0), ('P', 0), ('P', 0), ('P', 0), ('P', 0), ('P', 0),  ('P', 0 )],
#     [('P', 0), ('M', 0), ('S', 0), ('SH',0), ('F', 0), ('P', 0), ('M', 0),  ('P', 0 )],
#     [('HQ',1), ('H', 1), ('S', 0), ('S', 0), ('F', 0), ('P', 0), ('P', 0),  ('A', -1)]
# ]
terrain_codes = [[('BA',1),('HQ',1),('HQ', -1), ('BA', -1)]]
boardSize = (len(terrain_codes), len(terrain_codes[0]))

network = PVN(inChannels, boardSize, numActionsAWBW)
mctsComplex = MCTS(network, cPuct=1.0, numSims=2, numActions=numActionsAWBW)

# startingUnits = [(Unit(1,unitTypes.get('INF')), 0, 7), 
#                  (Unit(-1,unitTypes.get('INF')), 7, 0)]
startingUnits = [(Unit(1,unitTypes.get('INF')), 0, 0), 
                 (Unit(-1,unitTypes.get('INF')), 3, 0)]

game = Game(terrain_codes, terrain_types, player1CO=COs.get("Sami"), player2CO=COs.get("Andy"), startingUnits=startingUnits)

dataset = AWBWDataset(mctsComplex.runSelfPlay(game=game, numGames=2)) # Self play examples go here
loader = DataLoader(
    dataset,
    batch_size=32,
    shuffle=True,
    num_workers=0,
    pin_memory=True
)

batch = next(iter(loader))
print(batch["state"].shape)       # → [32, C, H, W]
print(batch["piStar"].shape)     # → [32, num_actions]
print(batch["value"].shape)       # → [32]
print(batch["legalMask"].shape)  # → [32, num_actions]