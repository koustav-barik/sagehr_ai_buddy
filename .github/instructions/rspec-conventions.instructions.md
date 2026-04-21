---
description: "Use when writing, reading, or reviewing RSpec test files. Covers spec structure, FactoryBot patterns, shared examples, request spec conventions, and common pitfalls."
applyTo: "spec/**/*.rb"
---

# rails-cakehr RSpec Conventions

**Related**: [code-quality](code-quality.instructions.md) · [rails-conventions](rails-conventions.instructions.md) · [write-rspec playbook](../playbooks/write-rspec/PLAYBOOK.md)

> **Style reference:** Follow the [RSpec Style Guide](https://github.com/rubocop/rspec-style-guide) for all spec files. Project-specific rules below take precedence where they differ.

## Spec Types & File Structure

| Code location | Spec type | Spec location |
|---|---|---|
| `app/models/` | Model spec | `spec/models/` |
| `app/controllers/` | Request spec | `spec/requests/` |
| `app/services/` | Service spec | `spec/services/` |
| `app/policies/` | Policy spec | `spec/policies/` |
| `app/jobs/` | Job spec | `spec/jobs/` |
| `app/serializers/` | Serializer spec | `spec/serializers/` |

Prefer **request specs over controller specs** — they test the full stack and give more confidence.

## Structure

```ruby
RSpec.describe Employee, type: :model do
  # Use subject for the primary object under test
  subject(:employee) { build(:employee) }

  # Group with describe (method names) and context (conditions)
  describe "#full_name" do
    context "when both names are present" do
      it "returns first and last name joined" do
        expect(employee.full_name).to eq("#{employee.first_name} #{employee.last_name}")
      end
    end

    context "when last_name is nil" do
      before { employee.last_name = nil }
      it "returns only the first name" do ...
    end
  end
end
```

## Naming Rules

- `describe` → class name or method name (e.g., `describe "#archive!"`)
- `context` → condition starting with "when", "with", "given", or "as" (e.g., `context "when the employee is inactive"`)
- `it` → expected outcome, present tense, no "should" (e.g., `it "returns 422 Unprocessable Entity"`)

## FactoryBot

```ruby
let(:employee) { build(:employee) }   # no DB hit — prefer for unit tests
let(:employee) { create(:employee) }  # DB-backed — use only when persistence is needed

# Use traits for named states
let(:admin)    { create(:user, :admin) }
let(:inactive) { create(:employee, :inactive) }
```

## Request Specs

Every request spec must include company-scoped context — **tenant scoping is MANDATORY**:

```ruby
RSpec.describe "POST /api/v1/employees", type: :request do
  subject(:make_request) { post api_v1_employees_path, params: params, headers: headers }

  let(:company)  { create(:company) }
  let(:user)     { create(:user, :admin, company: company) }
  let(:headers)  { auth_headers(user) }  # helper in spec/support/
  let(:params)   { { employee: attributes_for(:employee) } }

  it "returns 201" do
    make_request
    expect(response).to have_http_status(:created)
  end

  it "creates the employee" do
    expect { make_request }.to change(Employee, :count).by(1)
  end

  context "when unauthenticated" do
    let(:headers) { {} }

    it "returns 401" do
      make_request
      expect(response).to have_http_status(:unauthorized)
    end
  end
end
```

## Block Ordering

Always follow this order within every `describe`/`context` block:

```
subject → let / let! → before / after → it
```

One empty line after the last `let`/`subject` block. One empty line between `describe`/`context` blocks. No empty line directly after a `describe`/`context`/`it` declaration.

## No Inline Assignment in `it` Blocks

All test data setup must live in `let`, `let!`, or `before` blocks — **never assign variables inside an `it` block**.

```ruby
# ❌ BAD — setup inside the example
it 'archives the employee' do
  employee = create(:employee)
  employee.archive!
  expect(employee.archived?).to be true
end

# ✅ GOOD — setup in let/before, it block only contains action + expectation
let(:employee) { create(:employee) }

it 'archives the employee' do
  employee.archive!
  expect(employee).to be_archived
end
```

This keeps examples short, makes shared setup reusable across contexts, and prevents hidden state dependencies between examples.

## Packing Assertions with `aggregate_failures`

When multiple assertions share the same context (no variable changes, no state change needed), pack them into a single example:

```ruby
# ❌ BAD
describe 'associations' do
  it { is_expected.to belong_to(:company) }
  it { is_expected.to belong_to(:department) }
end

# ✅ GOOD
describe 'associations' do
  it 'has correct associations', :aggregate_failures do
    expect(subject).to belong_to(:company)
    expect(subject).to belong_to(:department)
  end
end
```

Apply to: associations, validations, simple attribute checks.

## Shared Examples

Place reusable examples in `spec/support/shared_examples/`. Use them for:
- Repetitive predicate tests (`#simple?`, `#meeting?`)
- Authorization patterns (`it_behaves_like 'an authenticated endpoint'`)
- Common validation patterns

```ruby
shared_examples 'sub_type predicate' do |method_name, sub_type_value|
  describe "##{method_name}" do
    context "when sub_type is #{sub_type_value}" do
      before { object.sub_type = sub_type_value }
      it { is_expected.to public_send("be_#{method_name}") }
    end

    context "when sub_type is not #{sub_type_value}" do
      before { object.sub_type = 'other' }
      it { is_expected.not_to public_send("be_#{method_name}") }
    end
  end
end
```

## Brainstorm Test Cases Before Writing

Before adding or editing any spec, produce a **test case inventory** as a commented list or inline plan:

```
# Test cases to cover:
# ✓ [positive] creates the record with valid params
# ✓ [positive] sends the notification email
# ✓ [positive] enqueues the background job with correct args
# – [negative] returns 422 when required field is blank
# – [negative] returns 401 when unauthenticated
# – [negative] returns 403 when user belongs to a different company
# – [edge] handles nil value without raising
# – [edge] is idempotent when called twice
```

Only start writing spec code once the full inventory is agreed. This ensures nothing is missed and gives a clear picture of what behaviours are being validated.

## Stubs & Mocks

- Use `instance_double` / `class_double` for verified doubles — they fail fast if the real interface changes
- Never rely on VCR cassettes for unit-level specs — stub directly with `allow(...).to receive(...)`
- In request specs, **stub heavy service objects** rather than adding extra `create` calls — every `create` is a DB round-trip

### `allow_any_instance_of` is FORBIDDEN

Never use `allow_any_instance_of`. It was designed for legacy code where you cannot inject dependencies. When you already have a reference to the specific object, always stub on that object directly:

```ruby
# ❌ WRONG — affects all Company instances, hides which one is stubbed
allow_any_instance_of(Company).to receive(:feature_enabled?).and_return(true)

# ✅ CORRECT — explicit about exactly which instance is stubbed
allow(company).to receive(:feature_enabled?).and_return(true)
```

If you think you need `allow_any_instance_of`, it means the code under test does not expose a seam for injection. Fix the design rather than reaching for this stub.

## Common Pitfalls to Avoid

- Do NOT use `before(:all)` — it shares state across examples and causes flaky tests
- Do NOT test private methods directly — test through the public interface
- Do NOT assert on implementation details (specific method calls) unless testing side effects
- Do NOT leave `binding.pry` or `pp` in committed specs
- Avoid `sleep` in tests — use `have_enqueued_job`, Timecop, or proper stubs instead
- Do NOT add new `create` calls inside controller specs to compensate for missing stubs
