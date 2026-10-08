"""

"""

from dataclasses import dataclass
from typing import override, Self
from enum import IntEnum

import subprocess as sub

from . import exceptions as exc
from . import layout_lexer as lex
from shared_types import SerialisedTMUXTypes as stypes
from tmux_formats import TMUX_SESSION_KEY, TMUX_PANE_FORMAT, TMUX_PANE_FIELD_COUNT, TMUX_WINDOW_FORMAT, TMUX_WINDOW_FIELD_COUNT
from .types import LayoutPaneArea, LayoutPaneType

WindowInfo = dict[str, str]
PaneInfo = dict[str, str]


class AreaType(IntEnum):
    TOP = 0 # no defined
    STACK = 1 # vertical
    LIST = 2 # horizontal

    @staticmethod
    def fromLexPaneType(pane_type: LayoutPaneType) -> "AreaType":
        return AreaType(pane_type.value)

    @override
    def __str__(self) -> str:
        return {
            0: "TOP",
            1: "STACK",
            2: "LIST",
        }[self]


@dataclass
class ResolvedTMUXPane:
    id: int
    index: int
    title: str
    active: bool
    command: str
    path: str
    relative_dimensions: tuple[int, int]

    @override
    def __repr__(self, depth: int = 0):
        tabs = '\t'.join(['' for _ in range(depth)])

        return f"{tabs}P[{self.title}:{self.id}@{self.index} | {self.path} -> " + \
            f"{self.command} ({self.relative_dimensions[0]}," + \
            f"{self.relative_dimensions[1]} | active: {self.active})]\n"

    def dict(self) -> stypes.SerialisedPaneInfo:
        return {
            "id": self.id,
            "index": self.index,
            "title": self.title,
            "active": self.active,
            "command": self.command,
            "path": self.path,
            "relative_dimensions": [
                self.relative_dimensions[0],
                self.relative_dimensions[1],
            ]
        }


@dataclass
class ResolvedTMUXArea:
    type: AreaType
    relative_dimensions: tuple[int, int]
    children: list[ResolvedTMUXPane | Self]

    @override
    def __repr__(self, depth: int = 0):
        tabs = '\t'.join(['' for _ in range(depth)])

        base = f"{tabs}A[{self.type}, ({self.relative_dimensions[0]}," + \
            f"{self.relative_dimensions[1]})] -> \n"

        return base + ''.join(
            [c.__repr__(depth+1) for c in self.children]
        ) + '\n'

    def dict(self) -> stypes.SerialisedWindowInfo:
        children = [child.dict() for child in self.children]

        return {
            "type": str(self.type),
            "relative_dimensions": [
                self.relative_dimensions[0],
                self.relative_dimensions[1],
            ],
            "children": children
        }


@dataclass
class TMUXWindow:
    index: int
    session_name: str
    name: str
    pane_tree: ResolvedTMUXArea

    @override
    def __repr__(self, depth: int = 0):
        tabs = '\t'.join(['' for _ in range(depth)])

        base = f"{tabs}WIN[{self.index}:{self.session_name} -> {self.name}]\n"

        return base + self.pane_tree.__repr__(depth+1) + '\n'

    def dict(self) -> dict[str, str | int | stypes.SerialisedWindowInfo]:
        return {
            "window_index": self.index,
            "window_name": self.name,
            "session_name": self.session_name,
            "panes": self.pane_tree.dict(),
        }


