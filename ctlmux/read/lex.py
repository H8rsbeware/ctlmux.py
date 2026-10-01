"""
5ba6,308x70,0,0[
    308x35,0,0,2,  // AREA DEFINITION
    308x34,0,36{    // PANES DEFINITION
        154x34,0,36,3,  // AREA
        153x34,155,36[      // PANES 
            153x17,155,36,4,    // AREA
            153x16,155,54{          // PANES
                76x16,155,54,8,
                76x16,232,54,9
            }
        ]
    }
]
"""
from . import tokenise as tkn
from dataclasses import dataclass
from enum import Enum
from typing import Self

import math


class CTLMUX_LexError(Exception):
    pass


class PaneType(Enum):
    TOP_LEVEL = 0
    STACK = 1
    LIST = 2


@dataclass(frozen=True)
class PaneItem:
    pane_id: str
    height_perc: int
    width_perc: int


@dataclass()
class PaneArea:
    children: list[PaneItem | Self]
    area_type: PaneType


class Lexer:
    def __init__(self, buffer: str):
        self.tokeniser: tkn.Tokenise = tkn.Tokenise(buffer)

        self.pane_tree: PaneArea = PaneArea([], PaneType.TOP_LEVEL)

    def Build(self) -> PaneArea:
        """
        Consumes the top-level window data (checksum, alignment, size, etc),
        and then either:
            - Create a single PaneItem for single PaneWindows
            - Calls consumeList to build a PaneArea of PaneType LIST to repr
                a vertical split (p1|p2)
            - Calls consumeList to build a PaneArea of PaneType STACK to repr
                a horizontal split (p1/p2)

        Only one of these types can exist at the top level, while each child 
        STACK or LIST can themselves contain PaneItems, STACKs, or LISTs

        Modifies self.pane_tree TL once decended the stack. [UNNEEDED]

        Returns a PaneArea with children.
        """
        _ = self.tokeniser.consume_until(',')  # checksum
        _ = self.tokeniser.advance()  # consume comma

        _ = self.tokeniser.consume_until(',')
        _ = self.tokeniser.advance()  # consume comma

        _ = self.tokeniser.consume_until(',')  # x align
        _ = self.tokeniser.advance()  # consume comma

        _ = self.tokeniser.consume_until(',')  # y align
        _ = self.tokeniser.advance()  # consume comma

        next_brace = self.tokeniser.find_next('{') or math.inf
        next_bracket = self.tokeniser.find_next('[') or math.inf

        if (
            next_brace is math.inf
            and next_bracket is math.inf
        ):
            # must be a single pane, which is terminated by eof
            pane_id, _ = self.tokeniser.consume_until(' ')
            self.pane_tree.children.append(
                PaneItem(pane_id, 100, 100)
            )
            return self.pane_tree

        if next_brace < next_bracket:
            list_area = self.consumeList((100, 100))
            self.pane_tree.children.append(list_area)
        else:
            list_area = self.consumeStack((100, 100))
            self.pane_tree.children.append(list_area)

        return self.pane_tree

    def consumeList(self, start_ratio: tuple[int, int]) -> PaneArea:
        _ = self.tokeniser.advance()

        return PaneArea(children=[], area_type=PaneType.LIST)

    def consumeStack(self, start_ratio: tuple[int, int]) -> PaneArea:
        _ = self.tokeniser.advance()
                 
        return PaneArea(children=[], area_type=PaneType.STACK)

    @staticmethod
    def create_ratio(ratio: str) -> tuple[int, int] | None:
        x, y = ratio.split('x', 1)
        x = int(x) or None
        y = int(y) or None

        if not x or not y:
            return None

        return x, y
