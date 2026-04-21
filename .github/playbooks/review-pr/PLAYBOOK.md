---
name: review-pr
description: "Checklist-driven procedure for performing a thorough pull request review covering correctness, Rails conventions, multi-tenancy, security, performance, testing, migrations, and documentation. Used by pr-code-review agent."
---

# Playbook: Review PR

## When to Use

Invoke this playbook once the PR diff scope has been established and the changed files have been read. This playbook covers what to check — the pr-code-review agent handles the git operations and output formatting.

> **Scope constraint**: Raise findings only for lines and methods introduced or modified in this PR. You may read surrounding context to understand a change, but do not flag pre-existing unmodified code as a blocking or important issue. Surface concerns about untouched code under "Additional Notes" only.

---

## Severity Labels

| Label | Meaning |
|---|---|
| 🔴 **MUST FIX** | Blocking — cannot merge. Security risk, data corruption, production breakage, or missing auth. |
| 🟡 **SHOULD FIX** | Important — technical debt, performance degradation at scale, missing test coverage. |
| 🔵 **CONSIDER** | Suggestion — nice to have, low urgency, author's discretion. |

---

## Dimension 1 — Purpose & Context

- Does the implementation match the PR title and description?
- Are the changes focused and cohesive, or is there scope creep?
- Is the PR too large to review safely — should it be split?
- Are there any incomplete, TODO, or commented-out sections suggesting work-in-progress?

---

## Dimension 2 — Code Quality (Rails-Specific)

- **Controllers**: Are they thin? Is business logic moved to service objects or models?
- **Models**: Are validations, associations, and scopes well-defined? Any N+1 queries lurking?
- **Service objects**: Is `.call` the only public method? Clear single responsibility?
- **Serializers**: Clean JSON shaping without leaking internal attributes?
- **Routes**: RESTful where possible? Proper namespacing under `/api/v1/`?
- **Naming**: Clear, consistent, Rails-idiomatic method and variable names?
- **Callbacks**: Are they used sparingly? No cross-model side effects in callbacks — those belong in service objects.
- **Enums**: Defined with a hash (not index position): `enum status: { active: "active" }` ✅

**Teaching requirement**: For every issue found, point to where the correct pattern already exists:
> _"We handle this correctly in `app/services/employees/archive.rb` — the fix here should follow that shape."_

---

## Dimension 3 — Multi-Tenancy & Authorization (MANDATORY)

These are **🔴 MUST FIX** by default if violated.

- **Tenant scoping**: Are all queries scoped through `current_company` or equivalent? No bare `Model.find(id)` without tenant context.
- **Authorization**: Is Pundit `authorize` or `policy_scope` called on every action that touches data?
- **Cross-tenant leakage**: Can a user from Company A access or modify Company B's data by manipulating IDs?

```ruby
# ❌ MUST FIX — exposes cross-tenant data
Employee.find(params[:id])

# ✅ CORRECT
current_company.employees.find(params[:id])
```

---

## Dimension 4 — Security

- **Mass assignment**: Strong parameters defined? No sensitive fields exposed? No `permit!`.
- **SQL injection**: No raw SQL with user input interpolation? Use `where(id: params[:id])` not `where("id = #{params[:id]}")`.
- **XSS**: No `html_safe` or `raw` on user-supplied content without `sanitize`?
- **Sensitive data**: Are passwords, tokens, and PII filtered from logs? Does `filter_parameters` cover new fields?
- **File uploads**: Type and size validation present?
- **Background jobs**: Are job arguments IDs, not AR objects? No sensitive data in job args?

---

## Dimension 5 — Performance

- **N+1 queries**: Check any `.each` or loop that accesses associations — are they eager-loaded with `includes` or `eager_load`?
- **Missing indexes**: Are new columns used in `where`, `order`, or `joins` indexed?
- **Unbounded queries**: Any `.all` without limits or pagination?
- **Expensive inline work**: Should any operation (email, external API call, report generation) be deferred to Sidekiq?
- **Re-queries**: Is data being fetched multiple times that could be loaded once?

---

## Dimension 6 — Testing

A spec that doesn't actually verify the feature is worse than no spec.

### 6a — Coverage Inventory Check
For every implementation file changed, verify the specs cover:
- ✅ Happy path — success outcome and its side effects (status code, record state, jobs enqueued)
- ✅ Negative paths — every early return, validation failure, error condition
- ✅ Authorization — all four cases: authenticated+authorised → success; unauthenticated → 401; wrong tenant → 403/not found; insufficient role → 403
- ✅ Edge cases — nil/empty/boundary inputs
- ✅ Side effects — emails, background jobs, associated record changes

Flag any missing category as at minimum 🟡 **SHOULD FIX**.

### 6b — Block Ordering
- Order: `subject` → `let`/`let!` → `before`/`after` → `it`
- `describe` for methods (`#method`, `.class_method`) and `context` for states (`when …`, `with …`)
- `it` descriptions in present tense, no "should"

### 6c — No Inline Variable Assignment in `it` Blocks (🟡 SHOULD FIX)
```ruby
# ❌ Flag this
it 'archives the employee' do
  employee = create(:employee)  # setup inside example — wrong
  ...
end
```

### 6d — `aggregate_failures` for Related Assertions (🔵 CONSIDER)
Associations, validations, and attribute checks should be grouped, not split into individual `it` blocks.

### 6e — `allow_any_instance_of` (🟡 SHOULD FIX)
Flag any use of `allow_any_instance_of`. Always stub on the specific object instance already in scope.

### 6f — Database Minimisation (🔵 CONSIDER)
Flag `create` calls where `build` would suffice — each unnecessary `create` is a database round-trip.

### 6g — External Service Stubbing (🔴 MUST FIX if absent)
All external service calls must be stubbed. Any un-stubbed HTTP client or mailer is a CI reliability risk.

---

## Dimension 7 — Database Migrations (if present)

- **Reversibility**: Is `def down` implemented? Can the migration be safely rolled back?
- **Data safety**: NOT NULL columns added nullable first → backfill via rake task → then add constraint (strong_migrations pattern)
- **Large table safety**: Does the migration lock a large table? Needs `disable_ddl_transaction!` + `algorithm: :concurrently` for index additions
- **Indexes**: New foreign keys and filtered columns indexed?

---

## Dimension 8 — Documentation & Clarity

- **Comments**: Are non-obvious decisions explained?
- **Error messages**: Actionable for users, debuggable for developers?
- **Magic values**: Hardcoded strings/numbers extracted to constants?
- **Dead code**: Any leftover commented code or unused methods?

---

## Teaching Requirement (applies to all dimensions)

For **every issue raised**, follow this format:
1. Point to where the correct pattern already exists in the codebase
2. Explain why this is a problem in production terms (not just "it violates a rule")
3. Name the underlying principle (N+1 query, cross-tenant leakage, mass assignment, etc.)
4. Describe a concrete fix anchored to the existing codebase pattern
