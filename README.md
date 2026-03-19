# sagehr_ai_buddy

A shared AI prompt library for the SageHR engineering team — developers, QA, and code reviewers working inside `rails-cakehr`.

---

## How It Works

This repo holds all team AI prompts as **VS Code Copilot customization files**. Once installed into `rails-cakehr`, they surface in two places:

| What you get | How to invoke | File type |
|---|---|---|
| **Specialized AI agents** (initial-analysis, pr-code-review) | Select from the **agent mode picker** in Copilot Chat | `.agent.md` |
| **Reusable editable prompts** (dev-*, qa-*, code-review-*, write-specs, suggestion-quality) | Type `/` in Copilot Chat → pick from the list | `.prompt.md` |
| **Always-on coding conventions** (Rails, RSpec, code quality) | Auto-injected when relevant files are open | `.instructions.md` |

---

## Quick Start

**1. Clone this repo** (if you haven't already):
```bash
cd ~/development
git clone <this-repo-url> sagehr_ai_buddy
```

**2. Run the install script** to link prompts into `rails-cakehr`:
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
./scripts/jira-fetch.sh CHR-6367
```

**5. Exclude the linked files from git tracking in `rails-cakehr`**:

The symlinked directories (`agents`, `prompts`, `instructions`, `scripts`) and `.env.jira` must not be tracked or committed by the `rails-cakehr` git repo. Rather than touching `rails-cakehr`'s shared `.gitignore`, add them to the **local-only exclude file** — this file works exactly like `.gitignore` but is never committed:

```bash
cat >> ~/development/rails-cakehr/.git/info/exclude << 'EOF'

# sagehr_ai_buddy symlinks and Jira credentials (local only)
.github/agents
.github/instructions
.github/prompts
.env.jira
scripts
EOF
```

---

## Directory Structure

```
.github/
├── agents/
│   ├── initial-analysis.agent.md       # Ticket → relevant code + change plan (Jira-aware)
│   ├── pr-code-review.agent.md         # GitHub PR URL → comprehensive review
│   └── jira.agent.md                   # Fetch Jira ticket details on demand
scripts/
│   └── jira-fetch.sh                   # curl + Python script; reads from .env.jira
.env.jira.example                       # Credential template (copy to .env.jira)
├── prompts/
│   ├── write-specs.prompt.md           # Write RSpec tests for PR changes
│   ├── suggestion-quality.prompt.md    # Critical review of PR changes
│   ├── dev-debug.prompt.md
│   ├── dev-refactor.prompt.md
│   ├── dev-explain.prompt.md
│   ├── dev-pr-description.prompt.md
│   ├── dev-migration.prompt.md
│   ├── dev-seed-factory.prompt.md
│   ├── qa-test-plan.prompt.md
│   ├── qa-regression.prompt.md
│   ├── qa-bug-report.prompt.md
│   ├── qa-acceptance-criteria.prompt.md
│   ├── code-review-checklist.prompt.md
│   ├── code-review-security.prompt.md
│   └── code-review-performance.prompt.md
└── instructions/
    ├── rails-conventions.instructions.md
    ├── rspec-conventions.instructions.md
    └── code-quality.instructions.md
install.sh                              # One-time setup per developer
sagehr.code-workspace                  # Alternative: multi-root workspace
```

---

## Using the Agents

Switch to the agent in the **Copilot Chat mode picker** (the dropdown next to the chat input):

### `initial-analysis`
Paste a Jira ticket key **or** paste ticket text directly and this agent will:
- Fetch the ticket from Jira automatically if you give it a key (e.g. `CHR-6367`)
- Find every file in `rails-cakehr` that is relevant to the ticket
- Map the current logic flow (routes → controller → service → model)
- List exactly what needs to be added, modified, or deleted

### `jira`
Fetch any Jira ticket into your Copilot session on demand:
- `CHR-6367` → full ticket: summary, description, subtasks, recent comments
- Add `analyse` or `plan` to proceed into codebase exploration

### `pr-code-review`
Paste a GitHub PR URL and this agent will:
- Fetch the PR from GitHub and switch to that branch locally
- Read all changed files in the PR
- Perform a comprehensive architectural review covering: correctness, security, performance, testing, multi-tenancy, Rails conventions, and code quality
- Return a structured review with 🔴 blocking issues / 🟡 improvements / 🔵 suggestions
- Consult the project's instruction files to ensure alignment with team standards

---

## Using the Prompts (`/` commands)

Type `/` in Copilot Chat and start typing the prompt name. The prompt text appears in the chat input as **editable text** — review and customize before submitting.

Prompts marked **_(preview)_** are AI-generated starting points that haven't been reviewed, tested, or customised yet — use with caution and verify the output.

| Command | Use case |
|---|---|
| `/write-specs` | Write RSpec tests for current PR changes |
| `/suggestion-quality` | Critical review of current PR implementation |
| `/dev-pr-description` | Draft a PR description from your changes |
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
./scripts/jira-fetch.sh CHR-6367
```
You should see a formatted Markdown summary of the ticket printed to stdout.

**4. Use it in Copilot:**
- Switch to the **`jira`** agent and type `CHR-6367`
- Or switch to **`initial-analysis`** and type `CHR-6367` — it fetches then analyses automatically

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
