---
description: "Full code review against SageHR team standards. Checks correctness, test coverage, Rails conventions, security, performance, and overall quality."
name: "code-review-checklist"
argument-hint: "Paste the PR link, diff, or describe what needs reviewing..."
agent: "agent"
tools: [read, search, edit, runCommands, todo]
---

Please review the following code change against our team standards:

**PR / Change:**
[link or describe the change]

**Context:**
[ticket this implements, any known constraints or decisions made]

---

Perform a full review covering every section below. Be specific — reference line numbers or method names, not vague observations.

> **Teaching note:** For every issue found, point to an existing file in the codebase where the same thing is done correctly: _"We already handle this correctly in `path/to/file.rb` — the fix here should follow that pattern."_ Explain issues in plain English, not just rule citations, so the author learns the principle.

---

## ✅ Correctness

- [ ] Does the implementation match the ticket / acceptance criteria?
- [ ] Are all edge cases from the AC handled?
- [ ] Is error handling in place for failure scenarios?
- [ ] Are there any silent failures (rescue without logging, empty rescue blocks)?
- [ ] Does the logic handle nil/empty/unexpected input safely?
- [ ] Are multi-step operations wrapped in transactions where data consistency matters?

## 🔐 Security

- [ ] Is authorization checked? (Pundit policy / CanCanCan ability for every action that touches user data)
- [ ] Is the query scoped to the current tenant/company? (No cross-tenant data leakage)
- [ ] Are strong parameters used for mass assignment?
- [ ] Is user input sanitized before use in queries, file paths, or external calls?
- [ ] Is any sensitive data (tokens, passwords, PII) logged or included in error responses?
- [ ] Are file uploads validated for type and size?

## ⚡ Performance

- [ ] Are there N+1 queries? (check `.each` blocks that trigger DB calls, check associations loaded inside loops)
- [ ] Are new columns that are filtered/sorted/joined indexed?
- [ ] Are large dataset operations paginated or batched?
- [ ] Could any expensive work be moved to a background job?
- [ ] Are there unnecessary re-queries of data already loaded?

## 🧪 Tests

- [ ] Are tests added/updated for the change?
- [ ] Do tests cover the happy path?
- [ ] Do tests cover the key error cases?
- [ ] Do tests cover authorization (can / cannot)?
- [ ] Are external services stubbed in tests?
- [ ] Would tests catch a regression if this logic is accidentally reverted?

## 🏗 Code Quality

- [ ] Are names (variables, methods, classes) clear and accurate?
- [ ] Is each method doing one thing?
- [ ] Is there duplication that should share a single implementation?
- [ ] Are there any magic numbers or hardcoded strings that should be constants?
- [ ] Is Rails convention followed (fat model/thin controller, scopes, callbacks used appropriately)?
- [ ] Are database migrations reversible?
- [ ] Is there dead code left behind?

## 📝 Maintainability

- [ ] Would a developer unfamiliar with this area understand the code?
- [ ] Is any non-obvious logic explained with a comment?
- [ ] Is the PR focused (doesn't mix unrelated changes)?
- [ ] Are deprecation warnings addressed?

---

## Summary

**Overall verdict:** Approve / Request Changes / Needs Discussion

**Must fix before merge:**
- 

**Nice to have (non-blocking):**
- 

**Questions for the author:**
- 
