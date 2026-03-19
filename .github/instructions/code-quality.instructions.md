---
description: "Use when adding or modifying code. Covers iterative test/fix workflow, coverage expectations, linting commands, and a pre-completion security checklist."
applyTo: ["app/**/*.rb", "spec/**/*.rb"]
---

# Code Quality Standards

## Test Coverage

Add or update unit tests for any code file that is added or changed. Follow existing spec patterns:
- Explore the project to find the appropriate spec location before creating new files
- Do not add new testing libraries or dependencies
- Achieve full coverage for any new or changed functionality

## Iterative Testing & Debugging Workflow

When running or fixing tests, follow this loop — **do not give up after the first error**:

1. Read the error message carefully
2. Identify the root cause (not just the symptom)
3. Make a targeted, minimal fix
4. Re-run the affected tests to verify
5. Repeat until fully resolved
6. Once all targeted tests pass, do one final run of the complete changed spec file

**During the debugging phase**, disable coverage reporting to speed up iteration:
```bash
COVERAGE=false bundle exec rspec spec/path/to/spec_file.rb
```

Only run the full suite after you're confident all changes are correct.

## Linting

Run linting after changes and apply auto-fixable offenses:
```bash
bundle exec rubocop -a app/path/to/changed_file.rb
```

- Follow the project's existing `.rubocop.yml` configuration
- Ignore configuration errors in the linting tools themselves (not code offenses)
- Do not disable cops inline (`# rubocop:disable`) without a documented reason

## Security Checklist (before marking done)

- `authenticate_user!` (or subdomain auth equivalent) guards every new controller action
- `authorize` / `policy_scope` (Pundit) called on every data-touching action
- No raw SQL string interpolation — use ActiveRecord query interface
- No hardcoded secrets — use `Rails.application.credentials` or `ENV[...]`
- No `html_safe` / `raw` on user-supplied content without explicit `sanitize`
- No PII, tokens, or passwords written to logs — verify `filter_parameters` covers any new fields
