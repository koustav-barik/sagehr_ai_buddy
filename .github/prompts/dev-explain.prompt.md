---
description: "Explain a complex or unfamiliar piece of code in plain English. Useful when onboarding, reviewing a PR, or jumping into an unfamiliar area of the codebase."
name: "dev-explain"
argument-hint: "Select the code you want explained, or describe what you're trying to understand..."
agent: "agent"
tools: [read, search]
---

I want to understand the following code well enough to work with it confidently.

**Code to explain:**
[paste the code or reference the file]

**My context:**
[e.g., "I'm new to this module", "I'm reviewing this PR", "I need to modify this but don't understand it yet"]

---

## Step 1 — Your Understanding First

Before reading the code in depth, ask:

> _"Before I walk you through this — what do you already know about it? Try explaining it in one or two sentences as if you were describing it to a colleague. Even a rough or uncertain answer is useful._
>
> _What specifically doesn't make sense yet? Which part are you most unsure about?"_

Use the user's answer to calibrate depth. Don't re-explain things they already understand — focus on the gaps they've named.

---

## Step 2 — Read and Explain

Read the full file and any callers / callees needed for context. Then cover:

1. **What this code does** — plain English summary in 2–4 sentences. No jargon.

2. **Why it exists** — look at git context or surrounding code. What problem does it solve? What would break if it were deleted?

3. **How it works step by step** — walk through the logic in execution order. For each significant block: what it does, and *why it's structured this way* (not just what it computes).

4. **Key concepts to understand** — when a Rails pattern, Ruby idiom, or domain concept appears, don't just explain it:
   - First ask: _"Before I explain `[concept]` — what's your current understanding of it?"_
   - Then enrich or correct their answer
   - Name when this codebase's usage is standard vs. non-standard

5. **How it connects to the rest of the system** — what calls this? What does it call? What would be affected if this logic changed?

6. **What's unusual or tricky about it** — things a developer might misunderstand or accidentally break. Explain *why* these are traps.

7. **A concrete example** — trace through the code with realistic inputs. Show what each step produces.

---

## Step 3 — Teach It Back (Feynman Close)

After the explanation, invite:

> _"Now — try explaining the core idea back to me in your own words, as if you were explaining it to someone joining the team tomorrow. What would you say?_
>
> _If anything's still fuzzy, name it and I'll try a different angle."_

This isn't a test. It's the most reliable way to find out what actually landed.
