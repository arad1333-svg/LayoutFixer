# LayoutFixer macOS Port — Phase 1 Status (Handover)

> **Read this first**, then `MAC_HANDOFF.md` (one folder up, at
> `/Users/aradkiriaty/Documents/layoutfixer/MAC_HANDOFF.md`) for full background if anything
> here is unclear.
> The user has **no coding background** — explain every command in plain English, run one
> step at a time, and pause to confirm it worked before moving on.

---

## Where we are

Phase 1 plan = `MAC_HANDOFF.md`, Section 8 (12 steps). **Steps 1–10 are done. ✅**
(including Step 6.5 — Save-button UX — two macOS 26 crash fixes, icon redesign,
real Light theme + System option removed, toggle-pill seam fix; test suite
102/102 passing.)

Committed on `main`: `0769f08` (port fixes + Save UX), `e83e511` (new icon),
`77f23a4` (light theme + pill seam + mac spec fix), `8741996` (permission
gate + Accessory policy + third SIGTRAP fix + geresh mapping).
**Not yet pushed to origin.** Tests now 104/104.

Build artifacts (not committed, current with `8741996`):
`layoutfixer/dist/LayoutFixer.app` (45 MB) and `layoutfixer/dist/LayoutFixer.dmg`
(19 MB, drag-to-Applications). DMG install + full first-run flow (permission
gate) tested by user on 2026-07-04 — working. The installed
/Applications/LayoutFixer.app is one build older (pre gate-redesign,
functionally identical).

**Step 11 DONE (2026-07-04 evening):** version bumped to 1.2.0 (`d5cacc3`),
all commits pushed to origin/main, release **v1.2.0** published as Latest at
https://github.com/arad1333-svg/LayoutFixer/releases/tag/v1.2.0 with two
assets: `LayoutFixer_v1.2.0.dmg` (mac) and `LayoutFixer_Setup_v1.1.0.exe`
(unchanged Windows build, re-attached so the releases/latest link keeps
serving Windows users). GitHub CLI (`~/bin/gh`) installed and authenticated
as arad1333-svg on this Mac (keyring token, git credential helper set up).

**Step 12 DONE (2026-07-04 evening):** landing page (`docs/index.html`,
commit `190db8d`) now detects the visitor's OS in-browser — hero + bottom CTA
offer the right installer (direct asset links resolved from the GitHub
latest-release API, releases page as no-JS fallback), an outlined
"Also available for …" button links to the other platform, step 02 shows
"Double-tap Globe" on Macs, copy made platform-neutral. Pushed live.

**v1.2.1 (2026-07-04, late evening, commit `5edddc5`):** feedback from the
first real macOS downloader — startup "app is running" notification now works
on macOS (osascript; pystray notify is Windows-only), start-at-login defaults
ON and self-enrolls in the packaged app (sys.frozen guard keeps dev runs out
of Login Items), landing-page version label self-updates from the latest
release tag. Released as Latest with the same unchanged Windows exe attached.

## 🏁 PHASE 1 COMPLETE — all 12 steps done (2026-07-04)

Remaining known follow-ups (not part of Phase 1):
- The .app is ad-hoc signed, NOT notarized — downloaded copies trigger
  Gatekeeper (right-click → Open once). Apple Developer ID signing +
  notarization ($99/yr) would remove the warning AND end the stale
  Accessibility-grant dance on app updates. Recommended before promoting.
- Windows: rebuild + release with the new icon, Save UX, and Light theme
  (shared code, untested visually on real Windows — 5-min QA needed).
- The build is Apple Silicon only (arm64); a universal2/Intel build would
  need target_arch='universal2' in the spec and universal deps.

Notes for future sessions:
- **User rule — Windows parity**: every change (UI, icon, features) must also apply
  to the Windows version when possible; only platform-specific bug fixes may be
  platform-guarded. All of today's UI/icon changes are in shared code or shared
  assets, but Windows needs a rebuild + a quick visual QA (esp. Light mode) on a
  real Windows machine before the next Windows release.
- Theme: Dark/Light only. All settings_window colors are (light, dark)
  tuples resolved by _c() for plain-tk widgets; custom widgets re-render via
  window._theme_refreshers on theme change. Legacy 'system' → 'dark'.
