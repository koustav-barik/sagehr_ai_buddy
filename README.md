# sagehr_ai_buddy

A shared AI prompt library for the SageHR engineering team — developers, QA, and code reviewers working inside `rails-cakehr`.

---

## How It Works

This repo holds all team AI prompts as **VS Code Copilot customization files**. Once installed into `rails-cakehr`, they surface in two places:

| What you get | How to invoke | File type |
|---|---|---|
| **Specialized AI agents** (`initial-analysis`, `jira`, `pr-code-review`, `e2e-development`) | Select from the **agent mode picker** in Copilot Chat | `.agent.md` |
| **Reusable editable prompts** (`dev-*`, `qa-*`, `code-review-*`) | Type `/` in Copilot Chat → pick from the list | `.prompt.md` |
| **Always-on coding conventions** (Rails, RSpec, code quality) | Auto-injected when relevant files are open | `.instructions.md` |

---

## Quick Start

**1. Clone this repo** (if you haven't already):
```bash
cd ~/development
git clone <this-repo-url> sagehr_ai_buddy
```

**2. Run the install script** to link prompts into `rails-cakehr`:
(Ideally, there should be a development folder with both the relevant repos present inside it: development/rails-cakehr and development/sagehr_ai_buddy)
```bash
cd sagehr_ai_buddy
./install.sh
# or specify a different target:
./install.sh /path/to/your/rails-cakehr
```

**3. Open `rails-cakehr` in VS Code** — the prompts are live immediately.

**4. Set up Jira access** so agents can fetch ticket details automatically:

Generate a Jira API token at: https://id.atlassian.com/manage-profile/security/api-tokens

Then create a `.env.jira` credentials file in **both** repos:
```bash
# In sagehr_ai_buddy
cp ~/development/sagehr_ai_buddy/.env.jira.example ~/development/sagehr_ai_buddy/.env.jira

# In rails-cakehr
cp ~/development/sagehr_ai_buddy/.env.jira.example ~/development/rails-cakehr/.env.jira
```

Edit both `.env.jira` files and fill in your values:
```
JIRA_EMAIL=your.email@sage.com
JIRA_API_TOKEN=your_api_token_here
JIRA_BASE_URL=https://cakehr.atlassian.net
```

Test it works:
```bash
cd ~/development/rails-cakehr
./scripts/jira-fetch.sh CHR-XXXX
```

**5. Exclude the linked files from git tracking in `rails-cakehr`**:

The symlinked directories (`agents`, `prompts`, `instructions`, `learnings`, `scripts`) and `.env.jira` must not be tracked or committed by the `rails-cakehr` git repo. Rather than touching `rails-cakehr`'s shared `.gitignore`, add them to the **local-only exclude file** — this file works exactly like `.gitignore` but is never committed:

```bash
cat >> ~/development/rails-cakehr/.git/info/exclude << 'EOF'

# sagehr_ai_buddy symlinks and Jira credentials (local only)
.github/agents
.github/instructions
.github/prompts
.github/learnings
.env.jira
scripts
EOF
```

---

## Directory Structure

```
.github/
├── agents/
│   ├── initial-analysis.agent.md       # Ticket → finds all relevant files, maps logic flow, produces implementation plan
│   ├── pr-code-review.agent.md         # PR URL or branch → comprehensive review
│   ├── jira.agent.md                   # Fetch Jira ticket details on demand; supports read / analyse / plan modes
│   └── e2e-development.agent.md        # Ticket → ticket branch → implementation → specs → quality critique → PR (full pipeline)
├── prompts/
│   ├── dev-write-specs.prompt.md       # Write RSpec tests — produces test case inventory for approval, then writes and runs specs
│   ├── dev-quality-critique.prompt.md  # Critical review of changed code — scoped to PR diff or staged/unstaged changes only
│   ├── dev-address-review-comments.prompt.md # Work through open PR review comments — evaluates each one, explains validity and implications, waits for approval before changing code
│   ├── dev-pr-description.prompt.md    # Full structured PR description — diff + Jira ticket → title, root cause, implementation details, test coverage, how to test
│   ├── dev-debug.prompt.md             # Systematically work through a bug — reproduces, isolates, and fixes with explanation
│   ├── dev-refactor.prompt.md          # Refactor code to Rails conventions — thin controllers, service objects, Pundit, idiomatic Ruby
│   ├── dev-explain.prompt.md           # Explain a complex piece of code — plain English walkthrough for any method, class, or flow
│   ├── dev-migration.prompt.md         # Plan and write a DB migration safely — strong_migrations patterns, reversibility, index strategy
│   ├── dev-seed-factory.prompt.md      # Generate FactoryBot factories and seed data — traits, associations, realistic values
│   ├── qa-test-plan.prompt.md          # Write a feature test plan — scenarios, preconditions, expected outcomes, edge cases
│   ├── qa-regression.prompt.md         # Identify what could break from this change — dependency mapping, risk areas, suggested regression checks
│   ├── qa-bug-report.prompt.md         # Structure a detailed bug report — steps to reproduce, expected vs actual, environment, logs
│   ├── qa-acceptance-criteria.prompt.md # Review or write acceptance criteria — Given/When/Then format, covers happy path and edge cases
│   ├── code-review-checklist.prompt.md  # Full code review against team standards — correctness, security, performance, conventions
│   ├── code-review-security.prompt.md   # Security-focused review — OWASP Top 10, auth boundaries, injection, data leakage
│   └── code-review-performance.prompt.md # Performance and query optimisation review — N+1, missing indexes, unbounded loads, caching
├── learnings/
│   └── journal.md                          # Your personal learning journal — paste anything here; agents read and apply it automatically
└── instructions/
    ├── learnings.instructions.md           # Tells every agent to read journal.md and apply relevant lessons silently
    ├── rails-conventions.instructions.md   # Multi-tenancy, Pundit auth, service objects, API conventions (anchored to Ruby Style Guide)
    ├── rspec-conventions.instructions.md   # Spec structure, FactoryBot, shared examples, no-inline-assignment rule (anchored to RSpec Style Guide)
    └── code-quality.instructions.md        # Test/fix workflow, RuboCop linting commands, pre-merge security checklist
scripts/
└── jira-fetch.sh                       # curl + Python script to fetch Jira ticket details; reads credentials from .env.jira
.env.jira.example                       # Credential template — copy to .env.jira and fill in email + API token
install.sh                              # One-time setup — symlinks agents, prompts, instructions, and scripts into rails-cakehr
sagehr.code-workspace                   # Alternative to install.sh — multi-root workspace pointing at both repos
```

---

## Using the Agents

Switch to the agent in the **Copilot Chat mode picker** (the dropdown next to the chat input):

### `initial-analysis`
Paste a Jira ticket key **or** paste ticket text directly and this agent will:
- Fetch the ticket from Jira automatically if you give it a key (e.g. `CHR-XXXX`)
- Find every file in `rails-cakehr` that is relevant to the ticket
- Map the current logic flow (routes → controller → service → model)
- List exactly what needs to be added, modified, or deleted

### `jira`
Fetch any Jira ticket into your Copilot session on demand:
- `CHR-XXXXX` → full ticket: summary, description, subtasks, recent comments
- Add `analyse` or `plan` to proceed into codebase exploration

### `pr-code-review`
Paste a GitHub PR URL (or branch name) and this agent will:
- Fetch the PR from GitHub and switch to that branch locally
- **Auto-detect feature-branch PRs** — if the PR targets a branch other than `master`/`main`, it automatically enters child-PR review mode, scoping the diff to only the delta the child introduces on top of its parent feature branch
- Read only the files changed in the review scope
- Produce a changes walkthrough table (per-file: what changed and why)
- Perform a comprehensive architectural review covering: correctness, security, performance, multi-tenancy, Rails conventions, and code quality
- **Critically review specs** using the same checklist as `dev-write-specs`: coverage inventory (happy path, negative, auth, edge cases, side effects), block ordering, no inline variable assignment, `aggregate_failures`, shared examples, DB minimisation, external service stubbing, and security test cases
- Return a structured review with 🔴 blocking issues / 🟡 improvements / 🔵 suggestions
- Consult the project's instruction files to ensure alignment with team standards

**Reviewing a child PR branched off a feature branch:**
- **Automatic** — paste a single PR URL; if the PR targets a non-master branch the agent detects this and scopes the review correctly
- **Explicit** — paste two URLs (child PR first, parent PR second) to force feature-branch mode, useful when the base branch has been deleted or you want to be explicit: `https://github.com/org/repo/pull/456 https://github.com/org/repo/pull/123`

### `e2e-development`
The full end-to-end pipeline from Jira ticket to merged-ready PR. Paste a ticket key and the agent will:
- Fetch the Jira ticket and confirm understanding
- Analyse the codebase and present an implementation plan for approval
- Create the ticket branch (`build-CHR-XXXX-brief-description`) immediately after plan approval — all code is written on that branch from the start, keeping `master` clean
- Implement the changes file by file
- Produce a test case inventory for approval, then write and run the specs
- Run a self-critique (dev-quality-critique pass) on staged/unstaged changes and ask which issues to fix
- Commit and raise a PR with labels `Pending Review` and `Ai-generated`

**Every stage has an approval gate** — the agent pauses and waits for your confirmation before proceeding.

---

## Using the Prompts (`/` commands)

Type `/` in Copilot Chat and start typing the prompt name. The prompt text appears in the chat input as **editable text** — review and customize before submitting.

Prompts marked **_(preview)_** are AI-generated starting points that haven't been reviewed, tested, or customised yet — use with caution and verify the output.

| Command | Use case |
|---|---|
| `/dev-write-specs` | Write RSpec tests — outputs a test case inventory (positive, negative, auth, edge cases) for approval first, then writes and runs the specs |
| `/dev-quality-critique` | Critical review of changed code — scoped to the active PR diff or staged/unstaged changes only; pre-existing untouched code is never flagged |
| `/dev-address-review-comments` | Work through open PR review comments (Copilot or team) — evaluates each one, explains whether it is valid and why like a senior dev teaching, then waits for your decision before touching any code |
| `/dev-pr-description` | Full structured PR description — reads the diff + Jira ticket, produces title, root cause, implementation details by layer, test coverage summary, how to test, and checklist |
| `/dev-debug` | _(preview)_ Systematically work through a bug |
| `/dev-refactor` | _(preview)_ Refactor code to Rails conventions |
| `/dev-explain` | _(preview)_ Explain a complex piece of code |
| `/dev-migration` | _(preview)_ Plan and write a DB migration safely |
| `/dev-seed-factory` | _(preview)_ Generate FactoryBot factories / seed data |
| `/qa-test-plan` | _(preview)_ Write a feature test plan |
| `/qa-regression` | _(preview)_ Identify what could break from this change |
| `/qa-bug-report` | _(preview)_ Structure a detailed bug report |
| `/qa-acceptance-criteria` | _(preview)_ Review or write acceptance criteria |
| `/code-review-checklist` | _(preview)_ Full code review against team standards |
| `/code-review-security` | _(preview)_ Security-focused review |
| `/code-review-performance` | _(preview)_ Performance and query optimization review |

---

## Jira Integration Setup

The `jira` agent and `initial-analysis` agent can fetch tickets directly from Jira using the REST API. This replaces copy-pasting ticket text.

**1. Get a Jira API token:**
> https://id.atlassian.com/manage-profile/security/api-tokens

**2. Create your credentials file** (never committed — already in `.gitignore`):
```bash
cd ~/development/sagehr_ai_buddy
cp .env.jira.example .env.jira
# then edit .env.jira and fill in your email + token
```

**3. Test it:**
```bash
./scripts/jira-fetch.sh CHR-XXXXX
```
You should see a formatted Markdown summary of the ticket printed to stdout.

**4. Use it in Copilot:**
- Switch to the **`jira`** agent and type `CHR-XXXXX`
- Or switch to **`initial-analysis`** and type `CHR-XXXXX` — it fetches then analyses automatically

> **Note:** `JIRA_BASE_URL` defaults to `https://cakehr.atlassian.net`. Override it in `.env.jira` if needed.

---

## Keeping Prompts Updated

All prompts live in this repo. To get the latest:
```bash
cd ~/development/sagehr_ai_buddy
git pull
```
Because the install uses symlinks, changes are instantly available in `rails-cakehr` — no reinstall needed.

---

## Learner Journal

The learner journal is a plain text file at `.github/learnings/journal.md`. It is your personal coding memory — paste anything into it and every agent will silently read and apply relevant entries to future work, without you having to update any prompt or instruction. 
Like we humans learn new concepts and retain in memory, this serves as the tool's memory which can be used in future sessions without explicitly updating any existing instructions, prompts or agents.

**How to add learnings:**

Open `.github/learnings/journal.md` and paste. No format required. Examples of what to add:
- A concept explained in a code review that clicked for you
- A mistake you want to avoid repeating
- A Rails pattern, security rule, or RSpec convention you want to internalise
- A plain English note from a debugging session

Dates, headings, and bullet points are optional. The AI is designed to extract meaning from unstructured prose.

**How it works:**

`learnings.instructions.md` has `applyTo: "**"` so it is injected into every agent session. It instructs the agent to read `journal.md` at the start of each task and silently apply any relevant entries. When a past lesson applies directly, the agent surfaces the connection briefly so you can see your knowledge being used — reinforcing the pattern rather than re-explaining it from scratch.

**Automatic capture from review sessions:**

At the end of every `/dev-address-review-comments` session, the agent identifies the most teachable moments and offers to append them to the journal as ready-to-paste entries. You choose which ones to keep.

## Contributing a New Prompt

1. Create a `.prompt.md` or `.agent.md` file in the right `.github/` subdirectory
2. Follow the frontmatter format of existing files
3. Open a PR — the whole team benefits immediately on merge

---

## Alternative: Multi-Root Workspace

If you prefer not to symlink, open the bundled workspace file:
```bash
code sagehr.code-workspace
```
VS Code will load both `sagehr_ai_buddy` and `rails-cakehr` as workspace roots, making all prompts available without any file system changes.
