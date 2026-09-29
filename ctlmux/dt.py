from dataclasses import dataclass
from uuid import uuid4
from datetime import datetime

DATE_FORMAT = '%Y-%m-%d %H:%M:%S.%f'


def NewStateId() -> str:
    return str(uuid4())


@dataclass(frozen=True)
class PaneState:
    id: str
    parent_id: str
    pane_name: str
    active: bool
    command: str

    @staticmethod
    def Create(
        id: str,
        parent_id: str,
        pane_name: str,
        active: bool,
        command: str
    ):
        return PaneState(
            id,
            parent_id,
            pane_name,
            active,
            command,
        )


@dataclass(frozen=True)
class WindowState:
    id: str
    parent_id: str
    window_name: str
    order: int
    child_count: int
    children: list[PaneState]

    @staticmethod
    def Create(
        id: str,
        parent_id: str,
        window_name: str,
        order: int,
        children: list[PaneState]
    ):
        return WindowState(
            id,
            parent_id,
            window_name,
            order,
            len(children),
            children,
        )


@dataclass(frozen=True)
class SessionState:
    id: str
    session_name: str
    time: datetime
    previous: "SessionState"

    @staticmethod
    def Create(
        id: str,
        session_name: str,
        time: str,
        previous: "SessionState"
    ):
        as_dt = datetime.strptime(time, DATE_FORMAT)

        return SessionState(
            id,
            session_name,
            as_dt,
            previous,
        )
