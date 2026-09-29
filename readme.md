# ctlmux

Ctlmux is a simple recover tool that:
- Builds a toml file to reconstruct your current tmux session, with `ctlmux new {tmux-session}`
- Reconstructs those sessions, even after reboots, with `ctlmux re {tmux-session}`
- Lists sessions saved
- Saves the current state of sessions as a snapshot or source with, repectively:
    - `ctlmux snap {tmux-session}`
    - `ctlmux src {tmux-session}`

This allows for a tree like session representation of layout, but not state 
