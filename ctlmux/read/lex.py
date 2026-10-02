"""
Format of TMUX window layout, where:
    - AREA: defines a stack or list of many pains, and its base size 
        (as compared to its parent)
    - PANE: literal definition of a pane, it size, and id

5ba6,308x70,0,0[                // TOP LEVEL DEF (PANE OR AREA)
    308x35,0,0,2,               // PANE DEFINITION
    308x34,0,36{                // AREA DEFINITION
        154x34,0,36,3,          // PANE
        153x34,155,36[          // AREA
            153x17,155,36,4,    // PANE
            153x16,155,54{      // AREA
                76x16,155,54,8, // PANE
                76x16,232,54,9  // PANE
            }
        ]
    }
]

Im not sure how much I like how I wrote this, but its the 3rd attempt (first
proper), so Ill leave it for now.

We rely on a tokeniser to consume and advance, figuring out what we are looking
for new within the Lexer.
It produces a tree, starting at a PaneArea, with children of PaneArea or PaneItem.

A PaneArea is either TOP_LEVEL (only the root), LIST (all PaneItem's within are
list items), or STACK (same as list, but for stacked panes). A PaneArea within
a PaneArea defines a new type

If I wrote this again, id do a few things:
    1. Its half flexible (getContainerSyntax) and half not - should maybe just
        bake that logic as constants up here
    2. Probably be a little more forgiving on format, I know the first (in non-
        root panes) is the ratio, and the last is either the id or a new PaneArea,
        but I end up having to check whats next after 3 steps of children, and 
        then again if its a comma.
    3. Dont use python, I can tell this tree will be slow af, and i have to crawl
        it again!
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
    width_perc: int
    height_perc: int


@dataclass()
class PaneArea:
    children: list[PaneItem | Self]
    area_type: PaneType


@dataclass()
class PaneContainerSyntax:
    open: str
    close: str


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

        area_type = PaneType.LIST if next_brace < next_bracket else PaneType.STACK
        open_syntax = self.getContainerSyntax(area_type).open

        # eat bracket/brace to be consistent with later processes
        _ = self.tokeniser.consume_until(open_syntax)
        _ = self.tokeniser.advance()

        # ratio doesnt matter, since we work in percentages
        final_area = self.consumeArea((100, 100), area_type)
        self.pane_tree.children.append(final_area)

        return self.pane_tree

    def closestCharacter(self, end_inside_char: str):
        list_open = self.getContainerSyntax(PaneType.LIST).open
        stack_open = self.getContainerSyntax(PaneType.STACK).open

        next_comma = self.tokeniser.find_next(
            ','
        ) or math.inf

        next_list = self.tokeniser.find_next(
            list_open
        ) or math.inf

        next_stack = self.tokeniser.find_next(
            stack_open
        ) or math.inf

        closest = min(
            next_comma,
            list_open,
            stack_open,
            -1
        )

        if closest == -1:
            return end_inside_char
        if closest == next_comma:
            return ','
        if closest == next_list:
            return list_open
        if closest == next_stack:
            return stack_open

        raise CTLMUX_LexError("Unreachable")

    def consumePaneOrArea(
        self,
        inside: PaneType
    ) -> tuple[tuple[int, int], str, str | None]:
        """
        Consumes either 3 or 4 comma seperated values, where 0 is the ratio
        and 4, if it exists, is an id for the pane.

        If 3 values followed by a { or [, its a pane area def
        If 4 values followed by a , or } or ], its a pane

        Returns the ratio, last consumed char ['[', '{', ',' '}', ']'], and the
        pane id, if one exists, or None
        """
        area_close_syntax = self.getContainerSyntax(inside).close

        size, _ = self.tokeniser.consume_until(',')
        size = self.create_size(size)
        _ = self.tokeniser.advance()
        if size is None:
            raise CTLMUX_LexError("...")

        _ = self.tokeniser.consume_until(',') # align x
        _ = self.tokeniser.advance()

        to_consume = self.closestCharacter(area_close_syntax)

        # we are in a pane, consume more, return early
        if to_consume == ',':
            _ = self.tokeniser.consume_until(',') # align y
            _ = self.tokeniser.advance()

            comma_or_inside = self.closestCharacter(
                area_close_syntax
            )

            if comma_or_inside != ',' or comma_or_inside != area_close_syntax:
                raise CTLMUX_LexError(
                    "consumePaneOrArea expects Pane (ends comma or `}`/`]`.)" +
                    f"found: `{comma_or_inside}`"
                )

            id, _ = self.tokeniser.consume_until(comma_or_inside)
            _ = self.tokeniser.advance()
            return size, comma_or_inside, id

        # if `inside_terminator` is 3rd something is broken - 
        # we expect panes to be 4 long, and areas to be 3 + { or [
        if to_consume == area_close_syntax:
            raise CTLMUX_LexError(
                "list-window layout form broken"
            )

        # otherwise, we can consume one and return
        _ = self.tokeniser.consume_until(to_consume)
        _ = self.tokeniser.advance()

        return size, to_consume, None

    def consumeArea(self, start_size: tuple[int, int], inside: PaneType) -> PaneArea:
        AREA_SYNTAX = self.getContainerSyntax(inside)
        this_pa = PaneArea(area_type=PaneType.LIST, children=[])

        lc = None
        while lc != AREA_SYNTAX.close:
            this_size, last_consumed, id_or_none = self.consumePaneOrArea(
                PaneType.LIST
            )

            if last_consumed == ',':
                if id_or_none is None:
                    raise CTLMUX_LexError(
                        "consumeList found ',' last, but no id returned"
                    )
                perc_size = self.calculate_proportional_size(
                    start_size,
                    this_size
                )

                this_pa.children.append(
                    PaneItem(
                        id_or_none,
                        perc_size[0],
                        perc_size[1],
                    )
                )
            else:
                next_type = PaneType.LIST \
                    if last_consumed == self.getContainerSyntax(PaneType.LIST).open \
                    else PaneType.STACK

                this_pa.children.append(
                    self.consumeArea(
                        (100, 100),
                        next_type
                    )
                )

            lc = last_consumed

        return this_pa

    @staticmethod
    def create_size(size: str) -> tuple[int, int] | None:
        x, y = size.split('x', 1)
        x = int(x) or None
        y = int(y) or None

        if not x or not y:
            return None

        return x, y

    @staticmethod
    def calculate_proportional_size(
        r_max: tuple[int, int],
        r_min: tuple[int, int]
    ) -> tuple[int, int]:
        if r_max[0] < r_min[0] or r_max[1] < r_min[1]:
            raise CTLMUX_LexError(
                "calculate_proportinal_size requires min < max"
            )

        px = math.floor((r_min[0] / r_max[0]) * 100)
        py = math.floor((r_min[1]) / r_max[1] * 100)

        return int(px), int(py)

    @staticmethod
    def getContainerSyntax(t: PaneType) -> PaneContainerSyntax:
        if t == PaneType.LIST:
            return PaneContainerSyntax('{', '}')
        if t == PaneType.STACK:
            return PaneContainerSyntax('[', "]")

        raise CTLMUX_LexError(
            "TOP_LEVEL has no PaneContainerSyntax, since it defines no areas"
        )

