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
cd layoutfixer && py -m pytest ../tests/ -v
```
Confirm 102/102 pass. Check for leftover old color values or patterns.

#### Step 7 — Commit & Push
Stage only source files (not build artifacts, not `.claude/`, not `SESSION_*.md`).
Commit with a detailed message covering both visual and functional changes.
Merge `TEST` → `main` → push to `origin/main`.

---

### Design System — Kinetic Terminal

The app and website share one design system. Never introduce colors outside this palette.

```python
# Color constants (use these names in settings_window.py)
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
             Theme selector (System / Dark / Light)
             [Save] button

Hotkey     → Radio buttons: Ctrl+Alt+X / Ctrl+Alt+Z / Ctrl+Alt+F
             [Save] button

Key Map    → Scrollable EN→HE remapping table
             [Reset to Defaults] button
```

No "Advanced" tab. The clipboard delay and debug log settings are gone from the UI (they exist in `settings_manager.DEFAULTS` but have no controls — intentional).

---

### Project Quick Reference

**Run:** `cd layoutfixer && py main.py`
**Test:** `cd layoutfixer && py -m pytest ../tests/ -v` (expect 102/102)
**Build exe:** `cd layoutfixer && py -m pyinstaller build/layoutfixer.spec --clean --noconfirm`
**Build installer:** run Inno Setup on `layoutfixer/build/installer.iss`
**Preview server:** `cd preview && py -m http.server 5500`

**Key files:**
- `layoutfixer/settings_window.py` — settings UI (customtkinter)
- `layoutfixer/settings_manager.py` — load/save `%APPDATA%/LayoutFixer/settings.json`
- `layoutfixer/hotkey_listener.py` — pynput GlobalHotKeys wrapper
- `layoutfixer/clipboard_handler.py` — full conversion pipeline
- `layoutfixer/converter.py` — Hebrew↔English character map
- `layoutfixer/tray_app.py` — pystray tray icon + menu
- `docs/index.html` — landing page (GitHub Pages, live on push to main)
- `preview/settings_preview.html` — HTML design preview (not shipped)

**Branch convention:** work on `TEST`, merge to `main`, push `origin/main`.
