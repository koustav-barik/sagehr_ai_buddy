---
description: "Use when writing, reviewing, or refactoring Ruby on Rails code in rails-cakehr. Covers Rails conventions, service object patterns, API design, multi-tenancy, and project-specific patterns."
applyTo: "app/**/*.rb"
---

# rails-cakehr Rails Conventions

## Architecture

- **Fat model, thin controller** — business logic belongs in service objects or models, not controllers
- **Service objects** live in `app/services/` — one public method (`.call`), name them as verbs: `ProcessPayroll`, `ArchiveEmployee`
- **Controllers** should: authenticate, authorize, call a service/model method, render the response — nothing else
- **Serializers** handle JSON shaping — keep serializer logic out of controllers and models

## Multi-tenancy

Every query against company-owned data **must** be scoped through the current company:

```ruby
# WRONG — exposes cross-tenant data
Employee.find(params[:id])

# CORRECT
current_company.employees.find(params[:id])
```

`current_company` is always available in controllers via `ApplicationController`. In service objects, pass `company:` explicitly rather than relying on globals.

## Authorization

- Use **Pundit** for policy-based authorization
- Every controller action that touches data must call `authorize @resource` or `policy_scope(Resource)`
- Policy files live in `app/policies/`
- Test policies in `spec/policies/` — treat them as first-class code

```ruby
# Controller
def show
  @employee = policy_scope(Employee).find(params[:id])
  authorize @employee
end
```

## API Conventions

- Namespace all API routes under `/api/v1/`
- Use HTTP status codes correctly: `200`, `201`, `204`, `400`, `401`, `403`, `404`, `422`, `500`
- Return errors as: `{ errors: ["message"] }` or `{ error: "message" }`
- Use `render json: EmployeeSerializer.new(@employee)` — never build JSON hashes manually in controllers

## Models

- Prefer named scopes over raw `where` in controllers
- Use `enum` with a hash (not index position): `enum status: { active: "active", inactive: "inactive" }`
- Validations: separate concern-grouped validations with `with_options` for readability
- Callbacks: use sparingly. Never use callbacks for cross-model side effects — use service objects instead

## Background Jobs

- Job files in `app/jobs/`
- Always use `perform_later` (async) unless synchronous execution is explicitly required
- Pass primitive IDs to jobs, not AR objects: `ProcessPayrollJob.perform_later(payroll_run.id)`
- Jobs must be idempotent — safe to retry on failure

## Error Handling

- Rescue at the controller or service boundary — not buried inside models
- Always log errors with context: `Rails.logger.error("Context: #{e.message}", e)`
- Never use bare `rescue Exception` — use `rescue StandardError` at most
- Surface user-facing errors via `422 Unprocessable Entity` with `{ errors: [...] }` body

## Logging

```ruby
Rails.logger.info("[ServiceName] Starting operation", { company_id: company.id })
```

Never log: passwords, tokens, SSNs, bank account numbers, or any PII.
