---
description: "Explain a complex or unfamiliar piece of code in plain English. Useful when onboarding, reviewing a PR, or jumping into an unfamiliar area of the codebase."
name: "dev-explain"
argument-hint: "Select the code you want explained, or describe what you're trying to understand..."
agent: "agent"
tools: [read, search]
---

Please explain the following code clearly enough that a developer unfamiliar with this area could understand it and work with it confidently.

**Code to explain:**
[paste the code or reference the file]

**My context:**
[e.g., "I'm new to this module", "I'm reviewing this PR", "I need to modify this but don't understand it yet"]

---

Your explanation should cover:

1. **What this code does** — plain English summary in 2–4 sentences. No jargon.

2. **Why it exists** — look at git context or surrounding code to understand the intent. What problem does it solve?

3. **How it works step by step** — walk through the logic in execution order. For each significant block, explain what it does and why.

4. **Key concepts to understand** — if the code uses a specific Rails pattern, Ruby idiom, or domain concept, explain that too:
   - Specific gems and why they're used
   - Domain concepts (what is a "payroll run", "leave accrual", etc.)
   - Rails patterns in use (concerns, callbacks, STI, polymorphic associations, etc.)

5. **How it connects to the rest of the system** — what calls this? What does it call? What data does it depend on?

6. **What's unusual or tricky about it** — things a developer might misunderstand or accidentally break

7. **A concrete example** — if helpful, trace through the code with real example inputs to show what happens at each step
