---
description: "Use when adding or modifying code that requires tests, linting, or security review. Covers iterative testing workflow, test coverage expectations, linting, and secure coding requirements."
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

## Security Requirements

Every code change must satisfy these requirements before it is considered complete:

- **Input validation**: Validate and sanitize all user inputs at system boundaries
- **Error handling**: Implement proper error handling that does not expose stack traces, SQL errors, or internal state to the client
- **Parameterized queries**: Use ActiveRecord's query interface — never interpolate user input into SQL strings
- **No hardcoded secrets**: No API keys, passwords, tokens, or sensitive configuration values in source code — use environment variables or credentials
- **Authentication**: Verify `authenticate_user!` (or equivalent) guards every action that requires a logged-in user
- **Authorization**: Verify `authorize` / `policy_scope` (Pundit) or equivalent guards every action that accesses or modifies user data
- **Least privilege**: Code should only access the data and perform the operations it explicitly needs
- **XSS protection**: Never use `html_safe` or `raw` on user-supplied content without explicit sanitization
- **CSRF protection**: Do not disable CSRF protection on endpoints that perform state-changing operations
- **Safe logging**: Logs must never contain passwords, tokens, SSNs, bank account numbers, or PII — use `filter_parameters` and audit log lines before committing
