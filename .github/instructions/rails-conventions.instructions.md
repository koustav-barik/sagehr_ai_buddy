---
description: "Use when writing, reviewing, or refactoring Ruby on Rails code in rails-cakehr. Covers Rails conventions, service object patterns, API design, multi-tenancy, and project-specific patterns."
applyTo: "app/**/*.rb"
---

# rails-cakehr Rails Conventions

> Follow the [Ruby Style Guide](https://github.com/rubocop/ruby-style-guide). Project-specific rules below take precedence.

## Architecture

- **Fat model, thin controller** — business logic belongs in service objects or models, not controllers
- **Service objects** live in `app/services/` — one public method (`.call`), named as verbs: `ProcessPayroll`, `ArchiveEmployee`
- **Controllers** should: authenticate, authorize, call a service/model method, render the response — nothing else
- **Serializers** handle JSON shaping — no serializer logic in controllers or models

## Multi-tenancy (MANDATORY)

Every query against company-owned data **must** scope through `current_company`. Never `Employee.find(params[:id])` — always `current_company.employees.find(params[:id])`. In service objects, pass `company:` explicitly — never access it as a global.

## Authorization (MANDATORY)

Every controller action touching data must call `authorize @resource` or `policy_scope(Resource)`. No exceptions.

## API Conventions

- Namespace all API routes under `/api/v1/`
- Return errors as: `{ errors: ["message"] }` or `{ error: "message" }`
- Use `render json: EmployeeSerializer.new(@employee)` — never build JSON hashes manually in controllers

## Models

- Prefer named scopes over raw `where` in controllers
- Use `enum` with a hash (not index position): `enum status: { active: "active", inactive: "inactive" }`
- Validations: group with `with_options` for readability
- Callbacks: use sparingly. **Never use callbacks for cross-model side effects** — use service objects instead

## Performance

- **N+1 queries**: use `includes` or `eager_load` for associations in loops — never call `.association` inside `.each`
- **Large datasets**: paginate with `will_paginate` or `pagy_cursor` — never load unbounded collections with `.all`
- **Expensive work**: email delivery, report generation, external API calls, and bulk operations belong in Sidekiq workers — not in the request cycle
- **New columns** used in `where`, `order`, or `joins` must be indexed in the migration
