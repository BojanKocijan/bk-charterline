"""Where the installed rules live (#199).

BK Charterline installs to ~/.bk-charterline. Installs from before v3.0.0
used ~/.design-forge; the v3.0.0 install moves that folder and leaves the
old name as a link for one release. Until an install has moved, the hook
and the scripts find it under either name.

It imports nothing from the repo, so the hook and every script can import it.
Dependency-free stdlib only.
"""
from __future__ import annotations

import os

NEW_NAME = ".bk-charterline"
OLD_NAME = ".design-forge"  # before v3.0.0; after the move, a link to NEW_NAME


def _home(home: str | None) -> str:
    return home if home is not None else os.path.expanduser("~")


def rules_home(home: str | None = None) -> str:
    """~/.bk-charterline when it exists; ~/.design-forge when only that
    exists (an install from before the move); else ~/.bk-charterline."""
    new = os.path.join(_home(home), NEW_NAME)
    old = os.path.join(_home(home), OLD_NAME)
    return old if not os.path.isdir(new) and os.path.isdir(old) else new


def install_dirs(home: str | None = None) -> list[str]:
    """Every path the installed clone may have, links resolved, without
    duplicates: after the move the old name resolves to the new folder."""
    seen: list[str] = []
    for name in (NEW_NAME, OLD_NAME):
        real = os.path.realpath(os.path.join(_home(home), name))
        if real not in seen:
            seen.append(real)
    return seen
