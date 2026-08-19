# LayoutFixer — Claude Code Instructions

## CEO Agent Workflow (Active — apply every session)

This project uses a structured multi-agent workflow. Follow it for every non-trivial task.

### The Team

| Role | Who | Responsibility |
|------|-----|----------------|
| **CEO** | Claude (main conversation) | Receive assignment, challenge scope, ask clarifying questions, coordinate agents, resolve conflicts, present summaries for user approval |
| **Design Agent** | Subagent (`Explore` or `general-purpose`) | Visual specs, HTML preview pages, design-to-code mappings, Stitch mockups |
| **CTO Agent** | Subagent (`general-purpose`) | Bug audits, code implementation, test verification, build updates |
| **Marketing Agent** | Subagent (`general-purpose`) | Copy, microcopy, labels, error messages, voice/tone consistency |

Not every task requires all three agents — spin up only the ones relevant to the work.

---

### Workflow Protocol

#### Step 1 — Challenge & Clarify (CEO)
Before doing anything, ask enough questions to understand:
- What exactly needs to change
- What must stay the same
- The scope (visual only? functional? both?)
- How the user wants to review outputs

Do not assume. A 2-minute Q&A prevents an hour of rework.

#### Step 2 — Parallel Research (Agents)
Launch Design Agent and CTO Agent in parallel (single message, two `Agent` tool calls) with specific, isolated briefs. Each agent gets only what it needs — no cross-contamination of concerns.

#### Step 3 — CEO Integration Review
Collect both outputs. Cross-check:
- Does the design fit the technical constraints?
- Does the copy fit the layout space?
- Are there conflicts between agents?

Resolve conflicts. Do NOT write any code yet.

#### Step 4 — Live Preview Gate
For any visual change, the Design Agent creates an HTML preview in `preview/` using the website's exact CSS tokens. Serve it with `py -m http.server 5500`. Send the link to the user.

**No Python code changes until the user approves the preview.**

#### Step 5 — Implementation (CTO Agent)
After user approval, dispatch the CTO Agent with a precise implementation brief that includes:
- Exact color values / constants to use
- File paths and line-level context
- Bug fixes to apply in the same pass
- What NOT to change

#### Step 6 — Verification
Always run tests after implementation:
```bash
cd layoutfixer && py -m pytest ../tests/ -v      # Windows
cd layoutfixer && python3 -m pytest ../tests/ -v # macOS
```
Confirm 104/104 pass. Check for leftover old color values or patterns.

#### Step 7 — Commit & Push
Stage only source files (not build artifacts, not `.claude/`, not `SESSION_*.md`).
Commit with a detailed message covering both visual and functional changes.
Merge `TEST` → `main` → push to `origin/main`.

---

### Design System — Kinetic Terminal

The app and website share one design system. Never introduce colors outside this palette.

```python
# Color constants (use these names in settings_window.py).
# The app supports Dark + Light themes: in settings_window.py each constant
# is a (light, dark) tuple; the dark values are listed below and remain the
# canonical brand palette. Plain-tk widgets resolve tuples via _c() and are
# re-rendered on theme change (see _theme_refreshers).
PRIMARY          = '#8eff71'   # LED green — all interactive accents
PRIMARY_HOVER    = '#2ff801'   # Bright green — hover states
ON_PRIMARY       = '#064200'   # Dark green — text ON green backgrounds
SURFACE          = '#0e0e0e'   # Main window background
SURFACE_LOW      = '#131313'   # Tab bar, secondary backgrounds
SURFACE_CONTAINER = '#1a1919'  # Tab content area, cards
SURFACE_HIGH     = '#201f1f'   # Elevated cards, secondary buttons
SURFACE_BRIGHT   = '#2c2c2c'   # Hover on containers
ON_SURFACE       = '#ffffff'   # Primary text
ON_SURFACE_VAR   = '#adaaaa'   # Secondary/muted text
OUTLINE          = '#777575'   # Visible borders (use sparingly)
OUTLINE_VAR      = '#494847'   # Subtle borders, toggle tracks
ERROR            = '#ff7351'   # Destructive actions
ERROR_HOVER      = '#e05a3a'   # Destructive hover
```

