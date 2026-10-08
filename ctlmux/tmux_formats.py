"""
This file contains the TMUX format strings used in the following commands:

    `tmux list-windows -t {session}:{window_index} -F {TMUX_WINDOW_FORMAT}`
    `tmux list-panes -t {session}:{window_index} -F {TMUX_PANE_FORMAT}`

It also contains the field counts, used to validate the `tmux` response.

While currently only used in `~/read/window_builder.py`, its felt appropriate
to include this in the root.

! DO NOT CHANGE THESE
"""
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
