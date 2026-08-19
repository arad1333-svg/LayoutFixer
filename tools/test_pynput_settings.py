"""Standalone test: verify the queue-based _tk_schedule fix stops the crash.

EXPERIMENT 9 (fix verification):
  Root cause (from native crash report of Experiments 7 & 8):
    pystray NSMenuItem callbacks re-acquire the Python GIL via pyobjc's
    PyGILState_Ensure(), bypassing tkinter's own PyEval_SaveThread /
    PyEval_RestoreThread pair. This leaves tkinter's internal saved-tstate as
    NULL. The next root.after() callback that calls PythonCmd →
    PyEval_RestoreThread(NULL) → fatal crash.
    Even calling root.after(0, fn) from the callback was enough to crash
    (Experiment 8).

  The fix (now applied to tray_app.py):
    - _tk_schedule(fn) just puts fn into a queue.SimpleQueue — no Tcl calls.
    - _start_callback_poller(root) sets up a root.after(50, ...) loop that
      drains the queue from the safe Tcl context.
    - create_tray() now calls _start_callback_poller() automatically.

  This experiment is identical to Experiment 7 (real tray icon, real click),
  but uses the fixed tray_app.create_tray() which wires up the queue poller.

Run with:
    python3.12 -u tools/test_pynput_settings.py > /tmp/test_pynput.log 2>&1 &

Click the LayoutFixer icon → "Open Settings". Should open without crashing.
Auto-shutdown in 60 seconds.
"""

import os
import sys
import tkinter as tk
import __main__

_APP_DIR = os.path.join(os.path.dirname(__file__), '..', 'layoutfixer')
sys.path.insert(0, os.path.abspath(_APP_DIR))

import customtkinter as ctk

print("Starting REAL HotkeyListener (GlobeTapListener)...", flush=True)

from hotkey_listener import HotkeyListener
import settings_manager
import tray_app


def run_conversion():
    pass


listener = HotkeyListener(hotkey='ctrl+alt+z', callback=run_conversion)
listener.start()

ctk.set_appearance_mode('system')
ctk.set_default_color_theme('blue')

root = tk.Tk()
root.withdraw()
__main__._tk_root = root

settings = settings_manager.load()

from settings_window import open_settings


def on_open_settings():
    print("on_open_settings() called — queue poller delivered it safely.", flush=True)
    open_settings(listener=listener)
    print("open_settings() returned.", flush=True)


def on_quit():
    print("on_quit() called.", flush=True)
    listener.stop()
    if tray_app._tray_icon:
        tray_app._tray_icon.visible = False
    root.quit()


# create_tray() now starts _start_callback_poller() automatically
tray_app.create_tray(listener, settings, on_open_settings, on_quit)

print("Tray icon is in the menu bar. Click it and choose 'Open Settings'.", flush=True)
print("Auto-shutdown in 60 seconds.", flush=True)


def shutdown():
    print("60-second timeout — shutting down.", flush=True)
    listener.stop()
    if tray_app._tray_icon:
        tray_app._tray_icon.visible = False
    root.quit()


root.after(300000, shutdown)

root.mainloop()
print("mainloop() exited.", flush=True)
