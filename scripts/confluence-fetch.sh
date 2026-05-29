#!/usr/bin/env bash
# confluence-fetch.sh — Fetch Confluence page content for Copilot context
#
# Usage:
#   ./scripts/confluence-fetch.sh <PAGE_ID>               # fetch by numeric page ID
#   ./scripts/confluence-fetch.sh "<Page Title>" [SPACE]  # search by title (optional space key)
#
# Requires credentials (set as env vars or in .env.jira at repo root):
#   JIRA_EMAIL              — Your Atlassian account email
#   CONFLUENCE_API_TOKEN    — API token (falls back to JIRA_API_TOKEN if unset)
#                             Generate at: https://id.atlassian.com/manage-profile/security/api-tokens
#   CONFLUENCE_BASE_URL     — Confluence instance URL (falls back to JIRA_BASE_URL if unset)

set -euo pipefail

INPUT="${1:?Usage: ./scripts/confluence-fetch.sh <PAGE_ID|Page Title> [SPACE_KEY]}"
SPACE_KEY="${2:-}"

# ── Credentials ────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

REAL_SCRIPT="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
REAL_REPO_ROOT="$(cd "$(dirname "$REAL_SCRIPT")/.." && pwd)"

for env_file in "$REPO_ROOT/.env.jira" "$REPO_ROOT/.env" "$REAL_REPO_ROOT/.env.jira" "$REAL_REPO_ROOT/.env"; do
  if [ -f "$env_file" ]; then
    set -a
    # shellcheck source=/dev/null
    source "$env_file"
    set +a
  fi
done

: "${JIRA_EMAIL:?Set JIRA_EMAIL in .env or .env.jira}"

# Fall back to Jira token/URL if Confluence-specific vars are empty
CONFLUENCE_API_TOKEN="${CONFLUENCE_API_TOKEN:-${JIRA_API_TOKEN:-}}"
: "${CONFLUENCE_API_TOKEN:?Set CONFLUENCE_API_TOKEN (or JIRA_API_TOKEN) in .env or .env.jira}"

CONFLUENCE_BASE_URL="${CONFLUENCE_BASE_URL:-${JIRA_BASE_URL:-https://cakehr.atlassian.net}}"

WIKI_URL="${CONFLUENCE_BASE_URL}/wiki"

# ── Fetch ───────────────────────────────────────────────────────────────────────
# Determine whether INPUT is a numeric page ID or a title search
if [[ "$INPUT" =~ ^[0-9]+$ ]]; then
  # Numeric — fetch directly by page ID
  API_URL="${WIKI_URL}/rest/api/content/${INPUT}?expand=body.storage,version,space,ancestors,children.page"
  RESPONSE=$(curl -s \
    -u "${JIRA_EMAIL}:${CONFLUENCE_API_TOKEN}" \
    -H "Accept: application/json" \
    "$API_URL") || {
    echo "Error: curl request failed — check CONFLUENCE_BASE_URL and your network connection." >&2
    exit 1
  }
  MODE="single"
else
  # Title search
  ENCODED_TITLE=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$INPUT")
  SPACE_PARAM=""
  [ -n "$SPACE_KEY" ] && SPACE_PARAM="&spaceKey=${SPACE_KEY}"
  API_URL="${WIKI_URL}/rest/api/content?title=${ENCODED_TITLE}&type=page${SPACE_PARAM}&expand=body.storage,version,space,ancestors,children.page&limit=5"
  RESPONSE=$(curl -s \
    -u "${JIRA_EMAIL}:${CONFLUENCE_API_TOKEN}" \
    -H "Accept: application/json" \
    "$API_URL") || {
    echo "Error: curl request failed — check CONFLUENCE_BASE_URL and your network connection." >&2
    exit 1
  }
  MODE="search"
fi

# ── Parse and Format ────────────────────────────────────────────────────────────
TMP_PY=$(mktemp /tmp/confluence-parse.XXXXXX.py)
trap 'rm -f "$TMP_PY"' EXIT

