"""Lets you run the project as `python -m shopper ...` (same as the `shopper` command)."""

import sys

from shopper.cli import main

sys.exit(main())
