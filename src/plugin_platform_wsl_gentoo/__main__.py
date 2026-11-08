"""`python -m plugin_platform_wsl_gentoo status | setup [STEP ...] | run -- COMMAND | instances`: the plugin from the
command line (the platform app drives the same hooks)."""
from __future__ import annotations

import json
import sys

from . import MACHINE


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    what = argv[0] if argv else "status"
    if what == "status":
        print(json.dumps(MACHINE.status(), indent=1))
        return 0 if MACHINE.present() else 1
    if what == "setup":
        done = MACHINE.setup(log=print, steps=argv[1:] or None)
        return 0 if all(d["ok"] is not False for d in done) else 1
    if what == "run":
        command = argv[2:] if len(argv) > 1 and argv[1] == "--" else argv[1:]
        if not command:
            print(f"a command is needed: python -m plugin_platform_wsl_gentoo run -- ls /", file=sys.stderr)
            return 2
        print(MACHINE.run(*command), end="")
        return 0
    if what == "instances":
        print(json.dumps([i.describe() for i in MACHINE.instances()], indent=1))
        return 0
    print(f"python -m plugin_platform_wsl_gentoo status | setup [STEP ...] | run -- COMMAND | instances", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
