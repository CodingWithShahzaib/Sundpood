from __future__ import annotations

import os
from typing import Iterable, List

from data.app_context import ctx


def iter_sound_paths() -> Iterable[str]:
    """
    Yield normalized full paths from ctx.menu structure.
    ctx.menu is a list of categories, each is [dir_path, file1, file2, ...]
    """
    for cat in ctx.menu or []:
        if not isinstance(cat, list) or len(cat) < 2:
            continue
        dir_path = cat[0]
        for f in cat[1:]:
            yield os.path.normpath(os.path.join(dir_path, f))


def category_display_name(category_path: str) -> str:
    path = os.path.normpath(str(category_path or ""))
    root = os.path.normpath(str(ctx.dir_ or ""))
    if not path:
        return ""
    if path.rstrip("\\/").lower() == root.rstrip("\\/").lower():
        return "All Sounds"
    return os.path.basename(path.rstrip("\\/")) or path


def list_sound_paths() -> List[str]:
    return list(iter_sound_paths())

