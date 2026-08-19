"""Standalone test: can pystray's tray icon appear and respond to clicks
while tkinter's mainloop is the only running event loop?

Run with:
    python3.12 -u tools/test_tray_tk.py > /tmp/test_tray.log 2>&1 &

Expected: a solid green square appears in the macOS menu bar. Clicking it
shows a "Quit" menu item; clicking "Quit" closes the script.
"""

import threading
import tkinter as tk

import pystray
from PIL import Image

root = tk.Tk()
root.withdraw()


def on_quit(icon, item):
    try:
        icon.visible = False
    except Exception as e:
        print(f"icon.visible = False raised: {e!r}", flush=True)
    root.quit()


icon = pystray.Icon(
    name='test',
    icon=Image.new('RGBA', (64, 64), (143, 255, 113, 255)),  # solid green square
    title='Test',
    menu=pystray.Menu(pystray.MenuItem('Quit', on_quit)),
)

# Do NOT call icon.run() / icon._run() — that would start a second,
# competing event loop. Instead, manually mark the icon ready and visible,
# relying on tkinter's mainloop() to pump the shared NSApplication loop.
icon._mark_ready()
icon.visible = True

print("Tray icon marked ready and visible. Starting tkinter mainloop()...", flush=True)
print(f"Main thread: {threading.current_thread().name}", flush=True)

root.mainloop()

print("mainloop() exited.", flush=True)
