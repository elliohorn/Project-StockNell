import pytest
from collections import deque

# Assume the playTurn method is imported from your game module
from SimpleAWEngine.Game import Game
from SimpleAWEngine.Unit import UnitType, Unit, unitTypes
from SimpleAWEngine.Board import Board, terrain_types
from SimpleAWEngine.CO import CO, COs

# --- Dummy classes to isolate playTurn logic ---

class DummyBoard:
    def __init__(self):
        self.units = {}  # (x,y) -> unit
        self.width = 2
        self.height = 1

    def get_legal_moves(self, unit):
        # Always allow one move to (1,0) with cost 1
        return [(1, 0)], {(1, 0): 1}

    def render(self, player):
        # No-op render
        return ""

    def moveUnit(self, fx, fy, tx, ty, moves, costs):
        # perform the move
        unit = self.units.pop((fx, fy))
        unit.x, unit.y = tx, ty
        self.units[(tx, ty)] = unit

    def loadUnit(self, transport, unit):
        pass

    def get_unload_positions(self, transport):
        return []

    def unloadUnit(self, transport, x, y):
        pass

    def captureTargets(self, unit):
        return False

    def capture(self, unit):
        pass

    def get_attack_targets(self, unit):
        return []

class DummyUnitType:
    def __init__(self, moveType='INF', stealthable=False, isStealthed=False,
                 stealthBurn=0, fuelBurn=0):
        self.moveType = moveType
        self.stealthable = stealthable
        self.isStealthed = isStealthed
        self.stealthBurn = stealthBurn
        self.fuelBurn = fuelBurn
        self.fuel = 10  # default fuel

class DummyUnit:
    def __init__(self, x, y, owner, unitType):
        self.x = x
        self.y = y
        self.owner = owner
        self.unitType = unitType
        self.movement = 2

class DummyGame(Game):
    def __init__(self):
        # Bypass the real Game initialization
        self.currentPlayer = 1
        self.board = DummyBoard()
        self.player1CO = None
        self.player2CO = None
        # No-op production and turn-end
        self.productionStep = lambda inputType: None
        self.endTurn = lambda : None
        self.resupplyCheck = lambda unit: None

# --- Tests ---

def test_move_action(monkeypatch):
    game = DummyGame()
    # place one unit at (0,0)
    ut = DummyUnitType(stealthable=False)
    unit = DummyUnit(x=0, y=0, owner=1, unitType=ut)
    game.board.units = {(0, 0): unit}

    # Simulate input: move → choose index 0 → end
    inputs = iter(['move', '0', 'end'])
    monkeypatch.setattr('builtins.input', lambda prompt='': next(inputs))

    game.playTurn()

    # After playTurn, unit should have moved to (1,0)
    assert (1, 0) in game.board.units
    assert unit.x == 1 and unit.y == 0
    # currentPlayer should toggle
    assert game.currentPlayer == -1

def test_stealth_toggle(monkeypatch):
    game = DummyGame()
    # place one stealthable unit at (0,0)
    ut = DummyUnitType(stealthable=True, isStealthed=False)
    unit = DummyUnit(x=0, y=0, owner=1, unitType=ut)
    game.board.units = {(0, 0): unit}

    # Simulate input: stealth → end
    inputs = iter(['stealth', 'end'])
    monkeypatch.setattr('builtins.input', lambda prompt='': next(inputs))

    game.playTurn()

    # Unit should now be stealthed
    assert unit.unitType.isStealthed
    # currentPlayer should toggle
    assert game.currentPlayer == -1

def test_autoresupply(monkeypatch):
    terrain_codes = [[('C',1),('P',0)], [('P',0),('P',0)]]
    startingUnits = [(Unit(1,unitTypes.get('INF')), 0, 0)]
    unit = startingUnits[0][0]
    unit.unitType.ammo = 0
    unit.unitType.fuel = 0
    unit.health = 80
    game = Game(terrain_codes, terrain_types, player1CO=None, player2CO=None, startingUnits=startingUnits)

    inputs = iter(['end'])
    monkeypatch.setattr('builtins.input', lambda prompt='': next(inputs))

    game.playTurn()

    assert unit.unitType.ammo == unit.unitType.ammoMax and unit.unitType.fuel == unit.unitType.fuelMax and unit.health == 100
    
def test_manual_supply(monkeypatch):
    terrain_codes = [[('P',0),('P',0)], [('P',0),('P',0)], [('S',0),('P',0)]]
    startingUnits = [(Unit(1,unitTypes.get('INF')), 0, 0), 
                     (Unit(1,unitTypes.get('APC')), 1, 0),
                     (Unit(1,unitTypes.get('INF')), 1, 2),
                     (Unit(1,unitTypes.get('BLK')), 0, 2)]
    unit1 = startingUnits[0][0]
    unit2 = startingUnits[2][0]
    unit1.unitType.ammo = 0 
    unit2.unitType.ammo = 0
    unit1.unitType.fuel = 0 
    unit2.unitType.fuel = 0
    unit2.health = 90
    game = Game(terrain_codes, terrain_types, player1CO=None, player2CO=None, startingUnits=startingUnits)

    inputs = iter(['end', 'supply', 'end', 'supply', 0])
    monkeypatch.setattr('builtins.input', lambda prompt='': next(inputs))

    game.playTurn()

    assert unit1.unitType.ammo == unit1.unitType.ammoMax and unit1.unitType.fuel == unit1.unitType.fuelMax
    assert unit2.unitType.ammo == unit2.unitType.ammoMax and unit2.unitType.fuel == unit2.unitType.fuelMax and unit2.health == 100

