from enum import Enum
from dataclasses import dataclass

class ActionType(Enum):
    MOVE = "move"
    ATTACK = "attack"
    CAPTURE = "capture"
    STEALTH = "stealth"
    UNLOAD = "unload"
    WAIT = "wait"
    END_TURN = "endTurn"

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

                actions.append(Action(ActionType.CAPTURE, (x0, y0), None))
                actions.append(Action(ActionType.STEALTH, (x0, y0), None))
                actions.append(Action(ActionType.WAIT, (x0, y0), (x0, y0)))
                actions.append(Action(ActionType.END_TURN, None, None))
        
        return actions