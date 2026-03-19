---
description: "Identify what existing features or functionality could regress from a given change. Produces a regression test checklist scoped to what's actually at risk."
name: "qa-regression"
argument-hint: "Describe the change being made (PR link, ticket, or summary of what changed)..."
agent: "agent"
tools: [read, search]
---

I need to identify regression risks for the following change:

**Change description:**
[describe what was changed — e.g., "refactored the payroll calculation service", "updated the employee leave accrual logic", "changed the authentication flow"]

**PR / Ticket:**
[optional link]

---

Please analyze the change and produce a targeted regression checklist:

### Step 1 — Map the blast radius
Read the changed files and trace dependencies:
- What other parts of the codebase call the changed code?
- What features use the affected models, services, or modules?
- Are there any background jobs triggered by the changed logic?
- Are there any webhooks, emails, or external integrations involved?
- What database tables are affected, and what features depend on those tables?

### Step 2 — Identify user-facing features at risk
For each dependency found, identify the user-facing feature it powers.

### Regression Checklist

#### High Risk (directly in the change path)
- [ ] [Feature] — [specific scenario to verify]
- [ ] [Feature] — [specific scenario to verify]

#### Medium Risk (shared dependencies)
- [ ] [Feature] — [what to check]
- [ ] [Feature] — [what to check]

#### Low Risk (indirect dependencies)
- [ ] [Feature] — [sanity check]

#### Background Jobs to Verify
- [ ] [Job name] — [what it does and why it could be affected]

#### Integrations / Emails to Verify
- [ ] [Integration] — [expected behavior]

---

### Suggested Test Approach

| Area | Manual Check | Automated (existing spec) |
|---|---|---|
| [feature] | [steps] | [spec file] |

### What is NOT at risk
[Explicitly call out what areas are definitely not affected — this scopes the regression effort]
