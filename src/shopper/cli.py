"""The `shopper` command: one entry point for every step of the project.

    shopper doctor        check the machine, the .env file and the client configs     (Step 00)
    shopper models        list the Gemini chat models this key can use                (Step 01)
    shopper ping          send one test message (--tool also tests function calling)  (Step 01)

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


def cmd_models(args: argparse.Namespace) -> None:
    from shopper.llm import list_models, make_client

    models = list_models(make_client())
    print(f"{'model':<40} {'input token limit':>18}")
    for model in models:
        print(f"{model.name:<40} {model.input_token_limit:>18,}")
    print(f"\n{len(models)} chat models")


def cmd_ping(args: argparse.Namespace) -> None:
    from shopper.config import load_client
    from shopper.llm import make_client, ping

    model = args.model or load_client(args.client).llm.model
    if not model:
        raise UserError(
            f"no model chosen: pass --model NAME, or set llm.model in clients/{args.client}/client.yaml"
        )

    result = ping(make_client(), model, with_tool=args.tool)
    print(f"model          {result.model}")
    print(f"reply          {result.reply}")
    if result.made_tool_call is not None:
        print(f"tool call      {'yes' if result.made_tool_call else 'NO - this model did not call the tool'}")
    print(f"tokens         {result.input_tokens} in, {result.output_tokens} out")
    print(f"time           {result.seconds} s")


# ---- parser ------------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="shopper", description="A retail assistant on Gemini.")
    parser.add_argument("-v", "--verbose", action="store_true", help="show debug logging")
    commands = parser.add_subparsers(dest="command", required=True)

    doctor = commands.add_parser("doctor", help="check the machine, .env and client configs")
    doctor.set_defaults(handler=cmd_doctor)

    models = commands.add_parser("models", help="list the Gemini chat models this key can use")
    models.set_defaults(handler=cmd_models)

    ping = commands.add_parser("ping", help="send one test message to Gemini")
    ping.add_argument("--model", help="model name (default: llm.model in the client's config)")
    ping.add_argument("--tool", action="store_true", help="also check the model calls a function")
    ping.add_argument("--client", default="shoppers_stop", help="client folder under clients/")
    ping.set_defaults(handler=cmd_ping)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(message)s")
    if not args.verbose:
        # The Gemini SDK's HTTP library logs every request at INFO; keep that for -v only.
        # google-genai 3.x uses "httpx2"; older versions use "httpx".
        for name in ["httpx", "httpx2"]:
            logging.getLogger(name).setLevel(logging.WARNING)
    try:
        args.handler(args)
    except UserError as error:
        log.error(f"error: {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
