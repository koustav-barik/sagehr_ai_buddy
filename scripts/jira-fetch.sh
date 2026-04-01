#!/usr/bin/env bash
# jira-fetch.sh — Fetch Jira ticket details for Copilot context
#
# Usage:
#   ./scripts/jira-fetch.sh CHR-XXXX
#
# Requires credentials (set as env vars or in .env.jira at repo root):
#   JIRA_EMAIL         — Your Atlassian account email
#   JIRA_API_TOKEN     — Jira API token
#                        Generate at: https://id.atlassian.com/manage-profile/security/api-tokens
#   JIRA_BASE_URL      — Your Jira instance base URL (default: https://cakehr.atlassian.net)

set -euo pipefail

TICKET="${1:?Usage: ./scripts/jira-fetch.sh <TICKET-KEY>  e.g. CHR-XXXX}"

# ── Credentials ────────────────────────────────────────────────────────────────
# Resolve CWD-relative repo root (works when called from rails-cakehr directly)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Also resolve the REAL script location (follows symlinks via Python).
# When scripts/ is symlinked from rails-cakehr → sagehr_ai_buddy, this lets
# us find credentials stored in sagehr_ai_buddy without duplicating them.
REAL_SCRIPT="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
REAL_REPO_ROOT="$(cd "$(dirname "$REAL_SCRIPT")/.." && pwd)"

# Load credentials — search order: target repo first, then source repo
for env_file in "$REPO_ROOT/.env.jira" "$REPO_ROOT/.env" "$REAL_REPO_ROOT/.env.jira" "$REAL_REPO_ROOT/.env"; do
  if [ -f "$env_file" ]; then
    set -a
    # shellcheck source=/dev/null
    source "$env_file"
    set +a
  fi
done

: "${JIRA_EMAIL:?Set JIRA_EMAIL in .env or .env.jira}"
: "${JIRA_API_TOKEN:?Set JIRA_API_TOKEN in .env or .env.jira}"
JIRA_BASE_URL="${JIRA_BASE_URL:-https://cakehr.atlassian.net}"

# ── Fetch ───────────────────────────────────────────────────────────────────────
RESPONSE=$(curl -s \
  -u "${JIRA_EMAIL}:${JIRA_API_TOKEN}" \
  -H "Accept: application/json" \
  "${JIRA_BASE_URL}/rest/api/3/issue/${TICKET}?expand=renderedFields&fields=summary,description,status,assignee,priority,labels,components,reporter,issuetype,parent,subtasks,comment,fixVersions,created,updated") || {
  echo "Error: curl request failed — check JIRA_BASE_URL and your network connection." >&2
  exit 1
}

# ── Parse and Format ────────────────────────────────────────────────────────────
# Write the Python parser to a temp file so we can pipe $RESPONSE into it via
# stdin without conflicting with the heredoc that defines the script itself.
TMP_PY=$(mktemp /tmp/jira-parse.XXXXXX.py)
trap 'rm -f "$TMP_PY"' EXIT

cat > "$TMP_PY" <<'PYEOF'
import sys
import json
import html
import re

