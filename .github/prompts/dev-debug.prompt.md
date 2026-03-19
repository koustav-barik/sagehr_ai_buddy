---
description: "Systematically debug a bug or unexpected behavior in the Rails app. Guides through hypothesis-driven debugging and identifies root cause."
name: "dev-debug"
argument-hint: "Describe the bug: what you expected, what actually happened, and any error messages..."
agent: "agent"
tools: [read, search]
---

I need help debugging the following issue in our Rails application:

**What I expected:**
[describe expected behavior]

**What actually happened:**
[describe actual behavior — include error message, stack trace, or unexpected output if available]

**Steps to reproduce:**
[list the steps, HTTP request, or code path that triggers this]

**What I've already tried:**
[list any debugging steps already taken]

---

Please help me work through this systematically:

1. **Identify the entry point** — find the route, controller action, or background job where this starts
2. **Read the relevant code** — trace the full execution path from entry to the failure point
3. **Form hypotheses** — list 2–4 possible root causes ranked by likelihood
4. **Identify the most likely cause** — explain the reasoning
5. **Suggest how to confirm** — what log line, byebug point, or test would confirm we found it
6. **Propose the fix** — once root cause is identified, suggest the minimal safe fix

Do not skip steps. A disciplined debugging process is faster than guessing.
