# from SimpleAWEngine.Unit import Unit
from Unit import Unit
import heapq
import copy
from typing import List, Tuple, Dict, Any
from pprint import pprint

class TerrainType:
    def __init__(self, name, infMoveCost, mecMoveCost, treadMoveCost, tireMoveCost, airMoveCost, seaMoveCost, landerMoveCost, prnMoveCost, capturable, defenseBonus, produces = None, owner=None):
        self.name          = name            # e.g. 'Plains', 'Forest'
        self.infMoveCost     = infMoveCost       # MP cost to enter
        self.mecMoveCost     = mecMoveCost
        self.treadMoveCost     = treadMoveCost
        self.tireMoveCost     = tireMoveCost
        self.airMoveCost     = airMoveCost
        self.seaMoveCost     = seaMoveCost
        self.landerMoveCost     = landerMoveCost
        self.prnMoveCost     = prnMoveCost
        self.capturable = capturable
        self.produces = produces
        if (self.capturable):
            self.capturePoints = 20
        self.defenseBonus = defenseBonus   # % damage reduction
        self.owner = owner

    def canProduce(self):
        return self.produces is not None

    def getTerrainName(self):
        return self.name
    
    def __repr__(self):
        return f"{self.name}, P{self.owner}"

# 10 represents an illegal move. The unit can't move there.
terrain_types = {
    'P': TerrainType('Plains', 1,1,1,2,1,10,10,10, False,defenseBonus=1),
    'F': TerrainType('Forest', 1,1,2,3,1,10,10,10, False,defenseBonus=2),
    'M': TerrainType('Mountain', 2,1,10,10,1,10,10,10, False,defenseBonus=4),
    'RV': TerrainType('River', 2,1,10,10,1,10,10,10, False,defenseBonus=0),
    'R': TerrainType('Road', 1,1,1,1,1,10,10,10, False,defenseBonus=0),
    'B': TerrainType('Bridge', 1,1,1,1,1,10,10,10, False,defenseBonus=0),
    'S': TerrainType('Sea', 10,10,10,10,1,1,1,10, False,defenseBonus=0),
    'SH': TerrainType('Shoal', 1,1,1,1,1,10,10,10, False,defenseBonus=0),
    'RE': TerrainType('Reef', 10,10,10,10,1,2,2,10, False,defenseBonus=1),  
    'C': TerrainType('City', 1,1,1,1,1,10,10,10, True,defenseBonus=3),
    'B': TerrainType('Base', 1,1,1,1,1,10,10,1, True,defenseBonus=3, produces=True),
    'A': TerrainType('Airport', 1,1,1,1,1,10,10,10, True,defenseBonus=3, produces=True), 
    'H': TerrainType('Harbor', 1,1,1,1,1,1,1,10, True,defenseBonus=3, produces=True),
    'HQ': TerrainType('HQ', 1,1,1,1,1,10,10,10, True,defenseBonus=4),
    'PI': TerrainType('Pipe', 10,10,10,10,10,10,10,1, False,defenseBonus=0),
    'MS': TerrainType('Missile Silo', 1,1,1,1,1,10,10,10, False,defenseBonus=3),
    'CM': TerrainType('Com Tower', 1,1,1,1,1,10,10,10, True,defenseBonus=3),
    'L': TerrainType('Lab', 1,1,1,1,1,10,10,10, True,defenseBonus=3),
  
}

