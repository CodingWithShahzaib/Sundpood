from __future__ import annotations

import os
import sys


def work_root() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def bundle_root() -> str:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return str(getattr(sys, "_MEIPASS"))
    return work_root()


def app_path(*parts: str) -> str:
    return os.path.join(work_root(), *parts)


def resource_path(*parts: str) -> str:
    return os.path.join(bundle_root(), *parts)
