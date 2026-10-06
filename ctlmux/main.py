# !/usr/bin/python
# import subprocess as sub
# import sys

from read.layout_collector import WindowsTree

def main() -> None:
    tree_builder = WindowsTree("test")
    windows = tree_builder.Build();
    
    for win in windows:
        print(win)
        print("\n------\n")

    return


if __name__ == "__main__":
    main()
