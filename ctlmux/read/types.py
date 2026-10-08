from enum import Enum
from dataclasses import dataclass
from typing import override, Self

class LayoutPaneType(Enum):
    TOP_LEVEL = 0
    STACK = 1
    LIST = 2


@dataclass()
class LayoutPaneItem:
    pane_id: str
    width_perc: int
    height_perc: int

    @override
    def __repr__(self, depth: int = 0):
        return ''.join(
            ['\t' for _ in range(0, depth)
        ]) + f"[{self.pane_id}: {self.width_perc}x{self.height_perc} (%)]"


@dataclass()
class LayoutPaneArea:
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
