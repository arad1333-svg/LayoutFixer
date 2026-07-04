# layoutfixer_mac.spec — PyInstaller spec for macOS .app bundle
#
# Usage (run on an actual Mac):
#   cd layoutfixer
#   pyinstaller build/layoutfixer_mac.spec --clean --noconfirm
#
# Prerequisites:
#   pip install pyobjc-framework-Quartz pyobjc-framework-Cocoa \
#               pyobjc-framework-ApplicationServices
#   icon.icns must exist at layoutfixer/assets/icon.icns
#   (generate with: sips -s format icns assets/icon.png --out assets/icon.icns
#    or use iconutil on a proper iconset folder)

import sys
from pathlib import Path

block_cipher = None

root = Path(SPECPATH).parent  # layoutfixer/  (SPECPATH = build/)

a = Analysis(
    [str(root / 'main.py')],
    pathex=[str(root)],
    binaries=[],
    datas=[
        (str(root / 'assets'), 'assets'),   # icon.png, icon.icns
    ],
    hiddenimports=[
        'pynput.keyboard._darwin',
        'pynput.mouse._darwin',
        'AppKit',
        'Quartz',
        'ApplicationServices',
        'Carbon',
        'Foundation',
        'objc',
        'plat',
        'plat.clipboard_mac',
        'plat.layout_mac',
        'plat.autostart_mac',
        'plat.system_mac',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'win32api', 'win32clipboard', 'win32con', 'winreg',
        'plat.clipboard_win', 'plat.layout_win', 'plat.autostart_win', 'plat.system_win',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='LayoutFixer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No terminal window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(root / 'assets' / 'icon.icns'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='LayoutFixer',
)

app = BUNDLE(
    coll,
    name='LayoutFixer.app',
    icon=str(root / 'assets' / 'icon.icns'),
    bundle_identifier='com.layoutfixer.app',
    info_plist={
        'CFBundleName': 'LayoutFixer',
        'CFBundleDisplayName': 'LayoutFixer',
        'CFBundleVersion': '1.2.0',
        'CFBundleShortVersionString': '1.2.0',
        'NSHighResolutionCapable': True,
        # Hide from Dock — menu bar app only
        'LSUIElement': True,
        # Required for Accessibility permission (pynput suppress=True)
        'NSAccessibilityUsageDescription': (
            'LayoutFixer needs Accessibility access to detect the Globe key '
            'double-tap and simulate copy/paste keystrokes.'
        ),
        # Human Language
        'CFBundleDevelopmentRegion': 'en',
        'CFBundleSupportedPlatforms': ['MacOSX'],
    },
)
