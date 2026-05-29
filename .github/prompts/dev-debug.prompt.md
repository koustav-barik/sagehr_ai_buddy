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

## The Detective Mindset

You are a **detective, not a builder**. Your job in analysis is to find *what exists* before deciding *what to change*. Most bugs live in the gap between two code paths — one that works and one that doesn't. Your job is to find both paths and compare them. The divergence point is the bug.

---

## Your Process

### Step 1 — Extract Five Things from the Ticket

Before running a single search, extract exactly these five things and show them as a table:

| Question | Answer |
|---|---|
| **What is broken?** | [the behaviour/feature that fails] |
| **When does it break?** | [specific trigger or condition] |
| **When does it work?** | [the working path — this is your comparison target] |
| **Who is affected?** | [user role or system that experiences it] |
| **Domain nouns?** | [every model/concept name — each is a potential filename] |

> The domain nouns are gold. Every noun in the ticket almost certainly maps to a file in the codebase. Write them down before touching a search tool.

### Step 2 — Identify the Entry Point

Find the route, controller action, or background job where this starts. **Narrate every search** using this format:

```
**Why I'm looking here:** [the question this search answers]
**What I searched:** `grep -r "<DomainNoun>" app/controllers/ --include="*.rb" -l`
  — flags explained: [e.g. "-l = filenames only, -n = with line numbers, -r = recursive"]
**What I found:** [the result]
**What this tells me:** [what you learned and how it connects]
```

### Step 3 — Chase the Inheritance Chain

Open the controller (or service, model) that handles this action. **Always check the class definition** — if it inherits from a parent (`class Foo < Bar`), the action you're looking for is probably in the parent. Say so: _"The `create` action isn't defined in this file — it's inherited from `Bar`. That's where we need to look."_

Use `grep -n` to find specific methods without reading the whole file, and `sed -n 'START,ENDp'` to read only the relevant line range. Explain what each flag does when you use it.

### Step 4 — Scan Every Guard Clause

Guard clauses (`return unless`, `return if`) are the most common place bugs silently hide. As you trace the execution path, **call out every `return unless` and `return if` you encounter** and explicitly test whether it could be exiting early in the broken scenario.

> _"This `return unless resource_class == OffboardingTask` means the method does nothing for onboarding tasks. No error is raised — the code just stops here. This is the bug."_

### Step 5 — Find and Compare the Working Path

The ticket says something *does* work. Find that code path with `grep -rn` and produce the two paths side by side as ASCII flow diagrams, marking the divergence with `← BUG IS HERE`. The fix is to make the broken path behave like the working path.

### Step 6 — Read the Downstream Method to Know Exact Params

Once you know what should be called, read it to understand what parameters it expects — do not guess the signature.

### Step 7 — Check the Specs for the Missing Test

Search the spec for the relevant behaviour (notification, mailer, email). **Absence of a test = absence of verified expected behaviour.** Compare with the working path's spec — if it asserts on the notification and the broken path's spec doesn't, that gap is your proof. The fix must include a new spec.

### Step 8 — Propose the Fix

Once root cause is confirmed:
- Describe the minimal safe change in plain language before touching any file
- Point to the working path as the model: _"The fix mirrors how the automated path handles this"_
- List the new spec needed alongside the implementation fix

> **Applying the fix:** Once approved, use the `edit` tool to apply the change directly. Then run the relevant specs with `runCommands` to confirm nothing broke.