- The .app needs its own Accessibility grant (separate from Python's), and a
  rebuilt/reinstalled .app may require re-granting (toggle off/on) because
  the binary changes. After a rebuild, clear stale grants with
  `tccutil reset Accessibility com.layoutfixer.app` (and
  `tccutil reset ListenEvent com.layoutfixer.app`) — otherwise the
  Accessibility toggle shows ON but doesn't apply. The first-run permission
  gate (permission_gate.py) handles the re-grant flow gracefully either way.
- First-run UX: permission_gate.py polls AXIsProcessTrusted and continues
  startup automatically once granted — never instruct users to restart.
- macOS 26 SIGTRAP rule (three fixes shipped): TIS*/TSM input-source calls
  and NSEvent.eventWithCGEvent_ must never run off the main thread. Any new
  code touching input sources must marshal to the main thread (see
  layout_mac._run_on_main_thread and hotkey_listener._KeyEventsOnlyListener).
- Proper codesigning (stable identity instead of ad-hoc per-build signatures)
  would eliminate the stale-grant dance for app updates — consider before a
  wide release.

### Icon redesign (2026-07-04, user-approved)

Old blue-circle icon violated the no-blue Kinetic Terminal rule. New design
("The Swap", picked by user from 3 candidates): muted grey א fading behind a
glowing LED-green A on a dark squircle — matches the landing-page hero
animation. `assets/generate_icon.py` regenerates icon.png (1024) + icon.ico;
icon.icns was written via Pillow (`Image.open('icon.png').save('icon.icns',
format='ICNS')` — note: `sips -s format icns` errors out on this machine).

- Repo root: `/Users/aradkiriaty/Documents/layoutfixer/LayoutFixer`
- App folder (run all commands from here): `/Users/aradkiriaty/Documents/layoutfixer/LayoutFixer/layoutfixer`
- Branch: `main`. **Six files changed, not yet committed** (6 modified + 4 untracked):
  ```
   M CLAUDE.md                        (minor additions from earlier session)
   M layoutfixer/hotkey_listener.py   (earlier fix + caps-lock SIGTRAP fix — see below)
   M layoutfixer/main.py              (good fix, earlier session — tray icon)
   M layoutfixer/plat/layout_mac.py   (ctypes layout switch + main-thread marshalling fix)
   M layoutfixer/settings_window.py   (Step 6.5 — Save button UX, this session)
   M layoutfixer/tray_app.py          (two fixes: tray icon + Settings crash queue fix)
  ?? .claude/skills/                  (skill files — do not commit)
  ?? MAC_HANDOFF_STATUS.md            (this file — do not commit)
  ?? tools/test_pynput_settings.py    (diagnostic script — safe to delete)
  ?? tools/test_tray_tk.py            (diagnostic script — safe to delete)
  ```
- No stray processes currently running.

---

## Environment already set up — don't redo this

- **Python 3.12.10** installed via the official python.org installer (universal2 build). It is
  now the default `python3` / `pip3` (`/usr/local/bin/python3` → `/Library/Frameworks/Python.framework/Versions/3.12/`).
  The Mac's original system Python 3.9.6 is untouched but no longer default.
- **All required pip packages installed**: pyperclip, pynput (1.8.2), pystray, customtkinter,
  Pillow, pyinstaller, pytest, pyobjc-framework-Quartz, pyobjc-framework-Cocoa,
  pyobjc-framework-ApplicationServices, pyobjc-framework-CoreText.
- **Accessibility AND Input Monitoring permissions** granted to Python
  (`/Library/Frameworks/Python.framework/Versions/3.12/Resources/Python.app/Contents/MacOS/Python`)
  in System Settings → Privacy & Security. Also Terminal has Accessibility permission.
- **Hebrew keyboard input source is already enabled** in System Settings, named exactly
  `"Hebrew"`. The English layout on this Mac is named `"ABC"` (not the commonly-assumed `"U.S."`).
- Mac details: Apple Silicon (arm64), macOS 26.4.

---

## ✅ RESOLVED — tray icon now appears and works correctly

(See previous sessions for full details — fix is in `layoutfixer/main.py` and `layoutfixer/tray_app.py`.)

---

## ✅ RESOLVED — "Open Settings" crash is fixed

(See previous sessions for full details — fix is in `layoutfixer/tray_app.py` via `queue.SimpleQueue` + `_start_callback_poller`.)

---

## ✅ RESOLVED — Layout switch now works and is fast

### The bug (fixed this session)

The AppleScript fallback used `tell process "SystemUIServer"`, but on this version of macOS
the input-source menu is owned by `TextInputMenuAgent` (not `SystemUIServer`). This caused
`Invalid index (-1719)` errors silently, so the switch did nothing.

### Two-part fix applied this session

**Fix 1 — AppleScript process name** (one-word change):
- Changed `"SystemUIServer"` → `"TextInputMenuAgent"` in `_switch_via_applescript()`.
- This made layout switching work, but it was slow (spawning osascript subprocess + UI automation).

**Fix 2 — ctypes fast path** (replaced `_switch_via_carbon` entirely):
- Removed the old `from Carbon import HIToolbox` import attempt (always fails on Python 3.12).
- Replaced with a direct `ctypes.CDLL` call into
  `/System/Library/Frameworks/Carbon.framework/Carbon`, calling `TISCreateInputSourceList`
  and `TISSelectInputSource` natively — no subprocess, no UI automation.
- Frameworks are loaded once and cached at module level.
- AppleScript remains as a fallback if ctypes ever fails.
- Result: layout switch is now instant (milliseconds instead of 1–2 seconds).

### `current_layout()` also fixed

Same ctypes approach — now reads `TISCopyCurrentKeyboardInputSource` + language property
directly instead of trying `from Carbon import HIToolbox`.

---

## ✅ Step 6 — All interactive tests passed

| Test | Result |
|------|--------|
| Accessibility permission dialog on first run | ✅ Shown correctly |
| Tray icon + menu | ✅ Working |
| Open Settings (crash was fixed) | ✅ Working |
| Exit | ✅ Working |
| Clipboard conversion (select gibberish, double-tap Globe) | ✅ Working |
| Layout switch (en↔he) | ✅ Working and fast |
| Clipboard restore after conversion | ✅ Working |

---

## ✅ DONE THIS SESSION (2026-07-04)

### Step 6.5 — Save-button UX polish ✅

Implemented in `layoutfixer/settings_window.py` and confirmed working interactively:
- Window snapshots all input values on open (`_saved_values` / `_current_values()`).
- All inputs watched (var traces + `<KeyRelease>` on keymap entries). Any unsaved
  change anywhere lights BOTH Save buttons green (user chose this over per-tab
  lighting, since Save writes all tabs at once and Key Map has no Save button).
- Save keeps the window open and greys the buttons back out; grey button click is
  a no-op. Undoing a change back to the saved value also greys the buttons.

### Crash fix 1 — Caps Lock killed the app (SIGTRAP) ✅

macOS 26 kills the process when pynput converts NSSystemDefined (media-key) events
to NSEvent on its tap thread — triggered every time the user pressed Caps Lock to
switch Hebrew/English. Fix in `hotkey_listener.py`: `_KeyEventsOnlyListener`
subclass drops NSSystemDefined from the event-tap mask (Globe arrives as a normal
key-down, vk=179, so detection is unaffected).

### Crash fix 2 — layout switch off the main thread (SIGTRAP) ✅

Same macOS 26 rule: TIS* input-source calls must run on the main dispatch queue.
Our ctypes fast path ran them on the conversion worker thread and crashed
(intermittently — more likely right after Caps Lock use). Fix in
`plat/layout_mac.py`: `_run_on_main_thread()` marshals all TIS calls through
tray_app's existing `_tk_schedule` queue (drained every 50 ms by the Tk main
loop), with direct-call fallback when no Tk root exists (tests/CLI) and
AppleScript fallback on timeout. Crash-recipe retested by user: fixed, still fast.

