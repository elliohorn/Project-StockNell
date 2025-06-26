from SimpleAWEngine.Board import Board
from SimpleAWEngine.Unit import Unit, unitTypes
from CO import CO, COs
# from Board import Board
# from Unit import Unit
import random
from collections import deque

class Game:
    def __init__(self, terrainCodes, terrainTypes, player1CO, player2CO, startingUnits={}):
        """
        terrain_codes: 2D list of map codes
        terrain_types: dict code→TerrainType
        starting_units: list of (unit_type, owner, x, y)
        """
        self.board = Board(terrainCodes, terrainTypes) 
        for unit, x, y in startingUnits:
            #unit = Unit(owner, utype)
            self.board.addUnit(unit, x, y)

        self.currentPlayer = 1 # 1, alternates to -1
        self.funds = {1: 1000, -1: 1000}

    def getCO(self, player):
        if player == 1: return self.player1CO
        else: return self.player2CO

    def collectIncome(self):
        # sum city/base income owned
        income = 0
        for (x,y), b in self.board.buildings.items():
            if b.owner == self.currentPlayer and b.name in ("City","Base","Aiport","Harbor","HQ"):
                income += 1000 
        self.funds[self.currentPlayer] += income

    def playTurn(self, inputType=0, FOW=False):
        # Build an initial queue of your units
        actionQueue = deque(
            u for u in self.board.units.values()
            if u.owner == self.currentPlayer
        )

        myUnits = [u for u in self.board.units.values()
                  if u.owner == self.currentPlayer]
        
        for unit in myUnits:
            if self.getCO(self.currentPlayer) == "Rachel":
                self.resupplyCheck(unit, modifier = 1)
            else:
                self.resupplyCheck(unit)
            if unit.unitType.stealthable and unit.unitType.isStealthed:
                unit.unitType.fuel -= unit.unitType.stealthBurn
            elif unit.unitType.fuelBurn != 0:
                unit.unitType.fuel -= unit.unitType.fuelBurn
        
        # Track which units have been explicitly "ended"
        done = set()

        while actionQueue:
            unit = actionQueue.popleft()

            # if unit was marked done, skip it
            if unit in done:
                continue

            # Show options, etc… like in your manual‐input branch
            moves, costs = self.board.get_legal_moves(unit)
            print(self.board.render(self.currentPlayer))
            print(f"Unit: {unit} MP={unit.movement} Fuel={unit.unitType.fuel}")
            for i, dest in enumerate(moves):
                print(f"{i}: → {dest} (cost {costs[dest]})")
            print(f"Actions: move, load, unload, capture, attack, stealth={unit.unitType.stealthable}, end")
            action = input("Action? ").strip().lower()

            match action:
                case "move":
                    idx = int(input("Move index: "))
                    dest = moves[idx]
                    self.board.moveUnit(unit.x, unit.y, *dest, moves, costs)
                    actionQueue.appendleft(unit)

                # _do not_ mark unit done—maybe you want to load/unload next
                # action_queue.appendleft(unit)  # optionally replay immediately

                case "load":
                    # only valid if stacked on a transport
                    transport = self.board.units.get((unit.x, unit.y))
                    if transport and transport.unitType.transportCapacity > 0:
                        self.board.loadUnit(transport, unit)
                        print(f"Loaded into {transport}")
                        # Re-enqueue the transport so you can then unload it:
                        actionQueue.appendleft(transport)
                    else:
                        print("No transport here.")

                case "unload":
                    # only valid if this unit is a transport with cargo
                    if unit.unitType.transportCapacity > 0 and unit.loaded:
                        spots = self.board.getAdjacentPositions(unit, 0)
                        for i, pos in enumerate(spots):
                            print(f"{i}: unload to {pos}")
                        idx = int(input("Unload index: "))
                        self.board.unloadUnit(unit, *spots[idx])
                        print("Unloaded.")
                        #action_queue.appendleft(unit)
                    else:
                        print("Nothing to unload.")

                case "capture":
                    if self.board.captureTargets(unit):
                        self.board.capture(unit)
                    else:
                        print("Cannot capture here.")

                case "attack":
                    enemies = self.board.get_attack_targets(unit)
                    for i, e in enumerate(enemies):
                        print(f"{i}: {e}")
                    idx = int(input("Enemy index: "))
                    self.board.attack(unit, enemies[idx], self.board)

                case "stealth":
                    if unit.unitType.stealthable:
                        if not unit.unitType.isStealthed: 
                            print("Unit stealthed")
                            unit.unitType.isStealthed = True
                        else:
                            print("Unit unstealthed")
                            unit.unitType.isStealthed = False
                    else:
                        print("Unit not stealthable.")
                        actionQueue.appendleft(unit)

                case "supply":
                    spots = self.board.getAdjacentPositions(unit, 2)
                    if unit.unitType.unitName == "APC":
                        for i, pos in enumerate(spots):
                            destX, destY = pos
                            self.board.units[(destX, destY)].resupply(self, 0)
                    elif unit.unitType.unitName == "BLK":
                        for i, pos in enumerate(spots):
                            print(f"{i}: heal unit at {pos}")
                        choice = int(input("Choose heal index, or -1 to skip: "))
                        if 0 <= choice < len(spots):
                            destX, destY = spots[choice]
                            print(destX, destY)
                            self.board.units[(destX, destY)].resupply(self, 10)

                case "end":
                    # mark this unit done for the rest of the turn
                    done.add(unit)
                case _:
                    print("Unknown action.")
                    # re-enqueue so they can try again
                    actionQueue.appendleft(unit)

        # After exhausting the queue, do your end_of_turn(), switch player, etc.
        self.productionStep(inputType)
        self.endTurn()
        self.currentPlayer *= -1

    def productionStep(self, inputType):
        for y in range(self.board.height):
            for x in range(self.board.width):
                terrain = self.board.getTerrain(x, y)
                # 1) must be a production tile
                if not terrain.canProduce():
                    continue
                # 2) must be owned by current player
                if self.board.getOwnership(x, y) != self.currentPlayer:
                    continue
                    # 3) must be empty (no unit there)
                if (x, y) in self.board.units:
                    continue
                if inputType == 1:
                    unitToBuild = "" 
                    unitBuilt = False
                    while (unitToBuild != None and unitBuilt == False):
                        unitToBuild = input(f"What unit would you like to build at {terrain.name} building at {(x, y)}? Owner {terrain.owner}, player {self.currentPlayer}\n")
                        try:
                            if self.funds[self.currentPlayer] < unitTypes.get(unitToBuild).value:
                               print("Not enough funds!")
                            elif ((unitTypes.get(unitToBuild).moveType == "Sea" and terrain.name == "Harbor") or # Naval unit at harbor
                                  (unitTypes.get(unitToBuild).moveType == "Air" and terrain.name == "Airport") or  # Air unit at airport
                                  ((unitTypes.get(unitToBuild).moveType != "Sea" and unitTypes.get(unitToBuild).moveType != "Air") and terrain.name == "Base")): # Land unit at base
                                
                                unitBuilt = True
                                self.funds[self.currentPlayer] -= unitTypes.get(unitToBuild).value
                                newUnit = Unit(self.currentPlayer,unitTypes.get(unitToBuild))
                                self.board.addUnit(newUnit, x, y, False)
                                print(self.board.render(self.currentPlayer))
                            else:
                                print("No unit built here")
                                unitToBuild = None
                        except Exception as e:
                            print("Not a unit!")
                            unitToBuild = None

    def resupplyCheck(self, unit, modifier=0):
        if unit.unitType.transportsUnits:
            for unit in unit.loaded:
                unit.resupply(self, 0)
            for adjUnit in self.board.getAdjacentPositions(unit, 2):
                adjUnit = self.board.units.get(adjUnit)
                if adjUnit.owner == self.currentPlayer:
                    adjUnit.resupply(self, 0)
            
        at = self.board.grid[unit.y][unit.x]
        if at.owner != unit.owner: return # Can't resupply on enemy or neutral city
        match unit.unitType.moveType:
            case "SEA":
                if at.name == "Harbor":
                    unit.resupply(self, 20 + modifier)
            case "AIR":
                if at.name == "Airport":
                    unit.resupply(self, 20 + modifier)
            case _:
                if at.name == "Base" or at.name == "City":
                    unit.resupply(self, 20 + modifier)

    def endTurn(self):
        for unit in list(self.board.units.values()):
            if unit.owner == self.currentPlayer:
                unit.movement = unit.unitType.maxMovement
                unit.attackAvailable = True

        ## FOG UPDATE GOES HERE WHEN IMPLEMENTED
        # self.board.updateVisibility(self.currentPlayer)

        winner = self.checkVictory()
        if winner is not None:
            print(f"Player {winner} wins!")
            return True
        return False
    
    def checkVictory(self):
        opp = -self.currentPlayer
        opp_units = [u for u in self.board.units.values() if u.owner == opp]
        hqCoords = [pos for pos, b in self.board.buildings.items() if b.name == "HQ"]
        if not opp_units: # Check for Rout
            return self.currentPlayer
        if self.board.HQCapped != (0, False): # Check for HQ Capture
            return self.board.HQCapped[0] * -1
        if not hqCoords: # Check for total lab captures on maps with no HQs
            labCoords = [pos for pos, b in self.board.buildings.items() if b.name == "Lab"]
            # if current player has zero labs, they lose
            myLabs = [c for c in labCoords if self.board.buildings[c].owner == self.currentPlayer]
            if not myLabs:
                return opp
        return self.checkDominationVictory() # Check for domination victory
    
    def checkDominationVictory(self):
        """
        Returns the winning player (1 or -1) if they own ≥75% of all properties,
        else returns None.
        """
        buildings = self.board.buildings  # dict of (x,y)→Building
        total = len(buildings)
        if total == 0:
            return None

        # Count ownership
        counts = {1: 0, -1: 0}
        for b in buildings.values():
            if b.owner in counts:
                counts[b.owner] += 1

        # Check if any player has ≥75%
        for player, cnt in counts.items():
            if cnt / total >= 0.75:
                return player
        return None