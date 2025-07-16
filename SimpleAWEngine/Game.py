# from SimpleAWEngine.Board import Board
# from SimpleAWEngine.Unit import Unit, unitTypes
# from SimpleAWEngine.CO import CO, COs, POWERS_LOOKUP
from .Board import Board
from .Unit import Unit, unitTypes
from .CO import CO
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
        self.player1CO = player1CO
        self.player2CO = player2CO
        self.weather = "CLEAR"
        self.weatherTimer = 0
        CO.parsePowers()
        if self.player1CO == self.player2CO:
            print("COs identical, copying")
            self.player2CO = CO.copyCO(self.player1CO)
            print(f"Player1: {self.player1CO}, Player2: {self.player2CO}")
        self.player1CO.setPlayer(1)
        self.player2CO.setPlayer(-1)
        self.player1CO.resetPowers(self)
        self.player2CO.resetPowers(self)


    def getCO(self, player):
        if player == 1: return self.player1CO
        else: return self.player2CO

    def collectIncome(self):
        # sum city/base income owned
        income = 0
        for (x,y), b in self.board.buildings.items():
            if b.owner == self.currentPlayer and b.name in ("City","Base","Aiport","Harbor","HQ"):
                if self.getCO(self.currentPlayer).name == "Sasha":
                    income += 1100 
                else:
                    income += 1000
        self.funds[self.currentPlayer] += income

    def setWeather(self, weather):
        self.weather = weather
        self.weatherTimer = 2

    def weatherEffects(self):
        print(f"Weather: {self.weather}")
        if self.weather == "RAIN" and self.getCO(self.currentPlayer).name != "Drake" and self.getCO(self.currentPlayer).name != "Olaf":
            for y in range(self.board.height):
                for x in range(self.board.width):
                    terrain = self.board.getTerrain(x, y)
                    if terrain.name == "Forest" or terrain.name == "Plains":
                        terrain.treadMoveCost += 1
                        terrain.tireMoveCost += 1
            return True
        if (self.weather == "SNOW" and self.getCO(self.currentPlayer).name != "Olaf") or ((self.weather == "RAIN" and self.getCO(self.currentPlayer).name == "Olaf")):
            for y in range(self.board.height):
                for x in range(self.board.width):
                    terrain = self.board.getTerrain(x, y)
                    match terrain.name:
                        case "Plains":
                            terrain.infMoveCost *= 2
                            terrain.treadMoveCost += 1
                            terrain.tireMoveCost += 1
                        case "Forest":
                            terrain.infMoveCost *= 2
                        case "Mountain":
                            terrain.infMoveCost *= 2
                            terrain.mecMoveCost *= 2
                        case "Sea":
                            terrain.seaMoveCost *= 2
                            terrain.landerMoveCost *= 2
                        case "Harbor":
                            terrain.seaMoveCost *= 2
                            terrain.landerMoveCost *= 2
                    terrain.airMoveCost *= 2
            return True
        
    def resetWeather(self):
        if self.weather == "RAIN": #and self.getCO(self.currentPlayer).name != "Drake" and self.getCO(self.currentPlayer).name != "Olaf":
            for y in range(self.board.height):
                for x in range(self.board.width):
                    terrain = self.board.getTerrain(x, y)
                    if terrain.name == "Forest" or terrain.name == "Plains":
                        terrain.treadMoveCost -= 1
                        terrain.tireMoveCost -= 1
        if self.weather == "SNOW": # and self.getCO(self.currentPlayer).name != "Olaf") or ((self.weather == "RAIN" and self.getCO(self.currentPlayer).name == "Olaf")):
            for y in range(self.board.height):
                for x in range(self.board.width):
                    terrain = self.board.getTerrain(x, y)
                    match terrain.name:
                        case "Plains":
                            terrain.infMoveCost = int(terrain.infMoveCost * 0.5)
                            terrain.treadMoveCost -= 1
                            terrain.tireMoveCost -= 1
                        case "Forest":
                            terrain.infMoveCost = int(terrain.infMoveCost * 0.5)
                        case "Mountain":
                            terrain.infMoveCost = int(terrain.infMoveCost * 0.5)
                            terrain.mecMoveCost = int(terrain.mecMoveCost * 0.5)
                        case "Sea":
                            terrain.seaMoveCost = int(terrain.seaMoveCost * 0.5)
                            terrain.landerMoveCost = int(terrain.landerMoveCost * 0.5)
                        case "Harbor":
                            terrain.seaMoveCost = int(terrain.seaMoveCost * 0.5)
                            terrain.landerMoveCost = int(terrain.landerMoveCost * 0.5)
                    terrain.airMoveCost = int(terrain.airMoveCost * 0.5)


    def playTurn(self, inputType=0, FOW=False):
        self.collectIncome()
        weatherChanged = False
        if self.weather != "CLEAR":
            weatherChanged = self.weatherEffects()
        if self.getCO(self.currentPlayer).powerStage != 0:
            self.getCO(self.currentPlayer).resetPowers(self)
        # Build an initial queue of your units
        actionQueue = deque(
            u for u in self.board.units.values()
            if u.owner == self.currentPlayer and u.disabled == False
        )

        myUnits = [u for u in self.board.units.values()
                  if u.owner == self.currentPlayer]
        
        for unit in myUnits:
            if self.getCO(self.currentPlayer).name == "Rachel":
                self.resupplyCheck(unit, modifier = 1)
            else:
                self.resupplyCheck(unit)
            if unit.unitType.stealthable and unit.unitType.isStealthed:
                if self.getCO(self.currentPlayer).name == "Eagle":
                    unit.unitType.fuel -= unit.unitType.stealthBurn + 2
                else:
                    unit.unitType.fuel -= unit.unitType.stealthBurn
            elif unit.unitType.fuelBurn != 0:
                if self.getCO(self.currentPlayer).name == "Eagle":
                    unit.unitType.fuel -= unit.unitType.fuelBurn + 2
                else:
                    unit.unitType.fuel -= unit.unitType.fuelBurn
        
        # Track which units have been explicitly "ended"
        done = set()

        while actionQueue:
            unit = actionQueue.popleft()
            if self.getCO(self.currentPlayer).copAvailable() and self.getCO(self.currentPlayer).powerStage == 0:
                choice = input("Activate COP? y/n: ")
                if choice == "y": 
                    self.getCO(self.currentPlayer).activate_co(self) 
                    if self.getCO(self.currentPlayer).name == "Sensei":
                        myUnits = [u for u in self.board.units.values()
                                    if u.owner == self.currentPlayer]
                        for indivUnit in myUnits:
                            if indivUnit.unitType.unitName == "INF" and indivUnit.health == 90 and indivUnit not in actionQueue:
                                actionQueue.append(indivUnit)
            
            if self.getCO(self.currentPlayer).scopAvailable() and self.getCO(self.currentPlayer).powerStage == 0:
                choice = input("Activate SCOP? y/n: ")
                if choice == "y": 
                    self.getCO(self.currentPlayer).activate_super(self)
                    if self.getCO(self.currentPlayer).name == "Eagle":
                        for indivUnit in myUnits:
                            if indivUnit not in actionQueue: actionQueue.append(indivUnit)
                    elif self.getCO(self.currentPlayer).name == "Sensei":
                        myUnits = [u for u in self.board.units.values()
                                    if u.owner == self.currentPlayer]
                        for indivUnit in myUnits:
                            if indivUnit.unitType.unitName == "MEC" and indivUnit.health == 90 and indivUnit not in actionQueue:
                                actionQueue.append(indivUnit)

            # if unit was marked done, skip it
            if unit in done:
                continue

            # Show options, etc… like in your manual‐input branch
            moves, costs = self.board.get_legal_moves(unit)
            #print(self.board.render(self.currentPlayer))
            print(f"Unit: {unit} MP={unit.movement} Fuel={unit.unitType.fuel}")
            for i, dest in enumerate(moves):
                print(f"{i}: → {dest} (cost {costs[dest]})")
            print(f"Actions: move, skip, unload, capture, attack, stealth={unit.unitType.stealthable}, end")
            action = input("Action? ").strip().lower()
            print(action)
            match action:
                case "move":
                    idx = input("Provide move index. \"wait\" To wait in place: ")
                    print(idx != 'wait')
                    if idx != 'wait': dest = moves[int(idx)]
                    else: dest = (unit.x, unit.y)
                    self.board.moveUnit(unit.x, unit.y, *dest, moves, costs, self)
                    if (unit.x, unit.y) in self.board.units: actionQueue.appendleft(unit)

                # _do not_ mark unit done—maybe you want to load/unload next
                # action_queue.appendleft(unit)  # optionally replay immediately

                # case "join":
                #     unitToJoin = self.board.units.get((unit.x, unit.y))
                #     unit.joinUnits(unitToJoin, self)
                #     self.board.units[(unit.x, unit.y)].disable()
                

                # case "load":
                #     # only valid if stacked on a transport
                #     transport = self.board.units.get((unit.x, unit.y))
                #     if transport and transport.unitType.transportCapacity > 0:
                #         self.board.loadUnit(transport, unit)
                #         print(f"Loaded into {transport}")
                #         # Re-enqueue the transport so you can then unload it:
                #         actionQueue.appendleft(transport)
                #     else:
                #         print("No transport here.")

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
                        unit.capture(self.board)
                    else:
                        print("Cannot capture here.")

                case "attack":
                    enemies = self.board.get_attack_targets(unit)
                    for i, e in enumerate(enemies):
                        print(f"{i}: {e}")
                    idx = int(input("Enemy index: "))
                    if self.getCO(self.currentPlayer).name == "Sasha" and self.getCO(self.currentPlayer).powerStage == 2:
                        fundsToAdd = unit.attack(enemies[idx], self, self.getCO(unit.owner).luckLowerBound, self.getCO(unit.owner).luckUpperBound)
                        if fundsToAdd is not None:
                            self.funds[self.currentPlayer] += 0.50 * fundsToAdd
                    else:
                        unit.attack(enemies[idx], self, self.getCO(unit.owner).luckLowerBound, self.getCO(unit.owner).luckUpperBound)

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
                case "skip":
                    actionQueue.append(unit)
                
                case _:
                    print("Unknown action.")
                    # re-enqueue so they can try again
                    actionQueue.appendleft(unit)

        # After exhausting the queue, do your end_of_turn(), switch player, etc.
        self.productionStep(inputType)
        self.endTurn()
        if self.weather != "CLEAR" and weatherChanged:
            self.resetWeather()
        if self.weatherTimer != 0: 
            self.weatherTimer -= 1
            if self.weatherTimer == 0:
                self.weather = "CLEAR"
        self.currentPlayer *= -1

    def productionStep(self, inputType, unitCode=None):
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
                else:
                    if self.funds[self.currentPlayer] >= unitTypes.get(unitCode).value:
                        if ((unitTypes.get(unitCode).moveType == "Sea" and terrain.name == "Harbor") or # Naval unit at harbor
                                (unitTypes.get(unitCode).moveType == "Air" and terrain.name == "Airport") or  # Air unit at airport
                                ((unitTypes.get(unitCode).moveType != "Sea" and unitTypes.get(unitCode).moveType != "Air") and terrain.name == "Base")): # Land unit at base
                            
                            self.funds[self.currentPlayer] -= unitTypes.get(unitCode).value
                            newUnit = Unit(self.currentPlayer,unitTypes.get(unitCode))
                            self.board.addUnit(newUnit, x, y, False)




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
                    unit.resupply(self, 20 + (10 * modifier))
            case "AIR":
                if at.name == "Airport":
                    unit.resupply(self, 20 + (10 * modifier))
            case _:
                if at.name == "Base" or at.name == "City":
                    unit.resupply(self, 20 + (10 * modifier))

    def endTurn(self):
        for unit in list(self.board.units.values()):
            if unit.owner == self.currentPlayer:
                unit.movement = unit.unitType.maxMovement
                unit.attackAvailable = True
                if unit.disabled: unit.disabled = False
            
        self.currentPlayer *= -1
        ## FOG UPDATE GOES HERE WHEN IMPLEMENTED
        # self.board.updateVisibility(self.currentPlayer)
        #print("Turn over")
        winner = self.checkVictory()
        if winner is not None:
            #print(f"Player {winner} wins!")
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
        if len(hqCoords) == 0: # Check for total lab captures on maps with no HQs
            labCoords = [pos for pos, b in self.board.buildings.items() if b.name == "Lab"]
            # if current player has zero labs, they lose
            myLabs = [c for c in labCoords if self.board.buildings[c].owner == self.currentPlayer]
            if len(myLabs) == 0:
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