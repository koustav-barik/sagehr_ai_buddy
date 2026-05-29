#!/usr/bin/env python3
"""
scripts/branch-report.py — Generate/update the build-yellow-copilot branch report.

Outputs:
  .github/reports/build-yellow-copilot-branches.csv  — full data table
  .github/reports/build-yellow-copilot-branches.md   — hierarchy view (bold parents)

Usage:
    python3 scripts/branch-report.py [OPTIONS]

Options:
    --output-dir DIR     Directory for output files (default: .github/reports)
    --root-branch NAME   Root feature branch (default: build-yellow-copilot)
    --no-fetch           Skip git fetch
    --no-gh              Skip GitHub PR discovery (git ancestry only)

Discovery strategy (converging, in order):
  1. Keywords in branch name: copilot, yellow, preboarding
  2. GitHub PRs targeting each candidate (gh pr list --base <candidate>)
  3. Git history scan: commits unique to candidates -> branches containing them

Hierarchy resolution (priority):
  1. GitHub PR base branch (authoritative)
  2. Git deepest-ancestor

Requires:
  - .env.jira  (JIRA_EMAIL, JIRA_API_TOKEN, JIRA_BASE_URL)
  - gh CLI authenticated (for GitHub PR discovery; skipped with --no-gh)
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
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# Paths  (abspath avoids symlink mis-navigation: scripts/ is symlinked)
# ─────────────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(os.path.abspath(__file__)).parent
REPO_ROOT  = SCRIPT_DIR.parent

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────
DISCOVERY_KEYWORDS = ["copilot", "yellow", "preboarding"]
ALWAYS_INCLUDE     = ["hide-copilot-button-for-master"]
GITHUB_REPO        = "Sage/rails-cakehr"
GIT_SCAN_DEPTH     = 80   # commits per candidate to scan for orphan children

CSV_COLUMNS = [
    "branch_name", "parent_branch", "depth", "is_parent",
    "primary_ticket", "related_pr_tickets",
    "ticket_summary", "ticket_status",
    "epic_key", "epic_summary",
    "initiative_key", "initiative_summary",
    "pr_number", "pr_state", "pr_merged_at",
    "remote_exists", "last_commit_date", "last_commit_author",
    "branch_type", "notes",
]

# ─────────────────────────────────────────────────────────────────────────────
# Jira helpers
# ─────────────────────────────────────────────────────────────────────────────

def load_jira_credentials():
    for env_file in [REPO_ROOT / ".env.jira", REPO_ROOT / ".env"]:
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    os.environ.setdefault(key.strip(), val.strip())
    email    = os.environ.get("JIRA_EMAIL", "")
    token    = os.environ.get("JIRA_API_TOKEN", "")
    base_url = os.environ.get("JIRA_BASE_URL", "https://cakehr.atlassian.net")
    if not email or not token:
        print("ERROR: JIRA_EMAIL and JIRA_API_TOKEN must be set.", file=sys.stderr)
        sys.exit(1)
    return email, token, base_url


_jira_cache: dict = {}

def jira_get(ticket_key, email, token, base_url):
    if ticket_key in _jira_cache:
        return _jira_cache[ticket_key]
    fields = "summary,status,issuetype,parent,customfield_10014"
    url    = f"{base_url}/rest/api/3/issue/{ticket_key}?fields={fields}"
    creds  = base64.b64encode(f"{email}:{token}".encode()).decode()
    req    = urllib.request.Request(url, headers={
        "Authorization": f"Basic {creds}",
        "Accept":        "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            _jira_cache[ticket_key] = data
            return data
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            _jira_cache[ticket_key] = None
            return None
        raise
    except Exception as exc:
        print(f"  WARNING Jira {ticket_key}: {exc}", file=sys.stderr)
        _jira_cache[ticket_key] = None
        return None


def resolve_jira(primary_ticket, email, token, base_url):
    """Walk ticket -> epic -> initiative. Returns dict of Jira fields."""
    empty = dict(
        ticket_summary="N/A", ticket_status="N/A",
        epic_key="N/A", epic_summary="N/A",
        initiative_key="N/A", initiative_summary="N/A",
    )
    if not primary_ticket or primary_ticket in ("N/A", "Multiple"):
        return empty
    data = jira_get(primary_ticket, email, token, base_url)
    if not data:
        return empty
    f = data.get("fields", {}) or {}
    result = dict(
        ticket_summary = f.get("summary", "N/A"),
        ticket_status  = (f.get("status") or {}).get("name", "N/A"),
        epic_key       = (f.get("customfield_10014")
                          or (f.get("parent") or {}).get("key")
                          or "N/A"),
        epic_summary   = "N/A",
        initiative_key = "N/A",
        initiative_summary = "N/A",
    )
    if result["epic_key"] != "N/A":
        epic_data = jira_get(result["epic_key"], email, token, base_url)
        if epic_data:
            ef = epic_data.get("fields", {}) or {}
            result["epic_summary"]   = ef.get("summary", "N/A")
            result["initiative_key"] = (ef.get("parent") or {}).get("key") or "N/A"
            if result["initiative_key"] != "N/A":
                init_data = jira_get(result["initiative_key"], email, token, base_url)
                if init_data:
                    result["initiative_summary"] = (
                        (init_data.get("fields") or {}).get("summary", "N/A")
                    )
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Git helpers
# ─────────────────────────────────────────────────────────────────────────────

def git(*args):
    r = subprocess.run(["git"] + list(args), capture_output=True, text=True, cwd=str(REPO_ROOT))
    return r.stdout.strip()

def git_lines(*args):
    return [l for l in git(*args).splitlines() if l.strip()]

def git_ok(*args):
    return subprocess.run(["git"] + list(args), capture_output=True,
                          cwd=str(REPO_ROOT)).returncode == 0

def fetch_remote():
    print("Fetching remote branches...", flush=True)
    subprocess.run(["git", "fetch", "--all", "--prune"],
                   capture_output=True, cwd=str(REPO_ROOT))

def all_remote_branches() -> list:
    lines = git_lines("branch", "-r")
    return [l.strip().replace("origin/", "") for l in lines
            if not l.strip().startswith("HEAD")]

def branch_tip(branch: str) -> str:
    return git("rev-parse", f"origin/{branch}")

def merge_base_commit(a: str, b: str) -> str:
    r = subprocess.run(["git", "merge-base", f"origin/{a}", f"origin/{b}"],
                       capture_output=True, text=True, cwd=str(REPO_ROOT))
    return r.stdout.strip() if r.returncode == 0 else ""

def is_ancestor_of(commit: str, branch: str) -> bool:
    return git_ok("merge-base", "--is-ancestor", commit, f"origin/{branch}")

def master_merge_base(branch: str) -> str:
    r = subprocess.run(["git", "merge-base", "origin/master", f"origin/{branch}"],
                       capture_output=True, text=True, cwd=str(REPO_ROOT))
    return r.stdout.strip() if r.returncode == 0 else ""

def unique_commits(branch: str, base: str = "master", limit: int = 0) -> list:
    lines = git_lines("log", "--format=%H", "--no-merges",
                      f"origin/{branch}", "--not", f"origin/{base}")
    return lines[:limit] if limit else lines

def unique_subjects(branch: str, base: str = "master") -> list:
    return git_lines("log", "--format=%s", "--no-merges",
                     f"origin/{branch}", "--not", f"origin/{base}")

def last_commit_info(branch: str) -> tuple:
    info = git("log", "-1", "--format=%ai|%an", f"origin/{branch}")
    if "|" in info:
        date, author = info.split("|", 1)
        return date.split(" ")[0], author.strip()
    return "N/A", "N/A"

def extract_chr(text: str) -> list:
    return [m.upper() for m in re.findall(r"CHR-\d+", text, re.IGNORECASE)]

def primary_ticket_for(branch: str, commit_base: str = "master") -> str:
    ticket = next(iter(extract_chr(branch)), None)
    if ticket:
        return ticket
    for subj in unique_subjects(branch, commit_base)[:30]:
        tickets = extract_chr(subj)
        if tickets:
            return tickets[0]
    return "N/A"


# ─────────────────────────────────────────────────────────────────────────────
# GitHub PR helpers
# ─────────────────────────────────────────────────────────────────────────────

_pr_registry: dict = {}  # branch_name -> PR info dict

def gh_available() -> bool:
    return subprocess.run(["which", "gh"], capture_output=True).returncode == 0

def fetch_prs_for_base(base_branch: str) -> list:
    r = subprocess.run(
        ["gh", "pr", "list", "--repo", GITHUB_REPO,
         "--base", base_branch, "--state", "all",
         "--json", "number,title,headRefName,baseRefName,state,mergedAt,body",
         "--limit", "200"],
        capture_output=True, text=True, cwd=str(REPO_ROOT)
    )
    if r.returncode != 0:
        return []
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return []

def register_pr(pr: dict):
    head = pr["headRefName"]
    tickets = extract_chr(pr.get("body", "") or "")
    seen_t: set = set()
    unique_tickets = [t for t in tickets if not (t in seen_t or seen_t.add(t))]
    entry = {
        "number":       pr["number"],
        "state":        pr["state"],
        "merged_at":    (pr.get("mergedAt") or "")[:10],
        "base":         pr["baseRefName"],
        "title":        pr.get("title", ""),
        "body_tickets": unique_tickets,
    }
    # Keep highest-numbered (most recent) PR per branch
    if head not in _pr_registry or pr["number"] > _pr_registry[head]["number"]:
        _pr_registry[head] = entry

def pr_for_branch(branch: str) -> dict:
    return _pr_registry.get(branch, {})


# ─────────────────────────────────────────────────────────────────────────────
# Discovery
# ─────────────────────────────────────────────────────────────────────────────

def discover_all_candidates(root_branch: str, use_gh: bool) -> list:
    all_remote = set(all_remote_branches())
    keyword_re = re.compile("|".join(DISCOVERY_KEYWORDS), re.IGNORECASE)

    candidates: list = [root_branch]
    candidate_set: set = {root_branch}

    def add(branch: str):
        if branch not in candidate_set and branch not in {"master", "main"}:
            candidates.append(branch)
            candidate_set.add(branch)

    # Phase 1: keyword scan
    print("Phase 1: keyword scan...", flush=True)
    for b in all_remote:
        if keyword_re.search(b) or b in ALWAYS_INCLUDE:
            add(b)
    for b in ALWAYS_INCLUDE:
        add(b)
    print(f"  {len(candidates)} candidates after keyword scan.", flush=True)

    # Phase 2: GitHub PR discovery (converge)
    if use_gh:
        print("Phase 2: GitHub PR discovery (converging)...", flush=True)
        processed_bases: set = set()
        wave = list(candidates)
        while wave:
            next_wave = []
            for base in wave:
                if base in processed_bases:
                    continue
                processed_bases.add(base)
                prs = fetch_prs_for_base(base)
                for pr in prs:
                    register_pr(pr)
                    head = pr["headRefName"]
                    if head not in candidate_set:
                        add(head)
                        next_wave.append(head)
                        print(f"    PR: {head} (base: {base})", flush=True)
            wave = next_wave
        print(f"  {len(candidates)} candidates after PR discovery.", flush=True)
    else:
        print("Phase 2: skipped (--no-gh).", flush=True)

    # Phase 3: git history scan
    print("Phase 3: git history scan for orphan children...", flush=True)
    all_shas: set = set()
    for cand in list(candidates):
        if cand in all_remote:
            all_shas.update(unique_commits(cand, "master", GIT_SCAN_DEPTH))
    print(f"  Scanning {len(all_shas)} unique commits...", flush=True)
    for sha in all_shas:
        for line in git_lines("branch", "-r", "--contains", sha):
            b = line.strip().replace("origin/", "")
            if b and "HEAD" not in b and "master" not in b and "main" not in b:
                if b not in candidate_set:
                    add(b)
                    print(f"    Git scan: {b}", flush=True)
    print(f"  {len(candidates)} candidates after git scan.", flush=True)

    # Deduplicate preserving order
    seen: set = set()
    return [b for b in candidates if not (b in seen or seen.add(b))]


# ─────────────────────────────────────────────────────────────────────────────
# Hierarchy
# ─────────────────────────────────────────────────────────────────────────────

def build_hierarchy(root_branch: str, candidates: list) -> dict:
    all_remote = set(all_remote_branches())
    existing   = [c for c in candidates if c in all_remote]

    print("Building hierarchy...", flush=True)
    tips: dict = {b: branch_tip(b) for b in existing}
    result: dict = {root_branch: {"parent": "(root)", "depth": 0}}

    for branch in candidates:
        if branch == root_branch:
            continue

        # Priority 1: PR base (if it's one of our candidates)
        pr = pr_for_branch(branch)
        pr_base = pr.get("base", "")
        if pr_base and pr_base in set(candidates) and pr_base != branch:
            result[branch] = {"parent": pr_base, "depth": None}
            continue

        # Priority 2: git ancestry (only for existing remote branches)
        if branch not in all_remote:
            result[branch] = {"parent": "unknown", "depth": None}
            continue

        base_with_root = merge_base_commit(root_branch, branch)
        m_base         = master_merge_base(branch)
        if not base_with_root or base_with_root == m_base:
            result[branch] = {"parent": "master (not from root)", "depth": "N/A"}
            continue

        # Deepest candidate whose tip is an ancestor of branch
        ancestor_cands = [
            c for c in existing
            if c != branch and tips.get(c)
            and is_ancestor_of(tips[c], branch)
        ]
        deepest = root_branch
        for c in ancestor_cands:
            c_tip = tips[c]
            has_deeper = any(
                o != c and tips.get(o) and is_ancestor_of(c_tip, o)
                for o in ancestor_cands
            )
            if not has_deeper:
                deepest = c
                break
        result[branch] = {"parent": deepest, "depth": None}

    # BFS depth assignment
    depths: dict = {root_branch: 0}
    changed = True
    while changed:
        changed = False
        for b, info in result.items():
            if info["depth"] is not None:
                continue
            p = info["parent"]
            if p in depths:
                info["depth"] = depths[p] + 1
                depths[b]     = info["depth"]
                changed = True
    for info in result.values():
        if info["depth"] is None:
            info["depth"] = "?"

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Branch type inference
# ─────────────────────────────────────────────────────────────────────────────

def infer_type(branch: str) -> str:
    name = branch.lower()
    if name == "build-yellow-copilot":
        return "root"
    if "poc"          in name: return "poc"
    if "debug"        in name: return "debug"
    if "experimental" in name: return "experimental"
    if any(w in name for w in ["remove", "hide-", "cleanup"]): return "cleanup"
    if any(w in name for w in ["fix", "defect", "bug", "hotfix"]): return "fix"
    if "draft"        in name: return "draft"
    if "refactor"     in name: return "fix"
    return "feature"


# ─────────────────────────────────────────────────────────────────────────────
# Markdown generation
# ─────────────────────────────────────────────────────────────────────────────

def generate_markdown(rows: list, root_branch: str, output_path: Path):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Which branches are parents?
    parents_with_children = {
        r["parent_branch"] for r in rows
        if r["parent_branch"] not in {"(root)", "master (not from root)", "unknown"}
    }
    parents_with_children.add(root_branch)

    def is_parent(b: str) -> bool:
        return b in parents_with_children

    lines = [
        f"# `{root_branch}` — Branch Dependency Map",
        "",
        f"_Generated: {now} · {len(rows)} branches total_",
        "",
        "## Legend",
        "",
        "- **`Bold branch names`** = parent branches (have child branches)",
        "- `depth` = levels below root (0 = root, 1 = direct child…)",
        "- `N/A` depth = branched from `master`, not from root",
        "- PR State: **OPEN** / MERGED / CLOSED",
        "- Remote ✓ = branch still exists as a remote ref · ✗ = merged/deleted",
        "",
        "---",
        "",
    ]

    # Root overview card
    root_row = next((r for r in rows if r["branch_name"] == root_branch), {})
    lines += [
        f"## Root Branch: **`{root_branch}`**",
        "",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| Tickets | {root_row.get('primary_ticket', 'N/A')} |",
        f"| Summary | {root_row.get('ticket_summary', 'N/A')} |",
        f"| Last commit | {root_row.get('last_commit_date','N/A')}"
        f" by {root_row.get('last_commit_author','N/A')} |",
        "",
        "---",
        "",
        "## Branch Hierarchy",
        "",
        "_Each section heading is a **parent branch**. "
        "Bold branch names within tables also have children of their own._",
        "",
    ]

    # Group rows by parent for BFS traversal
    by_parent: dict = defaultdict(list)
    for r in rows:
        if r["branch_name"] != root_branch:
            by_parent[r["parent_branch"]].append(r)

    # BFS ordering of parent sections
    visited: set = set()
    queue  = [root_branch]
    ordered_parents: list = []
    while queue:
        p = queue.pop(0)
        if p in visited:
            continue
        visited.add(p)
        ordered_parents.append(p)
        children = sorted(by_parent.get(p, []),
                          key=lambda r: (str(r["depth"]), r["branch_name"]))
        queue.extend(c["branch_name"] for c in children
                     if c["branch_name"] not in visited)

    TABLE_HEADER = (
        "| Branch | PR | Depth | Ticket | Summary | Ticket Status "
        "| Epic | Initiative | PR State | Merged/Closed | Remote | Type |"
    )
    TABLE_SEP = (
        "|--------|-----|-------|--------|---------|-------------- "
        "|------|------------|----------|---------------|--------|------|"
    )

    def format_row(r: dict) -> str:
        branch   = r["branch_name"]
        display  = f"**`{branch}`**" if is_parent(branch) else f"`{branch}`"
        pr_num   = r.get("pr_number", "")
        pr_link  = (f"[#{pr_num}](https://github.com/{GITHUB_REPO}/pull/{pr_num})"
                    if pr_num else "—")
        depth    = r.get("depth", "?")
        ticket   = r.get("primary_ticket", "N/A")
        summary  = (r.get("ticket_summary") or "N/A").replace("|", "\\|")[:70]
        t_status = r.get("ticket_status", "N/A")
        epic     = r.get("epic_key", "N/A")
        epic_s   = r.get("epic_summary", "")
        if epic_s and epic_s != "N/A":
            epic = f"{epic}: {epic_s[:45]}"
        init     = r.get("initiative_key", "N/A")
        init_s   = r.get("initiative_summary", "")
        if init_s and init_s != "N/A":
            init = f"{init}: {init_s[:45]}"
        pr_state  = r.get("pr_state", "—") or "—"
        merged_at = r.get("pr_merged_at", "—") or "—"
        remote    = "✓" if r.get("remote_exists") == "Y" else "✗"
        btype     = r.get("branch_type", "")
        return (f"| {display} | {pr_link} | {depth} | {ticket} | {summary} "
                f"| {t_status} | {epic} | {init} | {pr_state} | {merged_at} | {remote} | {btype} |")

    for parent in ordered_parents:
        children = sorted(by_parent.get(parent, []),
                          key=lambda r: (str(r["depth"]), r["branch_name"]))
        if not children:
            continue

        parent_row = next((r for r in rows if r["branch_name"] == parent), None)
        pr_ref = ""
        if parent_row and parent_row.get("pr_number"):
            pr_ref = (f" · [PR #{parent_row['pr_number']}]"
                      f"(https://github.com/{GITHUB_REPO}/pull/{parent_row['pr_number']})")

        lines.append(f"### **`{parent}`**{pr_ref}")
        lines.append("")
        if parent_row and parent_row.get("related_pr_tickets"):
            lines.append(f"> Related tickets: `{parent_row['related_pr_tickets']}`")
            lines.append("")
        lines.append(TABLE_HEADER)
        lines.append(TABLE_SEP)
        for r in children:
            lines.append(format_row(r))
        lines.append("")

    # Master-derived branches
    master_rows = [r for r in rows
                   if r["parent_branch"] in ("master (not from root)", "unknown")
                   and r["branch_name"] != root_branch]
    if master_rows:
        lines += [
            "---",
            "",
            "### Branches derived from `master`",
            "",
            "_Related by name/topic but not branched from root._",
            "",
            TABLE_HEADER,
            TABLE_SEP,
        ]
        for r in sorted(master_rows, key=lambda x: x["branch_name"]):
            lines.append(format_row(r))
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Markdown written to: {output_path}", flush=True)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--output-dir",
                        default=str(REPO_ROOT / ".github/reports"))
    parser.add_argument("--root-branch", default="build-yellow-copilot")
    parser.add_argument("--no-fetch", action="store_true")
    parser.add_argument("--no-gh",    action="store_true")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path   = output_dir / "build-yellow-copilot-branches.csv"
    md_path    = output_dir / "build-yellow-copilot-branches.md"

    email, token, base_url = load_jira_credentials()

    if not args.no_fetch:
        fetch_remote()

    use_gh = (not args.no_gh) and gh_available()
    if not use_gh and not args.no_gh:
        print("WARNING: gh CLI not found. GitHub PR discovery skipped.", file=sys.stderr)

    # ── Discover ──────────────────────────────────────────────────────────────
    candidates = discover_all_candidates(args.root_branch, use_gh)
    all_remote = set(all_remote_branches())

    # ── Hierarchy ─────────────────────────────────────────────────────────────
    hierarchy = build_hierarchy(args.root_branch, candidates)

    # ── Which branches are parents? ───────────────────────────────────────────
    parents_with_children = {
        info["parent"]
        for info in hierarchy.values()
        if info["parent"] not in {"(root)", "master (not from root)", "unknown", None}
    }
    parents_with_children.add(args.root_branch)

    # ── Build rows ────────────────────────────────────────────────────────────
    print("Fetching Jira data and compiling rows...", flush=True)
    rows = []

    for branch in candidates:
        print(f"  {branch}...", flush=True)
        info   = hierarchy.get(branch, {"parent": "unknown", "depth": "?"})
        parent = info["parent"]
        depth  = info["depth"]
        r_exists = "Y" if branch in all_remote else "N"

        if branch in all_remote:
            last_date, last_author = last_commit_info(branch)
        else:
            pr_info    = pr_for_branch(branch)
            last_date  = pr_info.get("merged_at") or "N/A"
            last_author = "N/A"

        pr       = pr_for_branch(branch)
        pr_num   = pr.get("number", "")
        pr_state = pr.get("state", "")
        pr_merge = pr.get("merged_at", "")
        pr_tickets = ", ".join(pr.get("body_tickets", [])[:10])

        commit_base = (args.root_branch
                       if parent not in ("master (not from root)", "unknown")
                       else "master")

        if branch == args.root_branch:
            all_t: list = []
            for subj in unique_subjects(branch, "master")[:300]:
                all_t.extend(extract_chr(subj))
            seen_t: set = set()
            uniq_t = [t for t in all_t if not (t in seen_t or seen_t.add(t))]
            primary = ("Multiple (" + ", ".join(uniq_t[:6]) +
                       ("…" if len(uniq_t) > 6 else "") + ")") if uniq_t else "N/A"
            jira = dict(
                ticket_summary="Root integration branch for Copilot AI and Preboarding features",
                ticket_status="Active",
                epic_key="Multiple", epic_summary="Multiple",
                initiative_key="Multiple", initiative_summary="Multiple",
            )
        elif branch in all_remote:
            primary = primary_ticket_for(branch, commit_base)
            jira    = resolve_jira(primary, email, token, base_url)
        else:
            # Deleted/merged branch — get ticket from name or PR title
            primary = next(iter(extract_chr(branch)), None)
            if not primary and pr.get("title"):
                primary = next(iter(extract_chr(pr["title"])), "N/A")
            primary = primary or "N/A"
            jira    = resolve_jira(primary, email, token, base_url)

        rows.append({
            "branch_name":        branch,
            "parent_branch":      parent,
            "depth":              str(depth),
            "is_parent":          "Y" if branch in parents_with_children else "N",
            "primary_ticket":     primary,
            "related_pr_tickets": pr_tickets,
            "ticket_summary":     jira["ticket_summary"],
            "ticket_status":      jira["ticket_status"],
            "epic_key":           jira["epic_key"],
            "epic_summary":       jira["epic_summary"],
            "initiative_key":     jira["initiative_key"],
            "initiative_summary": jira["initiative_summary"],
            "pr_number":          str(pr_num),
            "pr_state":           pr_state,
            "pr_merged_at":       pr_merge,
            "remote_exists":      r_exists,
            "last_commit_date":   last_date,
            "last_commit_author": last_author,
            "branch_type":        infer_type(branch),
            "notes":              "",
        })

    # Sort: root first, then depth, then parent, then name
    def sort_key(r):
        d = r["depth"]
        try:    d = int(d)
        except: d = 99
        return (d, r["parent_branch"], r["branch_name"])

    rows.sort(key=sort_key)

    # ── Write CSV ─────────────────────────────────────────────────────────────
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nCSV written to:      {csv_path}", flush=True)

    # ── Write markdown ────────────────────────────────────────────────────────
    generate_markdown(rows, args.root_branch, md_path)

    print(f"Total branches:      {len(rows)}", flush=True)
    print(f"  Open PRs:          {sum(1 for r in rows if r['pr_state'] == 'OPEN')}",
          flush=True)
    print(f"  Merged PRs:        {sum(1 for r in rows if r['pr_state'] == 'MERGED')}",
          flush=True)
    print(f"  Remote branches:   {sum(1 for r in rows if r['remote_exists'] == 'Y')}",
          flush=True)


if __name__ == "__main__":
    main()

    python3 scripts/branch-report.py [--output PATH] [--root-branch BRANCH]

Defaults:
    --output      .github/reports/build-yellow-copilot-branches.csv
    --root-branch build-yellow-copilot

Requires .env.jira at repo root (or env vars):
    JIRA_EMAIL       — Atlassian account email
    JIRA_API_TOKEN   — Jira API token
    JIRA_BASE_URL    — e.g. https://cakehr.atlassian.net

Discovery strategy:
  1. Find all remote branches containing keywords: copilot, yellow, preboarding.
  2. For each candidate, determine if it was branched off the root branch (or from
     master). Uses merge-base to establish the hierarchy.
  3. Extract the primary CHR ticket from the branch name (falling back to the first
     unique commit message).
  4. Look up Jira data (summary, status, epic, initiative).
  5. Write a sorted, grouped CSV.
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
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Use os.path.abspath (NOT resolve) so that we follow the path as given,
# not the real path through any symlinks.  The scripts/ directory in
# rails-cakehr is symlinked from sagehr_ai_buddy; resolve() would navigate
# to the wrong repo root.
SCRIPT_DIR = Path(os.path.abspath(__file__)).parent
REPO_ROOT   = SCRIPT_DIR.parent

# Keywords used to filter candidate branches (case-insensitive)
DISCOVERY_KEYWORDS = ["copilot", "yellow", "preboarding"]

# Branches that should always be included even if they don't match keywords
ALWAYS_INCLUDE = [
    "hide-copilot-button-for-master",
]

CSV_COLUMNS = [
    "branch_name",
    "parent_branch",
    "depth",
    "primary_ticket",
    "ticket_summary",
    "ticket_status",
    "epic_key",
    "epic_summary",
    "initiative_key",
    "initiative_summary",
    "last_commit_date",
    "last_commit_author",
    "branch_type",
    "notes",
]

# ---------------------------------------------------------------------------
# Jira helpers
# ---------------------------------------------------------------------------

def load_jira_credentials():
    """Load Jira credentials from .env.jira or environment."""
    for env_file in [REPO_ROOT / ".env.jira", REPO_ROOT / ".env"]:
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    os.environ.setdefault(key.strip(), val.strip())

    email     = os.environ.get("JIRA_EMAIL", "")
    token     = os.environ.get("JIRA_API_TOKEN", "")
    base_url  = os.environ.get("JIRA_BASE_URL", "https://cakehr.atlassian.net")

    if not email or not token:
        print("ERROR: JIRA_EMAIL and JIRA_API_TOKEN must be set (in .env.jira or env).",
              file=sys.stderr)
        sys.exit(1)

    return email, token, base_url


def jira_get(ticket_key, email, token, base_url):
    """Fetch a single Jira issue and return the parsed JSON fields dict."""
    fields = "summary,status,issuetype,parent,customfield_10014"
    url    = f"{base_url}/rest/api/3/issue/{ticket_key}?fields={fields}"
    creds  = base64.b64encode(f"{email}:{token}".encode()).decode()
    req    = urllib.request.Request(url, headers={
        "Authorization": f"Basic {creds}",
        "Accept":        "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise
    except Exception as exc:  # noqa: BLE001
        print(f"  WARNING: Jira fetch failed for {ticket_key}: {exc}", file=sys.stderr)
        return None


_jira_cache: dict = {}

def fetch_jira(ticket_key, email, token, base_url):
    """Cached fetch for a Jira ticket; returns (summary, status, epic_key, initiative_key)."""
    if not ticket_key or ticket_key == "N/A":
        return "N/A", "N/A", "N/A", "N/A"

    if ticket_key not in _jira_cache:
        data = jira_get(ticket_key, email, token, base_url)
        if not data:
            _jira_cache[ticket_key] = ("N/A", "N/A", "N/A", "N/A")
        else:
            f        = data.get("fields", {})
            summary  = f.get("summary", "N/A")
            status   = (f.get("status") or {}).get("name", "N/A")
            # Epic link is stored in customfield_10014 (classic) or parent for next-gen
            epic_key = f.get("customfield_10014") or (f.get("parent") or {}).get("key") or "N/A"
            _jira_cache[ticket_key] = (summary, status, epic_key, "N/A")

    return _jira_cache[ticket_key]


def resolve_epic_and_initiative(primary_ticket, email, token, base_url):
    """
    Walk up the Jira hierarchy: ticket → epic → initiative.
    Returns (epic_key, epic_summary, initiative_key, initiative_summary).
    """
    ticket_summary, ticket_status, epic_key, _ = fetch_jira(primary_ticket, email, token, base_url)

    epic_summary         = "N/A"
    initiative_key       = "N/A"
    initiative_summary   = "N/A"

    if epic_key and epic_key != "N/A":
        epic_data = jira_get(epic_key, email, token, base_url)
        if epic_data:
            f            = epic_data.get("fields", {})
            epic_summary = f.get("summary", "N/A")
            initiative_key = (f.get("parent") or {}).get("key") or "N/A"
            if initiative_key and initiative_key != "N/A":
                init_data = jira_get(initiative_key, email, token, base_url)
                if init_data:
                    initiative_summary = (init_data.get("fields") or {}).get("summary", "N/A")

    return ticket_summary, ticket_status, epic_key, epic_summary, initiative_key, initiative_summary


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def git(*args):
    """Run a git command and return stdout as a stripped string."""
    result = subprocess.run(
        ["git"] + list(args),
        capture_output=True, text=True, cwd=str(REPO_ROOT)
    )
    return result.stdout.strip()


def git_lines(*args):
    """Run a git command and return stdout as a list of non-empty lines."""
    return [l for l in git(*args).splitlines() if l.strip()]


def fetch_remote():
    print("Fetching remote branches...", flush=True)
    subprocess.run(
        ["git", "fetch", "--all", "--prune"],
        capture_output=True, cwd=str(REPO_ROOT)
    )


def all_remote_branches():
    """Return list of remote branch names (without 'origin/' prefix)."""
    lines = git_lines("branch", "-r")
    branches = []
    for line in lines:
        name = line.strip().replace("origin/", "")
        if not name.startswith("HEAD"):
            branches.append(name)
    return branches


def branch_tip(branch):
    return git("rev-parse", f"origin/{branch}")


def merge_base(branch_a, branch_b):
    result = subprocess.run(
        ["git", "merge-base", f"origin/{branch_a}", f"origin/{branch_b}"],
        capture_output=True, text=True, cwd=str(REPO_ROOT)
    )
    return result.stdout.strip() if result.returncode == 0 else None


def is_ancestor(commit, branch):
    """Return True if commit is an ancestor of (or equal to) origin/branch."""
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, f"origin/{branch}"],
        capture_output=True, cwd=str(REPO_ROOT)
    )
    return result.returncode == 0


def last_commit_info(branch):
    """Return (date, author) for the latest commit on origin/branch."""
    info = git("log", "-1", "--format=%ai|%an", f"origin/{branch}")
    if "|" in info:
        date, author = info.split("|", 1)
        return date.split(" ")[0], author
    return "N/A", "N/A"


def unique_commits_subjects(branch, base="master"):
    """Non-merge commit subjects on branch that are NOT on base branch."""
    lines = git_lines("log", "--format=%s", "--no-merges",
                      f"origin/{branch}", "--not", f"origin/{base}")
    return lines


def extract_chr_ticket(text):
    """Return the first CHR-NNNNN found in text, or None."""
    m = re.search(r"CHR-\d+", text, re.IGNORECASE)
    return m.group(0).upper() if m else None


def primary_ticket_for_branch(branch_name, root_branch="master"):
    """Extract primary CHR ticket: first from branch name, then from unique commits."""
    ticket = extract_chr_ticket(branch_name)
    if ticket:
        return ticket
    subjects = unique_commits_subjects(branch_name, root_branch)
    for subj in subjects[:20]:
        t = extract_chr_ticket(subj)
        if t:
            return t
    return "N/A"


# ---------------------------------------------------------------------------
# Branch type inference
# ---------------------------------------------------------------------------

def infer_branch_type(branch_name):
    name = branch_name.lower()
    if name in {"build-yellow-copilot"}:
        return "root"
    if "poc" in name:
        return "poc"
    if "debug" in name:
        return "debug"
    if "experimental" in name:
        return "experimental"
    if name.startswith("hide-") or "remove" in name or "cleanup" in name:
        return "cleanup"
    if any(w in name for w in ["fix", "defect", "bug", "hotfix"]):
        return "fix"
    return "feature"


# ---------------------------------------------------------------------------
# Hierarchy builder
# ---------------------------------------------------------------------------

def build_hierarchy(root_branch, candidate_branches):
    """
    For each candidate, determine:
      - parent_branch: the most specific (deepest) candidate that is an ancestor
      - depth: levels below root (0 = root, 1 = direct child, etc.)

    A branch is a child of root only if its merge-base with root is strictly
    later than its merge-base with master (contains root-specific commits).
    Among all candidates that are ancestors of the branch, we pick the deepest
    one (the candidate whose tip is not itself an ancestor of any other candidate
    that is also an ancestor of the branch).
    """
    print(f"  Computing branch tips...", flush=True)
    tips = {b: branch_tip(b) for b in candidate_branches}

    def master_base(branch):
        r = subprocess.run(
            ["git", "merge-base", "origin/master", f"origin/{branch}"],
            capture_output=True, text=True, cwd=str(REPO_ROOT)
        )
        return r.stdout.strip() if r.returncode == 0 else None

    hierarchy = {}

    for branch in candidate_branches:
        if branch == root_branch:
            hierarchy[branch] = {"parent": "(root)", "depth": 0}
            continue

        # First: does this branch contain root-specific commits?
        base_with_root = merge_base(root_branch, branch)
        m_base         = master_base(branch)
        if base_with_root is None or base_with_root == m_base:
            # Shares only master history — branched from master, not from root
            hierarchy[branch] = {"parent": "master (not from root)", "depth": "N/A"}
            continue

        # The branch has root-specific commits. Find its most specific parent:
        # all candidates C (excluding the branch itself) such that C's tip is
        # an ancestor of the branch.
        ancestor_candidates = [
            c for c in candidate_branches
            if c != branch and tips.get(c)
            and is_ancestor(tips[c], branch)
        ]

        # Among those, find the "deepest": the one whose tip is NOT an ancestor
        # of any other ancestor candidate (i.e., no ancestor candidate is further
        # down from it).
        deepest_parent = root_branch
        for c in ancestor_candidates:
            c_tip = tips[c]
            has_deeper = any(
                o != c and tips.get(o) and is_ancestor(c_tip, o)
                for o in ancestor_candidates
            )
            if not has_deeper:
                deepest_parent = c
                break

        hierarchy[branch] = {"parent": deepest_parent, "depth": None}

    # Compute depths via BFS
    depths = {root_branch: 0}
    changed = True
    while changed:
        changed = False
        for branch, info in hierarchy.items():
            if info["depth"] is not None and info["depth"] != "N/A":
                continue
            p = info["parent"]
            if p in depths:
                info["depth"] = depths[p] + 1
                depths[branch] = info["depth"]
                changed = True

    # Anything still None gets depth "?"
    for info in hierarchy.values():
        if info["depth"] is None:
            info["depth"] = "?"

    return hierarchy


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", default=str(REPO_ROOT / ".github/reports/build-yellow-copilot-branches.csv"),
                        help="Output CSV path")
    parser.add_argument("--root-branch", default="build-yellow-copilot",
                        help="Root feature branch to analyse")
    parser.add_argument("--no-fetch", action="store_true",
                        help="Skip git fetch (use cached remote refs)")
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # -- Jira credentials ---------------------------------------------------
    email, token, base_url = load_jira_credentials()

    # -- Git fetch ----------------------------------------------------------
    if not args.no_fetch:
        fetch_remote()

    # -- Discover candidate branches ----------------------------------------
    print("Discovering candidate branches...", flush=True)
    all_branches = all_remote_branches()
    keyword_pattern = re.compile("|".join(DISCOVERY_KEYWORDS), re.IGNORECASE)

    candidates = [args.root_branch]  # always include root
    for b in all_branches:
        if b == args.root_branch:
            continue
        if keyword_pattern.search(b) or b in ALWAYS_INCLUDE:
            candidates.append(b)

    # Deduplicate preserving order
    seen = set()
    candidates = [b for b in candidates if not (b in seen or seen.add(b))]

    print(f"  Found {len(candidates)} keyword-matched candidate branches.", flush=True)

    # -- Second pass: recursive child discovery -----------------------------
    # Use `git branch -r --contains <tip>` which is fast (O(branches)) to
    # find every remote branch that has a candidate's tip in its history,
    # meaning it was branched from (or IS) that candidate.
    # We then verify it's a *child* (has extra commits) by checking it's not
    # equal to the candidate.
    print("  Running recursive child discovery...", flush=True)
    candidate_set = set(candidates)
    new_children:  list = []

    for cand in list(candidates):  # iterate snapshot; candidates may grow
        cand_tip = branch_tip(cand)
        if not cand_tip:
            continue
        # All remote branches that contain this commit
        containing = git_lines("branch", "-r", "--contains", cand_tip)
        for line in containing:
            b = line.strip().replace("origin/", "")
            if b in candidate_set or b == "HEAD" or "master" in b or "main" in b:
                continue
            b_tip = branch_tip(b)
            if b_tip != cand_tip:  # it's a true child (has extra commits)
                print(f"    Child discovered: {b} (parent tip {cand_tip[:10]} from {cand})", flush=True)
                candidates.append(b)
                candidate_set.add(b)
                new_children.append(b)

    # Deduplicate preserving order
    seen = set()
    candidates = [b for b in candidates if not (b in seen or seen.add(b))]

    print(f"  Total candidates after child discovery: {len(candidates)}", flush=True)
    print(f"  Candidates: {candidates}", flush=True)

    # -- Build hierarchy ----------------------------------------------------
    print("Building branch hierarchy...", flush=True)
    hierarchy = build_hierarchy(args.root_branch, candidates)

    # -- Fetch Jira data and compose rows -----------------------------------
    print("Fetching Jira data...", flush=True)
    rows = []

    for branch in candidates:
        print(f"  Processing {branch}...", flush=True)
        info   = hierarchy.get(branch, {"parent": "unknown", "depth": "?"})
        parent = info["parent"]
        depth  = info["depth"]

        last_date, last_author = last_commit_info(branch)
        branch_type = infer_branch_type(branch)

        # Determine the base for unique commit extraction
        commit_base = args.root_branch if parent != "master (not from root)" else "master"
        primary = primary_ticket_for_branch(branch, commit_base)

        # For the root branch itself, gather all unique CHR tickets as a summary
        if branch == args.root_branch:
            unique_subjects = unique_commits_subjects(branch, "master")
            all_tickets = sorted(set(
                t for s in unique_subjects
                for t in re.findall(r"CHR-\d+", s, re.IGNORECASE)
            ))
            primary = "Multiple (" + ", ".join(all_tickets[:6]) + ("…" if len(all_tickets) > 6 else "") + ")" if all_tickets else "N/A"
            ticket_summary = "Root integration branch for Copilot AI and Preboarding features"
            ticket_status  = "Active"
            epic_key       = "Multiple"
            epic_summary   = "Multiple"
            init_key       = "Multiple"
            init_summary   = "Multiple"
        else:
            ticket_summary, ticket_status, epic_key, epic_summary, init_key, init_summary = \
                resolve_epic_and_initiative(primary, email, token, base_url)

        rows.append({
            "branch_name":       branch,
            "parent_branch":     parent,
            "depth":             str(depth),
            "primary_ticket":    primary,
            "ticket_summary":    ticket_summary,
            "ticket_status":     ticket_status,
            "epic_key":          epic_key,
            "epic_summary":      epic_summary,
            "initiative_key":    init_key,
            "initiative_summary": init_summary,
            "last_commit_date":  last_date,
            "last_commit_author": last_author,
            "branch_type":       branch_type,
            "notes":             "",  # free-form; preserved if CSV is hand-edited and re-merged
        })

    # -- Sort rows: root first, then by depth, then alphabetically ----------
    def sort_key(row):
        d = row["depth"]
        try:
            return (int(d), row["parent_branch"], row["branch_name"])
        except (ValueError, TypeError):
            return (99, row["parent_branch"], row["branch_name"])

    rows.sort(key=sort_key)

    # -- Write CSV ----------------------------------------------------------
    with open(output_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nReport written to: {output_path}", flush=True)
    print(f"Total branches: {len(rows)}", flush=True)


if __name__ == "__main__":
    main()
