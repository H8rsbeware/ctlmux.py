# Internal Errors
class CTLMUX_LexError(Exception):
    pass


class CTLMUX_SystemError(Exception):
    pass


# TMUX Assertion Errors
class CTLMUX_NoSessionFound(Exception):
    pass


class CTLMUX_TMUXPaneFormatInvalid(Exception):
    pass


class CTLMUX_TMUXCmdFailed(Exception):
    pass


class CTLMUX_PaneNotFormattedCorrectly(Exception):
    pass


class CTLMUX_WindowLayoutInvalid(Exception):
    pass


class CTLMUX_TMUXWindowFormatInvalid(Exception):
    pass

