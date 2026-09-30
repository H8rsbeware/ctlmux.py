from dataclasses import dataclass
from . import exceptions as exc
from typing import override
from enum import IntEnum

import subprocess as sub

TMUX_SESSION_KEY = "session"
TMUX_PANE_FORMAT = "'" + TMUX_SESSION_KEY + \
    "=#{session_name} pane_id=#{pane_id} " + \
    "window=#{window_index}:#{window_name} " + \
    "pane=#{pane_index}:#{pane_title} active=#{pane_active} " + \
    "command=#{pane_current_command} path=#{pane_current_path}'"
TMUX_PANE_FIELD_COUNT = TMUX_PANE_FORMAT.count('=')

TMUX_WINDOW_FORMAT = "'" + TMUX_SESSION_KEY + \
    "=#{session_name} window=#{window_index}:#{window_name} " + \
    "count=#{window_panes} layout=#{window_layout}'"
TMUX_WINDOW_FIELD_COUNT = TMUX_WINDOW_FORMAT.count('=')


class PanePosition(IntEnum):
    STAND_ALONE = 0
    TOP = 1
    BOTTOM = 2
    LEFT = 3
    RIGHT = 4


@dataclass(frozen=True)
class FormatPaneOut:
    id: str
    session_name: str
    window_index: int
    window_name: str
    pane_index: int
    pane_title: str
    active: bool
    command: str
    path: str

    @staticmethod
    def from_dict(d: dict[str, str]) -> "FormatPaneOut":
        id = d.get("pane_id", None)
        session = d.get("session", None)
        window_info = d.get("window", None)
        pane_info = d.get("pane", None)
        active = d.get("active", None)
        command = d.get("command", None)
        path = d.get("path", None)

        if (
            not id or
            not session or
            not window_info or
            not pane_info or
            not active or
            not command or
            not path
        ):
            raise exc.CTLMUX_PaneNotFormattedCorrectly(
                f"list-panes result expects: 'session', 'window', 'pane', 'active', 'command', and 'path' from:\n`list-panes -t ... -F {TMUX_PANE_FORMAT}"
            )

        win_split = window_info.split(':')
        if len(win_split) != 2:
            raise exc.CTLMUX_PaneNotFormattedCorrectly(
                f"list-panes `window` must be 'index:name', with exactly 1 `:`"
            )

        pane_split = pane_info.split(':')
        if len(pane_split) != 2:
            raise exc.CTLMUX_PaneNotFormattedCorrectly(
                f"list-panes `pane` must be 'index:name', with exactly 1 `:`"
            )

        w_index, w_name = win_split
        p_index, p_name = pane_split

        pane_number = int(p_index) or None
        window_index = int(w_index) or None

        if not pane_number or not window_index:
            raise exc.CTLMUX_PaneNotFormattedCorrectly(
                f"list-panes `window_index` or `pane_index` is not convertable to an integer, found: window={w_index}, pane={p_index}"
            )

        if active == "0":
            active = False
        elif active == "1":
            active = True
        else:
            raise exc.CTLMUX_PaneNotFormattedCorrectly(
                f"list-panes `active` not '0' or '1', found: {active}"
            )

        return FormatPaneOut(
            id,
            session,
            window_index,
            w_name,
            pane_number,
            p_name,
            active,
            command,
            path,
        )

    @override
    def __repr__(self) -> str:
        return f"{self.session_name}|{self.window_name}:{self.window_index} -> [{self.pane_index}]{self.command}"


@dataclass(frozen=True)
class WindowStackItem:
    height_perc: int
    width_perc: int
    format: FormatPaneOut


@dataclass(frozen=True)
class WindowListItem:
    height_perc: int
    width_perc: int
    format: FormatPaneOut


PANES_LIST = list[
        WindowListItem | list[WindowStackItem]
    ] | list[WindowStackItem]


@dataclass(frozen=True)
class FormatWindowOut:
    window_name: str
    window_index: str
    pane_count: int
    panes: PANES_LIST

    @staticmethod
    def create(
        window_name: str,
        window_index: str,
        pane_count: int,
        panes: PANES_LIST,
    ) -> "FormatWindowOut":
        return FormatWindowOut(
            window_name,
            window_index,
            pane_count,
            panes,
        )

def buildPane(window_name: str, base_one_idx: int, part: str) -> FormatPaneOut:
    pass


def buildWindowStandalone(
    window_name: str,
    index: str,
    buffer: str,
) -> tuple[list[WindowListItem], int]:
    return [], 0


def buildWindowList(
    window_name: str,
    index: str,
    buffer: str,
) -> tuple[list[WindowListItem], int]:
    return [], 0


# TODO: Need to extract or pass in the window max size, (pos 2, 1 idx in parts)
# to create percentages
def buildWindowStack(
    window_name: str,
    index: str,
    buffer: str
) -> tuple[list[WindowStackItem], int]:
    end = buffer.find(']')
    slice = buffer[:end]

    parts = slice.split(',')
    base_one = 1

    if (len(parts) % 4) != 0:
        raise exc.CTLMUX_TMUXWindowFormatInvalid(
            "list-window layout malformed"
        )

    stack: list[WindowStackItem] = []

    while (base_one * 4) < len(parts):
        curr_pos = (base_one * 4) - 1
        part = parts[curr_pos]

        item = buildPane(window_name, base_one, part)
        # TODO: Percentages
        stack.append(item)

        base_one += 1

    return stack, end


