# CLAUDE.md — The Brain (Mid-Project Safety)

## 0) Architecture Lock
- STRICT RULE: Do NOT move or rename existing files/folders.
- STRICT RULE: No silent refactors. No "cleanup" unless I ask.
- Default strategy: smallest possible additive change.

## 1) The Truth Rule
Before changing any naming or data shape:
- Check `.claude/SPECS.md`
- If SPECS is missing info, propose an update to SPECS FIRST

## 2) Simplified Plan Mode (MANDATORY)
Before writing code, STOP and provide:
- Path A (Simple): least risky option
- Path B (Standard): more complete option
Explain WHY for each in 1–2 sentences.

## 3) Change Control (Contracts)
If a change affects naming conventions or data shapes:
1) Show a small diff or before/after snippet
2) Explain impact (where it propagates)
3) Provide a verification command
4) Update or add a minimal test if possible

## 4) Definition of Done (DoD)
Do not say "done" unless:
- The relevant command runs
- A test/smoke command is executed
- Docs updated if behavior changed
- SPECS updated if any contract changed

## 5) Verification Rule
Every change must include:
- A terminal command to test it
- What success looks like
- Most likely failure + 1-step debug

## 6) Reviewer Mode Trigger
If I type: `REVIEW_MODE=ON`
You become a Strict Auditor and run a checklist:
- naming consistency vs SPECS
- contracts respected
- error handling and edge cases
- tests and verification commands
- no "lazy logic" shortcuts

## 7) Non-Negotiables
- All code reviews must follow the checklist in .claude/REVIEW_RULES.md

## 8) Import Pattern for Testability
- For any config value that tests might need to override, use `import config as _config` and reference `_config.VALUE` at runtime (not `from config import VALUE` which captures at import time).
- When adding fields to dataclasses, update SPECS.md in the same change.

## 9) Keyword Filter Safety
- Never use common English words as noise filter keywords (e.g., "strikes", "bomb", "war").
- Always use specific compound phrases ("air strikes", "bombing", "war ") and test against false positives.
