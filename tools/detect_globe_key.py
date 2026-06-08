#!/usr/bin/env python3
"""
tools/detect_globe_key.py — Find the Globe key's virtual keycode on this Mac.

Run this FIRST on the Mac, before doing anything else in Phase 1:

    python3 tools/detect_globe_key.py

Press a few normal keys, then press the Globe key (🌐) once.
The script prints each key's virtual keycode (vk).

Expected Globe vk: 63
If it prints something different, update _GLOBE_VK in:
    layoutfixer/hotkey_listener.py  (class GlobeTapListener)

Press Ctrl+C to quit.

NOTE: If the Globe key doesn't appear at all in the output, it may be
firing as a kCGEventFlagsChanged event instead of a keydown event.
In that case, report back and we will switch to a Quartz event tap approach.
"""
import sys

if sys.platform != 'darwin':
    print("ERROR: This script must be run on macOS.")
    sys.exit(1)

try:
    from pynput import keyboard
except ImportError:
    print("ERROR: pynput is not installed.")
    print("Run:  pip install pynput")
    sys.exit(1)

print()
print("=" * 55)
print("  LayoutFixer — Globe Key Detection Tool")
print("=" * 55)
print()
print("  Press any keys to see their virtual keycodes.")
print("  Press the Globe key (🌐) — expected: vk=63")
print()
print("  Press Ctrl+C to quit.")
print("-" * 55)


def on_press(key):
    vk   = getattr(key, 'vk',   None)
    char = getattr(key, 'char', None)
    name = getattr(key, 'name', None)

    if vk is not None:
        # Flag keys outside printable ASCII range as candidates for Globe
        flag = "  ← possible Globe key!" if vk not in range(32, 127) else ""
        print(f"  vk={vk:<5}  repr={key!r}{flag}")
    elif name:
        print(f"  name={name!r:<20}  repr={key!r}")
    elif char:
        print(f"  char={char!r:<20}  repr={key!r}")
    else:
        print(f"  (unknown)  repr={key!r}")


with keyboard.Listener(on_press=on_press, suppress=False) as listener:
    try:
        listener.join()
    except KeyboardInterrupt:
        print()
        print("Done.")
        print()
        print("If Globe key DID appear above:")
        print("  → note the vk number")
        print("  → if it's not 63, update _GLOBE_VK in hotkey_listener.py")
        print()
        print("If Globe key did NOT appear above:")
        print("  → the Globe key fires as a flags-changed event")
        print("  → report back and we will use a different detection method")
        print()
