---
description: "Refactor selected code to follow Rails conventions, project patterns, and clean code principles. Does not change behavior — only improves structure."
name: "dev-refactor"
argument-hint: "Select the code to refactor, or describe what needs cleaning up..."
agent: "agent"
tools: [read, search, edit]
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
3. **Search for similar patterns** in the codebase that we should be consistent with
4. **Apply the refactors** — one at a time, in order of safety:
   - Rename for clarity (variables, methods, classes)
   - Extract methods for code that can be named
   - Extract service objects / concerns if a class is doing too much
   - Replace raw SQL / complex queries with named scopes
   - Remove dead code (but confirm `grep` shows it's truly unused)
5. **Verify the tests still pass** — run relevant specs after each change

Rails-specific anti-patterns to check for:
- Fat controllers (move logic to service objects or models)
- Logic in views (move to helpers or presenters)
- Callbacks doing too much (consider extracting to services)
- N+1 queries hiding in loops
- Missing `with_options` on grouped validations
- Direct use of `params` in unexpected places (use strong parameters consistently)
