"""The `shopper` command: one entry point for every step of the project.

    shopper doctor        check the machine, the .env file and the client configs     (Step 00)

Each command only parses its options and calls a function in the package, so the real work
can be tested without the command line. Imports are inside the handlers on purpose: they keep
`shopper --help` instant once the voice and cloud libraries are installed.
"""

import argparse
import logging
import sys

from shopper.errors import UserError

log = logging.getLogger("shopper")


# ---- handlers: one small function per command ----------------------------------------------


def cmd_doctor(args: argparse.Namespace) -> None:
    from shopper.doctor import run_doctor

    for check, result in run_doctor():
        print(f"{check:<22} {result}")


# ---- parser ------------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="shopper", description="A retail assistant on Gemini.")
    parser.add_argument("-v", "--verbose", action="store_true", help="show debug logging")
    commands = parser.add_subparsers(dest="command", required=True)

    doctor = commands.add_parser("doctor", help="check the machine, .env and client configs")
    doctor.set_defaults(handler=cmd_doctor)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(message)s")
    try:
        args.handler(args)
    except UserError as error:
        log.error(f"error: {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