cat > "$TMP_PY" <<'PYEOF'
import sys
import json
import html
import re

mode       = sys.argv[1]   # "single" or "search"
base_url   = sys.argv[2]
wiki_url   = base_url + "/wiki"
raw        = sys.stdin.read()

# ── helpers ───────────────────────────────────────────────────────────────────
def strip_storage(text):
    """Convert Confluence storage format (XML/HTML hybrid) to readable plain text."""
    if not text:
        return ""
    # Confluence structured macros — extract body or drop
    text = re.sub(r'<ac:structured-macro[^>]*ac:name="code"[^>]*>(.*?)</ac:structured-macro>',
                  lambda m: _extract_code_macro(m.group(0)), text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<ac:structured-macro[^>]*>(.*?)</ac:structured-macro>',
                  lambda m: _extract_macro_body(m.group(1)), text, flags=re.DOTALL | re.IGNORECASE)
    # Confluence inline elements
    text = re.sub(r'<ac:link[^>]*/>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<ac:link>(.*?)</ac:link>',
                  lambda m: _extract_link_text(m.group(1)), text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<ri:page[^>]*ri:content-title="([^"]*)"[^>]*/>', r'[\1]', text, flags=re.IGNORECASE)
    text = re.sub(r'<ac:plain-text-body[^>]*><!\[CDATA\[(.*?)\]\]></ac:plain-text-body>',
                  r'\1', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<ac:[^>]+>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'</ac:[^>]+>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<ri:[^>]+>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'</ri:[^>]+>', '', text, flags=re.IGNORECASE)
    # Standard HTML → Markdown-ish
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<hr\s*/?>', '\n---\n', text, flags=re.IGNORECASE)
    for lvl in range(6, 0, -1):
        text = re.sub(rf'<h{lvl}[^>]*>', '\n' + '#' * lvl + ' ', text, flags=re.IGNORECASE)
        text = re.sub(rf'</h{lvl}>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<(?:p|div)[^>]*>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</(?:p|div)>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<li[^>]*>', '\n- ', text, flags=re.IGNORECASE)
    text = re.sub(r'</li>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'</?[uo]l[^>]*>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<(?:strong|b)[^>]*>', '**', text, flags=re.IGNORECASE)
    text = re.sub(r'</(?:strong|b)>', '**', text, flags=re.IGNORECASE)
    text = re.sub(r'<(?:em|i)[^>]*>', '_', text, flags=re.IGNORECASE)
    text = re.sub(r'</(?:em|i)>', '_', text, flags=re.IGNORECASE)
    text = re.sub(r'<code[^>]*>', '`', text, flags=re.IGNORECASE)
    text = re.sub(r'</code>', '`', text, flags=re.IGNORECASE)
    text = re.sub(r'<pre[^>]*>', '\n```\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</pre>', '\n```\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r'[\2](\1)', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def _extract_code_macro(macro_html):
    lang_m = re.search(r'<ac:parameter ac:name="language">([^<]*)</ac:parameter>', macro_html, re.IGNORECASE)
    body_m = re.search(r'<ac:plain-text-body[^>]*><!\[CDATA\[(.*?)\]\]></ac:plain-text-body>', macro_html, re.DOTALL | re.IGNORECASE)
    lang = lang_m.group(1).strip() if lang_m else ''
    code = body_m.group(1) if body_m else ''
    return f"\n```{lang}\n{code}\n```\n"

def _extract_macro_body(inner_html):
    body_m = re.search(r'<ac:rich-text-body[^>]*>(.*?)</ac:rich-text-body>', inner_html, re.DOTALL | re.IGNORECASE)
    return body_m.group(1) if body_m else ''

def _extract_link_text(inner_html):
    alias_m = re.search(r'<ac:link-body>(.*?)</ac:link-body>', inner_html, re.DOTALL | re.IGNORECASE)
    page_m  = re.search(r'ri:content-title="([^"]*)"', inner_html, re.IGNORECASE)
    if alias_m:
        return alias_m.group(1)
    if page_m:
        return f"[{page_m.group(1)}]"
    return ''

def format_page(page, wiki_url, truncate_body=False):
    page_id    = page.get('id', 'N/A')
    title      = page.get('title', 'Untitled')
    space      = (page.get('space') or {})
    space_name = space.get('name', 'N/A')
    space_key  = space.get('key', 'N/A')
    version    = (page.get('version') or {})
    ver_num    = version.get('number', 'N/A')
    ver_by     = (version.get('by') or {}).get('displayName', 'N/A')
    ver_when   = (version.get('when') or '')[:10]
    ancestors  = page.get('ancestors', [])
    children   = (page.get('children') or {}).get('page', {}).get('results', [])
    body_raw   = (page.get('body') or {}).get('storage', {}).get('value', '')
    body_text  = strip_storage(body_raw)
    web_link   = wiki_url + (page.get('_links') or {}).get('webui', f'/pages/{page_id}')

    lines = []
    lines.append(f"# Confluence Page: {title}\n")
    lines.append(f"**Page ID:** {page_id}")
    lines.append(f"**Space:** {space_name} (`{space_key}`)")
    lines.append(f"**Version:** {ver_num}  |  **Last edited by:** {ver_by}  |  **Date:** {ver_when}")
    lines.append(f"**Link:** {web_link}")

    if ancestors:
        breadcrumb = ' > '.join(a.get('title', '') for a in ancestors) + f' > {title}'
        lines.append(f"**Breadcrumb:** {breadcrumb}")

    if children:
        lines.append(f"\n## Child Pages ({len(children)})\n")
        for child in children[:10]:
            child_link = wiki_url + (child.get('_links') or {}).get('webui', '')
            lines.append(f"- [{child['title']}]({child_link})  (ID: {child['id']})")
        if len(children) > 10:
            lines.append(f"_... and {len(children) - 10} more_")

    lines.append(f"\n## Content\n")
    if truncate_body and len(body_text) > 1500:
        lines.append(body_text[:1500] + '\n\n_[content truncated — fetch by page ID for full content]_')
    else:
        lines.append(body_text if body_text else '_No content._')

    return '\n'.join(lines)

# ── main ───────────────────────────────────────────────────────────────────────
try:
    data = json.loads(raw)
except json.JSONDecodeError:
    print(f"Error: Could not parse Confluence response. Raw output:\n{raw}", file=sys.stderr)
    sys.exit(1)

if mode == "single":
    if 'id' not in data:
        msg = data.get('message') or data.get('reason') or raw[:300]
        print(f"Error fetching page: {msg}", file=sys.stderr)
        sys.exit(1)
    print(format_page(data, wiki_url))

elif mode == "search":
    results = data.get('results', [])
    total   = data.get('size', 0)

    if total == 0:
        print("No pages found matching your search.", file=sys.stderr)
        sys.exit(1)

    if total == 1:
        # Single match — show full page
        print(format_page(results[0], wiki_url))
    else:
        print(f"# Confluence Search Results\n")
        print(f"Found **{total}** matching page(s). Showing up to 5:\n")
        for page in results:
            page_id   = page.get('id', 'N/A')
            title     = page.get('title', 'Untitled')
            space     = (page.get('space') or {})
            space_key = space.get('key', '')
            web_link  = wiki_url + (page.get('_links') or {}).get('webui', f'/pages/{page_id}')
            print(f"- **{title}** (ID: `{page_id}`, Space: `{space_key}`)  →  {web_link}")
        print(f"\n_Re-run with the page ID for full content, e.g.:_")
        print(f"`./scripts/confluence-fetch.sh {results[0]['id']}`")
PYEOF

printf '%s' "$RESPONSE" | python3 "$TMP_PY" "$MODE" "$CONFLUENCE_BASE_URL"
