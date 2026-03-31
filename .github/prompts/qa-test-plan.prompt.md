---
description: "Create a structured test plan for a feature or change. Lists all scenarios that need manual or automated verification before the feature ships."
name: "qa-test-plan"
argument-hint: "Describe the feature, ticket, or change you need a test plan for..."
agent: "agent"
tools: [read, search, runCommands, todo]
---

I need a test plan for the following feature or change:

**Feature / Ticket:**
[describe the feature or paste the Jira ticket title and description]

**Scope:**
[e.g., "manual regression", "exploratory testing", "full feature verification before release"]

---

Please produce a structured test plan:

## Feature Analysis
First, read any relevant code and ticket details to understand:
- What the feature does and its acceptance criteria
- Who the affected user types are (admin, manager, employee, unauthenticated)
- What data states are involved
- What integrations or side effects exist (emails, jobs, external APIs)

## Test Plan

### Setup / Prerequisites
[What data/configuration needs to exist before testing begins]

### Happy Path Scenarios
| # | Scenario | Role | Steps | Expected Result |
|---|---|---|---|---|
| 1 | | | | |

### Edge Cases
| # | Scenario | Input | Expected Result |
|---|---|---|---|
| 1 | | | |

### Negative / Error Cases
| # | Scenario | Expected Behavior |
|---|---|---|
| 1 | | |

### Authorization Boundaries
| Role | Can do | Cannot do |
|---|---|---|
| Admin | | |
| Manager | | |
| Employee | | |
| Unauthenticated | | |

### Regression Risk Areas
[List existing features that this change could break — these need verification too]

### API / Integration Checks (if applicable)
[Endpoints, request/response format, error codes to verify]

### Performance Considerations
[Any scenarios where volume or load should be tested]

---

**Definition of Done for this test plan:**
- [ ] All happy path scenarios pass
- [ ] All error scenarios behave as expected
- [ ] Authorization boundaries are enforced
- [ ] No regression in related features
