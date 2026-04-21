---
name: quality-critique
description: "Self-critique procedure for reviewing implemented changes as a skeptical principal engineer before a PR is raised. Covers security, correctness, performance, and maintainability. Used by dev-quality-critique prompt and e2e-development (Stage 5)."
---

# Playbook: Quality Critique

## When to Use

Invoke this playbook after implementation is complete but **before a PR is raised**. The goal is to catch issues that passed the implementation phase — before they reach human review or production.

This playbook operates on the current diff (staged/unstaged changes), not an open PR. Use `get_changed_files` to establish the scope.

> **Scope constraint**: Critique only code that appears in the diff. Do not flag pre-existing unmodified code. If you spot a concern in untouched code, add it under "Questions for the Author" — do not raise it as a finding.

---

## Mindset

You are a **principal engineer with extremely high standards who has seen every way code can fail in production**.

- "It works for the happy path" is not sufficient
- Every assumption is suspect until proven safe
- "It won't happen in practice" is not an acceptable argument
- Performance problems that only show at scale are still real problems
- Security issues don't need to be obvious to be exploitable
- The next developer to read this code may not have your context

---

## Step 1 — Establish Scope

Get the current diff using `get_changed_files`. Identify:
- Which implementation files changed
- Which spec files changed or were added
- What the change is trying to accomplish (PR description, commit message, or user explanation)

Read all changed files in full — not just the diff lines. Surrounding context matters for understanding what assumptions the new code is making.

---

## Step 2 — Security Review

For each changed file, ask:

- Is there **any user-controlled input** reaching a query, a rendered template, or an external call without sanitization?
- Is **`authorize` / `policy_scope`** called on every action that touches data? Is it possible to reach the data layer without the auth check running?
- Is there a **cross-tenant leakage risk**? Could a user from Company A access Company B's records by manipulating an ID parameter?
- Is **sensitive data** (passwords, tokens, PII) written to logs or included in API error responses?
- Are **background job arguments** IDs and primitives — not AR objects or tokens?
- Are **file upload** type and size constraints validated before processing?

Flag absences as 🔴 **Blocking** — these are production safety issues.

---

## Step 3 — Correctness Review

For each method or block changed, ask:

- What happens if **any input is nil, empty, or an unexpected type**? Are there guard clauses or validations?
- Is there a **race condition** if two requests hit this simultaneously? (Shared mutable state, counter increments, check-then-act patterns)
- If a **database write fails halfway**, is the operation wrapped in a transaction to prevent partial state?
- If an **external service** (email, job queue, third-party API) is unavailable, is the failure handled gracefully or does it leave the system in a broken state?
- Do all **early returns and guard clauses** reach the correct exit path?

---

## Step 4 — Performance Review

- Is there an **N+1 query** in any loop that accesses associations? (Look for `.each` or `.map` blocks that call `.association` or trigger a new query on each iteration.)
- Is there any **unbounded data load** — `.all`, `.where(...)` without a limit or pagination?
- Is **expensive work** (report generation, image processing, external API calls, bulk email) deferred to a background job, or running inline in the request cycle?
- Are **new columns that will be filtered, sorted, or joined** indexed in the migration?

---

## Step 5 — Maintainability Review

- Is any **method doing more than one thing**? Could it be extracted into a private method with a clear name?
- Is there **duplicate logic** that already exists elsewhere in the codebase? (Before flagging, run a quick search to confirm.)
- Are **magic numbers or strings** hardcoded that should be constants or configuration?
- Is there **dead code** — commented-out blocks, unused variables, leftover debugging artefacts?
- Is any **non-obvious decision** unexplained? Would a developer six months from now understand why this was written this way?

---

## Step 6 — Format Findings

Format each issue as:

```markdown
### [Issue Title]
**Severity:** 🔴 Blocking / 🟡 Should Fix / 🔵 Suggestion
**Location:** `path/to/file.rb` — `MethodName#method`
**Problem:** [Specific description of the issue]
**Production impact:** [What could go wrong in production without this fix]
**Recommendation:** [How to fix — plain English description, no code yet]
**Codebase parallel:** [Where we already handle this correctly — e.g. "See `app/services/payroll/archive.rb` for the same pattern done right"]
```

---

## Step 7 — Present and Wait for Approval

Present all findings grouped by severity (🔴 first, then 🟡, then 🔵).

Then ask:
> _"Here are my findings. Which of these would you like me to address before raising the PR? (Reply with item numbers, 'all', or 'none')"_

Only implement fixes that the user explicitly approves. After implementing approved fixes, re-run affected specs to confirm nothing broke before proceeding.
