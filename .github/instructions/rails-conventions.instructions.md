---
description: "Use when writing, reviewing, or refactoring Ruby on Rails code in rails-cakehr. Covers Rails conventions, service object patterns, API design, multi-tenancy, and project-specific patterns."
applyTo: "app/**/*.rb"
---

# rails-cakehr Rails Conventions

**Related**: [code-quality](code-quality.instructions.md) · [rspec-conventions](rspec-conventions.instructions.md) · [ai-workflow](ai-workflow.instructions.md)

> **Style reference:** Follow the [Ruby Style Guide](https://github.com/rubocop/ruby-style-guide) for all Ruby code. Project-specific rules below take precedence where they differ.

## Architecture

- **Fat model, thin controller** — business logic belongs in service objects or models, not controllers
- **Service objects** live in `app/services/` — one public method (`.call`), named as verbs: `ProcessPayroll`, `ArchiveEmployee`
- **Controllers** should: authenticate, authorize, call a service/model method, render the response — nothing else
- **Serializers** handle JSON shaping — keep serializer logic out of controllers and models

```ruby
# ❌ WRONG — business logic in the controller
def create
  @employee = Employee.new(employee_params)
  @employee.company = current_company
  OnboardingWorkflow.new(@employee).trigger! if @employee.save
  render json: @employee
end

# ✅ CORRECT — controller delegates to a service
def create
  @employee = Employees::CreateService.call(employee_params, company: current_company)
  authorize @employee
  render json: EmployeeSerializer.new(@employee), status: :created
end
```

## Multi-tenancy (MANDATORY)

Every query against company-owned data **must** be scoped through the current company:

```ruby
# WRONG — exposes cross-tenant data
Employee.find(params[:id])

# CORRECT
current_company.employees.find(params[:id])
```

In service objects, pass `company:` explicitly as a parameter — never access it as a global.

## Authorization (MANDATORY)

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
- Use `enum` with a hash (not index position):

```ruby
# ❌ WRONG — index-based enums break silently if values are reordered
enum status: [:active, :inactive]

# ✅ CORRECT — explicit string values, safe to reorder
enum status: { active: "active", inactive: "inactive" }
```

- Validations: separate concern-grouped validations with `with_options` for readability
- Callbacks: use sparingly. **Never use callbacks for cross-model side effects** — use service objects instead:

```ruby
# ❌ WRONG — callback reaching across model boundary
after_create :trigger_onboarding_workflow

# ✅ CORRECT — side effect owned explicitly by the service
class Employees::CreateService
  def call
    employee = Employee.create!(params)
    OnboardingWorkflow.new(employee).trigger!
    employee
  end
end
```

## Performance

- **N+1 queries**: avoid calling associations inside loops — use `includes` or `eager_load`:

```ruby
# ❌ WRONG — N+1: hits the DB for every employee
employees.each { |e| e.department.name }

# ✅ CORRECT
employees.includes(:department).each { |e| e.department.name }
```

- **Large datasets**: paginate with `will_paginate` or `pagy_cursor` (match the style already used in the area you're working in) — never load unbounded collections with `.all`
- **Expensive work**: email delivery, report generation, external API calls, and bulk operations belong in Sidekiq workers — not in the request cycle
- **New columns** used in `where`, `order`, or `joins` must be indexed in the migration
