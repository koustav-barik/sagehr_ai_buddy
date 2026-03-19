---
description: "Generate FactoryBot factories and seed data for Rails models. Useful when adding a new model, extending an existing factory, or setting up realistic development seeds."
name: "dev-seed-factory"
argument-hint: "Name the model you need a factory for, or describe the seed data scenario..."
agent: "agent"
tools: [read, search, edit]
---

I need to create or update FactoryBot factories and/or seed data for:

**Model(s):**
[e.g., `Employee`, `PayrollRun`, `LeaveRequest`]

**Context:**
[e.g., "just added this model", "need traits for different states", "need realistic seed data for dev environment"]

---

Please:

### 1. Read the model
- All attributes and their types from the schema
- All validations (required fields, formats, uniqueness constraints)
- All associations (belongs_to, has_many, has_one)
- Any enum definitions

### 2. Check existing factories
Look in `spec/factories/` for:
- Related factories that can be reused as associations
- Existing sequences or shared traits to follow the same style
- Helper modules loaded in `spec/support/`

### 3. Write the factory

```ruby
# spec/factories/employees.rb
FactoryBot.define do
  factory :employee do
    # Use sequences for unique fields
    sequence(:email) { |n| "employee#{n}@example.com" }
    sequence(:employee_number) { |n| "EMP#{n.to_s.rjust(4, '0')}" }

    first_name  { Faker::Name.first_name }
    last_name   { Faker::Name.last_name }
    hired_on    { 1.year.ago }
    status      { :active }

    # Use association for belongs_to (avoids unnecessary DB hits)
    association :company
    association :department

    # Traits for common states
    trait :manager do
      role { :manager }
    end

    trait :inactive do
      status    { :inactive }
      left_on   { 30.days.ago }
    end

    trait :with_avatar do
      after(:create) do |employee|
        employee.avatar.attach(
          io: Rails.root.join("spec/fixtures/files/avatar.png").open,
          filename: "avatar.png"
        )
      end
    end
  end
end
```

Guidelines:
- Use `Faker` for realistic-looking data, sequences for uniqueness
- Never hardcode emails or unique values directly — they'll conflict in parallel tests
- Include traits for every meaningful state the model can be in
- Use `transient` attributes for factory-only config that affects traits

### 4. Seed data (if requested)
Write seed entries in `db/seeds.rb` or a scoped seed file, using `find_or_create_by` so seeds are idempotent:

```ruby
company = Company.find_or_create_by!(subdomain: "demo") do |c|
  c.name = "Demo Company"
end
```
