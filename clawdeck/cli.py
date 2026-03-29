"""
ClawDeck — Stream Deck controller for Claude Code terminal sessions

Maps a 5x3 (15-key) Elgato Stream Deck into three horizontal session rows:

ROW MODE (default):
  ┌─────┬─────┬─────┬─────┬─────┐
  │ T1  │info │info │info │info │
  ├─────┼─────┼─────┼─────┼─────┤
  │ T2  │info │info │info │info │
  ├─────┼─────┼─────┼─────┼─────┤
  │ T3  │info │info │info │info │
  └─────┴─────┴─────┴─────┴─────┘
  - Label key shows session status and focuses the mapped iTerm2 session
  - Tap the active label key again to enter Nav Mode
  - If Claude is waiting for permission, tap the label key to approve with `y`
  - Hold a label key to focus that session and trigger Whisprflow
  - The four info keys show the CWD, or a scrolling command preview in permission state

NAV MODE:
  ┌─────┬─────┬─────┬─────┬─────┐
  │  1  │  2  │  3  │  4  │  5  │
  ├─────┼─────┼─────┼─────┼─────┤
  │     │     │  ↑  │     │BACK │
  ├─────┼─────┼─────┼─────┼─────┤
  │ MIC │  ←  │  ↓  │  →  │  ⏎  │
  └─────┴─────┴─────┴─────┴─────┘
"""

import sys

from .controller import DeckController


def main(argv=None):
    """Run the CLI entrypoint and honor the built-in help screen."""
    args = list(sys.argv[1:] if argv is None else argv)
    if "--help" in args or "-h" in args:
        print(__doc__)
        print("Usage: python main.py")
        print()
        return 0

    DeckController().run()
    return 0
