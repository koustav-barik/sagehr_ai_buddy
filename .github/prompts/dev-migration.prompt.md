---
description: "Plan and write a safe database migration for Rails. Covers schema changes, data migrations, index additions, and rollback safety."
name: "dev-migration"
argument-hint: "Describe the schema change you need (add column, rename, add index, data backfill, etc.)..."
agent: "agent"
tools: [read, search, edit]
---

I need to write a database migration for the following change:

**What needs to change:**
[describe the schema change — e.g., "add nullable `archived_at` datetime to employees table", "rename `manager_id` to `reports_to_id` on users", "add index on `company_id` on payroll_runs"]

**Reason / ticket:**
[why is this change needed]

---

Please help me plan and write this migration safely:

### Step 1 — Understand the current state
Read the relevant model(s) and existing migrations to understand:
- Current schema for the affected table(s)
- Existing indexes and constraints
- Model validations that reference this column
- Any associations that may be affected

### Step 2 — Your Risk Assessment First

Before presenting the full risk analysis, ask:

> _"Before I assess the risks — how would YOU rate the riskiness of this migration, and why?_
>
> _Think through: How large is this table likely to be in production? Is this column nullable? Can the migration be rolled back without data loss? What happens in the window between deploying code and running the migration — will anything break?_
>
> _(Say 'assess it' to skip straight to my analysis.)"_

After the user responds (or skips), present the full risk assessment and note where their instincts were right, where they missed something, and — most importantly — *why* the risks that surprised them are real.

### Step 3 — Risk Assessment (AI analysis)
- **Table size**: Large tables need `algorithm: :instafile` / online schema change — flag if the table could have thousands of rows
- **Null safety**: Is the new column nullable? Does it have a default? What do existing rows get?
- **Rollback plan**: Can the `down` method truly undo this change without data loss?
- **Deployment order**: If code and migration are deployed separately, will things break between the two?

### Step 4 — Write the migration

Follow these rules:
- Always implement `def down` (make migrations reversible)
- For data migrations: use `find_each` in batches — never `update_all` on a table with millions of rows without considering locks
- For new NOT NULL columns: add the column as nullable first, backfill, THEN add the not-null constraint in a second migration
- Include indexes in the same migration as the column if the table is small; separate migration if large
- Use strong migration patterns (no default values on large tables in the same statement)

```ruby
# Example skeleton
class AddArchivedAtToEmployees < ActiveRecord::Migration[7.1]
  def up
    add_column :employees, :archived_at, :datetime
    add_index :employees, :archived_at
  end

  def down
    remove_index :employees, :archived_at
    remove_column :employees, :archived_at
  end
end
```

### Step 5 — Update the model
List any changes needed to the model:
- Add/update validations
- Add/update scopes (e.g., `scope :active, -> { where(archived_at: nil) }`)
- Update `attr_accessor` or strong parameters if needed

---

## Reflection Beat

After presenting the full migration, close with one question:

> _"One thing to sit with: if you ran this migration on a table with 2 million rows at 9am on a Monday — walk me through exactly what would happen. What would lock? For how long? What would users see?_
>
> _If you're not sure, that's the answer — it means this deserves stronger migrations tooling or an online schema change strategy."_