class WindowsTree:
    def __init__(self, session_name: str):
        self.tree: list[TMUXWindow] = []
        self.session_name: str = session_name

    def Build(self) -> list[TMUXWindow]:
        try:
            winfo = self.getWindowInfos()
        except exc.CTLMUX_TMUXCmdFailed as e:
            print(
                "\x1b[31mCannot get window information for: " +
                f"'{self.session_name}'.\x1b[0m"
            )
            raise e

        for windex, data in winfo.items():
            layout: str | None = data.get("layout", None)
            expected_pane_count = int(
                data.get("count", "")
            ) or None

            if not layout or not expected_pane_count:
                raise exc.CTLMUX_TMUXWindowFormatInvalid(
                    "list-windows expects layout= and pane count"
                )

            lxr = lex.Lexer(layout)
            tree = lxr.Build()

            # Walk tree with windex, get pane data, build new tree
            this_tl_pane: ResolvedTMUXArea = self.BuildTopPaneFromLayoutTree(
                tree,
                expected_pane_count,
                windex,
            )

            this_window = TMUXWindow(
                windex,
                self.session_name,
                data["_window_name"],
                this_tl_pane,
            )

            self.tree.append(this_window)

        return self.tree

    def BuildTopPaneFromLayoutTree(
        self,
        layout_tree: LayoutPaneArea,
        expected_pane_count: int,
        index: int,
    ) -> ResolvedTMUXArea:
        panes_by_id = self.getPaneInfos(index)

        def walk(node: LayoutPaneArea, count: int = 0) -> tuple[ResolvedTMUXArea, int]:
            children: list[ResolvedTMUXArea | ResolvedTMUXPane] = []
            node_type = AreaType.fromLexPaneType(node.area_type)

            for child in node.children:
                this = None
                if isinstance(child, LayoutPaneArea):
                    this, c = walk(child, count)
                    count = c
                else:
                    pane_id = child.pane_id
                    pane_int = int(pane_id) or -1
                    this_pane = panes_by_id.get(pane_int, None)

                    if not this_pane:
                        raise exc.CTLMUX_SystemError(
                            f"list-panes info for window '{self.session_name}:" +
                            f"{index}' (+uint), does not match Lex state ids"
                        )

                    active: bool = True if this_pane["active"] == '1' else False

                    # get all this shit
                    this = ResolvedTMUXPane(
                        index,
                        pane_int,
                        this_pane["_pane_title"],
                        active,
                        this_pane["command"],
                        this_pane["path"],
                        (child.width_perc, child.height_perc)
                    )
                    count += 1

                # account for area or panes existance
                children.append(this)

            return ResolvedTMUXArea(
                node_type,
                (node.width_perc, node.height_perc),
                children,
            ), count

        area, count = walk(layout_tree, 0)

        if expected_pane_count != count:
            raise exc.CTLMUX_SystemError(
                "BuildWindowFromLayoutTree child mismatch, Lex produced " +
                f"`{expected_pane_count}` children, walked {count}"
            )

        return area

    def getPaneInfos(self, windex: int) -> dict[int, PaneInfo]:
        try:
            result = sub.check_output(
                f"tmux list-panes -t {self.session_name}:{windex} -F {TMUX_PANE_FORMAT}",
                shell=True,
                executable="/bin/bash",
                stderr=sub.STDOUT,
            )
        except sub.CalledProcessError as cpe:
            raise exc.CTLMUX_TMUXCmdFailed(
                f"Encounted error when calling list-panes on" +
                f"{self.session_name}:{windex}:\n\t{cpe}"
            )

        expected_start = TMUX_SESSION_KEY + "=" + self.session_name
        all_panes_by_id: dict[int, PaneInfo] = {}

        for line in result.splitlines():
            fmt = line.decode().strip()
            if fmt.startswith(expected_start) is False:
                continue

            pane_info, pane_id = WindowsTree.parse_tmux_pane(fmt)

            if all_panes_by_id.get(pane_id, None) is not None:
                raise exc.CTLMUX_WindowLayoutInvalid(
                    "list-windows retuned multiple of the same window_index " +
                    "for a single session name"
                )

            all_panes_by_id[pane_id] = pane_info

        return all_panes_by_id

    def getWindowInfos(self) -> dict[int, WindowInfo]:
        try:
            result = sub.check_output(
                f"tmux list-windows -t {self.session_name} -F {TMUX_WINDOW_FORMAT}",
                shell=True,
                executable="/bin/bash",
                stderr=sub.STDOUT,
            )
        except sub.CalledProcessError as cpe:
            raise exc.CTLMUX_TMUXCmdFailed(
                f"Encounted error when calling list-windows on" +
                f"{self.session_name}:\n\t{cpe}"
            )

        expected_start = TMUX_SESSION_KEY + "=" + self.session_name
        winfo: dict[int, WindowInfo] = {}

        for line in result.splitlines():
            fmt = line.decode().strip()
            if fmt.startswith(expected_start) is False:
                continue

            wi, index = WindowsTree.parse_tmux_window(fmt)

            if winfo.get(index, None) is not None:
                raise exc.CTLMUX_WindowLayoutInvalid(
                    "list-windows retuned multiple of the same window_index " +
                    "for a single session name"
                )

            winfo[index] = wi

        return winfo
    
    @staticmethod
    def parse_tmux_pane(fmt_ln: str) -> tuple[PaneInfo, int]:
        fields: list[str] = fmt_ln.split(' ')

        if len(fields) != TMUX_PANE_FIELD_COUNT:
            raise exc.CTLMUX_SystemError(
                "Format string: '{fmt}', cannot be parsed"
            )

        found: PaneInfo = {}
        for field in fields:
            key, value = field.split('=', 1)
            found[key.lower()] = value.strip()

        window = found.get("window", None)
        if window is None:
            raise exc.CTLMUX_TMUXPaneFormatInvalid(
                "list-panes command did not return key `window`"
            )

        split_window: list[str] = window.split(':')
        if len(split_window) != 2:
            raise exc.CTLMUX_TMUXPaneFormatInvalid(
                "list-panes command did not return valid `window`, " + 
                "expected exactly one ':'"
            )
        index, name = split_window

        pane_id = found.get("pane_id", "")
        if pane_id.startswith('%'):
            pane_id = pane_id.removeprefix('%')

        pane_id_int = int(pane_id) or None

        if not pane_id_int:
            raise exc.CTLMUX_TMUXPaneFormatInvalid(
                "list-panes `pane_id` must be set, and int convertable"
            )

        pane = found.get("pane", None)
        if pane is None:
            raise exc.CTLMUX_TMUXPaneFormatInvalid(
                "list-panes `pane` must be index:title"
            )

        split_pane = pane.split(':')
        if len(split_pane) != 2:
            raise exc.CTLMUX_TMUXPaneFormatInvalid(
                "list-panes `pane` must be index:title"
            )

        pane_index, pane_title = split_pane

        command: str | None = found.get("command", None)
        path: str | None = found.get("path", None)
        active = found.get("active", None)

        if not command or not path or not active:
            raise exc.CTLMUX_TMUXPaneFormatInvalid(
                "list-panes must return `command`, and `path`"
            )

        found["_window_name"] = name
        found["_window_index"] = index
        found["_pane_index"] = pane_index
        found["_pane_title"] = pane_title

        return found, pane_id_int

    @staticmethod
    def parse_tmux_window(fmt_ln: str) -> tuple[WindowInfo, int]:
        fields: list[str] = fmt_ln.split(' ')

        if len(fields) != TMUX_WINDOW_FIELD_COUNT:
            raise exc.CTLMUX_SystemError(
                "Format string: '{fmt}', cannot be parsed"
            )

        found: WindowInfo = {}
        for field in fields:
            key, value = field.split('=', 1)
            found[key.lower()] = value.strip()

        window = found.get("window", None)
        if window is None:
            raise exc.CTLMUX_TMUXWindowFormatInvalid(
                "list-windows command did not return key `window`"
            )

        split_window = window.split(':')
        if len(split_window) != 2:
            raise exc.CTLMUX_TMUXWindowFormatInvalid(
                "list-windows command did not return valid `window`, " +
                "expected exactly one ':'"
            )

        index, name = split_window
        index_int = int(index) or None

        if index_int is None:
            raise exc.CTLMUX_TMUXWindowFormatInvalid(
                "list-windows command did not return valid `window_index`, " +
                "expected int convertable value"
            )

        found["_window_name"] = name
        found["_window_index"] = index

        return (found, index_int)
