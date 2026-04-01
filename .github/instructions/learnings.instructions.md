---
description: "Developer learning journal — lessons accumulated from code reviews, debugging, and team feedback. Automatically scanned and applied to relevant work without requiring any manual prompt updates."
applyTo: "**"
---

## Learning Journal

At the start of every task, use the `read` tool to load `.github/learnings/journal.md`.

Scan the entries for anything relevant to the current request — same Rails pattern, same type of bug, same security concern, same testing approach, same naming convention, or any lesson that applies to what is being built or reviewed right now.

**Apply relevant lessons silently** — weave them into your response naturally rather than quoting the journal. Only surface the connection explicitly when a past lesson directly explains something in the current task:

> _"Based on your learning about N+1 queries — this is the same pattern: calling an association inside an `.each` loop without eager loading. The fix is the same one you noted before."_

This closes the loop between what was learned in a past review and what is being encountered now. It helps patterns stick rather than being re-explained from scratch each time.

**Do not:**
- Summarise or read the journal aloud unless asked
- Force-apply learnings that are not genuinely relevant to the current task
- Treat entries as hard rules — they are lessons and observations, not constraints
- Mention the journal exists unless the user asks about it
