---
description: "Plan and write a safe database migration for Rails. Covers schema changes, data migrations, index additions, and rollback safety."
name: "dev-migration"
argument-hint: "Describe the schema change you need (add column, rename, add index, data backfill, etc.)..."
agent: "agent"
tools: [read, search, edit, runCommands, todo]
---

I need to write a database migration for the following change:

**What needs to change:**
[describe the schema change — e.g., "add nullable `archived_at` datetime to employees table", "rename `manager_id` to `reports_to_id` on users", "add index on `company_id` on payroll_runs"]

**Reason / ticket:**
[why is this change needed]

---

Please help me plan and write this migration safely:

### Step 0 — Find a similar migration already in our repo
Search `db/migrate/` for a migration that does the same type of change (same column type, similar constraint, same table structure). Show me: _"Here's a migration we already have that does something similar: `db/migrate/20250101_...rb` — we'll follow the same pattern."_ This helps me learn what safe migrations look like in our specific codebase, not just in theory.

### Step 1 — Understand the current state
Read the relevant model(s) and existing migrations to understand:
- Current schema for the affected table(s)
- Existing indexes and constraints
- Model validations that reference this column
- Any associations that may be affected

### Step 2 — Assess risk
- **Table size**: Large tables need `algorithm: :instafile` / online schema change — flag if the table could have thousands of rows
- **Null safety**: Is the new column nullable? Does it have a default? What do existing rows get?
- **Rollback plan**: Can the `down` method truly undo this change without data loss?
- **Deployment order**: If code and migration are deployed separately, will things break between the two?

### Step 3 — Write the migration

Follow these rules:
- Always implement `def down` (make migrations reversible)
- For data migrations: use `find_each` in batches — never `update_all` on a table with millions of rows without considering locks
- For new NOT NULL columns: add the column as nullable first, backfill, THEN add the not-null constraint in a second migration
- Include indexes in the same migration as the column if the table is small; separate migration if large
- Use strong migration patterns (no default values on large tables in the same statement)

### Step 4 — Update the model
List any changes needed to the model:
- Add/update validations
- Add/update scopes (e.g., `scope :active, -> { where(archived_at: nil) }`)
- Update `attr_accessor` or strong parameters if needed

### Step 5 — Apply & verify
Use the `edit` tool to write the migration file, then run:
```bash
bundle exec rails db:migrate
bundle exec rails db:rollback
bundle exec rails db:migrate
```
to verify the migration is reversible. Run any affected specs with `runCommands` to confirm nothing broke.

