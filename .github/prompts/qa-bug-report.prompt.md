---
description: "Write a clear, detailed bug report with all the information developers need to reproduce and fix the issue. Structures the report in the project's standard format."
name: "qa-bug-report"
argument-hint: "Describe what you observed — what happened and what you expected..."
agent: "agent"
tools: [read, search]
---

I need to write a detailed bug report for the following issue:

**What I observed:**
[describe what actually happened]

**What I expected:**
[describe what should have happened]

**Where it happened:**
[environment, page/screen, user role, company/account used]

---

Please help me write a complete bug report:

## Bug Report

### Summary
[One sentence: what is broken, on what feature, with what impact]

### Environment
- **Environment:** [Production / Staging / Local]
- **Browser / Client:** [e.g., Chrome 121, iOS 17, Postman]
- **User role:** [Admin / Manager / Employee]
- **Company / Tenant:** [if multi-tenant]
- **Date / Time observed:** [when did this happen]

### Steps to Reproduce
1. [Action one]
2. [Action two]
3. [Action three]
4. **Observed:** [what happened]
5. **Expected:** [what should have happened]

### Frequency
- [ ] Always reproducible
- [ ] Intermittent — happens approximately X% of the time
- [ ] Only happened once

### Impact
- **Severity:** Critical / High / Medium / Low
- **Users affected:** [everyone / specific roles / specific scenario]
- **Workaround available:** [yes/no — describe if yes]

### Evidence
- **Error message:** (paste exact text)
- **Stack trace / server error:** (paste if available)
- **Screenshot / Recording:** (attach)
- **Network request/response:** (paste relevant API response if applicable)
- **Relevant log lines:** (paste from Datadog / Papertrail / local logs)

### Additional Context
[Any other relevant information — recent deployments, data characteristics, related tickets]

### Suspected Area
[If you have a hypothesis about where the bug might be — route, model, service — mention it here to help the developer start faster]