**Rules:**
- No blue anywhere (`#3b82f6` is gone)
- Font: `Segoe UI` in customtkinter (approximates Space Grotesk/Inter from the website)
- Separators: `fg_color=OUTLINE_VAR` at 1px, or use spacing instead
- Save buttons: `fg_color=PRIMARY, hover_color=PRIMARY_HOVER, text_color=ON_PRIMARY`
- Danger buttons: `fg_color=ERROR, hover_color=ERROR_HOVER`
- Switches/sliders: `button_color=PRIMARY, progress_color=PRIMARY`

---

### Settings Window — Current Tab Structure

```
General    → Auto-Switch Layout toggle
             Start with Windows toggle
             Show Notifications toggle
             Theme selector (Dark / Light — no System option; legacy
             stored value 'system' is treated as 'dark')
             [Save] button

Hotkey     → Radio buttons: Ctrl+Alt+X / Ctrl+Alt+Z / Ctrl+Alt+F
             [Save] button

Key Map    → Scrollable EN→HE remapping table
             [Reset to Defaults] button
```

No "Advanced" tab. The clipboard delay and debug log settings are gone from the UI (they exist in `settings_manager.DEFAULTS` but have no controls — intentional).

### Save Button UX (pending — implement after Step 6 testing passes, before Step 9 build)

The [Save] button on each tab must reflect whether there is anything to save:
- **Unsaved changes present**: button is fully active (normal PRIMARY green style).
- **No unsaved changes** (on open, or immediately after saving): button is visually
  inactive — faded/greyed out (use `state="disabled"` or a muted `fg_color`). It should
  still be clickable if the user tries, but do nothing (or save idempotently).
- After clicking Save: do NOT close the window. Just return the button to the inactive
  (no-changes) state.
- Track changed state per tab: switching tabs should not reset the dirty flag for other tabs.

---

### Project Quick Reference

Windows commands use `py`, macOS commands use `python3`.

**Run:** `cd layoutfixer && py main.py` (Windows) · `python3 main.py` (macOS)
**Test:** `cd layoutfixer && py -m pytest ../tests/ -v` (expect 104/104)
**Build exe (Windows):** `cd layoutfixer && py -m pyinstaller build/layoutfixer.spec --clean --noconfirm`
**Build installer (Windows):** run Inno Setup on `layoutfixer/build/installer.iss`
**Build .app (macOS):** `cd layoutfixer && python3 -m PyInstaller build/layoutfixer_mac.spec --clean --noconfirm`
**Build .dmg (macOS):** `cd layoutfixer && dmgbuild -s build/dmgbuild_settings.py "LayoutFixer" dist/LayoutFixer.dmg`
**Preview server:** `cd preview && py -m http.server 5500`

**Key files:**
- `layoutfixer/settings_window.py` — settings UI (customtkinter)
- `layoutfixer/settings_manager.py` — load/save `%APPDATA%/LayoutFixer/settings.json`
- `layoutfixer/hotkey_listener.py` — Windows: pynput GlobalHotKeys · macOS: Globe double-tap listener
- `layoutfixer/clipboard_handler.py` — full conversion pipeline
- `layoutfixer/converter.py` — Hebrew↔English character map (+ macOS geresh extra)
- `layoutfixer/tray_app.py` — pystray tray icon + menu (+ macOS main-thread callback queue)
- `layoutfixer/permission_gate.py` — macOS first-run Accessibility gate (polls until granted)
- `layoutfixer/plat/layout_mac.py` — macOS input-source switching (ctypes TIS, main-thread marshalled)
- `docs/index.html` — landing page (GitHub Pages, live on push to main; platform-aware download buttons)
- `preview/settings_preview.html` — HTML design preview (not shipped)

**macOS hard rule (macOS 26 kills the process otherwise):** TIS*/TSM input-source
calls and `NSEvent.eventWithCGEvent_` must only run on the main thread. Marshal via
`layout_mac._run_on_main_thread()` / `tray_app._tk_schedule()`; see
`hotkey_listener._KeyEventsOnlyListener` for the pynput workarounds.

**Branch convention:** work on `TEST`, merge to `main`, push `origin/main`.
