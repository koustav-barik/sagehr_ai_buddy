---
description: "Refactor selected code to follow Rails conventions, project patterns, and clean code principles. Does not change behavior — only improves structure."
name: "dev-refactor"
argument-hint: "Select the code to refactor, or describe what needs cleaning up..."
agent: "agent"
tools: [read, search, edit, runCommands, todo]
---

I want to refactor the following code. The **behavior must not change** — this is purely a structural improvement.

**Code to refactor:**
[paste code or reference the selected file]

**What feels wrong about it (if you know):**
[e.g., too long, too many responsibilities, duplicated logic, hard to test]

---

Please:

1. **Read the code and its context** — check how it's called and what tests cover it before touching anything
2. **Identify the specific problems**: naming, length, responsibility count, duplication, missing abstractions, Rails anti-patterns
3. **Search for similar patterns** in the codebase that we should be consistent with — and show me _where_ those patterns live: _"We already handle this shape of problem in `app/services/...` — let's make this consistent."_ Always anchor refactors to what's already done well in our codebase.
4. **Explain the refactor before applying it** — tell me in plain English what you're changing and why, as a senior dev explaining to a junior. Name the Rails principle or pattern being applied.
5. **Apply the refactors** using the `edit` tool — one at a time, in order of safety:
   - Rename for clarity (variables, methods, classes)
   - Extract methods for code that can be named
   - Extract service objects / concerns if a class is doing too much
   - Replace raw SQL / complex queries with named scopes
   - Remove dead code (but confirm `grep` shows it's truly unused)
6. **Verify the tests still pass** — run relevant specs with `runCommands` after each change. Don't leave partially-refactored code without a green test run.
7. **Call out the common pitfall** — for each extracted pattern, mention the one thing a beginner might get wrong when applying the same refactor next time.

Rails-specific anti-patterns to check for:
- Fat controllers (move logic to service objects or models)
- Logic in views (move to helpers or presenters)
- Callbacks doing too much (consider extracting to services)
- N+1 queries hiding in loops
- Missing `with_options` on grouped validations
- Direct use of `params` in unexpected places (use strong parameters consistently)
