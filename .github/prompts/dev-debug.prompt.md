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

## Step 1 — Your Hypotheses First

Before reading a single line of code, ask:

> _"Before I trace the execution path — what are your current hypotheses for what's wrong? List them, even if they're vague or uncertain. Rank them by likelihood if you can._
>
> _What have you already ruled out, and why? What would prove or disprove your top hypothesis?"_

Record their hypotheses. After the analysis, come back to them: which were right, which were wrong, and what the codebase revealed that the hypothesis didn't anticipate.

---

## Step 2 — Read and Trace

1. **Identify the entry point** — find the route, controller action, or background job where this starts
2. **Read the relevant code** — trace the full execution path from entry to the failure point. State what you expect to find at each layer before reading it.
3. **Form hypotheses** — list 2–4 possible root causes ranked by likelihood
4. **Check against the user's hypotheses** — which did they predict correctly? What was different? If their mental model was wrong, explain *why* — what assumption led them there?

---

## Step 3 — Confirm and Fix

5. **Identify the most likely cause** — explain the reasoning. Pose the diagnosis as a question first:
   > _"Based on the trace, I think the issue is [X]. Does that match what you're seeing? Here's why I think that..."_

6. **Suggest how to confirm** — what log line, byebug point, or test would confirm the root cause before patching?

7. **Propose the fix** — once confirmed, present the minimal safe fix. If there are two valid approaches, name both with tradeoffs:
   > _"Option A: [quick fix] — resolves the symptom immediately but doesn't address [underlying issue]. Option B: [deeper fix] — more work but prevents this class of bug recurrence. Given the urgency, which do you want?"_

---

Do not skip steps. A disciplined debugging process is faster than guessing — and knowing *why* you were wrong is as valuable as the fix itself.
