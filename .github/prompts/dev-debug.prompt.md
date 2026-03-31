---
description: "Systematically debug a bug or unexpected behavior in the Rails app. Guides through hypothesis-driven debugging and identifies root cause."
name: "dev-debug"
argument-hint: "Describe the bug: what you expected, what actually happened, and any error messages..."
agent: "agent"
tools: [read, search, edit, runCommands, todo]
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

0. **Find a similar fix in the codebase first** — before proposing any fix, search the repo for an existing place where the same type of problem was solved (similar error handling, same service layer pattern, same controller edge case). Show me: _"Here's where we already handle something like this: `path/to/file.rb` — our fix should follow the same approach."_ This helps me learn the pattern, not just apply the fix.

1. **Identify the entry point** — find the route, controller action, or background job where this starts
2. **Read the relevant code** — trace the full execution path from entry to the failure point
3. **Form hypotheses** — list 2–4 possible root causes ranked by likelihood
4. **Identify the most likely cause** — explain the reasoning
5. **Suggest how to confirm** — what log line, byebug point, or test would confirm we found it
6. **Propose the fix** — once root cause is identified, suggest the minimal safe fix. Explain in plain English what the fix does and why, and point to the codebase parallel found in step 0. If I'm new to this concept, explain it as a senior dev would to a junior: what it is, why it matters, and what to watch out for.

Do not skip steps. A disciplined debugging process is faster than guessing.

> **Applying the fix:** Once I approve, use the `edit` tool to apply the change directly. Then run the relevant specs with `runCommands` to confirm nothing broke. Don't leave me with code in chat — implement it.