class Board:
    def __init__(self, terrainCodes, terrainTypes, FOW=False):
        """
        terrain_codes: List[List[str]]  2D array of terrain keys, e.g. [['P','P','F'], ['M','P','P'], …]
        terrain_types: Dict[str,TerrainType]  maps code → TerrainType instance
        """
        self.height = len(terrainCodes)
        self.width  = len(terrainCodes[0]) if self.height>0 else 0
        self.fog = FOW
        self.flatMoveCost = False

        # Build a 2D grid of TerrainType objects
        # self.grid = [
        #     [terrainTypes[code] for code in row]
        #     for row in terrainCodes
        # ]
        self.grid = []
        for row in terrainCodes:
            grid_row = []
            for code, owner in row:
                terrainCell = terrainTypes[code]
                cell = copy.copy(terrainCell)
                cell.owner = owner
                grid_row.append(cell)
            self.grid.append(grid_row)

        if self.fog:
            self.visibility = {
                1: [[False]*self.width  for _ in range(self.height)],  # Player 1’s fog map
                -1: [[False]*self.width  for _ in range(self.height)],  # Player 2
            }
        else:
            self.visibility = {
                1: [[True]*self.width  for _ in range(self.height)],  # Player 1’s fog map
                -1: [[True]*self.width  for _ in range(self.height)],  # Player 2
            }
        # Units placed on board: (x,y) → Unit
        self.units = {}
        self.HQCapped = (0, False)

        # Tracking buildings for the Domination victory
        self.buildings: Dict[Tuple[int,int], Any] = {}
        for y in range(self.height):
            for x in range(self.width):
                cell = self.grid[y][x]
                # Only cells that have capturePoints are capturable buildings
                if hasattr(cell, "capturePoints") and (cell.name != "Com Tower" or cell.name != "Lab"):
                    # map from (x,y) to the very same cell object
                    self.buildings[(x, y)] = cell

    def getTerrain(self, x, y):
        return self.grid[y][x]
    
    def getOwnership(self, x, y):
        return self.grid[y][x].owner

    def getMoveCost(self, x, y, unitType):
        if self.flatMoveCost == True:
            return 1
        else:
            match unitType:
                case "INF":
                    return self.grid[y][x].infMoveCost
                case "MEC":
                    return self.grid[y][x].mecMoveCost
                case "TIRE":
                    return self.grid[y][x].tireMoveCost
                case "TREAD":
                    return self.grid[y][x].treadMoveCost
                case "AIR":
                    return self.grid[y][x].airMoveCost
                case "SEA":
                    return self.grid[y][x].seaMoveCost
                case "LANDER":
                    return self.grid[y][x].landerMoveCost
                case "PIPE":
                    return self.grid[y][x].prnMoveCost

    def getDefenseBonus(self, unit, x, y, game):
        if game.getCO(unit.owner).name == "Lash" and game.getCO(unit.owner).powerStage == 2: 
            return self.grid[y][x].defenseBonus * 2
        else:
            return self.grid[y][x].defenseBonus
    

    def unitIsVisible(self, unit, viewer: int) -> bool:
        # 1) If it’s the same side, always show your own troops
        if unit.owner == viewer:
            return True

        # 2) If fog is on, but tile isn’t visible under fog, hide everything
        if self.fog and not self.visibility[viewer][unit.y][unit.x]:
            return False

        # 3) If unit isn’t stealthed, you see it
        if not unit.unitType.isStealthed:
            return True

        # 4) Stealthed: only see if you have a friendly unit adjacent
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
            x2, y2 = unit.x+dx, unit.y+dy
            if (x2,y2) in self.units and self.units[(x2,y2)].owner == viewer:
                return True

        return False
    
    def updateVisibility(self, player):
        """
        1) Standard fog-of-war: reveal all tiles within vision of player’s non-stealthed units.
        2) Adjacency override: reveal any stealthed enemy unit only if one of player’s units
           is on an adjacent square, even if it’s outside vision/fog.
        """
        # reset or keep previous visibility depending on your rules…
        # (here we _add_ visibility each turn)
        if not self.fog:
            # If fog is off, we don't need a visibility map at all.
            # Optionally, you could fill visibility[player] with all True,
            # but since unit_is_visible ignores fog when fog_enabled==False,
            # you can just return here.
            return
        
        self.visibility[player] = [
            [False]*self.width
            for _ in range(self.height)
        ]
        
        # 1) Reveal by vision
        for unit in self.units.values():
            if unit.owner != player:
                continue
            if unit.unitType.isStealthed:
                continue  # stealthed don’t reveal by vision
            ux, uy = unit.x, unit.y
            for dy in range(-unit.unitType.vision, unit.unitType.vision+1):
                for dx in range(-unit.unitType.vision, unit.unitType.vision+1):
                    x, y = ux+dx, uy+dy
                    if 0 <= x < self.width and 0 <= y < self.height:
                        self.visibility[player][y][x] = True

        # 2) Reveal stealthed enemy units by adjacency only
        for unit in self.units.values():
            if unit.owner == player:
                continue
            if not unit.unitType.isStealthed:
                continue
            ux, uy = unit.x, unit.y
            # check the four adjacent squares for an enemy unit
            for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                x2, y2 = ux+dx, uy+dy
                if (x2, y2) in self.units and self.units[(x2, y2)].owner == player:
                    # adjacency gives visibility to the stealthed unit’s tile
                    self.visibility[player][uy][ux] = True
                    break

    def addUnit(self, unit: Unit, x : int, y : int, moveFirstTurn = True):
        if (x,y) in self.units:
            raise ValueError(f"Square {(x,y)} already occupied")
        unit.x, unit.y = x, y
        self.units[(x,y)] = unit
        if not moveFirstTurn:
            unit.movement = 0
            unit.attackAvailable = False
    
    def setUnitHP(self, x : int, y : int, amount : int):
        if (x,y) not in self.units:
            return
        self.units[(x,y)].health = amount


    def removeUnit(self, unit: Unit, x: int, y: int):
        if (x,y) not in self.units:
            raise ValueError(f"Square {(x,y)} already empty") 
        self.units.pop((x,y))

    def moveUnit(self, fromX: int, fromY: int, toX: int, toY: int, legalMoves, moveCosts, game):
        if (fromX, fromY) not in self.units:
            raise ValueError(f"No unit at starting point {(fromX, fromY)}")
        if (toX, toY) in self.units:
            unitAtTile = self.units[(toX, toY)]
            unit = self.units[(fromX, fromY)]
            # Handles joining and transport loading
            if unit.unitType.unitName == unitAtTile.unitType.unitName:
                unit.joinUnits(unitAtTile, game)
            if unitAtTile.unitType.transportsUnits and unitAtTile.unitType.transportCapacity > 0:
                self.loadUnit(unitAtTile, unit)
            return            

            #raise ValueError(f"Destination occupied at {(toX, toY)}")
        
        unit = self.units.pop((fromX, fromY))
        #legalMoves, moveCosts = self.get_legal_moves(unit)
        print(f"Legal Moves: {legalMoves}")
        moveCost = moveCosts[(toX, toY)]
        if (toX, toY) not in legalMoves or unit.unitType.fuel < moveCost:
            raise ValueError(f"Illegal move to {(toX, toY)}")
        unit.movement = 0
        unit.unitType.fuel -= moveCost
        unit.x, unit.y = toX, toY
        self.units[(toX, toY)] = unit

        if unit.unitType.transportsUnits:
            for sub in unit.loaded:
                sub.x, sub.y = toX, toY

    def loadUnit(self, transport: Unit, unit: Unit):
        # check capacity
        if len(transport.loaded) >= transport.unitType.transportCapacity:
            raise ValueError("Transport full")
        
        # if (unit.x, unit.y) != (transport.x, transport.y):
        #     raise ValueError("Unit must move onto the transport tile to load")
        
        if self.canLoad(transport, unit):
            # remove from board
            del self.units[(unit.x, unit.y)]
            unit.movement = 0
            unit.attackAvailable = 0
            transport.loaded.append(unit)

    def canLoad(self, transport, unit):
        if transport.unitType.unitName != "LAN" and (unit.unitType.unitName != "INF" and unit.unitType.unitName != "MEC"):
            print(f"This transport {transport.unitType.unitName} is unable to transport {unit.unitType.unitName}!")
            return False
        elif transport.unitType.unitName == "LAN" and (unit.unitType.moveType == "AIR" or unit.unitType.moveType == "SEA" or unit.unitType.moveType == "LANDER" or unit.unitType.moveType == "PIPE"):
            print("This lander can only transport ground units!")
            return False
        elif transport.unitType.unitName == "CRS" and (unit.unitType.unitName != "TCP" or unit.unitType.unitName != "BCP"):
            print("This cruiser can only transport copter units!")
            return False
        elif transport.unitType.unitName == "CAR" and (unit.unitType.unitName != "STE" or unit.unitType.unitName != "FIG" or unit.unitType.unitName != "BOM"):
            print("This carrier can only transport plane units!")
            return False
        return True
        

    def getAdjacentPositions(self, unit: Unit, returnEmptyFull: int) -> List[Tuple[int,int]]:
        """
        Return all adjacent squares (x,y) next to this unit.
        """
        spots = []
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
            x, y = unit.x + dx, unit.y + dy
            if 0 <= x < self.width and 0 <= y < self.height:
                if returnEmptyFull == 0: # 0 means return all empty tiles
                    if (x, y) not in self.units:
                        spots.append((x, y))
                elif returnEmptyFull == 1: # 1 means return all tiles
                    spots.append((x,y))
                elif returnEmptyFull == 2: # 2 means return all occupied tiles
                    if (x, y) in self.units:
                        spots.append((x, y))

        return spots
    
    def unloadUnit(self, transport: Unit, x: int, y: int):
        # pick a unit to unload (pop last for simplicity)
        unit = transport.loaded.pop()
        # place it on the board
        unit.x, unit.y = x, y
        # check adjacency
        dx,dy = abs(transport.x - x), abs(transport.y - y)
        if dx+dy != 1:
            raise ValueError("Must unload next to transport")
        self.units[(x, y)] = unit
        # boosting should be implemented properly since the transport's
        # turn never ends.


    def get_legal_moves(self, unit: Unit) -> Tuple[List[Tuple[int,int]], Dict[Tuple[int,int],int]]:
        """
        Returns a list of (x,y) coordinates the unit can move to,
        based on its remaining movement points and terrain costs.
        """
        print(f"Board Dims {self.width}, {self.height}")
        start = (unit.x, unit.y)
        max_mp = unit.movement

        # Priority queue of (cost, (x,y))
        frontier = [(0, start)]
            # Track best cost so far to each cell
        cost_so_far = {start: 0}

        legal_moves = [start]

        while frontier:
            cost, (x, y) = heapq.heappop(frontier)

            # Record this cell (skip start if you prefer)
            #if (x,y) != start:
            legal_moves.append((x, y))

            # Explore neighbors
            for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                nx, ny = x + dx, y + dy
                # Check bounds
                #print(f"Checking neighbor {(nx,ny)}")
                if not (0 <= nx < self.width and 0 <= ny < self.height):
                   #print(f"Neighbor {(nx, ny)} out of bounds")
                   continue
                # Disallow moving onto occupied squares?
                if (nx, ny) in self.units and self.units[(nx, ny)].owner != unit.owner:
                   #print(f"Neighbor {nx, ny} contains enemy unit")
                   continue

                move_cost = self.getMoveCost(nx, ny, unit.unitType.moveType)
                #print(f"Move Type: {unit.moveType}, Type: {self.getTerrain(nx, ny)}, cost: {move_cost}")
                new_cost = cost + move_cost

                if new_cost > max_mp:
                    continue

                # If we found a cheaper path
                #print(f"Cost So Far: {cost_so_far} at tile {nx, ny}")
                if (nx, ny) not in cost_so_far or new_cost < cost_so_far[(nx, ny)]:
                    cost_so_far[(nx, ny)] = new_cost
                    heapq.heappush(frontier, (new_cost, (nx, ny)))
        #legal_moves = [pos for pos in legal_moves if pos not in self.units]
        legal_moves = []
        for pos in cost_so_far:
            if pos == start:
                continue
            if pos in self.units:
                other = self.units[pos]
                # only allow if it’s your own transport
                if other.owner == unit.owner and other.unitType.transportCapacity > 0 and self.canLoad(other, unit):
                    legal_moves.append(pos)
                # allow the same unit types to stack for joining
                if other.unitType.unitName == unit.unitType.unitName:
                    legal_moves.append(pos)

            else:
                legal_moves.append(pos)
        return legal_moves, cost_so_far
    
    def captureTargets(self, unit):
        at = self.grid[unit.y][unit.x]
       # print(at.name in {"City", "Base", "Airport", "Harbor", "HQ", "Com Tower", "Lab"})
       # print(unit.unitType.unitName in {"INF", "MEC"})
       # print(at.owner != unit.owner)
        if at.name in {"City", "Base", "Airport", "Harbor", "HQ", "Com Tower", "Lab"} and unit.unitType.unitName in {"INF", "MEC"} and at.owner != unit.owner:
            return True
        return False
    
    def get_attack_targets(self, unit):
        """
        Returns list of enemy units adjacent to this unit.
        """
        targets = []
        # Direct check
        if unit.unitType.minRange == 0:
            for dx,dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                x2, y2 = unit.x+dx, unit.y+dy
                if (x2,y2) in self.units:
                    other = self.units[(x2,y2)]
                    if other.owner != unit.owner:
                        targets.append(other)
        else: # Indirect check
            start = (unit.x, unit.y)
            frontier = [(0, start)]
            distanceSearched = 0
            while frontier:
                dist, (x, y) = heapq.heappop(frontier)
                # Explore neighbors
                for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                    nx, ny = x + dx, y + dy
                    distanceSearched = dist + 1
                    if distanceSearched > unit.unitType.maxRange:
                        continue
                    heapq.heappush(frontier, (distanceSearched, (nx, ny)))
                    if (nx, ny) not in self.units or (nx, ny) == start:
                        continue
                    distanceX = abs(unit.x - nx)
                    distanceY = abs(unit.y - ny)
                    if (unit.unitType.minRange < distanceX + distanceY < unit.unitType.maxRange and self.units[(nx, ny)].owner != unit.owner and self.units[(nx,ny)] not in targets):
                        targets.append(self.units[(nx, ny)])
        return targets
    
    def reduceCapturePoints(self, unit):
        self.grid[unit.y][unit.x].capturePoints -= int(unit.health / 10 * (1 + unit.unitType.captureBonus))
        remainingPoints = self.grid[unit.y][unit.x].capturePoints
        if (remainingPoints <= 0):
            if self.grid[unit.y][unit.x].name == "HQ":
                print(f"Player {-1*unit.owner}'s HQ has been captured!")
                self.HQCapped = (-1*unit.owner, True)
            else:
                print(f"Building at {(unit.x, unit.y)} captured!")
            self.grid[unit.y][unit.x].owner = unit.owner
    
    def globalHPChange(self, owner, amount):
        myUnits = [u for u in self.units.values()
                  if u.owner == owner]
        for unit in myUnits:
            if unit.health - (amount * 10) <= 0: 
                unit.health = 1
            else:
                unit.health += amount * 10
            if unit.health > 100: 
                unit.health = 100
            

    def globalValueChange(self, owner, discount):
        myUnits = [u for u in self.units.values()
                  if u.owner == owner]
        for unit in myUnits:
            unit.unitType.value *= discount
            unit.unitType.value = int(unit.unitType.value)


    def globalMovementChange(self, owner, amount):
        """
        This function exists for when the catch-all Unit Modifier can't handle a CO's power
        AKA The Block Rock Exception, because THIS LITERALLY ONLY APPLIES TO JAKE
        Everybody else plays nice and boosts the stats of the same unit type every time.
        All except for Jake. JAKE, GO FUCK YOURSELF
        """
        myUnits = [u for u in self.units.values()
                  if u.owner == owner]
        for unit in myUnits:
            moveType = unit.unitType.moveType
            if moveType == "TREAD" or moveType == "TIRE":
                if unit.movement != 0: unit.movement += amount

    def globalUnitModifier(self, owner, modifiers):
        if len(modifiers) == 1: return
        myUnits = [u for u in self.units.values()
                  if u.owner == owner]

        attackAmount = int(modifiers[0].strip("("))
        moveAmount = int(modifiers[1])
        defenseAmount = int(modifiers[2])
        captureModifier = None
        indirBonus = None
        type = modifiers[3].strip(")").strip("'")
        print(f"MODS: {modifiers}")
        if len(modifiers) == 5 and type == "INF": captureModifier = float(modifiers[4].strip(")"))
        elif len(modifiers) == 5 and type == "INDIRECT": indirBonus = int(modifiers[4].strip(")"))
        #print(f"{type} == 'DIRECT' {type == 'DIRECT'}")
        print(repr(type), repr('DIRECT'))
        match type:
            case 'INF':
                for unit in myUnits: 
                    moveType = unit.unitType.moveType
                    if moveType == "INF" or moveType == "MEC": 
                        self.setHelper(attackAmount, moveAmount, defenseAmount, unit)
                        if captureModifier is not None: unit.unitType.captureBonus = captureModifier
            case 'DIRECT': # Direct always excludes footsoldiers
                print(myUnits)
                for unit in myUnits:
                    moveType = unit.unitType.moveType
                    if unit.unitType.minRange == 0 and moveType != "INF" and moveType != "MEC": self.setHelper(attackAmount, moveAmount, defenseAmount, unit)
            case 'INDIRECT':
                for unit in myUnits:
                    if unit.unitType.minRange != 0:
                        self.setHelper(attackAmount, moveAmount, defenseAmount, unit)
                        if indirBonus is not None: unit.unitType.maxRange = unit.unitType.staticMax + indirBonus
            case 'GROUND':
                for unit in myUnits:
                    moveType = unit.unitType.moveType
                    if moveType == "TREAD" or moveType == "TIRE": self.setHelper(attackAmount, moveAmount, defenseAmount, unit)
            case 'AIR':
                for unit in myUnits:
                    if unit.unitType.moveType == "AIR": self.setHelper(attackAmount, moveAmount, defenseAmount, unit)
            case 'SEA':
                for unit in myUnits:
                    if unit.unitType.moveType == "SEA": self.setHelper(attackAmount, moveAmount, defenseAmount, unit)
            case 'COPTER':
                for unit in myUnits:
                    if unit.unitType.unitName == "BCP": self.setHelper(attackAmount, moveAmount, defenseAmount, unit)
            case 'TRANSPORT':
                for unit in myUnits:
                    if unit.unitType.transportsUnits == True and unit.movement != 0: unit.movement += moveAmount 
            # case 'PLAINS': # Literally just Jake. These might not be necessary.
            #     for unit in myUnits:
            #         if self.getTerrain(unit.x, unit.y).name == "Plains": self.setHelper(attackAmount, moveAmount, defenseAmount, unit)
            # case 'PROPERTIES': # Just for Kindle
            #     for unit in myUnits:
            #         terName = self.getTerrain(unit.x, unit.y).name
            #         if terName == "City" or terName == "Base" or terName == "Harbor" or terName == "HQ" or terName == "Airport" or terName == "Com Tower":
            #             self.setHelper(attackAmount, moveAmount, defenseAmount, unit)
            # case 'ROADS': # Just for Koal
            #     for unit in myUnits:
            #         terName = self.getTerrain(unit.x, unit.y).name
            #         if terName == "Road" or terName == "Bridge":
            #             self.setHelper(attackAmount, moveAmount, defenseAmount, unit)
            case 'ALL':
                for unit in myUnits:
                    self.setHelper(attackAmount, moveAmount, defenseAmount, unit)

    def setHelper(self, attackAmount, moveAmount, defenseAmount, unit):
        if attackAmount != 0: unit.attackModifier = attackAmount
        if defenseAmount!= 0: unit.defenseModifier = defenseAmount
        if unit.movement != 0: 
            unit.movement += moveAmount

            

                
    
    def __repr__(self):
        return self.render(player=1)

    def render(self, player: int) -> str:
        lines = []
        for y in range(self.height):
            cells = []
            for x in range(self.width):
                if (x,y) in self.units and self.unitIsVisible(self.units[(x,y)], player):
                    u = self.units[(x,y)]
                    sym = f"{u.unitType.unitName[:2]}{ '+' if u.owner==1 else '-' }"
                else:
                    terrain = self.grid[y][x]
                    sym = terrain.name[:2] + str(terrain.owner)
                cells.append(f"{sym:3}")
            lines.append(" ".join(cells))
        return "\n".join(lines)

