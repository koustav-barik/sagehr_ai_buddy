---
name: write-rspec
description: "Step-by-step procedure for producing a complete RSpec test suite for implemented changes: discover existing patterns, build a test case inventory, write specs following project conventions, and run iteratively until green. Used by dev-write-specs prompt and e2e-development (Stage 4)."
---

# Playbook: Write RSpec

## When to Use

Invoke this playbook when:
- Specs need to be written or updated for newly implemented code
- A test case inventory needs to be produced for review before writing any spec code
- Existing specs need to be extended for a changed code path

This playbook **does not run in isolation from context** — always identify the implementation files under test before starting Step 1.

---

## Step 1 — Read the Code Under Test

For each implementation file changed, read it fully and identify:

- Every **public method / controller action** that needs coverage
- Every **conditional branch** (if/else, case, guard clauses, early returns)
- All **validations, associations, scopes** on models
- **Authorization checks** — who can do what, and what happens to those who cannot
- **Side effects** — emails sent, background jobs enqueued, records created/updated/deleted, external API calls

Do not write a single spec line until you have a clear picture of what the code actually does.

---

## Step 2 — Discover Existing Patterns

Before writing any spec code:

1. Read `spec/rails_helper.rb` and `spec/spec_helper.rb` for shared configuration
2. Check `spec/support/` for shared examples, custom matchers, and helper modules
3. Find **2–3 existing specs of the same type** (model spec, request spec, service spec) to understand the established style — and note which file you're modelling after:
   > _"I'm following the pattern in `spec/requests/api/v1/employees_spec.rb` — here's the structure it uses."_
4. Check `spec/factories/` for factories to reuse or extend
5. Check for shared examples that cover repeated patterns (authorization, pagination)

---

## Step 3 — Produce the Test Case Inventory

**Before writing any spec code**, output a complete test case inventory. Present it as a checklist and wait for the user to confirm it is complete before proceeding to Step 4.

```markdown
## Test Case Inventory: [ClassName or endpoint]

### Positive (happy path)
- [ ] [what succeeds — be specific about the observable outcome: status code, record state, job enqueued]

### Negative (failure / rejection)
- [ ] [what input or state causes failure — be specific about error response or raised exception]

### Authorization
- [ ] Authenticated user with correct role → succeeds (expected outcome)
- [ ] Unauthenticated request → 401 Unauthorized
- [ ] Authenticated user from wrong company/tenant → 403 or record not found
- [ ] Authenticated user with insufficient role → 403 Forbidden

### Edge Cases
- [ ] nil / empty / boundary inputs
- [ ] Concurrent calls (if idempotency matters)
- [ ] [domain-specific edge case]

### Side Effects
- [ ] [email sent / not sent under which condition]
- [ ] [background job enqueued with correct args]
- [ ] [associated record created / updated / deleted]
```

---

## Step 4 — Write the Specs

Write specs following all of these conventions. Where an existing spec already sets a convention in that file, match it first — then apply these rules.

### Block Ordering (MANDATORY)
```ruby
subject → let / let! → before / after → it
```
One empty line after the last `let`/`subject` group. One empty line between `describe`/`context` blocks. No empty line immediately after `describe`/`context`/`it` declarations.

### No Inline Setup in `it` Blocks (MANDATORY)
All test data must live in `let`, `let!`, or `before` — never inside an `it` block:

```ruby
# ❌ WRONG
it 'archives the employee' do
  employee = create(:employee)
  employee.archive!
  expect(employee.archived?).to be true
end

# ✅ CORRECT
let(:employee) { create(:employee) }

it 'archives the employee' do
  employee.archive!
  expect(employee).to be_archived
end
```

### `aggregate_failures` for Related Assertions
When multiple assertions share the same context with no state change between them, pack them:

```ruby
# ❌ WRONG — unnecessary separate examples
describe 'associations' do
  it { is_expected.to belong_to(:company) }
  it { is_expected.to belong_to(:department) }
end

# ✅ CORRECT
describe 'associations' do
  it 'has correct associations', :aggregate_failures do
    expect(subject).to belong_to(:company)
    expect(subject).to belong_to(:department)
  end
end
```

Applies to: associations, validations, simple attribute checks, response body field checks.

### `build` vs. `create`
- Use `build` (no DB hit) wherever the test does not require the record to be persisted
- Use `create` only when persistence is genuinely required by the test logic
- Every unnecessary `create` is a database round-trip that slows the suite

### Tenant Scoping in Request Specs (MANDATORY)
Every request spec must include a company-scoped user and use `current_company` context:

```ruby
let(:company)  { create(:company) }
let(:user)     { create(:user, :admin, company: company) }
let(:headers)  { auth_headers(user) }
```

Never test against a user without a company, or a resource without scoping to that company.

### External Service Stubbing (MANDATORY)
Stub all external calls — email delivery, background jobs, third-party API clients:

```ruby
# Jobs
expect { make_request }.to have_enqueued_job(SomeWorker).with(record.id)

# External HTTP
stub_request(:post, 'https://api.external.com/...').to_return(status: 200, body: '{}')
```

Never allow real network calls in specs — they cause intermittent CI failures.

### Verified Doubles
Use `instance_double` and `class_double` — never raw `double` unless the class does not exist yet.

### `allow_any_instance_of` — FORBIDDEN
Never use `allow_any_instance_of`. Always stub on the specific object you already have:

```ruby
# ❌ WRONG
allow_any_instance_of(Company).to receive(:feature_enabled?).and_return(true)

# ✅ CORRECT
allow(company).to receive(:feature_enabled?).and_return(true)
```

---

## Step 5 — Run Iteratively Until Green

Run only the spec file(s) you wrote — not the full suite:

```bash
COVERAGE=false bundle exec rspec spec/path/to/spec_file.rb
```

For each failure:
1. Read the error message carefully — identify root cause, not just symptom
2. Make a targeted, minimal fix
3. Re-run the same spec file
4. Repeat until all pass

Only run the full suite once you are confident all new/changed specs are green.

---

## Output for Review

After specs pass, present:

1. The spec file(s) written
2. The final passing test run output (with `COVERAGE=false`)
3. Any edge cases from the inventory that could not be tested and why
