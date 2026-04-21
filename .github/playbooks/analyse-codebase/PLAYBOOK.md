---
name: analyse-codebase
description: "Systematic procedure for discovering relevant files, tracing the full request lifecycle, and producing a structured implementation plan from a ticket or requirement. Used by initial-analysis, e2e-development (Stage 2), and jira agent (analyse/plan modes)."
---

# Playbook: Analyse Codebase

## When to Use

Invoke this playbook whenever you need to:
- Understand what files are affected by a ticket or requirement
- Trace the current logic flow for a feature end-to-end
- Produce an implementation plan before any code is written

This playbook is **read-only**. It produces a plan. No code is written.

---

## Step 1 — Parse the Ticket

Extract from the ticket or requirement description:

- **Core problem or feature** — one sentence: what is being added, changed, or fixed?
- **Key domain entities** — model names, concepts, or areas (e.g. `Employee`, `Payroll`, `Leave`, `Onboarding`)
- **Acceptance criteria** — explicit and implied; note anything marked as edge case
- **Preserved behaviours** — what currently works that must not break?
- **Module / component** — which area of the product does this belong to?

---

## Step 2 — Discover Relevant Files

For each key entity and concept identified in Step 1, search systematically in this order:

1. **Routes** — `config/routes.rb` — find the endpoint(s); note namespace, HTTP verb, controller
2. **Controllers** — `app/controllers/` — find the controller action; note `before_action` chain, auth checks
3. **Models** — `app/models/` — read associations, validations, scopes, callbacks related to the feature
4. **Service objects** — `app/services/` — find the service(s) the controller delegates to
5. **Serializers / Presenters** — `app/serializers/`, `app/presenters/` — understand JSON/HTML output shape
6. **Policies** — `app/policies/` — read the Pundit policy for this resource
7. **Background jobs** — `app/workers/` or `app/jobs/` — are there async operations involved?
8. **Specs** — `spec/` — read existing specs for the affected files; they document current expected behaviour
9. **Migrations** — `db/migrate/` — any recent schema changes related to these models?

> **Do not skim.** For each file found, read the relevant sections and understand the actual logic — not just the method names.

**Teaching narration**: As you discover each file, say how you found it and why it's relevant:
_"I found `app/services/employees/archive.rb` because the controller delegates to it — here's what it does and why that matters for this ticket."_

---

## Step 3 — Map the Current Logic Flow

Trace the full request lifecycle for the affected feature end-to-end. Produce a numbered list:

```
1. Route: POST /api/v1/employees — routes to EmployeesController#create
2. Auth: SubdomainController#authenticate_user! runs before action
3. Auth: Pundit authorize(@employee) called in create action
4. Scope: current_company.employees used — tenant isolation enforced
5. Service: Employees::CreateService.call(params, company: current_company)
6. Model: Employee.create! — triggers :after_create callback → OnboardingWorkflow#trigger
7. Serializer: EmployeeSerializer renders JSON response
8. Response: 201 Created with employee JSON
```

The goal is that any engineer reading this flow can understand the system without opening a file.

---

## Step 4 — Identify the Delta

List exactly what needs to change to implement the ticket:

```
## Files to CREATE
- app/services/[domain]/[action].rb — [one-line purpose]

## Files to MODIFY
- app/models/employee.rb — [specific change: add scope / add validation / change callback]
- app/controllers/api/v1/employees_controller.rb — [specific change]

## Files to DELETE or DEPRECATE
- (list only if genuinely obsoleted by this ticket)

## Migrations needed
- Add column `[name]` to `[table]` — nullable first, backfill via rake task, then constraint
- Add index on `[table]([column])` with `algorithm: :concurrently`

## Risks & Gotchas
- [Race condition, auth boundary, dependent feature, performance concern]
- [strong_migrations concern if modifying large tables]
```

---

## Step 5 — Produce the Implementation Plan

Output the full structured plan in this format:

```markdown
## Ticket Summary
[2–3 sentence plain English summary of what this ticket asks for and why]

## Relevant Files Found
### Routes
- [route → controller#action]

### Controllers
- [path] — [what it does]

### Models
- [path] — [relevant validations/associations/scopes]

### Services
- [path] — [what it does]

### Specs
- [path] — [what's covered]

## Current Logic Flow
[numbered trace — see Step 3 format above]

## Required Changes
### Files to CREATE
### Files to MODIFY
### Migrations needed

## Risks & Gotchas
[bullet list]

## Suggested Implementation Order
[ordered steps — safest sequence to make changes without breaking existing behaviour]
```

---

## Teaching Note

For **every file and pattern** you identify, point to a similar one already in the codebase:

> _"We have a nearly identical service at `app/services/payroll/archive.rb` — the new one should follow the same shape: one `.call` method, `company:` passed explicitly, Sentry rescue wrapping."_

This anchors the plan in what is already proven to work in this codebase, and teaches the developer how to navigate it.
