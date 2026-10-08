"""
`~/read/window_builder` `ResolvedTMUXPane.dict() | ResolvedTMUXArea.dict()`
    outputs and `~/store` input for creating json data
"""
SerialisedPaneInfo = dict[str, str | int | bool | list[int]]
SerialisedWindowInfo = dict[str, str | list[int | int] | SerialisedPaneInfo]