def test_fuel_consumption(monkeypatch):
    terrain_codes = [[('P',0),('P',0)], [('P',0),('P',0)], [('S',0),('P',0)]]
    startingUnits = [(Unit(1,unitTypes.get('INF')), 0, 0), 
                     (Unit(1,unitTypes.get('BOM')), 1, 0),
                     (Unit(1,unitTypes.get('SUB')), 0, 2),
                     (Unit(-1,unitTypes.get('INF')), 1, 2)]
    game = Game(terrain_codes, terrain_types, player1CO=None, player2CO=None, startingUnits=startingUnits)

    inputs = iter(['move', 0, 'end', 'end', 'stealth', 'end', 'end', 'end', 'end'])
    monkeypatch.setattr('builtins.input', lambda prompt='': next(inputs))
    unit1 = startingUnits[0][0]
    unit2 = startingUnits[1][0]
    unit3 = startingUnits[2][0]
    game.playTurn()
    game.playTurn()
    game.playTurn()
    assert unit1.unitType.fuel == 98 and unit2.unitType.fuel == 89 and unit3.unitType.fuel == 54


@pytest.fixture
def simple_board():
    # Minimal 2×2 grid (terrain doesn’t matter for load/unload)
    terrain_codes = [[('P',0),('P',0)], [('P',0),('P',0)]]
    terrain_types = {'P': type('T', (), {'name':'Plains', 'move_cost':1, 'defense_bonus':0})}
    board = Board(terrain_codes, terrain_types)
    return board

@pytest.fixture
def transport_and_unit(simple_board):
    board = simple_board
    # Create a transport that can carry 1 unit
    ttype = unitTypes.get("APC")
    transport = Unit(1, ttype)
    transport.x, transport.y = (0,0)
    board.units = {(0,0): transport}
    # Create a soldier to load
    stype = unitTypes.get("INF")
    soldier = Unit(1, stype)
    soldier.x, soldier.y = (0,0)
    # place soldier onto transport tile (stacking allowed here for test)
    board.units[(0,0)] = transport  # the soldier isn't in board.units
    transport.loaded = []  # ensure no cargo yet
    return board, transport, soldier

def test_load_transports_unit(transport_and_unit):
    board, transport, soldier = transport_and_unit
    # call loadUnit: soldier is at same coords as transport
    board.loadUnit(transport, soldier)
    # transport should have soldier in its loaded list
    assert soldier in transport.loaded
    # soldier should no longer be in board.units
    assert all(soldier not in u.loaded if hasattr(u, 'loaded') else True for u in board.units.values())

def test_unload_places_and_boosts(transport_and_unit):
    board, transport, soldier = transport_and_unit
    stype = unitTypes.get("INF")
    soldier2 = Unit(1, stype)
    # pre-load
    transport.loaded = [soldier]
    transport.x, transport.y = (1,1)
    transport.movement = 3
    transport.fuel = 7
    # unload to an adjacent tile (1,0)
    board.unloadUnit(transport, 1, 0)
    # soldier should now be on the board at (1,0)
    soldier2.x, soldier2.y = (1,1)
    board.units[(1,1)] = soldier2
    board.loadUnit(transport, soldier2)
    board.unloadUnit(transport, 0, 1)
    assert (1,0) in board.units
    assert (0,1) in board.units
    # and soldier removed from transport.loaded
    assert soldier not in transport.loaded
    assert soldier2 not in transport.loaded

# COs Confirmed to be functioning correctly:
#

# COs Confirmed to have errors:
# 

def testCOs(monkeypatch):
    terrain_codes = [[('P',0),('P',0)], [('P',0),('P',0)], [('P',0),('P',0)], [('P',0),('P',0)], [('P',0),('P',0)]]
    startingUnits = [(Unit(1,unitTypes.get('INF')), 0, 0), 
                     (Unit(1,unitTypes.get('INF')), 1, 0),
                     (Unit(1,unitTypes.get('INF')), 0, 2), 
                     (Unit(1,unitTypes.get('INF')), 1, 2),
                     (Unit(1,unitTypes.get('TNK')), 0, 4),
                     (Unit(-1,unitTypes.get('TNK')), 1, 4)]
    game = Game(terrain_codes, terrain_types, player1CO=COs.get("Sami"), player2CO=COs.get("Max"), startingUnits=startingUnits)
    game.getCO(1).gainMeter(50000)
    game.getCO(-1).gainMeter(50000)
    inputs = iter(['n', 'n', 'attack', 0, # Unit 1 attacks, no COP/SCOP
                    'y', 'attack', 0, # Unit 3 attacks with COP
                    'end', 'stealth', 'end', 'end', 'end', 'end'])
    monkeypatch.setattr('builtins.input', lambda prompt='': next(inputs))
    

def test_parsing():
    max = CO("Max", 3, 6, None, None, None, player=1)
    terrain_codes = [[('P',0),('P',0)], [('P',0),('P',0)], [('S',0),('P',0)]]
    startingUnits = [(Unit(1,unitTypes.get('TNK')), 0, 0), 
                     (Unit(1,unitTypes.get('BOM')), 1, 0),
                     (Unit(1,unitTypes.get('SUB')), 0, 2),
                     (Unit(-1,unitTypes.get('INF')), 1, 2)]
    unit1 = startingUnits[0][0]
    game = Game(terrain_codes, terrain_types, player1CO=None, player2CO=None, startingUnits=startingUnits)
    powers = CO.parsePowers()
    print(powers)
    print(powers["maxBlast"])
    max.basicPower(values=powers["maxBlast"], board=game.board)
    assert unit1.movement == 8 and unit1.attackModifier == 50


