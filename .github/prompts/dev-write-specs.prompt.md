---
description: "Write or update RSpec tests for implemented changes. Brainstorms all test scenarios and writes production-ready specs following project conventions, including authorization, edge cases, and error conditions."
name: "dev-write-specs"
argument-hint: "I'll write specs for the current PR changes..."
agent: "agent"
tools: [read, search, edit, runCommands, todo, github-pull-request_activePullRequest, get_changed_files]
---

Write thorough, well-structured RSpec specs that give the team confidence to refactor and ship safely.

## Initial Context Gathering

**Before writing any specs, fetch the current PR context:**

1. Use #tool:github-pull-request_activePullRequest to get the active PR details:
   - PR title and description (understand what feature/fix was implemented)
   - List of all changed files (these are the files that need specs)
   - Existing review comments (may highlight areas needing extra test coverage)
2. Alternatively, if no active PR or user provides specific code, use #tool:get_changed_files to see what was modified
3. Identify which changed files are in `app/` (implementation) vs. `spec/` (tests)
4. For each implementation file changed, check if corresponding specs exist and need updates

If the user selects specific code or describes a feature, write specs for that. Otherwise, default to writing/updating specs for all implementation changes in the active PR.

---

## Your Process

→ Follow the **write-rspec playbook** (`.github/playbooks/write-rspec/PLAYBOOK.md`). Start with Step 1 — read the code under test.

When discovering existing patterns (Step 2), always **show the user which existing spec you're modelling after**: _"I'm following the pattern in `spec/requests/api/v1/employees_spec.rb` — the new spec will mirror that structure."_

---

## After Writing Specs

1. **Run the specs** with `runCommands`: `bundle exec rspec <spec_files>` — fix any failures iteratively, showing the output of each run.
2. **Explain each spec block** as you write it, in plain English, as a senior dev would to a junior: _"This context tests what happens when X — we need it because Y."_ Always point to the existing spec you modelled it after (from Step 2), so the user learns the pattern, not just sees the result.
3. **Name the common pitfall** \u2014 for each new spec pattern introduced (shared examples, aggregate_failures, verified doubles), mention the one thing beginners most often get wrong with it.
