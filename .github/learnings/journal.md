# Developer Learning Journal

This file is your personal coding memory. Paste anything here — notes from a code review, a concept that clicked, a mistake you want to avoid, a pattern you learned. No structure required. The AI will read this file at the start of every session and silently apply whatever is relevant to the current task.

When a past lesson applies to something you are working on, the AI will surface the connection briefly so you can see your own knowledge being used in practice.

---

<!-- Add your learnings below this line. Paste freely — dates, headings, and formatting are optional. -->

Rails convention is that a controller action should read like a sentence — call a service, render a response, done. The nested branching adds cognitive overhead that private methods can remove. The project's own RuboCop config caps method length at 20 lines. "Fat controller action" is a common code smell in Rails. The fix is not to move logic to the model — it's to extract the rendering decision into small, private methods so the create action reads as a linear flow without nested conditionals.

Controller specs should cover all meaningful response paths — status code, body shape, and redirect destination — not just side effects (like worker invocations). The failure path is often where security and UX regressions hide: a 500 instead of a 422, or a leaked stack trace in JSON, would only be caught by this test.

SubdomainController is the base class for every controller in the application — it carries session management, tenant loading, Pundit, and before-action chains that affect every request. Putting sage_50_payroll_additional_texts (specific to one ticket, just an example) there makes a method about the copy inside a very specific payroll modal available on every controller in the app. That is a violation of the Single Responsibility Principle and pollutes the shared namespace. A concern gives you the same code reuse while being explicit about which controllers actually need this capability. Rails controller concerns are the right tool when a behaviour is shared between a small set of controllers that don't share a closer common ancestor.

Fail fast over silent fallback. When you write a fallback for a case that shouldn't happen, ask yourself: "If this triggers, do I want it to be invisible?" Silent fallbacks hide bugs in development and in staging, letting them reach production where they're harder to diagnose.

Defence in depth — sanitise data at the point you produce it, not just at the point you render it. If you rely on the consumer to be safe, you're one careless .html() refactor away from a stored XSS vulnerability.

allow_any_instance_of is a code smell in RSpec. It was designed for legacy code where you can't inject dependencies. In a spec where you already have a reference to the specific object (let(:company)), stubbing on that object is always preferred — it's explicit about exactly which instance returns the stubbed value, and it won't unexpectedly affect other Company instances that might be created during the test.