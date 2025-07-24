import torch
from tqdm import tqdm
from pathlib import Path
from torch.utils.data import Dataset, DataLoader
from torch.optim.lr_scheduler import StepLR
from PVN import PVN, ALL_ACTIONS
from MCTS import MCTS

import os, sys
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, PROJECT_ROOT)
from SimpleAWEngine.Game import Game
from SimpleAWEngine.Unit import Unit, unitTypes
from SimpleAWEngine.Board import terrain_types
from SimpleAWEngine.CO import COs


TOLERANCE = 1e-4
PATIENCE = 5
MODEL_PATH = Path("StockNell/models")
MODEL_PATH.mkdir(parents=True, exist_ok=True)

MODEL_NAME = "stock_nell_v1.pth"
MODEL_SAVE_PATH = MODEL_PATH / MODEL_NAME

# ACTIVATE VENV: source venv/bin/activate
# DEACTIVATE USING deactivate
# IF ADDING MORE LIBRARIES, DO pip3 freeze > requirements.txt

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
def accuracyFNTutorial(y_true, y_pred):
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

def accuracyFNPolicy(preds, piStar):
    topMove = preds.argmax(dim=1)
    label = piStar.argmax(dim=1)
    return (topMove == label).float().mean()

def accuracyFNValue(valuesTrue, valuePreds):
    return (valuePreds.sign() == valuesTrue.sign()).float().mean()

def trainModel(model, lossFN, opt, device, scheduler, accuracyFNPolicy, accuracyFNValue, mcts, game, numSelfPlayGames, startEpoch, endEpoch=10):
    dataset = []
    trainExamples = mcts.runSelfPlay(game=game, numGames=numSelfPlayGames)
    testExamples = mcts.runSelfPlay(game=game, numGames=numSelfPlayGames)
    dataset.extend(trainExamples)

    trainLoader = DataLoader(AWBWDataset(dataset), batch_size=32, shuffle=True, num_workers=0, pin_memory=True)
    testLoader = DataLoader(AWBWDataset(testExamples), batch_size=32, shuffle=False, num_workers=0, pin_memory=True, drop_last=False)

    trainingLoop(model, trainLoader, testLoader, lossFN, opt, device, scheduler, accuracyFNPolicy, accuracyFNValue, startEpoch, endEpoch)


