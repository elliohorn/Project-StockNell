from enum import Enum
from dataclasses import dataclass

import sys, os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, PROJECT_ROOT)
from SimpleAWEngine.Unit import unitTypes

class ActionType(Enum):
    MOVE = "move"
    ATTACK = "attack"
    CAPTURE = "capture"
    STEALTH = "stealth"
    UNLOAD = "unload"
    WAIT = "wait"
    END_TURN = "endTurn"
    BUILD_UNIT = "buildUnit"
    ACTIVATE_POWER = "activateCOP"
    ACTIVATE_SUPER = "activateSCOP"

@dataclass(frozen=True)
class Action:
    type: ActionType
    actor: tuple # coords
    target: tuple # also coords


    def buildAllActions(width, height):
        actions = []
        for x0 in range(width):
            for y0 in range(height):

                for x1 in range(width):
                    for y1 in range(height):
                        actions.append(Action(ActionType.MOVE, (x0, y0), (x1, y1)))
                        actions.append(Action(ActionType.ATTACK, (x0,y0), (x1,y1)))
                        actions.append(Action(ActionType.UNLOAD, (x0, y0), (x1, y1)))
                        for ut in unitTypes:
                            actions.append(Action(ActionType.BUILD_UNIT, (x0, y0), (ut,)))

                actions.append(Action(ActionType.CAPTURE, (x0, y0), None))
                actions.append(Action(ActionType.STEALTH, (x0, y0), None))
                actions.append(Action(ActionType.WAIT, (x0, y0), (x0, y0)))
                actions.append(Action(ActionType.END_TURN, None, None))


        actions.append(Action(ActionType.ACTIVATE_POWER, None, None))
        actions.append(Action(ActionType.ACTIVATE_SUPER, None, None))
        
        return actions