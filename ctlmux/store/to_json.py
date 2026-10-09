from shared_types.SerialisedTMUXTypes import SerialisedWindowInfo 
from read.window_builder import TMUXWindow

import json


def WriteTMUXState(directory_path: str, window: TMUXWindow) -> bool:
    serial: SerialisedWindowInfo = window.dict()

    file_name = "ctlmux_%s" % window.name
    full_path: str = directory_path.removesuffix('/') + "/" + file_name

    try:
        with open(full_path, 'w') as f:
            json.dump(serial, f)
    except (json.JSONEncodeError, FileNotFoundError) as e:
        return False

    return True

