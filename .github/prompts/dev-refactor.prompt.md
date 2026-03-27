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

4. **Present refactoring options before touching anything**

   After identifying the problems, do NOT immediately apply fixes. Instead, present the options as a choice:

   > _"I've found [N] problems. Here are two ways to approach this refactor:_
   >
   > **Option A — [Name, e.g. 'Extract service object']**
   > What changes: [1–2 sentences]
   > You gain: [readability / testability / SRP compliance]
   > You accept: [indirection / more files / migration effort]
   > When to pick this: [context where this makes more sense]
   >
   > **Option B — [Name, e.g. 'Extract private methods + rename']**
   > What changes: [1–2 sentences]
   > You gain: [simpler change / less risk / no new files]
   > You accept: [still somewhat fat / doesn't fully address X]
   > When to pick this: [context where this makes more sense]
   >
   > Which direction fits your goal here — and what are you optimising for (speed of change, long-term maintainability, test coverage)?"_

   Wait for the user's choice and reasoning before applying any changes.

5. **Apply the chosen refactors** — one at a time, in order of safety:
   - Rename for clarity (variables, methods, classes)
   - Extract methods for code that can be named
   - Extract service objects / concerns if a class is doing too much
   - Replace raw SQL / complex queries with named scopes
   - Remove dead code (but confirm `grep` shows it's truly unused)

6. **After each significant change**, pause briefly:
   > _"Here's what the [method name / class] looks like now. Does this match what you had in mind? Is there a Rails pattern from elsewhere in the codebase this should mirror?"_

7. **Verify the tests still pass** — run relevant specs after each change

---

Rails-specific anti-patterns to check for:
- Fat controllers (move logic to service objects or models)
- Logic in views (move to helpers or presenters)
- Callbacks doing too much (consider extracting to services)
- N+1 queries hiding in loops
- Missing `with_options` on grouped validations
- Direct use of `params` in unexpected places (use strong parameters consistently)

When one of these patterns is found, name it explicitly and ask:
> _"This is a [fat controller / N+1 / callback anti-pattern]. In your own words, why is this a problem in Rails — not just in general? How would you explain the risk to a junior developer?"_
