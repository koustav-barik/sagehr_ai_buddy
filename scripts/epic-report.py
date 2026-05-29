#!/usr/bin/env python3
"""
scripts/epic-report.py  —  Jira-hierarchy report for build-yellow-copilot

Groups every branch and PR in build-yellow-copilot by its Jira hierarchy:
  Initiative → Epic → Story/Task → Branches & PRs

Also detects standalone "cherry-pick" branches/PRs that consolidate an entire
epic into a single PR targeting master, so you can see what's already been
consolidated and what still needs to be.

Usage:
    python3 scripts/epic-report.py [OPTIONS]

Options:
    --initiatives KEY[,KEY…]   Root initiative keys (comma-separated).
                               Default: auto-discovered from existing CSV.
    --csv-path PATH            Branch CSV produced by branch-report.py.
                               Default: .github/reports/build-yellow-copilot-branches.csv
    --output-dir DIR           Directory for output files.
                               Default: .github/reports
    --no-gh                    Skip GitHub PR lookups (cherry-pick detection skipped).

Requires:
    .env.jira at repo root  (JIRA_EMAIL, JIRA_API_TOKEN, JIRA_BASE_URL)
    gh CLI authenticated    (to detect cherry-pick PRs; skip with --no-gh)
"""

import argparse
import base64
import csv
import json
import os
import re
import subprocess
import sys
import urllib.request
import urllib.error
import urllib.parse
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# Paths  (abspath avoids symlink mis-navigation: scripts/ may be symlinked)
# ─────────────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(os.path.abspath(__file__)).parent
REPO_ROOT  = SCRIPT_DIR.parent

GITHUB_REPO  = "Sage/rails-cakehr"
JIRA_BROWSE  = "https://cakehr.atlassian.net/browse"
GITHUB_PR    = f"https://github.com/{GITHUB_REPO}/pull"

DEFAULT_CSV    = REPO_ROOT / ".github/reports/build-yellow-copilot-branches.csv"
DEFAULT_OUTPUT = REPO_ROOT / ".github/reports"

# Issue types that mark the root of a trackable sub-tree
INITIATIVE_TYPES = {"Initiative", "Feature", "Program"}
EPIC_TYPES       = {"Epic"}
STORY_TYPES      = {"Story", "Task", "Bug", "Improvement", "Sub-task", "Subtask"}

CHR_RE = re.compile(r"\bCHR-\d+\b", re.IGNORECASE)


# ─────────────────────────────────────────────────────────────────────────────
# Credentials
# ─────────────────────────────────────────────────────────────────────────────

def load_credentials() -> tuple:
    for env_file in [REPO_ROOT / ".env.jira", REPO_ROOT / ".env"]:
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())
    email    = os.environ.get("JIRA_EMAIL", "")
    token    = os.environ.get("JIRA_API_TOKEN", "")
    base_url = os.environ.get("JIRA_BASE_URL", "https://cakehr.atlassian.net")
    if not email or not token:
        print("ERROR: JIRA_EMAIL and JIRA_API_TOKEN must be set.", file=sys.stderr)
        sys.exit(1)
    return email, token, base_url


# ─────────────────────────────────────────────────────────────────────────────
# Jira API helpers
# ─────────────────────────────────────────────────────────────────────────────

_jira_cache: dict = {}


