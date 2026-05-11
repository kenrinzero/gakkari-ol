from __future__ import annotations

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="gakkari",
        description="Gakkari OL — terminal subscription tracker. "
        "Run with no args to launch the TUI; --notice prints today's "
        "renewals to stdout (for Task Scheduler / daily routines).",
    )
    parser.add_argument(
        "--notice",
        action="store_true",
        help="Print today's renewals + 7-day preview and exit.",
    )
    parser.add_argument(
        "--lang",
        choices=("en", "ja"),
        default=None,
        help="Override the saved UI language for --notice output.",
    )
    args = parser.parse_args()

    if args.notice:
        # Deferred import so --notice doesn't pay the Textual startup cost.
        from gakkari.cli import print_notice
        sys.exit(print_notice(lang_override=args.lang))

    from gakkari.app import GakkariApp
    GakkariApp().run()


if __name__ == "__main__":
    main()
