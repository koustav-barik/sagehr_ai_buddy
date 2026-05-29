---
description: "Use when writing, reading, or reviewing RSpec test files. Covers spec structure, FactoryBot patterns, shared examples, request spec conventions, and common pitfalls."
applyTo: "spec/**/*.rb"
---

# rails-cakehr RSpec Conventions

> Follow the [RSpec Style Guide](https://github.com/rubocop/rspec-style-guide). Project-specific rules below take precedence.

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

## Naming Rules

- `describe` → class/method name (e.g. `describe "#archive!"`)
- `context` → condition starting with "when", "with", "given", or "as"
- `it` → expected outcome, present tense, no "should" (e.g. `it "returns 422 Unprocessable Entity"`)

## FactoryBot

- `build` (no DB hit) — prefer for unit tests; `create` only when persistence is needed
- Use traits for named states: `create(:user, :admin)`, `create(:employee, :inactive)`

## Request Specs — Tenant Scoping (MANDATORY)

Every request spec must scope to a company: `let(:company) { create(:company) }`, `let(:user) { create(:user, :admin, company: company) }`, `let(:headers) { auth_headers(user) }`. Never test against a user without a company, or a resource without scoping to that company.

## Block Ordering (MANDATORY) (MANDATORY)

Always: `subject` → `let`/`let!` → `before`/`after` → `it`. One empty line after the last `let`/`subject` block. One empty line between `describe`/`context` blocks. No empty line directly after a `describe`/`context`/`it` declaration.

## No Inline Assignment in `it` Blocks (MANDATORY)

All test data setup in `let`, `let!`, or `before` — never assign variables inside an `it` block. Keeps examples short, setup reusable, and prevents hidden state dependencies.

## Pack Related Assertions (`aggregate_failures`)

When multiple assertions share the same context with no state change, pack them with `:aggregate_failures`. Apply to: associations, validations, simple attribute checks.

## Shared Examples

Place in `spec/support/shared_examples/`. Use for: repetitive predicate tests, authorization patterns (`it_behaves_like 'an authenticated endpoint'`), and common validation patterns.

## Stubs & Mocks

- `instance_double`/`class_double` for verified doubles — fail fast if the real interface changes
- Never VCR cassettes for unit-level specs — stub directly with `allow(...).to receive(...)`
- In request specs, stub heavy service objects rather than extra `create` calls

### `allow_any_instance_of` is FORBIDDEN

Always stub on the specific object instance already in scope. `allow_any_instance_of` is for legacy code without dependency injection — if you think you need it, fix the design instead.

## External Service Stubbing (MANDATORY)

All external calls — email, background jobs, third-party API clients — must be stubbed. No real network calls in specs.

## Common Pitfalls

- No `before(:all)` — shares state, causes flaky tests
- No testing private methods directly — test through the public interface
- No `binding.pry` or `pp` in committed specs
- No `sleep` — use `have_enqueued_job`, Timecop, or stubs
- No extra `create` calls in controller specs to compensate for missing stubs