# Game board
terrain_codes = [
    #      0      1      2      3      4      5      6       7
    [('A', 1), ('CM', -1), ('P', 0), ('F', 0), ('S', 0), ('S', 0), ('H', -1), ('HQ', -1)],
    [('P', 0), ('M', 0), ('P', 0), ('F', 0), ('SH', 0), ('S', 0), ('M', 0),  ('P', 0 )],
    [('P', 0), ('P', 0), ('P', 0), ('P', 0), ('P', 0), ('P', 0), ('P', 0),  ('B', -1)],
    [('C', 0), ('P', 0), ('P', 0), ('C', 0), ('C', 0), ('R', 0), ('R', 0),  ('R', 0 )],
    [('R', 0), ('R', 0), ('R', 0), ('C', 0), ('C', 0), ('P', 0), ('P', 0),  ('C', 0 )],
    [('B', 1), ('P', 0), ('P', 0), ('P', 0), ('P', 0), ('P', 0), ('P', 0),  ('P', 0 )],
    [('P', 0), ('M', 0), ('S', 0), ('SH',0), ('F', 0), ('P', 0), ('M', 0),  ('P', 0 )],
    [('HQ',1), ('H', 1), ('S', 0), ('S', 0), ('F', 0), ('P', 0), ('P', 0),  ('A', -1)]
]

#gameBoard = Board(terrain_codes, terrain_types, False)
#print(gameBoard.width, gameBoard.height)         # expect 8, 8
#print(gameBoard.getMoveCost(3,0, "TREAD"))         # cost for 'P'
#print(gameBoard.getDefenseBonus(1,1))     # bonus for 'M'