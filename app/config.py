"""Runtime configuration for the app (toggleable during tests/runtime)."""
from typing import NamedTuple


class ConfigState(NamedTuple):
    vulnerable: bool


# Default: non-vulnerable
state = ConfigState(vulnerable=False)


def set_vulnerable(value: bool):
    global state
    state = ConfigState(vulnerable=bool(value))


def is_vulnerable() -> bool:
    return state.vulnerable
