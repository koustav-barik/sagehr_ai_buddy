---
description: "Write a clear, informative pull request description based on the code changes. Covers what changed, why, how to test, and any deployment notes."
name: "dev-pr-description"
argument-hint: "Describe what this PR does, or I'll read the diff..."
agent: "agent"
tools: [read, search]
---

I need a pull request description for this change.

**Ticket/issue:** [Jira ticket number or issue link]

**What this PR does (if you want to describe it yourself):**
[optional — leave blank and I'll read the diff]

---

Please write a PR description with the following sections:

## What

A clear, concise explanation of what changed. Not a list of files — a plain English description of the feature or fix. Explain it to someone who hasn't read the code.

## Why

The context and motivation. What problem does this solve? What was wrong or missing before? Link to the Jira ticket.

## How

A brief technical explanation of the approach. Why did you implement it this way? Were there alternative approaches? This is the section for any interesting decisions or tradeoffs.

## How to Test

Step-by-step instructions a reviewer or QA person can follow to manually verify this works:
1. [ ] Step one
2. [ ] Step two
3. [ ] Expected result

## Screenshots / Recordings
*(if applicable — add here)*

## Checklist
- [ ] Tests added / updated
- [ ] No N+1 queries introduced
- [ ] Migrations are reversible
- [ ] No sensitive data in logs
- [ ] No hardcoded values that should be configurable

## Deployment Notes
*(any env vars to set, rake tasks to run, cache to clear, etc.)*

---

Keep the tone clear and professional. Assume the reviewer is technical but doesn't know the context of this specific ticket.