# ── helpers ──────────────────────────────────────────────────────────────────
def strip_html(text):
    if not text:
        return ""
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</?p[^>]*>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</?div[^>]*>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<li[^>]*>', '\n- ', text, flags=re.IGNORECASE)
    text = re.sub(r'</?[uo]l[^>]*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<h[1-6][^>]*>', '\n### ', text, flags=re.IGNORECASE)
    text = re.sub(r'</h[1-6]>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<code[^>]*>', '`', text, flags=re.IGNORECASE)
    text = re.sub(r'</code>', '`', text, flags=re.IGNORECASE)
    text = re.sub(r'<(?:strong|b)[^>]*>', '**', text, flags=re.IGNORECASE)
    text = re.sub(r'</(?:strong|b)>', '**', text, flags=re.IGNORECASE)
    text = re.sub(r'<em[^>]*>', '_', text, flags=re.IGNORECASE)
    text = re.sub(r'</em>', '_', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def adf_to_text(node, depth=0):
    if not node or not isinstance(node, dict):
        return ""
    ntype = node.get('type', '')
    out = []
    if ntype == 'text':
        marks = {m['type'] for m in node.get('marks', [])}
        t = node.get('text', '')
        if 'strong' in marks:
            t = f'**{t}**'
        if 'em' in marks:
            t = f'_{t}_'
        if 'code' in marks:
            t = f'`{t}`'
        out.append(t)
    elif ntype == 'hardBreak':
        out.append('\n')
    elif ntype in ('paragraph', 'heading'):
        content = node.get('content', [])
        text = ''.join(adf_to_text(c) for c in content)
        prefix = '#' * node.get('attrs', {}).get('level', 2) + ' ' if ntype == 'heading' else ''
        out.append(f"{prefix}{text}\n")
    elif ntype == 'listItem':
        content = node.get('content', [])
        text = ''.join(adf_to_text(c) for c in content).strip()
        out.append(f"{'  ' * depth}- {text}\n")
    elif ntype in ('bulletList', 'orderedList'):
        for item in node.get('content', []):
            out.append(adf_to_text(item, depth + 1))
    elif ntype == 'codeBlock':
        lang = node.get('attrs', {}).get('language', '')
        code = ''.join(c.get('text', '') for c in node.get('content', []) if c.get('type') == 'text')
        out.append(f"```{lang}\n{code}\n```\n")
    elif ntype == 'blockquote':
        text = ''.join(adf_to_text(c) for c in node.get('content', [])).strip()
        out.append('\n'.join(f'> {line}' for line in text.splitlines()) + '\n')
    elif ntype == 'rule':
        out.append('---\n')
    else:
        for child in node.get('content', []):
            out.append(adf_to_text(child, depth))
    return ''.join(out)

def render_description(fields, rendered):
    html_desc = rendered.get('description') or ''
    if html_desc:
        return strip_html(html_desc)
    adf_desc = fields.get('description')
    if adf_desc and isinstance(adf_desc, dict):
        return adf_to_text(adf_desc).strip()
    if isinstance(adf_desc, str):
        return adf_desc
    return ''

def render_comment_body(comment):
    rendered = comment.get('renderedBody') or ''
    if rendered:
        return strip_html(rendered)
    body = comment.get('body')
    if isinstance(body, dict):
        return adf_to_text(body).strip()
    if isinstance(body, str):
        return body
    return ''

# ── main ──────────────────────────────────────────────────────────────────────
raw = sys.stdin.read()
ticket_key = sys.argv[1]
base_url   = sys.argv[2]

try:
    data = json.loads(raw)
except json.JSONDecodeError:
    print(f"Error: Could not parse Jira response. Raw output:\n{raw}", file=sys.stderr)
    sys.exit(1)

if 'fields' not in data:
    errors = data.get('errorMessages', []) + list(data.get('errors', {}).values())
    print(f"Error fetching {ticket_key}: {'; '.join(errors) or raw}", file=sys.stderr)
    sys.exit(1)

fields   = data.get('fields', {})
rendered = data.get('renderedFields', {})

summary      = fields.get('summary', 'N/A')
status       = (fields.get('status') or {}).get('name', 'N/A')
issue_type   = (fields.get('issuetype') or {}).get('name', 'N/A')
priority     = (fields.get('priority') or {}).get('name', 'N/A')
assignee     = (fields.get('assignee') or {}).get('displayName', 'Unassigned')
reporter     = (fields.get('reporter') or {}).get('displayName', 'N/A')
labels       = ', '.join(fields.get('labels', [])) or 'None'
components   = ', '.join(c.get('name', '') for c in fields.get('components', [])) or 'None'
fix_versions = ', '.join(v.get('name', '') for v in fields.get('fixVersions', [])) or 'None'
created      = (fields.get('created') or '')[:10]
updated      = (fields.get('updated') or '')[:10]
parent       = fields.get('parent')
parent_str   = f"{parent['key']}: {parent['fields']['summary']}" if parent else 'None'

description  = render_description(fields, rendered)
subtasks     = fields.get('subtasks', [])
all_comments = (fields.get('comment') or {}).get('comments', [])

# ── Output ────────────────────────────────────────────────────────────────────
print(f"# Jira Ticket: {ticket_key}\n")
print(f"**Summary:** {summary}")
print(f"**Type:** {issue_type}")
print(f"**Status:** {status}")
print(f"**Priority:** {priority}")
print(f"**Assignee:** {assignee}")
print(f"**Reporter:** {reporter}")
print(f"**Labels:** {labels}")
print(f"**Components:** {components}")
print(f"**Fix Versions:** {fix_versions}")
print(f"**Parent:** {parent_str}")
print(f"**Created:** {created}  |  **Updated:** {updated}")
print(f"**Link:** {base_url}/browse/{ticket_key}")

print(f"\n## Description\n")
print(description if description else "_No description provided._")

if subtasks:
    print(f"\n## Subtasks\n")
    for st in subtasks:
        st_status = (st.get('fields', {}).get('status') or {}).get('name', '?')
        st_summary = st.get('fields', {}).get('summary', '')
        print(f"- [{st_status}] **{st['key']}**: {st_summary}")

recent = all_comments[-3:] if len(all_comments) > 3 else all_comments
if recent:
    print(f"\n## Recent Comments ({len(recent)} of {len(all_comments)} total)\n")
    for c in recent:
        author  = (c.get('author') or {}).get('displayName', 'Unknown')
        created = (c.get('created') or '')[:10]
        body    = render_comment_body(c)
        if len(body) > 600:
            body = body[:600] + '\n_[truncated]_'
        print(f"---\n**{author}** ({created}):\n{body}\n")
PYEOF

printf '%s' "$RESPONSE" | python3 "$TMP_PY" "$TICKET" "$JIRA_BASE_URL"
