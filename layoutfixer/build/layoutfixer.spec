# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for LayoutFixer.

Build with:
    pyinstaller build/layoutfixer.spec --clean --noconfirm
"""
import sys
from pathlib import Path

block_cipher = None
root = Path(SPECPATH).parent  # layoutfixer/

a = Analysis(
    [str(root / 'main.py')],
    pathex=[str(root)],
    binaries=[],
    datas=[
        (str(root / 'assets' / 'icon.png'), 'assets'),
        (str(root / 'assets' / 'icon.ico'), 'assets'),
    ],
    hiddenimports=[
        'pynput.keyboard._win32',
        'pynput.mouse._win32',
        'win32timezone',
        'pkg_resources.py2_warn',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='LayoutFixer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,           # No terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=False,         # No admin rights required
    icon=str(root / 'assets' / 'icon.ico'),
    version_file=None,
)
