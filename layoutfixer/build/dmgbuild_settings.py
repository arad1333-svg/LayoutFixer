# build/dmgbuild_settings.py — Configuration for dmgbuild
#
# Usage (run from the layoutfixer/ directory on Mac after PyInstaller build):
#   pip install dmgbuild
#   dmgbuild -s build/dmgbuild_settings.py "LayoutFixer" dist/LayoutFixer.dmg
#
# Produces a standard drag-to-Applications installer DMG.

import os.path

# Source application path (relative to where dmgbuild is run — layoutfixer/)
application = defines.get('app', 'dist/LayoutFixer.app')
appname = os.path.basename(application)

# DMG format: UDZO = zlib-compressed, read-only (standard for distribution)
format = defines.get('format', 'UDZO')

# Files placed inside the DMG window
files = [application]

# Symlink to /Applications so the user can drag-to-install
symlinks = {'Applications': '/Applications'}

# Icon positions: app on left, Applications folder on right
icon_locations = {
    appname:        (130, 150),
    'Applications': (390, 150),
}

# Arrow background (built-in dmgbuild style — no custom image needed)
background = 'builtin-arrow'

# DMG Finder window: position (x, y) and size (width, height)
window_rect = ((100, 100), (540, 330))

# Icon and label sizes
icon_size = 128
text_size = 14
