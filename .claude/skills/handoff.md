# /handoff — Session Handoff

Prepare a clean handoff to the next Claude session for the LayoutFixer macOS port.
Run this when the context window is getting full or at the end of a working session.

## What to do (in order)

### 1. Kill stray processes
Run these two commands and report if anything was killed:
```bash
ps aux | grep -E "(main\.py|test_pynput|test_tray)" | grep -v grep | awk '{print $2}' | xargs kill 2>/dev/null; echo "done"
```

### 2. Update MAC_HANDOFF_STATUS.md
Read `/Users/aradkiriaty/Documents/layoutfixer/LayoutFixer/MAC_HANDOFF_STATUS.md` and update it to reflect everything that happened THIS session:
- Move any completed steps from ⏳ to ✅
- Update "Where we are" at the top
- Update "NEXT STEP" to point exactly at what comes next
- Update the uncommitted-files list if files changed
- If a new bug was discovered, document it clearly with the crash log / root cause

### 3. Check git status
Run:
```bash
cd /Users/aradkiriaty/Documents/layoutfixer/LayoutFixer && git diff --stat
```
List which files are modified/untracked so the next session knows what's pending.

### 4. Output the next-session prompt
After completing steps 1–3, print the following block between the two rows of ═══ characters (so the user can copy it easily). Fill in the blanks from the current state of MAC_HANDOFF_STATUS.md.

Fill in [CURRENT_BLOCKER_OR_NEXT_STEP] with a one-sentence description of exactly what to do first in the next session.

```
═══════════════════════════════════════════════════════════════
We're in the middle of a multi-session macOS port of LayoutFixer. Read
/Users/aradkiriaty/Documents/layoutfixer/LayoutFixer/MAC_HANDOFF_STATUS.md first (this is the
up-to-date handover), then /Users/aradkiriaty/Documents/layoutfixer/MAC_HANDOFF.md for full
background if anything is unclear.

[CURRENT_BLOCKER_OR_NEXT_STEP]

I have no coding background — explain every step in plain English, run one step at a time,
and pause for me to confirm before continuing. Pick up exactly where the status file leaves
off.
═══════════════════════════════════════════════════════════════
```

## Important rules
- Do NOT commit anything — that's the user's decision.
- Do NOT start any new work — this skill is handoff-only.
- Keep the prompt short and self-contained. The next Claude will read the status file; the prompt just needs to orient it.
- The user has no coding background — every explanation must be in plain English.
