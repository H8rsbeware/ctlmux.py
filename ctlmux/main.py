# !/usr/bin/python
# import subprocess as sub
# import sys

from read_session import BuildSessionState

def main() -> None:
    state_name: str | None = BuildSessionState(None)
    print(state_name)

    return


if __name__ == "__main__":
    main()