def _jira_get_url(url: str, email: str, token: str):
    if url in _jira_cache:
        return _jira_cache[url]
    creds = base64.b64encode(f"{email}:{token}".encode()).decode()
    req   = urllib.request.Request(url, headers={
        "Authorization": f"Basic {creds}",
        "Accept":        "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            _jira_cache[url] = data
            return data
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            _jira_cache[url] = None
            return None
        print(f"  WARN Jira HTTP {exc.code} for {url}", file=sys.stderr)
        _jira_cache[url] = None
        return None
    except Exception as exc:
        print(f"  WARN Jira {exc} for {url}", file=sys.stderr)
        _jira_cache[url] = None
        return None


def fetch_issue(key: str, email: str, token: str, base_url: str) -> dict | None:
    fields = "summary,status,issuetype,parent,subtasks,customfield_10014,priority"
    url    = f"{base_url}/rest/api/3/issue/{key}?fields={fields}"
    return _jira_get_url(url, email, token)


def fetch_epic_stories_agile(
    epic_key: str,
    email: str,
    token: str,
    base_url: str,
    start: int = 0,
) -> list:
    """
    Fetch all Jira issues belonging to an epic using the Agile API.
    Works where the JQL `parent = EPIC_KEY` returns 410 (classic projects).
    Endpoint: GET /rest/agile/1.0/epic/{epicKey}/issue
    """
    url = (
        f"{base_url}/rest/agile/1.0/epic/{epic_key}/issue"
        f"?fields=summary,status,issuetype,parent,subtasks,customfield_10014"
        f"&maxResults=100&startAt={start}"
    )
    data = _jira_get_url(url, email, token)
    if not data:
        return []
    issues = data.get("issues", [])
    total  = data.get("total", 0)
    if start + len(issues) < total:
        issues += fetch_epic_stories_agile(epic_key, email, token, base_url,
                                           start + len(issues))
    return issues


def _extract_fields(issue: dict) -> dict:
    f = issue.get("fields", {}) or {}
    return {
        "key":     issue.get("key", "?"),
        "summary": f.get("summary", "N/A"),
        "status":  (f.get("status")   or {}).get("name", "N/A"),
        "type":    (f.get("issuetype") or {}).get("name", "Unknown"),
    }


def build_initiative_tree(
    init_key: str,
    epic_keys: list,
    email: str,
    token: str,
    base_url: str,
) -> dict | None:
    """
    Build the Jira hierarchy for one initiative.

    Strategy (JQL search is disabled for this Jira instance):
      - Initiative level: fetch the issue directly.
      - Epic level:       fetch each epic directly using known keys from the CSV.
      - Story level:      use the Jira Agile API endpoint
                          GET /rest/agile/1.0/epic/{epicKey}/issue
      - Sub-task level:   read the `subtasks` field on the story issue.
    """
    print(f"  Fetching initiative {init_key}…", flush=True)
    init_issue = fetch_issue(init_key, email, token, base_url)
    if not init_issue:
        return None

    node = {**_extract_fields(init_issue), "depth": 0, "children": []}

    for epic_key in epic_keys:
        print(f"    Fetching epic {epic_key}…", flush=True)
        epic_issue = fetch_issue(epic_key, email, token, base_url)
        if not epic_issue:
            continue
        epic_node = {**_extract_fields(epic_issue), "depth": 1, "children": []}

        # Fetch all stories for this epic via Agile API
        story_issues = fetch_epic_stories_agile(epic_key, email, token, base_url)
        print(f"      {len(story_issues)} stories found.", flush=True)

        for story_issue in story_issues:
            s_fields = story_issue.get("fields", {}) or {}
            story_node = {
                "key":      story_issue["key"],
                "summary":  s_fields.get("summary", "N/A"),
                "status":   (s_fields.get("status")   or {}).get("name", "N/A"),
                "type":     (s_fields.get("issuetype") or {}).get("name", "Story"),
                "depth":    2,
                "children": [],
            }
            # Sub-tasks are listed in the `subtasks` field of the story
            for sub in (s_fields.get("subtasks") or []):
                sub_f = sub.get("fields", {}) or {}
                story_node["children"].append({
                    "key":      sub["key"],
                    "summary":  sub_f.get("summary", "N/A"),
                    "status":   (sub_f.get("status")   or {}).get("name", "N/A"),
                    "type":     (sub_f.get("issuetype") or {}).get("name", "Sub-task"),
                    "depth":    3,
                    "children": [],
                })
            epic_node["children"].append(story_node)

        node["children"].append(epic_node)

    return node


def collect_all_keys(node: dict, result: set | None = None) -> set:
    """Recursively collect all Jira keys in a tree."""
    if result is None:
        result = set()
    result.add(node["key"])
    for child in node.get("children", []):
        collect_all_keys(child, result)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Branch CSV helpers
# ─────────────────────────────────────────────────────────────────────────────

def load_branch_csv(csv_path: Path) -> list:
    if not csv_path.exists():
        print(f"WARNING: CSV not found at {csv_path}", file=sys.stderr)
        print("  Run `python3 scripts/branch-report.py` first.", file=sys.stderr)
        return []
    with open(csv_path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def build_ticket_branch_map(rows: list) -> dict:
    """
    Returns: { "CHR-XXXXX": [row, row, …] }

    Each branch row is associated with every CHR ticket found in:
      - primary_ticket column
      - related_pr_tickets column
      - branch name itself
    """
    mapping: dict = defaultdict(list)
    for row in rows:
        branch = row.get("branch_name", "")
        if branch == "build-yellow-copilot":
            continue

        tickets: set = set()
        for src in (
            row.get("primary_ticket", ""),
            row.get("related_pr_tickets", ""),
            branch,
        ):
            for t in CHR_RE.findall(src or ""):
                tickets.add(t.upper())

        for ticket in tickets:
            # Avoid double-adding the same row for the same ticket
            if not any(r is row for r in mapping[ticket]):
                mapping[ticket].append(row)

    return mapping


# ─────────────────────────────────────────────────────────────────────────────
# GitHub cherry-pick PR detection
# ─────────────────────────────────────────────────────────────────────────────

def gh_available() -> bool:
    return subprocess.run(["which", "gh"], capture_output=True).returncode == 0


def fetch_master_prs() -> list:
    """Fetch all PRs (open + closed) that target master for this repo."""
    r = subprocess.run(
        [
            "gh", "pr", "list",
            "--repo",  GITHUB_REPO,
            "--base",  "master",
            "--state", "all",
            "--json",  "number,title,headRefName,state,mergedAt,body",
            "--limit", "300",
        ],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    if r.returncode != 0:
        return []
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return []


def build_cherry_pick_map(master_prs: list) -> dict:
    """
    Returns: { "CHR-XXXXX": [pr_dict, …] }

    A "cherry-pick PR" is any PR targeting master whose branch name or body
    contains a CHR ticket key that appears in an epic or higher (i.e. is
    being consolidated).  We index by every CHR key mentioned in that PR.
    """
    mapping: dict = defaultdict(list)
    for pr in master_prs:
        head    = pr.get("headRefName", "")
        body    = pr.get("body", "") or ""
        title   = pr.get("title", "") or ""
        tickets = set()
        for src in (head, title, body[:3000]):
            for t in CHR_RE.findall(src):
                tickets.add(t.upper())

        entry = {
            "number":    pr["number"],
            "state":     pr["state"],
            "merged_at": (pr.get("mergedAt") or "")[:10],
            "head":      head,
            "title":     title,
            "tickets":   sorted(tickets),
        }
        for t in tickets:
            if not any(e["number"] == entry["number"] for e in mapping[t]):
                mapping[t].append(entry)

    return mapping


# ─────────────────────────────────────────────────────────────────────────────
# Markdown helpers
# ─────────────────────────────────────────────────────────────────────────────

PR_STATE_LABELS = {
    "MERGED": "**MERGED**",
    "OPEN":   "**OPEN**",
    "CLOSED": "CLOSED",
}


def _safe(text: str, max_len: int = 65) -> str:
    return (text or "N/A").replace("|", "\\|")[:max_len]


def _jira_link(key: str) -> str:
    return f"[{key}]({JIRA_BROWSE}/{key})"


def _pr_link(number) -> str:
    if not number:
        return "—"
    return f"[#{number}]({GITHUB_PR}/{number})"


def _branch_display(branch: str) -> str:
    return f"`{branch}`"


def _pr_state_label(state: str) -> str:
    return PR_STATE_LABELS.get((state or "").upper(), state or "—")


def format_branch_rows(
    rows: list,
    ticket_key: str,
    cherry_map: dict,
) -> list[str]:
    """
    Return table rows (strings) for a single ticket's branches.
    One row per branch.  If no branches, returns a single placeholder row.
    """
    if not rows:
        return [
            f"| {_jira_link(ticket_key)} | — | — | — | — | — | — |"
        ]
    result = []
    for row in rows:
        branch    = row.get("branch_name", "?")
        pr_num    = row.get("pr_number", "")
        pr_state  = row.get("pr_state", "") or "—"
        pr_merge  = row.get("pr_merged_at", "") or ""
        parent    = row.get("parent_branch", "?")
        depth_val = row.get("depth", "?")
        remote    = "✓" if row.get("remote_exists") == "Y" else "✗"
        t_status  = row.get("ticket_status", "N/A")
        t_summary = _safe(row.get("ticket_summary", "N/A"))

        pr_cell = "—"
        if pr_num:
            state_label = _pr_state_label(pr_state)
            date_part   = f" {pr_merge}" if pr_state == "MERGED" and pr_merge else ""
            pr_cell     = f"{_pr_link(pr_num)} {state_label}{date_part}"

        # Cherry-pick PR for this ticket (if any)
        cp_entries = cherry_map.get(ticket_key.upper(), [])
        cp_cell = "—"
        if cp_entries:
            cp_parts = []
            for cp in cp_entries[:3]:
                sl = _pr_state_label(cp["state"])
                dt = f" {cp['merged_at']}" if cp["state"] == "MERGED" and cp["merged_at"] else ""
                cp_parts.append(f"{_pr_link(cp['number'])} {sl}{dt}")
            cp_cell = " · ".join(cp_parts)

        result.append(
            f"| {_jira_link(ticket_key)} "
            f"| {t_summary} "
            f"| {t_status} "
            f"| {_branch_display(branch)} "
            f"| {pr_cell} "
            f"| `{parent}` (d{depth_val}) {remote} "
            f"| {cp_cell} |"
        )
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Epic-level stats helpers
# ─────────────────────────────────────────────────────────────────────────────

def epic_stats(epic_node: dict, ticket_branch_map: dict, cherry_map: dict) -> dict:
    """
    Return summary stats for an epic node and all its descendants.
    """
    all_keys    = collect_all_keys(epic_node) - {epic_node["key"]}
    child_count = len(epic_node.get("children", []))
    branch_rows: list = []
    for k in all_keys:
        branch_rows += ticket_branch_map.get(k, [])

    # Deduplicate by branch_name
    unique: dict = {}
    for r in branch_rows:
        unique.setdefault(r["branch_name"], r)
    deduped = list(unique.values())

    merged  = sum(1 for r in deduped if r.get("pr_state") == "MERGED")
    open_   = sum(1 for r in deduped if r.get("pr_state") == "OPEN")
    closed  = sum(1 for r in deduped if r.get("pr_state") == "CLOSED")
    no_pr   = sum(1 for r in deduped if not r.get("pr_number"))

    # Cherry-pick PRs for this epic
    cp_entries = cherry_map.get(epic_node["key"].upper(), [])

    return {
        "ticket_count":  len(all_keys),
        "child_count":   child_count,
        "branch_count":  len(deduped),
        "merged":        merged,
        "open":          open_,
        "closed":        closed,
        "no_pr":         no_pr,
        "cherry_prs":    cp_entries,
    }


def render_epic_summary_row(
    epic_node: dict,
    stats: dict,
) -> str:
    key     = epic_node["key"]
    summary = _safe(epic_node["summary"], 60)
    status  = epic_node["status"]
    bc      = stats["branch_count"]
    merged  = stats["merged"]
    open_   = stats["open"]

    cp_cell = "—"
    if stats["cherry_prs"]:
        parts = []
        for cp in stats["cherry_prs"][:2]:
            sl = _pr_state_label(cp["state"])
            dt = f" {cp['merged_at']}" if cp["state"] == "MERGED" and cp["merged_at"] else ""
            parts.append(f"{_pr_link(cp['number'])} {sl}{dt}")
        cp_cell = " · ".join(parts)

    return (
        f"| {_jira_link(key)} "
        f"| {summary} "
        f"| {status} "
        f"| {stats['ticket_count']} "
        f"| {bc} ({merged}✅ {open_}🔵) "
        f"| {cp_cell} |"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Recursive renderer
# ─────────────────────────────────────────────────────────────────────────────

STORY_TABLE_HEADER = (
    "| Ticket | Summary | Ticket Status "
    "| Branch | PR in build-yellow-copilot "
    "| Parent Branch (depth) "
    "| Cherry-pick PR → master |"
)
STORY_TABLE_SEP = (
    "|--------|---------|--------------|"
    "--------|--------------------------|"
    "----------------------|------------------------|"
)


def render_initiative(
    node: dict,
    ticket_branch_map: dict,
    cherry_map: dict,
    lines: list,
    used_branch_names: set,
):
    key     = node["key"]
    summary = node["summary"]
    status  = node["status"]
    epics   = node.get("children", [])

    lines += [
        f"## {_jira_link(key)} — {summary}",
        "",
        f"> **Status**: {status}",
        "",
    ]

    if not epics:
        lines += ["_No epics found under this initiative._", "", "---", ""]
        return

    # ── Epics overview table ──────────────────────────────────────────────────
    lines += [
        "### Epics Overview",
        "",
        "| Epic | Summary | Epic Status | Stories/Tasks | Branches (merged/open) | Cherry-pick PR → master |",
        "|------|---------|-------------|---------------|------------------------|-------------------------|",
    ]
    all_epic_stats: dict = {}
    for epic in epics:
        stats = epic_stats(epic, ticket_branch_map, cherry_map)
        all_epic_stats[epic["key"]] = stats
        lines.append(render_epic_summary_row(epic, stats))
    lines += ["", "---", ""]

    # ── Per-epic detail sections ──────────────────────────────────────────────
    for epic in epics:
        render_epic(
            epic,
            all_epic_stats[epic["key"]],
            ticket_branch_map,
            cherry_map,
            lines,
            used_branch_names,
        )


def render_epic(
    node: dict,
    stats: dict,
    ticket_branch_map: dict,
    cherry_map: dict,
    lines: list,
    used_branch_names: set,
):
    key     = node["key"]
    summary = node["summary"]
    status  = node["status"]
    stories = node.get("children", [])

    cherry_note = ""
    if stats["cherry_prs"]:
        parts = []
        for cp in stats["cherry_prs"]:
            sl = _pr_state_label(cp["state"])
            dt = f" · {cp['merged_at']}" if cp["state"] == "MERGED" and cp["merged_at"] else ""
            parts.append(
                f"{_pr_link(cp['number'])} ({sl}{dt}) — `{cp['head']}`"
            )
        cherry_note = "\n> **Cherry-pick PR(s)**: " + " · ".join(parts) + "\n>"
    else:
        cherry_note = "\n> _No cherry-pick PR detected yet for this epic._\n>"

    lines += [
        f"### {_jira_link(key)} — {summary}",
        "",
        f"> **Epic Status**: {status} "
        f"· {stats['ticket_count']} tickets "
        f"· {stats['branch_count']} branches "
        f"({stats['merged']} merged, {stats['open']} open, "
        f"{stats['closed']} closed, {stats['no_pr']} no PR)",
        cherry_note,
        "",
    ]

    if not stories:
        # No child stories — check if the epic itself has branches
        epic_branches = ticket_branch_map.get(key, [])
        if epic_branches:
            lines += [
                "_No child stories — branches linked directly to this epic:_",
                "",
                STORY_TABLE_HEADER,
                STORY_TABLE_SEP,
            ]
            for row in epic_branches:
                lines += format_branch_rows([row], key, cherry_map)
                used_branch_names.add(row["branch_name"])
            lines += ["", "---", ""]
        else:
            lines += ["_No stories and no branches found for this epic._", "", "---", ""]
        return

    # ── Story table ───────────────────────────────────────────────────────────
    lines += [STORY_TABLE_HEADER, STORY_TABLE_SEP]

    for story in stories:
        story_key  = story["key"]
        s_summary  = _safe(story["summary"], 60)
        s_status   = story["status"]
        s_branches = ticket_branch_map.get(story_key, [])

        if s_branches:
            rows_output = format_branch_rows(s_branches, story_key, cherry_map)
            lines += rows_output
            for r in s_branches:
                used_branch_names.add(r["branch_name"])
        else:
            # Ticket has no branch — still show it so there are no gaps
            cp_entries = cherry_map.get(story_key, [])
            cp_cell = "—"
            if cp_entries:
                cp_parts = [
                    f"{_pr_link(cp['number'])} {_pr_state_label(cp['state'])}"
                    for cp in cp_entries[:2]
                ]
                cp_cell = " · ".join(cp_parts)
            lines.append(
                f"| {_jira_link(story_key)} "
                f"| {s_summary} "
                f"| {s_status} "
                f"| _no branch_ "
                f"| — "
                f"| — "
                f"| {cp_cell} |"
            )

        # Render sub-tasks if any
        sub_tasks = story.get("children", [])
        for sub in sub_tasks:
            sub_key      = sub["key"]
            sub_summary  = _safe(sub["summary"], 55)
            sub_status   = sub["status"]
            sub_branches = ticket_branch_map.get(sub_key, [])
            if sub_branches:
                for row in sub_branches:
                    branch    = row.get("branch_name", "?")
                    pr_num    = row.get("pr_number", "")
                    pr_state  = row.get("pr_state", "") or "—"
                    pr_merge  = row.get("pr_merged_at", "") or ""
                    parent    = row.get("parent_branch", "?")
                    depth_val = row.get("depth", "?")
                    remote    = "✓" if row.get("remote_exists") == "Y" else "✗"

                    pr_cell = "—"
                    if pr_num:
                        sl      = _pr_state_label(pr_state)
                        dt      = f" {pr_merge}" if pr_state == "MERGED" and pr_merge else ""
                        pr_cell = f"{_pr_link(pr_num)} {sl}{dt}"

                    lines.append(
                        f"| ↳ {_jira_link(sub_key)} "
                        f"| _{sub_summary}_ "
                        f"| {sub_status} "
                        f"| {_branch_display(branch)} "
                        f"| {pr_cell} "
                        f"| `{parent}` (d{depth_val}) {remote} "
                        f"| — |"
                    )
                    used_branch_names.add(row["branch_name"])
            else:
                lines.append(
                    f"| ↳ {_jira_link(sub_key)} "
                    f"| _{sub_summary}_ "
                    f"| {sub_status} "
                    f"| _no branch_ | — | — | — |"
                )

    lines += ["", "---", ""]


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--initiatives", default="",
        help="Comma-separated initiative keys, e.g. CHR-21354,CHR-22311. "
             "Default: auto-discover from CSV.",
    )
    parser.add_argument("--csv-path",   default=str(DEFAULT_CSV))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    parser.add_argument(
        "--no-gh", action="store_true",
        help="Skip GitHub cherry-pick PR detection.",
    )
    args = parser.parse_args()

    email, token, base_url = load_credentials()
    csv_path   = Path(args.csv_path)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Load branch data ──────────────────────────────────────────────────────
    print("Loading branch CSV…", flush=True)
    rows = load_branch_csv(csv_path)
    print(f"  {len(rows)} branch rows loaded.", flush=True)

    ticket_branch_map = build_ticket_branch_map(rows)
    print(f"  {len(ticket_branch_map)} unique ticket-to-branch associations.", flush=True)

    # ── Detect cherry-pick PRs ────────────────────────────────────────────────
    cherry_map: dict = defaultdict(list)
    if not args.no_gh and gh_available():
        print("Fetching PRs targeting master (cherry-pick detection)…", flush=True)
        master_prs = fetch_master_prs()
        print(f"  {len(master_prs)} PRs found.", flush=True)
        cherry_map = build_cherry_pick_map(master_prs)
        print(f"  {len(cherry_map)} ticket keys with cherry-pick PR associations.", flush=True)
    else:
        if not args.no_gh:
            print("WARNING: gh CLI not found. Cherry-pick detection skipped.", file=sys.stderr)

    # ── Determine initiative keys ─────────────────────────────────────────────
    if args.initiatives.strip():
        init_keys = [k.strip().upper() for k in args.initiatives.split(",") if k.strip()]
    else:
        # Auto-discover from CSV — deduplicate preserving order.
        # Exclude keys that appear as an epic_key where that row ALSO has a
        # valid (non-N/A) initiative_key, which means they sit below an initiative
        # and are truly epics themselves.
        true_epic_keys: set = {
            row.get("epic_key", "").upper()
            for row in rows
            if (
                row.get("epic_key", "") not in ("N/A", "Multiple", "")
                and row.get("initiative_key", "") not in ("N/A", "Multiple", "")
            )
        }
        seen: set = set()
        init_keys = []
        for row in rows:
            ik = row.get("initiative_key", "")
            if (
                ik
                and ik not in ("N/A", "Multiple")
                and ik.upper() not in seen
                and ik.upper() not in true_epic_keys
            ):
                init_keys.append(ik.upper())
                seen.add(ik.upper())
        print(f"Auto-discovered initiatives: {init_keys}", flush=True)

    if not init_keys:
        print(
            "ERROR: No initiative keys found. "
            "Run branch-report.py first or pass --initiatives.",
            file=sys.stderr,
        )
        sys.exit(1)

    # ── Build initiative → epic mapping from CSV ──────────────────────────────
    # For each initiative, collect all unique epic keys from the branch CSV.
    # (The Jira JQL search API returns 410 for this instance, so we derive
    #  the epic list from the data already collected by branch-report.py.)
    init_to_epics: dict = defaultdict(list)
    seen_epic: dict     = {}  # epic_key -> initiative_key (first seen wins)
    for row in rows:
        ik = row.get("initiative_key", "")
        ek = row.get("epic_key", "")
        if ik in init_keys and ek and ek not in ("N/A", "Multiple"):
            if ek not in seen_epic:
                seen_epic[ek] = ik
                init_to_epics[ik].append(ek)

    # Allow --initiatives to include epics not in the CSV
    # (e.g., when specifying a single epic key like CHR-22318 directly)
    for ik in init_keys:
        if ik not in init_to_epics:
            # It might itself be an epic — add it as its own "epic" group
            init_to_epics[ik] = [ik]

    # ── Build Jira trees ──────────────────────────────────────────────────────
    print("Building Jira hierarchy…", flush=True)
    trees: list = []
    for ik in init_keys:
        epic_keys = init_to_epics.get(ik, [])
        print(f"  Initiative {ik}: {len(epic_keys)} epic(s) from CSV…", flush=True)
        tree = build_initiative_tree(ik, epic_keys, email, token, base_url)
        if tree:
            trees.append(tree)
        else:
            print(f"  WARNING: Could not fetch {ik}.", file=sys.stderr)

    # ── Generate report ───────────────────────────────────────────────────────
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines: list = [
        "# Initiative Report — build-yellow-copilot",
        "",
        f"_Generated: {now}_",
        "",
        (
            "Grouped by Jira hierarchy: **Initiative → Epic → Story/Task → Branch/PR**. "
            "Use this report to identify which branches to cherry-pick per epic and "
            "track consolidation progress."
        ),
        "",
        "## How to read this report",
        "",
        "- Each **Initiative** has an _Epics Overview_ summary table "
        "followed by a per-epic detail section.",
        "- **Branch columns**: `d1` = depth 1 (direct child of `build-yellow-copilot`), "
        "`d2` = grandchild, etc.",
        "- **Cherry-pick PR → master**: an existing PR that consolidates this epic "
        "into a standalone branch targeting `master`.",
        "- Rows with `_no branch_` are Jira tickets that exist but have no matching "
        "branch in `build-yellow-copilot` yet.",
        "",
        "### PR State Key",
        "",
        "| Symbol | Meaning |",
        "|--------|---------|",
        "| **MERGED** | PR was merged |",
        "| **OPEN** | PR is open / awaiting review |",
        "| CLOSED | PR was closed without merging |",
        "| ✓ | Remote branch still exists |",
        "| ✗ | Branch merged/deleted |",
        "",
        "---",
        "",
    ]

    # ── Summary table across all initiatives ─────────────────────────────────
    lines += [
        "## Summary",
        "",
        "| Initiative | Summary | Epics | Total Branches | Merged | Open | Cherry-pick PRs |",
        "|------------|---------|-------|----------------|--------|------|-----------------|",
    ]
    for tree in trees:
        all_keys = collect_all_keys(tree) - {tree["key"]}
        epics    = [c for c in tree.get("children", [])]
        b_rows   = [r for k in all_keys for r in ticket_branch_map.get(k, [])]
        unique_b = {r["branch_name"]: r for r in b_rows}
        merged   = sum(1 for r in unique_b.values() if r.get("pr_state") == "MERGED")
        open_    = sum(1 for r in unique_b.values() if r.get("pr_state") == "OPEN")
        cp_keys  = set()
        for k in all_keys:
            for cp in cherry_map.get(k, []):
                cp_keys.add(cp["number"])
        lines.append(
            f"| {_jira_link(tree['key'])} "
            f"| {_safe(tree['summary'], 55)} "
            f"| {len(epics)} "
            f"| {len(unique_b)} "
            f"| {merged} "
            f"| {open_} "
            f"| {len(cp_keys)} |"
        )
    lines += ["", "---", ""]

    # ── Per-initiative detail ─────────────────────────────────────────────────
    used_branch_names: set = set()
    for tree in trees:
        render_initiative(tree, ticket_branch_map, cherry_map, lines, used_branch_names)
        lines += ["", ""]

    # ── Orphaned branches ─────────────────────────────────────────────────────
    # Collect all ticket keys covered by any tree
    all_tree_keys: set = set()
    for tree in trees:
        collect_all_keys(tree, all_tree_keys)

    orphaned = []
    for row in rows:
        branch = row.get("branch_name", "")
        if branch in used_branch_names or branch == "build-yellow-copilot":
            continue
        # Check if any of this branch's tickets are covered in the trees
        branch_tickets: set = set()
        for src in (
            row.get("primary_ticket", ""),
            row.get("related_pr_tickets", ""),
            branch,
        ):
            for t in CHR_RE.findall(src or ""):
                branch_tickets.add(t.upper())

        if not branch_tickets.intersection(all_tree_keys):
            orphaned.append(row)

    if orphaned:
        lines += [
            "## Branches Outside Reported Initiatives",
            "",
            "_Branches in `build-yellow-copilot` whose tickets do not appear in "
            "any of the reported initiatives above. "
            "They may belong to unreported initiatives or have no Jira ticket._",
            "",
            "| Branch | PR | PR State | Ticket | Epic | Initiative | Parent Branch |",
            "|--------|-----|----------|--------|------|------------|----------------|",
        ]
        for row in sorted(orphaned, key=lambda r: r.get("branch_name", "")):
            branch   = row.get("branch_name", "?")
            pr_num   = row.get("pr_number", "")
            pr_state = row.get("pr_state", "—") or "—"
            ticket   = row.get("primary_ticket", "N/A")
            epic     = row.get("epic_key", "N/A")
            init_key = row.get("initiative_key", "N/A")
            parent   = row.get("parent_branch", "?")
            lines.append(
                f"| `{branch}` "
                f"| {_pr_link(pr_num)} "
                f"| {_pr_state_label(pr_state)} "
                f"| {ticket} "
                f"| {epic} "
                f"| {init_key} "
                f"| `{parent}` |"
            )
        lines += [""]

    # ── Write output ──────────────────────────────────────────────────────────
    out_path = output_dir / "build-yellow-copilot-initiative-report.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"\nReport written → {out_path}", flush=True)
    print(f"Initiatives reported: {len(trees)}", flush=True)
    print(f"Branches covered:     {len(used_branch_names)}", flush=True)
    print(f"Orphaned branches:    {len(orphaned)}", flush=True)


if __name__ == "__main__":
    main()
