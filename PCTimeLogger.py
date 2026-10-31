"""Entry point for the PyInstaller build of PCTimeLogger.exe."""

import sys

from pctimelogger.__main__ import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
