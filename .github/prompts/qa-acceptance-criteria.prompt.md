---
description: "Review, critique, or write acceptance criteria for a feature. Identifies ambiguities, missing edge cases, and untestable criteria before development starts."
name: "qa-acceptance-criteria"
argument-hint: "Paste the ticket, user story, or draft acceptance criteria you want reviewed..."
agent: "agent"
tools: [read, search, runCommands, todo]
---

I need help with acceptance criteria for the following:

**Ticket / User story:**
[paste the ticket description or user story]

**Draft acceptance criteria (if you have them):**
[paste existing ACs, or leave blank to generate from scratch]

**Mode:** [Review existing ACs / Write ACs from scratch / Both]

---

## If reviewing existing acceptance criteria:

For each criterion, evaluate:
- **Is it testable?** Can a QA engineer write a clear pass/fail test for this?
- **Is it specific enough?** Or does it leave room for interpretation?
- **Is it complete?** Does it cover error cases, not just happy path?
- **Is it consistent?** Does it contradict any other criterion or existing behavior?
- **Is it realistic?** Can this actually be built within the stated constraint?

Flag each issue as:
- ❓ **Ambiguous** — "what does 'should work correctly' mean?"
- ❌ **Missing** — gap in coverage (edge case, error state, auth boundary)
- ⚠️ **Conflicting** — contradicts another AC or existing behavior
- 🔁 **Duplicate** — covered elsewhere

---

## If writing acceptance criteria from scratch:

Use the Given/When/Then (Gherkin) format and cover:

**Given** [precondition / state of the world]  
**When** [user action or event]  
**Then** [expected observable result]

Ensure coverage of:
- [ ] Happy path — primary success scenario
- [ ] Empty/zero state — what happens with no data
- [ ] Validation errors — what errors appear and when
- [ ] Authorization — who can and cannot do this action
- [ ] Edge cases — boundary values, concurrent actions
- [ ] Side effects — emails sent, records created, jobs enqueued

---

## Output

Produce a numbered list of acceptance criteria ready to paste into the ticket.
Each criterion should be a single, independently testable statement.
