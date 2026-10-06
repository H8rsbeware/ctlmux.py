""" !!! Added frame, need to fix - see the dotfiles/buffer.py|nvim.md

Format of TMUX window layout, where:
    - AREA: defines a stack or list of many pains, and its base size 
        (as compared to its parent)
    - PANE: literal definition of a pane, it size, and id

5ba6,308x70,0,0[                // top level def (pane or area)
    308x35,0,0,2,               // pane definition
    308x34,0,36{                // area definition
        154x34,0,36,3,          // pane
        153x34,155,36[          // area
            153x17,155,36,4,    // pane
            153x16,155,54{      // area
                76x16,155,54,8, // pane
                76x16,232,54,9  // pane
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
from typing import Self, override

import math


class CTLMUX_LexError(Exception):
    pass


@dataclass()
class PaneContainerSyntax:
    open: str
    close: str


class PaneType(Enum):
    TOP_LEVEL = 0
    STACK = 1
    LIST = 2


@dataclass()
class PaneItem:
    pane_id: str
    width_perc: int
    height_perc: int

    @override
    def __repr__(self, depth: int = 0):
        return ''.join(
            ['\t' for _ in range(0, depth)
        ]) + f"[{self.pane_id}: {self.width_perc}x{self.height_perc} (%)]"


@dataclass()
class PaneArea:
    children: list[PaneItem | Self]
    area_type: PaneType
    width_perc: int
    height_perc: int

    @override
    def __repr__(self, depth: int = 0):
        tabs = ''.join(['\t' for _ in range(0, depth)]) 
        return  f"{tabs}[{self.area_type}: {self.width_perc}x{self.height_perc}]:\n" + '\n'.join([
            child.__repr__(depth + 1) for child in self.children
        ])


@dataclass()
class Frame:
    size: tuple[int, int]
    last_char: str
    pane_id: str | None


class Lexer:
    def __init__(self, buffer: str):
        self.tokeniser: tkn.Tokenise = tkn.Tokenise(buffer)

        self.pane_tree: PaneArea = PaneArea([], PaneType.TOP_LEVEL, 100, 100)

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

        size, _ = self.tokeniser.consume_until(',')
        size = self.create_size(size)
        _ = self.tokeniser.advance()  # consume comma
        if size is None:
            raise CTLMUX_LexError(
                "Top Level size is formatted incorrectly"
            )

        _ = self.tokeniser.consume_until(',')  # x align
        _ = self.tokeniser.advance()  # consume comma

        next_of_interest = self.closestCharacter('*')
        if next_of_interest == '*':
            raise CTLMUX_LexError(
                "Top level isnt a single pain or termiated with a group operator"
            )

        if next_of_interest == ',':
            # consume y align
            _ = self.tokeniser.consume_until(',')  # y align
            _ = self.tokeniser.advance()  # consume comma

            # then consume the pane, since this defines one
            pane_id, _ = self.tokeniser.consume_until(' ')
            self.pane_tree.children.append(
                PaneItem(pane_id, size[0], size[1])
            )
            return self.pane_tree

        area_type = PaneType.LIST if next_of_interest == '{'else PaneType.STACK
        open_syntax = Lexer.get_container_syntax(area_type).open

        # eat bracket/brace to be consistent with later processes
        # y align consumed
        _ = self.tokeniser.consume_until(open_syntax)
        last_ch, _ = self.tokeniser.advance()

        # ratio doesnt matter, since we work in percentages
        final_area,  _ = self.consumeArea(size, area_type, last_ch)
        self.pane_tree.children.append(final_area)
        Lexer.post_scale_children(self.pane_tree)

        return self.pane_tree

    def closestCharacter(self, end_inside_char: str):
        list_open = Lexer.get_container_syntax(PaneType.LIST).open
        stack_open = Lexer.get_container_syntax(PaneType.STACK).open

        next_comma = self.tokeniser.find_next(
            ','
        ) or math.inf

        next_list = self.tokeniser.find_next(
            list_open
        ) or math.inf

        next_stack = self.tokeniser.find_next(
            stack_open
        ) or math.inf

        next_end = self.tokeniser.find_next(
            end_inside_char
        ) or math.inf

        closest = min(
            next_comma,
            next_list,
            next_stack,
            next_end,
        )

        if closest == math.inf:
            raise CTLMUX_LexError(
                "no next closest char matches"
            )

        if closest == next_end:
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
        inside: PaneType,
    ) -> Frame:
        """
        Consumes either 3 or 4 comma seperated values, where 0 is the ratio
        and 4, if it exists, is an id for the pane.

        If 3 values followed by a { or [, its a pane area def
        If 4 values followed by a , or } or ], its a pane

        Returns the ratio, last consumed char ['[', '{', ',' '}', ']'], and the
        pane id, if one exists, or None
        """

        area_close_syntax = Lexer.get_container_syntax(inside).close

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

            if comma_or_inside != ',' and comma_or_inside != area_close_syntax:
                raise CTLMUX_LexError(
                    "consumePaneOrArea expects Pane (ends comma or `}`/`]`.)" +
                    f"found: `{comma_or_inside}`"
                )

            id, _ = self.tokeniser.consume_until(comma_or_inside)
            consumed, _ = self.tokeniser.advance()

            return Frame(size, consumed, id)

        # if `inside_terminator` is 3rd something is broken - 
        # we expect panes to be 4 long, and areas to be 3 + { or [
        if to_consume == area_close_syntax:
            raise CTLMUX_LexError(
                "list-window layout form broken"
            )

        # otherwise, we can consume one and return
        _ = self.tokeniser.consume_until(to_consume)
        consumed, _ = self.tokeniser.advance()

        return Frame(size, consumed, None)

    def consumeArea(self, start_size: tuple[int, int], inside: PaneType, last_seen: str = '') -> tuple[PaneArea, str]:
        AREA_SYNTAX = Lexer.get_container_syntax(inside)
        this_pa = PaneArea([], inside, start_size[0], start_size[1])
        lc = last_seen if last_seen != '' else self.tokeniser.peek()[0]
        
        total_od = 0
        while lc != AREA_SYNTAX.close:
            frame = self.consumePaneOrArea(
                inside
            )

            if frame.pane_id:
                perc_size = Lexer.calculate_proportional_size(
                    start_size,
                    frame.size
                )

                this_pa.children.append(
                    PaneItem(
                        frame.pane_id,
                        perc_size[0],
                        perc_size[1],
                    )
                )
                total_od += perc_size[0] if inside == PaneType.LIST else perc_size[1]

            if frame.last_char in ['{', '[']:
                next_type = PaneType.LIST \
                    if frame.last_char == Lexer.get_container_syntax(PaneType.LIST).open \
                    else PaneType.STACK

                tpane, last_ch = self.consumeArea(
                    frame.size,
                    next_type,
                    frame.last_char,
                )

                this_pa.children.append(tpane)
                lc = last_ch
            elif frame.pane_id:
                lc = frame.last_char
        

        lc, _ = self.tokeniser.advance()
        return this_pa, lc

    @staticmethod
    def create_size(size: str) -> tuple[int, int] | None:
        x, y = size.split('x')
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

        px = math.ceil((r_min[0] / r_max[0]) * 100)
        py = math.ceil((r_min[1]) / r_max[1] * 100)

        return int(px), int(py)

    @staticmethod
    def get_container_syntax(t: PaneType) -> PaneContainerSyntax:
        if t == PaneType.LIST:
            return PaneContainerSyntax('{', '}')
        if t == PaneType.STACK:
            return PaneContainerSyntax('[', "]")

        raise CTLMUX_LexError(
            "TOP_LEVEL has no PaneContainerSyntax, since it defines no areas"
        )

    @staticmethod
    def post_scale_children(pa: PaneArea) -> None:
        """Convert raw area sizes and pane percentages into parent-relative shares.

        Run once on the completed tree, while area dimensions are still raw.
        Modifies values in place.
        """
        if not pa.children:
            return

        horizontal = pa.area_type == PaneType.LIST
        parent_dimension = pa.width_perc if horizontal else pa.height_perc
        weights: list[int] = []

        for child in pa.children:
            dimension = child.width_perc if horizontal else child.height_perc
            # Scale the PAs and PIs to be the same. Parent and PA dimensions 
            # are real widths while their multipliers are percentages.
            if isinstance(child, PaneArea):
                weights.append(dimension * 100)
            else:
                weights.append(dimension * parent_dimension)

        total = sum(weights)
        if total <= 0:
            raise CTLMUX_LexError("Cannot scale children with no positive size")

        # Convert the per-child weights into percentage shares
        shares = [weight * 100 // total for weight in weights]
        # Calculate the relative loss of each child
        remainders = [weight * 100 % total for weight in weights]

        # Create an ordered list of indexes from largest to smallest loss
        order = sorted(range(len(weights)), key=remainders.__getitem__, reverse=True)

        # Distribute the remaining shares against the children 
        # (will never be more than children)
        for i in order[:100 - sum(shares)]:
            shares[i] += 1

        # For each child, share pair, apply the share to the main-axis of this
        # container type (x for list, y for stack). 
        for child, share in zip(pa.children, shares):
            if isinstance(child, PaneArea):
                # Children need raw dimensions for scaling so we apply first.
                Lexer.post_scale_children(child)

            child.width_perc = share if horizontal else 100
            child.height_perc = 100 if horizontal else share

        return


if __name__ == "__main__":
    s = "5ba6,308x70,0,0[308x35,0,0,2,308x34,0,36{154x34,0,36,3,153x34,155,36[153x17,155,36,4,153x16,155,54{76x16,155,54,8,76x16,232,54,9}]}]"
    x = Lexer(s)
    a = x.Build()
    print(a)

    print("--------")

    s = "b693,308x70,0,0{154x70,0,0[154x35,0,0,1,154x34,0,36,5],76x70,155,0,2,76x70,232,0[76x35,232,0,3,76x34,232,36,4]}"
    x = Lexer(buffer=s)
    a = x.Build()
    print(a)
