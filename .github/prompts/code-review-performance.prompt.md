---
description: "Performance-focused code review. Analyzes N+1 queries, missing indexes, memory usage, slow queries, and opportunities to defer work to background jobs."
name: "code-review-performance"
argument-hint: "Paste the code or describe what needs a performance review..."
agent: "agent"
tools: [read, search]
---

Perform a performance-focused review of the following code:

**Code / PR:**
[paste code or describe the affected area]

**Context:**
[e.g., "high-traffic endpoint", "runs on every payroll calculation", "called in a webhook loop"]

**Current known scale:**
[e.g., "~50k employees per company", "3000 API calls/minute"]

---

Analyze the code for every performance concern below. For each finding, include:
- The exact code location
- What happens at scale (10x the current data volume)
- The fix

---

## 1. N+1 Queries
- Scan every loop (`.each`, `.map`, `.select`, `.reject`) for database calls inside them
- Check associations accessed inside loops — are they eager-loaded with `includes`, `preload`, or `eager_load`?
- Check if `belongs_to` associations are called inside iteration without eager loading
- Are counter caches available but unused?

Example of an N+1:
```ruby
# BAD — 1 query for companies + N queries for employees
Company.all.each { |c| puts c.employees.count }

# GOOD
Company.includes(:employees).all.each { |c| puts c.employees.size }
```

## 2. Missing Database Indexes
- For every new column introduced: will it be used in `WHERE`, `ORDER BY`, `GROUP BY`, or a `JOIN`? If yes, it needs an index.
- For every `find_by` or `where(column: value)`: is `column` indexed?
- For every `belongs_to` foreign key: is there an index on `*_id`?
- Are there composite index opportunities? (queries filtering on multiple columns together)

## 3. Unbounded Data Loading
- Is there a `Model.all` or large query with no `limit`/`where` scope?
- Are paginated endpoints using `limit`+`offset` (slow at scale) instead of cursor-based pagination?
- Is a full table being loaded into memory when only IDs or counts are needed?
- Use `find_each` or `in_batches` for bulk processing — never `.all.each` on large tables

## 4. Expensive Work in the Request Cycle
- Is any of this work something that could be deferred to a background job?
  - Sending emails → should be in a job
  - Generating reports/CSV → should be in a job
  - Calling external APIs → should be in a job unless the response is needed immediately
  - Bulk record updates → should be batched and backgrounded

## 5. Inefficient Queries
- Is `SELECT *` used when only specific columns are needed? (use `pluck`, `select(:id, :name)`)
- Are there queries that could use `exists?` instead of `count > 0` or `present?`
- Are there queries counting large sets where an approximation or counter cache would do?
- Is `.first` used without an explicit `order`? (non-deterministic and unindexed by default)

## 6. Memory Usage
- Are large file uploads or downloads streamed, or loaded entirely into memory?
- Are large arrays or hashes built in memory that could be handled in the database?
- Does this add significant object creation to a hot path?

## 7. Caching Opportunities
- Is this data queried repeatedly but rarely changes? Could it be cached with `Rails.cache`?
- Are there `memoization` opportunities (`@variable ||= ...`) for expensive computations within a request?

---

## Performance Review Summary

### 🔴 Critical (will cause production incidents at current or near-term scale)
- 

### 🟡 Should Fix (will degrade performance as data grows)
- 

### 🔵 Optimization Opportunities (nice to have)
- 

### Benchmark Recommendations
[If any changes are being proposed, suggest how to measure the improvement with `Benchmark.ms` or DB query count]