def buildWindowPaneList(window: dict[str, str]) -> FormatWindowOut:
    layout = window.get("layout", None)

    if not layout:
        raise exc.CTLMUX_SystemError(
            "buildWindowPaneList(1) failed to find `layout` in `window`"
        )

    window_name = window.get("_window_name", None)
    window_index = window.get("_window_index", None)
    pane_count = window.get("count", None)
    pane_count = int(pane_count) if pane_count is not None else None

    if (
        not window_name or
        not window_index or
        not pane_count
    ):
        raise exc.CTLMUX_SystemError(
            "FormatWindowOut.build_with(2) got malformed window_info dict, " +
            "expected `_window_name`, `_window_index`, and `count`"
        )

    if start := layout.find('[') != -1:
        layout = layout[start:]
    elif start := layout.find('{') != -1:
        layout = layout[start:]

    if layout[0] == '[':
        panes, _ = buildWindowStack(
            window_name,
            window_index,
            layout[1:],
        )
        return FormatWindowOut.create(
            window_name,
            window_index,
            pane_count,
            panes,
        )
    elif layout[0] == '{':
        panes, _ = buildWindowList(
            window_name,
            window_index,
            layout[1:]
        )
        return FormatWindowOut.create(
            window_name,
            window_index,
            pane_count,
            panes,
        )

    panes, _ = buildWindowStandalone(window_name, window_index)
    return FormatWindowOut.create(
        window_name,
        window_index,
        pane_count,
        panes,
    )


def parseWindow(tmux_fmt_ln: str) -> tuple[dict[str, str], int]:
    fields = tmux_fmt_ln.split(' ')

    if len(fields) != TMUX_PANE_FIELD_COUNT:
        raise exc.CTLMUX_PaneNotFormattedCorrectly(
            "Format string: '{fmt}', cannot be parsed"
        )

    found: dict[str, str] = {}
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


def buildWindowsInfo(session_name: str) -> dict[int, dict[str, str]]:
    try:
        result = sub.check_output(
            f"tmux list-windows -t {session_name} -F {TMUX_WINDOW_FORMAT}",
            shell=True,
            executable="/bin/bash",
            stderr=sub.STDOUT,
        )
    except sub.CalledProcessError as cpe:
        raise exc.CTLMUX_TMUXCmdFailed(
            f"Encounted error when calling list-windows on '{session_name}':" +
            f"\n\t{cpe}"
        )

    expected_start = TMUX_SESSION_KEY + "=" + session_name
    winfo: dict[int, dict[str, str]] = {}

    for line in result.splitlines():
        fmt = line.decode().strip()
        if fmt.startswith(expected_start) is False:
            continue

        wi, index = parseWindow(fmt)

        if winfo.get(index, None) is not None:
            raise exc.CTLMUX_WindowLayoutInvalid(
                "list-windows retuned multiple of the same window_index for " +
                "a single session name"
            )

        winfo[index] = wi

    return winfo


def GetWindows(session_name: str) -> list[FormatWindowOut]:
    winfo = buildWindowsInfo(session_name)
    panes: list[FormatWindowOut] = []

    for w_idx, d in winfo.items():
        layout: str | None = d.get("layout", None)
        pane_count: str | None = d.get("count", None)
        # Guaranteed by buildWindowInfo > parseWindow but we will check
        index: str | None = d.get("_window_index", None)
        name: str | None = d.get("_window_name", None)

        if (
            not layout or
            not pane_count or
            not index or
            not name
        ):
            raise exc.CTLMUX_TMUXWindowFormatInvalid(
                "GetWindows(1) expects buildWindowsInfo to return: " +
                "`layout` and `count` from list-windows, and " +
                "`_window_index`, `_window_name` from `window`"
            )

        if w_idx != int(index):
            raise exc.CTLMUX_SystemError(
                "GetWindows(1): Assertion that winfo dict key == " +
                f"value._window_index failed. Found {w_idx}==" +
                f"{index}"
            )

        pane_fmt: FormatWindowOut = buildWindowPaneList(d)
        panes.append(pane_fmt)

    return panes


# ! DEPRECATING - since we build window first now
# def GetPanesForWindow(session_name: str, window_index: int) -> list[FormatPaneOut]:
#     try:
#         result: bytes = sub.check_output(
#             f"tmux list-panes -t {session_name}:{window_index} -F {TMUX_PANE_FORMAT}",
#             shell=True,
#             executable="/bin/bash",
#             stderr=sub.STDOUT,
#         )
#     except sub.CalledProcessError as cpe:
#         raise exc.CTLMUX_TMUXCmdFailed(
#             f"Encountered error when calling list-panes on '{session_name}':\n\t{cpe}"
#         )
#
#     expected_start = TMUX_SESSION_KEY + "=" + session_name
#     fmt_panes: list[FormatPaneOut] = []
#
#     for line in result.splitlines():
#         line = line.decode().strip()
#
#         if not line.startswith(expected_start):
#             continue
#
#         fmt_panes.append(
#             parsePane(line)
#         )
#
#     return fmt_panes