# The full training loop
def trainingLoop(model: torch.nn.Module,
        trainDataLoader: torch.utils.data.DataLoader, 
        testDataLoader: torch.utils.data.DataLoader,
        lossFN: torch.nn.Module,
        opt: torch.optim.Optimizer,
        device,
        scheduler,
        accuracyFNPolicy = accuracyFNPolicy, 
        accuracyFNValue = accuracyFNValue,
        startEpoch : int = 0,
        endEpoch: int = 10):
        
    bestValLoss = float('inf')
    epochsWithoutImprove = 0
    results = {"policyLossTrain": [], "valueLossTrain": [], "policyAccTrain": [], "valueAccTrain": [],
               "policyLossTest": [], "valueLossTest": [], "policyAccTest": [], "valueAccTest": []}
    for epoch in tqdm(range(startEpoch, endEpoch)):
        policyLossTrain, valueLossTrain, policyAccTrain, valueAccTrain = trainStep(model, trainDataLoader, lossFN, opt, accuracyFNPolicy, accuracyFNValue, device)
        policyLossTest, valueLossTest, policyAccTest, valueAccTest = testStep(model, testDataLoader, lossFN, accuracyFNPolicy, accuracyFNValue, device)

        print(f"Epoch: {epoch+1} | "
            f"policyLossTrain: {policyLossTrain:.4f} | "
            f"valueLossTrain: {valueLossTrain:.4f} | "
            f"policyAccTrain: {policyAccTrain:.4f} | "
            f"valueAccTrain: {valueAccTrain:.4f} | "
            f"policyLossTest: {policyLossTest:.4f} | "
            f"valueLossTest: {valueLossTest:.4f} | "
            f"policyAccTest: {policyAccTest:.4f} | "
            f"valueAccTest: {valueAccTest:.4f} | ")
        results["policyLossTrain"].append(policyLossTrain.item() if isinstance(policyLossTrain, torch.Tensor) else policyLossTrain)
        results["valueLossTrain"].append(valueLossTrain.item() if isinstance(valueLossTrain, torch.Tensor) else valueLossTrain)
        results["policyAccTrain"].append(policyAccTrain.item() if isinstance(policyAccTrain, torch.Tensor) else policyAccTrain)
        results["valueAccTrain"].append(valueAccTrain.item() if isinstance(valueAccTrain, torch.Tensor) else valueAccTrain)
        results["policyLossTest"].append(policyLossTest.item() if isinstance(policyLossTest, torch.Tensor) else policyLossTest)
        results["valueLossTest"].append(valueLossTest.item() if isinstance(valueLossTest, torch.Tensor) else valueLossTest)
        results["policyAccTest"].append(policyAccTest.item() if isinstance(policyAccTest, torch.Tensor) else policyAccTest)
        results["valueAccTest"].append(valueAccTest.item() if isinstance(valueAccTest, torch.Tensor) else valueAccTest)

        scheduler.step()

        # Early stopping
        if (valueLossTest + policyLossTest) < (bestValLoss - TOLERANCE):
            bestValLoss = (valueLossTest + policyLossTest)
            epochsWithoutImprove = 0
            saveTrainingCheckpoint(MODEL_SAVE_PATH, model, opt, scheduler, epoch, bestValLoss)
        else:
            epochsWithoutImprove += 1
            if epochsWithoutImprove >= PATIENCE:
                print(f"Stopping early at epoch {epoch} due to no improvement by {TOLERANCE} in {PATIENCE} epochs")
                break

    return results

# One epoch of the training loop
def trainStep(model, dataLoader, lossFN, opt, accuracyFNPolicy, accuracyFNValue, device):
    model.train()
    policyTrainAcc, valueTrainAcc, totalPolicy, totalValue, totalExamples = 0, 0, 0, 0, 0
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
        

        policyTrainAcc = accuracyFNPolicy(policyPreds, piStar)
        valueTrainAcc += accuracyFNValue(valuesTrue, valuePreds.argmax(dim=1))

        loss.backward()
        opt.step()

        batchSize = states.size(0)
        totalPolicy += policyLoss.item() * batchSize
        totalValue += valueLoss.item() * batchSize
        totalExamples += batchSize
    
    return totalPolicy/totalExamples, totalValue/totalExamples, policyTrainAcc/totalExamples, valueTrainAcc/totalExamples

def testStep(model, dataLoader, lossFN, accuracyFNPolicy, accuracyFNValue, device):
    totalPolicy, totalValue, count, policyTestAcc, valueTestAcc = 0,0,0,0,0
    model.eval()
    with torch.inference_mode():
        for batch in dataLoader:
            states = batch["state"].to(device)
            piStar = batch["piStar"].to(device)
            valuesTrue = batch["value"].to(device)
            legalMask = batch["legalMask"].to(device)

            policyPreds, valuePreds = model(states, legalMask)

            lp = torch.log(policyPreds + 1e-8)
            policyLoss = -(piStar * lp).sum(dim=1).mean()
            valueLoss = lossFN(valuePreds, valuesTrue)

            totalPolicy += policyLoss.item() * states.size(0)
            totalValue += valueLoss.item() * states.size(0)
            policyTestAcc += accuracyFNPolicy(policyPreds, piStar)
            valueTestAcc += accuracyFNValue(valuesTrue, valuePreds)#.argmax(dim=1))
            count += states.size(0)

    #print(f"\nTest Loss: {testLoss:.4f}, Test acc: {testAcc:.4f}")
    return totalPolicy/count, totalValue/count, policyTestAcc / count, valueTestAcc / count

