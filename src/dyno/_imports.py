"""Load "package.module:attribute" paths (custom agents and custom checks)."""

from __future__ import annotations

import importlib
from typing import Any


def load_attr(target: str) -> Any:
    if ":" not in target:
        raise ValueError(f"expected 'package.module:attribute', got {target!r}")
    module_name, attr = target.split(":", 1)
    return getattr(importlib.import_module(module_name), attr)
