import subprocess as sub
from dataclasses import dataclass
from typing import override

SESSION_KEY = "session"
PANE_FMT = "'" + SESSION_KEY + "=#{session_name} window=#{window_index}:#{window_name} pane=#{pane_index}:#{pane_title} active=#{pane_active} command=#{pane_current_command} path=#{pane_current_path}'"
PANE_FIELDS = PANE_FMT.count('=')


class CTLMUX_TMUXCmdFailed(Exception):
    pass


class CTLMUX_NoSessionFound(Exception):
    pass


class CTLMUX_PaneNotFormattedCorrectly(Exception):
    pass


@dataclass(frozen=True)
class FormatPaneOut:
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
        session = d.get("session", None)
        window_info = d.get("window", None)
        pane_info = d.get("pane", None)
        active = d.get("active", None)
        command = d.get("command", None)
        path = d.get("path", None)

        if (
            not session or
            not window_info or
            not pane_info or
            not active or
            not command or
            not path
        ):
            raise CTLMUX_PaneNotFormattedCorrectly(
                f"list-panes result expects: 'session', 'window', 'pane', 'active', 'command', and 'path' from:\n`list-panes -t ... -F {PANE_FMT}"
            )

        win_split = window_info.split(':')
        if len(win_split) != 2:
            raise CTLMUX_PaneNotFormattedCorrectly(
                f"list-panes `window` must be 'index:name', with exactly 1 `:`"
            )

        pane_split = pane_info.split(':')
        if len(pane_split) != 2:
            raise CTLMUX_PaneNotFormattedCorrectly(
                f"list-panes `pane` must be 'index:name', with exactly 1 `:`"
            )

        w_index, w_name = win_split
        p_index, p_name = pane_split

        pane_number = int(p_index) or None
        window_index = int(w_index) or None

        if not pane_number or not window_index:
            raise CTLMUX_PaneNotFormattedCorrectly(
                f"list-panes `window_index` or `pane_index` is not convertable to an integer, found: window={w_index}, pane={p_index}"
            )

        if active == "0":
            active = False
        elif active == "1":
            active = True
        else:
            raise CTLMUX_PaneNotFormattedCorrectly(
                f"list-panes `active` not '0' or '1', found: {active}"
            )

        return FormatPaneOut(
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


def GetMostRecentSession() -> str | None:
    try:
        result = sub.check_output(
            "tmux list-windows -F 'session=#{session_name}'",
            shell=True,
            executable="/bin/bash",
            stderr=sub.STDOUT,
        )
    except sub.CalledProcessError as cpe:
        raise CTLMUX_TMUXCmdFailed(
            f"Encounted error when getting most recent session:\n\t{cpe}"
        )

    lines = result.splitlines()

    if len(lines) == 0:
        return None

    line_split = lines[0].decode().split('=')

    if len(line_split) != 2:
        return None

    return line_split[1]


def CheckSessionExists(session_name: str) -> bool:
    try:
        _ = sub.check_output(
            f"tmux list-windows -t {session_name}",
            shell=True,
            executable="/bin/bash",
            stderr=sub.STDOUT,
        )
        return True
    except sub.CalledProcessError:
        return False


def parsePane(fmt: str) -> FormatPaneOut:
    fields = fmt.split(' ')

    if len(fields) != PANE_FIELDS:
        raise CTLMUX_PaneNotFormattedCorrectly(
            "Format string: '{fmt}', cannot be parsed"
        )

    found: dict[str, str] = {}
    for field in fields:
        key, value = field.split("=")
        found[key.lower()] = value.strip()

    return FormatPaneOut.from_dict(found)


def GetPanes(session_name: str) -> list[FormatPaneOut]:
    try:
        result: bytes = sub.check_output(
            f"tmux list-panes -t {session_name} -a -F {PANE_FMT}",
            shell=True,
            executable="/bin/bash",
            stderr=sub.STDOUT,
        )
    except sub.CalledProcessError as cpe:
        raise CTLMUX_TMUXCmdFailed(
            f"Encountered error when calling list-panes on '{session_name}':\n\t{cpe}"
        )

    expected_start = SESSION_KEY + "=" + session_name
    fmt_panes: list[FormatPaneOut] = []

    for line in result.splitlines():
        line = line.decode().strip()

        if not line.startswith(expected_start):
            pass

        fmt_panes.append(
            parsePane(line)
        )

    return fmt_panes


def BuildSessionState(session_name: str | None):
    session = session_name or GetMostRecentSession()

    if session is None:
        raise CTLMUX_NoSessionFound("TMUX Latest Session could not be resolved, but was likely found.")

    if CheckSessionExists(session) is False:
        raise CTLMUX_NoSessionFound(f"TMUX Session, with name '{session}' could not be found.")

    panes_fmt_def = GetPanes(session)

    for p in panes_fmt_def:
        print(p)



