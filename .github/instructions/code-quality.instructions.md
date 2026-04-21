---
description: "Use when adding or modifying code. Covers iterative test/fix workflow, coverage expectations, linting commands, and a pre-completion security checklist."
applyTo: ["app/**/*.rb", "spec/**/*.rb"]
---

# Code Quality Standards

**Related**: [rails-conventions](rails-conventions.instructions.md) · [rspec-conventions](rspec-conventions.instructions.md) · [write-rspec playbook](../playbooks/write-rspec/PLAYBOOK.md) · [ai-workflow](ai-workflow.instructions.md)

## Test Coverage

Add or update unit tests for any code file that is added or changed. Follow existing spec patterns:
- Explore the project to find the appropriate spec location before creating new files
- Do not add new testing libraries or dependencies
- Achieve full coverage for any new or changed functionality

## Iterative Testing & Debugging Workflow (MANDATORY)

When running or fixing tests, follow this loop — **do not give up after the first error**:

1. Read the error message carefully
2. Identify the root cause (not just the symptom)
3. Make a targeted, minimal fix
4. Re-run the affected tests to verify
5. Repeat until fully resolved
6. Once all targeted tests pass, do one final run of the complete changed spec file

**During the debugging phase**, disable coverage reporting to speed up iteration:
```bash
# ✅ CORRECT — fast iteration during debugging
COVERAGE=false bundle exec rspec spec/path/to/spec_file.rb

# ❌ WRONG — running the full suite on every fix attempt wastes minutes per cycle
bundle exec rspec
```

Only run the full suite after you're confident all changes are correct.

## Linting (MANDATORY — run before every commit)

Run linting after changes and apply auto-fixable offenses:
```bash
bundle exec rubocop -a app/path/to/changed_file.rb
```

- Follow the project's existing `.rubocop.yml` configuration and the [Ruby Style Guide](https://github.com/rubocop/ruby-style-guide)
- For spec files, additionally follow the [RSpec Style Guide](https://github.com/rubocop/rspec-style-guide)
- Ignore configuration errors in the linting tools themselves (not code offenses)
- Do not disable cops inline (`# rubocop:disable`) without a documented reason
- Surface any unresolved offenses (those `-a` cannot fix) to the user before committing

## Security Checklist (MANDATORY — before marking any implementation done)

Full security rules are defined in the project's `copilot-instructions.md` ("Secure Coding Practices" section). Before marking any implementation complete, verify these non-negotiables:

- `authenticate_user!` (or subdomain auth equivalent) guards every new controller action
- `authorize` / `policy_scope` (Pundit) called on every data-touching action — see [rails-conventions](rails-conventions.instructions.md)
- All queries scoped through `current_company` — no bare `Model.find(params[:id])`
- No raw SQL string interpolation — use `where(id: params[:id])`, not `where("id = #{params[:id]}")`
- No hardcoded secrets — use `Rails.application.credentials` or `ENV[...]`
- No `html_safe` / `raw` on user-supplied content without explicit `sanitize`
- No PII, tokens, or passwords written to logs — verify `filter_parameters` covers any new fields