### Step 7 — Test suite ✅

`python3 -m pytest ../tests/ -v` → **102/102 passed**.

## NEXT STEP for the new session

- **Commit** all 6 modified files together (not the untracked diagnostics/status/skills
  files) — pending user go-ahead at end of 2026-07-04 session.

---

## Remaining Phase 1 steps (from `MAC_HANDOFF.md` Section 8)

- **Steps 1–7 (incl. 6.5)** ✅ DONE.
- **Step 8** — Generate the app icon:
  ```bash
  sips -s format icns assets/icon.png --out assets/icon.icns
  ```
- **Step 9** — Build the `.app` bundle:
  ```bash
  pyinstaller build/layoutfixer_mac.spec --clean --noconfirm
  ```
  Output: `dist/LayoutFixer.app`. Test by double-clicking (must run without Terminal). A fresh
  `.app` will re-trigger the Accessibility prompt — expected.
- **Step 10** — Build the `.dmg` installer:
  ```bash
  pip3 install dmgbuild
  dmgbuild -s build/dmgbuild_settings.py "LayoutFixer" dist/LayoutFixer.dmg
  ```
- **Step 11** — Create a GitHub release (e.g. tag `v1.2.0`), attach `dist/LayoutFixer.dmg`.
- **Step 12** — Update `docs/index.html` with a macOS download button + platform-detection JS.

---

## Working style reminders (from `CLAUDE.md` / past sessions)

- **No coding background** — plain English always, one step at a time, confirm before
  proceeding.
- If something crashes during testing, **explain crash dialogs immediately**.
- After any test run, **always check for and clean up stray background processes**
  (`ps aux | grep main.py`) before starting the next attempt.
- **Branch convention**: work on `TEST`, merge to `main`, push `origin/main`. All fixes so far
  are uncommitted on `main` directly — commit once Step 6.5 is done.
- Don't commit build artifacts, `__pycache__`, `.claude/`, `MAC_HANDOFF_STATUS.md`, or
  `tools/test_*.py` files.
- Design system ("Kinetic Terminal", LED-green `#8eff71`, no blue) is in `CLAUDE.md`.
- The `tools/` folder is the established place for small standalone diagnostic scripts.
