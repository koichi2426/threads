"""後方互換: `python fetch_threads.py` は `threads-kit backup` と同等。"""

import sys

from threads_kit.cli import main

if __name__ == "__main__":
    main(["backup", *sys.argv[1:]])
