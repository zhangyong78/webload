# -*- mode: python ; coding: utf-8 -*-

import os


a = Analysis(
    ['run_windows.pyw'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

# Ignore unrelated ICU libraries discovered on PATH (for example Poppler's
# version-suffixed ICU). Qt on Windows uses the system ICU implementation.
a.binaries = [
    item
    for item in a.binaries
    if os.path.basename(item[0]).casefold() != 'icuuc.dll'
    and not (
        os.path.basename(item[0]).casefold().startswith('icudt')
        and os.path.basename(item[0]).casefold().endswith('.dll')
    )
]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='OKXFlashEarnReminder_v0.1.6',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='OKXFlashEarnReminder_v0.1.6',
)
