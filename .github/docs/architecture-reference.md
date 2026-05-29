# Architecture Reference — rails-cakehr

> Single source of truth for codebase structure. Referenced by the `analyse-codebase` playbook — load when doing analysis, exploration, or planning work.

---

## Stack

- **Ruby 2.7 / Rails 6.1** — avoid Ruby 3 syntax (`&.` is fine; pattern matching, numbered params are not)
- **PostgreSQL + PostGIS** — location-based features use PostGIS geometry columns
- **Sidekiq** — background job processing with retries
- **React 18** (new features) + **Vue 2** (legacy), TypeScript throughout
- **Webpack** (not Webpacker) — auto-discovers `container.tsx` and `application.js` per feature folder

---

## Repository Layout

The Rails app lives in `src/`. Other root folders rarely need changes:

- `configuration/` — environment config (pre-prod, prod, QA)
- `deployment/` — Docker configuration
- `docs/` — API documentation (Markdown, organized by API category)
- `reference/` — OpenAPI specifications

---

## Inside `src/`

| Folder | Purpose |
|---|---|
| `app/` | Main application code |
| `config/` | Rails config — routes, DB, initializers |
| `db/` | Migrations and schema |
| `spec/` | RSpec tests — mirrors `app/` structure |
| `features/` | Cucumber end-to-end browser tests |
| `hexagonal/` | Hexagonal architecture for complex/extractable features |
| `lib/` | Shared libraries and utilities |

---

## `app/` Directory

| Folder | Purpose |
|---|---|
| `controllers/` | HTTP request handling — **keep thin** |
| `models/` | ActiveRecord models — **keep thin** |
| `services/` | All business logic — plain Ruby, organized by domain |
| `workers/` | Sidekiq background jobs — call services; no logic here |
| `policies/` | Pundit authorization policies |
| `serializers/` | API response formatting |
| `decorators/` | Presentation logic for models |
| `admin/` | ActiveAdmin ("Bake the Cake" internal portal) |
| `javascript/` | Legacy Vue/JS code |
| `views/` | HAML/ERB server-rendered templates |
| `mailers/` | Email sending logic |

---

## Controller Inheritance Chain

```
ApplicationController        ← base: sets current company/user, CSRF, rescues common errors
├── SubdomainController      ← web: Pundit auth, multitenancy, scopes queries by subdomain/company
└── BaseController           ← API: Pundit auth, JSON responses, authentication, error formatting
```

When an action is not found in a controller, **always check the parent class** — it may be inherited from `SubdomainController` or `BaseController`.

---

## API Namespaces

`mobile/`, `sage/` (ecosystem integrations), `qa/`, `scheduling/`, `timesheets/`, internal service APIs  
Controllers are organized by domain, not by version.

---

## Service Object Pattern

```ruby
class Domain::ServiceName
  def initialize(dependency)
    @dependency = dependency
  end

  def call
    # all business logic here
  end
end

# Usage: Domain::ServiceName.new(resource).call
```

Organized by domain: `services/timesheets/`, `services/employees/`, `services/documents/`, etc.

---

## Sidekiq Worker Pattern

```ruby
class Domain::WorkerName
  include Sidekiq::Worker
  sidekiq_options queue: :default

  def perform(resource_id)
    Domain::ServiceName.new(Resource.find(resource_id)).call
    # keep perform small — logic belongs in the service
  end
end
```

---

## Authorization (Pundit)

- Every controller action **must** call `authorize` — never skip it
- `ApplicationPolicy` is the base — all policies inherit from it
- Policy methods answer "Can this user do X?" — return `true` or `false`
- All queries **must** be scoped through `current_company` — prevents cross-tenant data leakage

---

## Frontend

- **React 18** — functional components + hooks, for all new features
- **Vue 2** — legacy code only
- **TypeScript** in both React and Vue
- **Translations**: gettext-style; defined in `app/javascript/`; passed from controller as props to React containers — all user-facing text must be translatable
- **Webpack** bundles one entry per feature folder (not Webpacker/Sprockets)

---

## Hexagonal Architecture (`hexagonal/`)

Use when a feature has multiple entry points (web, mobile, API), needs strict business/delivery isolation, or is a candidate for future service extraction.

- `application/` — use case services (inherit base service, implement `.call`)
- `infrastructure/` — serializers, responders (isolated from business logic)

---

## Testing

| Type | Tool | Location |
|---|---|---|
| Ruby unit/integration | RSpec | `spec/` — mirrors `app/` |
| Frontend | Jest + React Testing Library | `spec/javascript/` |
| End-to-end browser | Cucumber | `features/` |
| Test data | FactoryBot | `spec/factories/` |
| External API mocking | WebMock | Throughout specs — **never hit real APIs in tests** |
