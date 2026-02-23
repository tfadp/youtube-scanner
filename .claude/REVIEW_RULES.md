# REVIEW_RULES.md — What to Check During Code Review

## A) Naming & Clarity (Semantic Review)
- FLAG any function, file, or variable named: helper, utils, misc, common, shared, base, manager, handler, service (unless precisely accurate)
- FLAG generic names like `data`, `result`, `temp`, `item`, `value`, `info` — demand specific names
- Every name should describe WHAT it represents in business/domain terms, not technical terms
- Ask: "Would a new developer understand what this does from the name alone?"

## B) Silent Defaults (Claude's #1 Bad Habit)
- FLAG any fallback/default value that was added without discussion
- Example: `const timeout = options.timeout ?? 30000` — where did 30000 come from?
- Example: `value || ""` or `value ?? []` — should undefined actually be allowed here?
- Ask: "Should this throw an error instead of silently defaulting?"
- Ask: "Was this default value chosen deliberately or did Claude just pick something to make the code run?"

## C) Silent Refactors & Scope Creep
- FLAG any renamed variable, function, or file that wasn't in the original task
- FLAG any "cleanup" or "reorganization" that wasn't requested
- FLAG any new abstraction (new class, new utility function, new wrapper) that wasn't discussed
- FLAG files that were modified but shouldn't have been touched for this task
- Check: Does the diff include ONLY what was asked for?

## D) Error Handling
- FLAG empty catch blocks or generic `catch(e) { console.log(e) }`
- FLAG swallowed errors (caught but no re-throw, no user feedback, no logging)
- FLAG optimistic assumptions: "this will always be defined" without validation
- Ask: "What happens when this fails? Does the user see anything helpful?"

## E) Architecture & Boundaries
- FLAG logic that leaked into the wrong layer (UI logic in data layer, business logic in API routes)
- FLAG direct dependencies between things that should be decoupled
- FLAG code that duplicates existing functionality elsewhere in the codebase
- Check against SPECS.md: Do the data shapes and contracts still match?

## F) Testing
- FLAG any new function without a corresponding test
- FLAG tests that only test the happy path
- FLAG tests that mock so heavily they don't test real behavior
- Ask: "What's the most likely way this breaks? Is that tested?"

## G) Comments & Documentation
- FLAG any comment that says WHAT the code does (redundant) instead of WHY
- FLAG public functions missing docstrings
- FLAG TODO/FIXME/HACK comments that were added without a corresponding todo.md entry
- Check: Were docs updated if behavior changed? (per Definition of Done)

## H) Security & Performance (Quick Scan)
- FLAG hardcoded secrets, API keys, or credentials
- FLAG SQL or command injection vulnerabilities
- FLAG unbounded loops or queries without limits
- FLAG missing input validation on user-facing inputs