def saveTrainingCheckpoint(path, model, optimizer, scheduler, epoch, bestValLoss):
    torch.save({
        "epoch": epoch,
        "modelState": model.state_dict(),
        "optimState": optimizer.state_dict(),
        "schedState": scheduler.state_dict() if scheduler else None,
        "bestValLoss": bestValLoss,
    }, path)

def loadTrainingCheckpoint(path, model, optimizer=None, scheduler=None):
    ckpt = torch.load(path, map_location="mps")
    model.load_state_dict(ckpt["modelState"])
    if optimizer and ckpt["optimState"]:
        optimizer.load_state_dict(ckpt["optimState"])
    if scheduler and ckpt.get("schedState"):
        scheduler.load_state_dict(ckpt["schedState"])
    return ckpt["epoch"], ckpt.get("bestValLoss", float('inf'))


# # numChannels = numTerrainTypes + (2 * numUnitTypes) + HP + Fuel + Ammo (all 1) + PlayerToMove
# inChannels = 18 + (25 * 2) + 1 + 1 + 1 + 1
# numActionsAWBW = len(ALL_ACTIONS)
# numActionsTTT = 9

# # terrain_codes = [
# #     #      0      1      2      3      4      5      6       7
# #     [('A', 1), ('CM', -1), ('P', 0), ('F', 0), ('S', 0), ('S', 0), ('H', -1), ('HQ', -1)],
# #     [('P', 0), ('M', 0), ('P', 0), ('F', 0), ('SH', 0), ('S', 0), ('M', 0),  ('P', 0 )],
# #     [('P', 0), ('P', 0), ('P', 0), ('P', 0), ('P', 0), ('P', 0), ('P', 0),  ('BA', -1)],
# #     [('C', 0), ('P', 0), ('P', 0), ('C', 0), ('C', 0), ('R', 0), ('R', 0),  ('R', 0 )],
# #     [('R', 0), ('R', 0), ('R', 0), ('C', 0), ('C', 0), ('P', 0), ('P', 0),  ('C', 0 )],
# #     [('BA', 1), ('P', 0), ('P', 0), ('P', 0), ('P', 0), ('P', 0), ('P', 0),  ('P', 0 )],
# #     [('P', 0), ('M', 0), ('S', 0), ('SH',0), ('F', 0), ('P', 0), ('M', 0),  ('P', 0 )],
# #     [('HQ',1), ('H', 1), ('S', 0), ('S', 0), ('F', 0), ('P', 0), ('P', 0),  ('A', -1)]
# # ]
# terrain_codes = [[('BA',1),('HQ',1),('HQ', -1), ('BA', -1)]]
# boardSize = (len(terrain_codes), len(terrain_codes[0]))

# network = PVN(inChannels, boardSize, numActionsAWBW)
# mctsComplex = MCTS(network, cPuct=1.0, numSims=2, numActions=numActionsAWBW)

# # startingUnits = [(Unit(1,unitTypes.get('INF')), 0, 7), 
# #                  (Unit(-1,unitTypes.get('INF')), 7, 0)]
# startingUnits = [(Unit(1,unitTypes.get('INF')), 0, 0), 
#                  (Unit(-1,unitTypes.get('INF')), 3, 0)]

# game = Game(terrain_codes, terrain_types, player1CO=COs.get("Sami"), player2CO=COs.get("Andy"), startingUnits=startingUnits)

# dataset = AWBWDataset(mctsComplex.runSelfPlay(game=game, numGames=2)) # Self play examples go here
# loader = DataLoader(
#     dataset,
#     batch_size=32,
#     shuffle=True,
#     num_workers=0,
#     pin_memory=True
# )

# optimizer = torch.optim.Adam(network.parameters(), lr=1e-3)
# scheduler = StepLR(optimizer, step_size=10, gamma=0.5)






# batch = next(iter(loader))
# print(batch["state"].shape)       # → [32, C, H, W]
# print(batch["piStar"].shape)     # → [32, num_actions]
# print(batch["value"].shape)       # → [32]
# print(batch["legalMask"].shape)  # → [32, num_actions]