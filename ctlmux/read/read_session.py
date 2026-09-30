import subprocess as sub

from . import exceptions as exc
from .pane_collector import FormatPaneOut


def GetMostRecentSession() -> str | None:
    try:
        result = sub.check_output(
            "tmux list-windows -F 'session=#{session_name}'",
            shell=True,
            executable="/bin/bash",
            stderr=sub.STDOUT,
        )
    except sub.CalledProcessError as cpe:
        raise exc.CTLMUX_TMUXCmdFailed(
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


def BuildSessionState(session_name: str | None):
    session = session_name or GetMostRecentSession()

    if session is None:
        raise exc.CTLMUX_NoSessionFound("TMUX Latest Session could not be resolved, but was likely found.")

    if CheckSessionExists(session) is False:
        raise exc.CTLMUX_NoSessionFound(f"TMUX Session, with name '{session}' could not be found.")


    # panes_fmt_def: list[FormatPaneOut] = GetPanes(session)
    # for p in panes_fmt_def:
    #     print(p)

    raise NotImplemented("WIP")

