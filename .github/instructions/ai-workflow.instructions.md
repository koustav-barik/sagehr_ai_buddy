---
description: "AI workflow governance for rails-cakehr. Defines what Copilot can do autonomously, what requires approval, and what is forbidden. Loads for every conversation. Cross-references all agents and playbooks."
applyTo: "**"
---

# AI Workflow Governance

This file defines how Copilot behaves in this codebase — what it can do without asking, what it must confirm first, and what it must never do. It complements `copilot-instructions.md` (which covers Rails/stack conventions) by adding agent workflow and autonomy rules.

---

## Autonomy Boundaries

### ✅ ALWAYS — Proceed Without Asking
- Read any file, search the codebase, run grep or semantic search
- Explain code, summarise logic, identify patterns
- Run linting on specific changed files: `bundle exec rubocop -a <file>`
- Run individual or small groups of specs: `COVERAGE=false bundle exec rspec <spec_file>`
- Fetch Jira tickets via `./scripts/jira-fetch.sh`
- Produce implementation plans and analysis reports
- Trivial edits: fix typos in comments, correct a variable name, reformat to match `.rubocop.yml`

### ⚠️ ASK FIRST — Require Explicit Confirmation
- **Create or switch git branches** — confirm the branch name and ticket before `git checkout -b`
- **Run database migrations** — confirm the migration content and direction before `rails db:migrate`
- **Raise a PR or push to remote** — confirm branch, commit message, and PR description
- **Multi-file changes affecting >5 files** not covered by an approved plan
- **Run the full test suite** (>50 specs) — confirm scope before `bundle exec rspec`
- **Any destructive git operation** — `reset`, `rebase`, `force push`

### 🔒 NEVER — Forbidden Under All Circumstances
- Commit directly to `master` or `main`
- Skip `authenticate_user!` / `authorize` on any new controller action
- Write a query that is not scoped through `current_company` (cross-tenant leakage)
- Use raw SQL string interpolation: `where("id = #{params[:id]}")` ← always use parameterized form
- Hardcode secrets, tokens, or API keys — use `Rails.application.credentials` or `ENV[...]`
- Commit `.env` files, credentials files, or any file containing secrets
- Force-push (`git push --force`) to any branch that has an open PR

---

## Plan-First Rule

For any non-trivial ticket (more than a single-file change), **produce a plan and wait for approval before writing any code**:

1. Use the `initial-analysis` agent or the `e2e-development` agent Stage 2 to produce the plan
2. Save it as `.github/plans/<TICKET-KEY>.md` (see `plans/plan-template.md`)
3. Present it to the user and wait for explicit approval
4. Only begin implementation after the user confirms the plan is correct

Proceeding directly to code without a plan is only acceptable for: typo fixes, trivial single-line changes, or when the user explicitly waives the plan step.

---

## Agent Reference

| I want to… | Use this agent |
|---|---|
| Read and understand a Jira ticket | `jira` |
| Analyse a ticket and produce an implementation plan | `initial-analysis` |
| Implement a ticket end-to-end with approval gates | `e2e-development` |
| Review a pull request | `pr-code-review` |

---

## Playbook Reference

| Procedure | Playbook |
|---|---|
| Systematic file discovery and logic tracing | [analyse-codebase](../playbooks/analyse-codebase/PLAYBOOK.md) |
| Test inventory and RSpec writing | [write-rspec](../playbooks/write-rspec/PLAYBOOK.md) |
| Checklist-driven PR review | [review-pr](../playbooks/review-pr/PLAYBOOK.md) |
| Pre-PR self-critique pass | [quality-critique](../playbooks/quality-critique/PLAYBOOK.md) |

---

## Prompt Reference

| I want to… | Use this prompt (`/`) |
|---|---|
| Write or update specs for current changes | `/dev-write-specs` |
| Self-critique current implementation | `/dev-quality-critique` |
| Review code against team standards | `/code-review-checklist` |
| Review for performance issues | `/code-review-performance` |
| Review for security issues | `/code-review-security` |
| Write a PR description | `/dev-pr-description` |
| Debug a failing test or error | `/dev-debug` |
| Explain a piece of code | `/dev-explain` |
| Refactor without changing behaviour | `/dev-refactor` |
| Write a migration safely | `/dev-migration` |
| Address PR review comments | `/dev-address-review-comments` |
| Create seed data or a factory | `/dev-seed-factory` |
| Write QA acceptance criteria | `/qa-acceptance-criteria` |
| Write a bug report | `/qa-bug-report` |
| Plan a regression test | `/qa-regression` |
| Create a QA test plan | `/qa-test-plan` |
