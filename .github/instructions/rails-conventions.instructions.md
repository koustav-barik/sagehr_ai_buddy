---
description: "Use when writing, reviewing, or refactoring Ruby on Rails code in rails-cakehr. Covers Rails conventions, service object patterns, API design, multi-tenancy, and project-specific patterns."
applyTo: "app/**/*.rb"
---

# rails-cakehr Rails Conventions

> **Style reference:** Follow the [Ruby Style Guide](https://github.com/rubocop/ruby-style-guide) for all Ruby code. Project-specific rules below take precedence where they differ.

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

In service objects, pass `company:` explicitly as a parameter — never access it as a global.

## Authorization

- Every controller action that touches data must call `authorize @resource` or `policy_scope(Resource)`

```ruby
# Controller
def show
  @employee = policy_scope(Employee).find(params[:id])
  authorize @employee
end
```

## API Conventions

- Namespace all API routes under `/api/v1/`
- Return errors as: `{ errors: ["message"] }` or `{ error: "message" }`
- Use `render json: EmployeeSerializer.new(@employee)` — never build JSON hashes manually in controllers

## Models

- Prefer named scopes over raw `where` in controllers
- Use `enum` with a hash (not index position): `enum status: { active: "active", inactive: "inactive" }`
- Validations: separate concern-grouped validations with `with_options` for readability
- Callbacks: use sparingly. Never use callbacks for cross-model side effects — use service objects instead

