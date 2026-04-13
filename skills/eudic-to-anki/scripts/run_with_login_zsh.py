#!/usr/bin/env python3
"""Run command under `zsh -lic` so login+interactive zsh loads user profiles."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: run_with_login_zsh.py <command> [args...]", file=sys.stderr)
        return 2
    zsh = shutil.which("zsh")
    if not zsh:
        print("error: zsh not found in PATH", file=sys.stderr)
        return 127
    inner = "cd " + shlex.quote(os.getcwd()) + " && exec " + " ".join(
        shlex.quote(a) for a in sys.argv[1:]
    )
    return subprocess.call([zsh, "-lic", inner])


if __name__ == "__main__":
    raise SystemExit(main())
