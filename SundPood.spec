# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


project_root = Path(SPECPATH)
icon_path = project_root / "icon.ico"
themes_dir = project_root / "themes"

datas = []
if icon_path.exists():
    datas.append((str(icon_path), "."))

if themes_dir.exists():
    for path in themes_dir.rglob("*"):
        if path.is_file():
            rel_parent = path.parent.relative_to(themes_dir).as_posix()
            dest_dir = "themes" if rel_parent == "." else f"themes/{rel_parent}"
            datas.append((str(path), dest_dir))

hiddenimports = list(
    dict.fromkeys(
        collect_submodules("data")
        + collect_submodules("pycaw")
        + [
            "pygame._sdl2.audio",
        ]
    )
)


a = Analysis(
    ["launcher.py"],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SundPood",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_path) if icon_path.exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="SundPood",
)
