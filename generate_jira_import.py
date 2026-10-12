"""
generate_jira_import.py
-----------------------
Generates a Jira Cloud-compatible import JSON file with randomised issues.

Dog tag
-------
  Name     : generate_jira_import.py
  Project  : jira-data-generator
  Repo     : https://github.com/emretoptanci/jira-data-generator
  Author   : Emre Toptancı (https://github.com/emretoptanci)
  Version  : 1.1.0
  Updated  : 2026-10-12
  Requires : Python 3.9+ (standard library only)
  Output   : Jira Cloud JSON importer format (users + projects/issues/history)
  Note     : All user emails use the reserved example.com domain and all
             accountIds are randomly generated; no real accounts are referenced.

Usage
-----
python generate_jira_import.py [OPTIONS]

Options
-------
  --num-issues                INT   Number of issues to generate                      (default: 5)
  --start-date                DATE  Earliest possible issue created date (YYYY-MM-DD)  (default: 2024-01-01)
  --num-months                INT   Number of months to spread issues over             (default: 24)
  --min-status-transitions    INT   Minimum status transitions per issue               (default: 2)
  --max-status-transitions    INT   Maximum status transitions per issue               (default: 5)
  --min-assignee-transitions  INT   Minimum assignee transitions per issue             (default: 2)
  --max-assignee-transitions  INT   Maximum assignee transitions per issue             (default: 5)
  --min-hours-between         FLOAT Minimum hours between consecutive changelog entries (default: 1)
  --max-hours-between         FLOAT Maximum hours between consecutive changelog entries (default: 48)
  --focused-user-ratio           FLOAT Probability (0.00-1.00) that the next assignee is a focused user (default: 0.20)
  --min-minutes-focused-user     FLOAT Minimum minutes a focused user stays assigned before reassignment  (default: 15)
  --max-minutes-focused-user     FLOAT Maximum minutes a focused user stays assigned before reassignment  (default: 120)
  --output                    PATH  Output file path                                   (default: JiraCloudImport_generated.json)
  --seed                      INT   Random seed for reproducibility                    (optional)
  --project-key               STR   Jira project key                                  (default: SDP)
  --project-name              STR   Jira project name                                 (default: Sample Data Project)
  --min-summary-words         INT   Minimum number of random words in an issue summary (default: 4)
  --max-summary-words         INT   Maximum number of random words in an issue summary (default: 8)
  --last-user-account-id      STR   accountId of the user who is the final assignee on every issue (optional)

Example
-------
python generate_jira_import.py --num-issues 10 --start-date 2024-01-01 --num-months 12 --min-status-transitions 2 --max-status-transitions 6 --min-assignee-transitions 1 --max-assignee-transitions 3 --min-hours-between 2 --max-hours-between 24 --focused-user-ratio 0.30 --min-minutes-focused-user 10 --max-minutes-focused-user 60 --project-key DEMO --project-name 'Demo Data Project' --seed 95 --output my_import.json
"""

import argparse
import calendar
import json
import random
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# Static reference data
# ---------------------------------------------------------------------------

USERS = [
    {"name": "ahmet",       "fullname": "Ahmet",       "email": "ahmet@example.com",     "accountId": "cf7f00d16f8f6eb353b7daee"},
    {"name": "emre",        "fullname": "Emre",        "email": "emre@example.com",      "accountId": "9c2d12ca4c5fb2dfb3ab4545"},
    {"name": "oguzhan",     "fullname": "Oğuzhan",     "email": "oguzhan@example.com",   "accountId": "15b27e2d2ac76ba5ec5aa299"},
    {"name": "berk",        "fullname": "Berk",        "email": "berk@example.com",      "accountId": "a373f3b0df91d8086d0c2728"},
    {"name": "orkun",       "fullname": "Orkun",       "email": "orkun@example.com",     "accountId": "c49c89193c6c83813d52dc79"},
    {"name": "omer",        "fullname": "Ömer",        "email": "omer@example.com",      "accountId": "070b051a09adbbc806c6e789"},
]

# Focused users (e.g. triage/support) form a combined pool with regular USERS.
# focused_user_ratio controls the probability that the next assignee is a focused user.
# Focused users are never the first or last assignee of an issue; their time in
# assignment is governed by --min/max-minutes-focused-user rather than --min/max-hours-between.
FOCUSED_USERS = [
    {"name": "triage_agent",   "fullname": "Triage Agent",    "email": "triage_agent@example.com",    "accountId": "52bae79fee106ecb689df363"},
    {"name": "support1_agent", "fullname": "Support Agent 1", "email": "support_agent_1@example.com", "accountId": "1263e99cc41b88a829350e7d"},
    {"name": "support2_agent", "fullname": "Support Agent 2", "email": "support_agent_2@example.com", "accountId": "7e8148f90daa359198c98e41"},
]

_FOCUSED_USER_NAMES = {u["name"] for u in FOCUSED_USERS}

ISSUE_TYPES   = ["Task", "Bug", "Story", "Epic", "Improvement"]
PRIORITIES    = ["Highest", "High", "Medium", "Low", "Lowest"]
RESOLUTIONS   = [
    ("1",           "Resolved"),
    ("1",           "Resolved"),   # weighted: Resolved is most common
    ("1",           "Resolved"),
    ("test-res-1",  "Won't Do"),
    ("test-res-2",  "Duplicate"),
    ("test-res-3",  "Cannot Reproduce"),
]

# Jira status catalogue used for transitions
# id → (id, name)
STATUSES = {
    "1": ("1", "Open"),
    "3": ("3", "In Progress"),
    "4": ("4", "Reopened"),
    "5": ("5", "Resolved"),
    "6": ("6", "Closed"),
}

# Valid next-statuses from each status (keeps workflows realistic)
TRANSITIONS = {
    "1": ["3", "5", "6"],           # Open       → In Progress / Resolved / Closed
    "3": ["1", "4", "5"],           # In Progress → Open / Reopened / Resolved
    "4": ["3", "5"],                # Reopened   → In Progress / Resolved
    "5": ["6", "4"],                # Resolved   → Closed / Reopened
    "6": ["4"],                     # Closed     → Reopened
}

# Terminal statuses (issue lands here after all transitions)
TERMINAL_STATUSES = {"5": "Resolved", "6": "Closed"}

TZ_OFFSET = timezone(timedelta(hours=3))  # +0300

# Word pool for randomly generated issue summaries.
SUMMARY_WORDS = [
    "amber", "anchor", "arrow", "aspen", "atlas", "badge", "banner", "basin",
    "beacon", "birch", "blossom", "bridge", "bronze", "cabin", "canyon",
    "carbon", "cedar", "cobalt", "comet", "copper", "coral", "crystal",
    "dawn", "delta", "desert", "dolphin", "dragon", "eagle", "ember",
    "falcon", "feather", "fjord", "forest", "fossil", "galaxy", "garden",
    "glacier", "granite", "harbor", "hazel", "horizon", "indigo", "island",
    "jasmine", "jungle", "kernel", "lagoon", "lantern", "lemon", "lighthouse",
    "lunar", "maple", "marble", "meadow", "mirror", "monsoon", "mosaic",
    "nebula", "nectar", "oasis", "ocean", "olive", "orbit", "orchard",
    "pebble", "pepper", "phoenix", "pillar", "planet", "prairie", "prism",
    "quartz", "quiver", "raven", "reef", "ribbon", "river", "saddle",
    "saffron", "shadow", "silver", "summit", "sunset", "thunder", "timber",
    "tundra", "valley", "velvet", "violet", "walnut", "willow", "winter",
    "zenith", "zephyr",
]

# Dedicated RNG for summaries so that adding/removing summary generation never
# shifts the main random sequence (same --seed => same dates, users, statuses).
_SUMMARY_RNG = random.Random()


def generate_summary(min_words: int, max_words: int) -> str:
    """Return a summary made of a random number of random words (inclusive range)."""
    n = _SUMMARY_RNG.randint(min_words, max_words)
    words = _SUMMARY_RNG.sample(SUMMARY_WORDS, n) if n <= len(SUMMARY_WORDS) \
        else [_SUMMARY_RNG.choice(SUMMARY_WORDS) for _ in range(n)]
    return " ".join(words).capitalize()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _add_months(dt: datetime, months: int) -> datetime:
    """Return dt advanced by the given number of calendar months."""
    month = dt.month - 1 + months
    year  = dt.year + month // 12
    month = month % 12 + 1
    day   = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def distribute_issues_over_months(num_issues: int,
                                  num_months: int,
                                  start_date: datetime) -> list[datetime]:
    """
    Return a list of `num_issues` creation datetimes spread roughly evenly
    across `num_months` calendar months starting at `start_date`.
    Each month receives a share with up to ±20% random variation.
    """
    weights  = [random.uniform(0.8, 1.2) for _ in range(num_months)]
    total    = sum(weights)
    raw      = [w / total * num_issues for w in weights]
    counts   = [int(c) for c in raw]
    remainder = num_issues - sum(counts)
    # Distribute remainder to months with the largest fractional parts
    order = sorted(range(num_months), key=lambda i: raw[i] - counts[i], reverse=True)
    for i in range(remainder):
        counts[order[i]] += 1

    times = []
    for month_idx, count in enumerate(counts):
        m_start   = _add_months(start_date, month_idx)
        m_end     = _add_months(start_date, month_idx + 1)
        span_secs = max(0, int((m_end - m_start).total_seconds()) - 1)
        for _ in range(count):
            times.append(m_start + timedelta(seconds=random.randint(0, span_secs)))

    random.shuffle(times)
    return times


def fmt_dt(dt: datetime) -> str:
    """Format a datetime as Jira-compatible string with +0300 offset."""
    return dt.strftime("%Y-%m-%dT%H:%M:%S+0300")



# ---------------------------------------------------------------------------
# Core generators
# ---------------------------------------------------------------------------

def generate_status_chain(num_transitions: int) -> list[tuple[str, str]]:
    """
    Build a list of (from_id, to_id) status transitions.

    Starts at "Open" and ensures the final status is terminal (Resolved/Closed).
    `num_transitions` is the *exact* number of transitions to produce.
    """
    current = "1"   # Open
    chain = []

    for i in range(num_transitions):
        remaining = num_transitions - i
        if remaining == 1:
            # Last step must land in a terminal status
            candidates = [s for s in TRANSITIONS[current] if s in TERMINAL_STATUSES]
            if not candidates:
                # If no direct path, go through Resolved then Closed
                chain.append((current, "5"))
                current = "5"
                chain.append(("5", "6"))
                break
            next_status = random.choice(candidates)
        else:
            # Avoid terminal statuses until the last transition
            candidates = [s for s in TRANSITIONS[current] if s not in TERMINAL_STATUSES]
            if not candidates:
                # Forced into terminal early; pad by adding a Reopened bounce
                candidates = list(TRANSITIONS[current])
            next_status = random.choice(candidates)

        chain.append((current, next_status))
        current = next_status

    return chain


def generate_assignee_chain(initial_assignee: str,
                            num_transitions: int,
                            focused_user_ratio: float) -> list[tuple[dict, dict]]:
    """
    Build a list of (from_user, to_user) assignee transitions.

    USERS and FOCUSED_USERS form a single pool. For each transition `focused_user_ratio`
    is the probability that the next assignee is drawn from FOCUSED_USERS. Focused users
    are never the first or last assignee. An issue may be assigned to focused users
    more than once; each transition counts equally toward num_transitions.
    """
    current = next(u for u in USERS if u["name"] == initial_assignee)
    chain = []
    for i in range(num_transitions):
        is_last = (i == num_transitions - 1)
        if not is_last and focused_user_ratio > 0 and random.random() < focused_user_ratio:
            pool = [u for u in FOCUSED_USERS if u["name"] != current["name"]]
            if not pool:
                pool = FOCUSED_USERS
        else:
            pool = [u for u in USERS if u["name"] != current["name"]]
            if not pool:
                pool = USERS
        next_user = random.choice(pool)
        chain.append((current, next_user))
        current = next_user
    return chain


def generate_assignee_times(issue_created: datetime,
                             assignee_chain: list[tuple[dict, dict]],
                             min_hours_between: float,
                             max_hours_between: float,
                             min_focused_minutes: float,
                             max_focused_minutes: float) -> list[datetime]:
    """
    Generate one timestamp per assignee transition. The gap before each
    transition depends on who is currently assigned:
      - focused user  → gap in [min_focused_minutes, max_focused_minutes]
      - regular user → gap in [min_hours_between, max_hours_between]
    """
    hours_min_secs = max(1, int(min_hours_between * 3600))
    hours_max_secs = max(hours_min_secs, int(max_hours_between * 3600))
    focused_min_secs  = max(1, int(min_focused_minutes * 60))
    focused_max_secs  = max(focused_min_secs, int(max_focused_minutes * 60))

    times = []
    current = issue_created
    for from_user, _ in assignee_chain:
        if from_user["name"] in _FOCUSED_USER_NAMES:
            gap = timedelta(seconds=random.randint(focused_min_secs, focused_max_secs))
        else:
            gap = timedelta(seconds=random.randint(hours_min_secs, hours_max_secs))
        current = current + gap
        times.append(current)
    return times


def generate_event_times(issue_created: datetime,
                         total_events: int,
                         min_hours_between: float,
                         max_hours_between: float) -> list[datetime]:
    """
    Generate `total_events` strictly ascending timestamps starting after
    `issue_created`. Each consecutive pair (including the gap from
    `issue_created` to the first event) is separated by a random duration
    in [min_hours_between, max_hours_between].
    """
    min_secs = max(1, int(min_hours_between * 3600))
    max_secs = max(min_secs, int(max_hours_between * 3600))

    times = []
    current = issue_created
    for _ in range(total_events):
        gap = timedelta(seconds=random.randint(min_secs, max_secs))
        current = current + gap
        times.append(current)
    return times


def generate_issue(index: int,
                   issue_created: datetime,
                   min_status_trans: int,
                   max_status_trans: int,
                   min_assignee_trans: int,
                   max_assignee_trans: int,
                   min_hours_between: float,
                   max_hours_between: float,
                   focused_user_ratio: float,
                   min_focused_user_minutes: float,
                   max_focused_user_minutes: float,
                   min_summary_words: int = 4,
                   max_summary_words: int = 8,
                   last_user: dict = None) -> dict:
    """Generate a single Jira issue with its full change history."""

    # --- Basic fields ---
    issue_type = random.choice(ISSUE_TYPES)
    priority   = random.choice(PRIORITIES)
    reporter   = random.choice(USERS)

    num_status_trans   = random.randint(min_status_trans, max_status_trans)
    num_assignee_trans = random.randint(min_assignee_trans, max_assignee_trans)

    # --- Generate transition chains (needed before timing so assignee chain
    #     is known when computing per-transition time gaps) ---
    status_chain   = generate_status_chain(num_status_trans)
    initial_user   = random.choice(USERS)
    assignee_chain = generate_assignee_chain(initial_user["name"], num_assignee_trans,
                                             focused_user_ratio)

    # If a specific last user is requested, override the target of the final transition
    if last_user is not None:
        from_user, _ = assignee_chain[-1]
        assignee_chain[-1] = (from_user, last_user)

    # --- Build timeline ---
    # Status events use hours gaps; assignee events use hours or minutes depending
    # on whether the current assignee is a focused user.
    status_times   = generate_event_times(issue_created, num_status_trans,
                                          min_hours_between, max_hours_between)
    assignee_times = generate_assignee_times(issue_created, assignee_chain,
                                             min_hours_between, max_hours_between,
                                             min_focused_user_minutes, max_focused_user_minutes)

    # Final state
    final_status_id, final_status_name = STATUSES[status_chain[-1][1]]
    final_assignee = assignee_chain[-1][1] if assignee_chain else initial_user

    # --- Build individual changelog entries ---
    # Each entry: (datetime, author_name, items_list)
    raw_entries = []

    for (from_id, to_id), ts in zip(status_chain, status_times):
        _, from_name = STATUSES[from_id]
        _, to_name   = STATUSES[to_id]

        assignee_at_time = _assignee_at(initial_user, assignee_chain, assignee_times, ts)

        items = [{
            "fieldType": "jira",
            "field": "status",
            "from": from_id,
            "fromString": from_name,
            "to": to_id,
            "toString": to_name,
        }]

        # Attach resolution when moving into Resolved/Closed
        if to_id in ("5", "6"):
            res_id, res_name = random.choice(RESOLUTIONS)
            items.append({
                "fieldType": "jira",
                "field": "resolution",
                "to": res_id,
                "toString": res_name,
            })

        raw_entries.append((ts, assignee_at_time, items))

    for (from_user, to_user), ts in zip(assignee_chain, assignee_times):
        items = [{
            "fieldType": "jira",
            "field": "assignee",
            "from": from_user["accountId"],
            "fromString": from_user["fullname"],
            "to": to_user["accountId"],
            "toString": to_user["fullname"],
        }]
        raw_entries.append((ts, from_user, items))

    # Sort all entries by timestamp (ascending – required by Jira)
    raw_entries.sort(key=lambda e: e[0])

    # The issue's "updated" must equal the last changelog timestamp
    last_ts = raw_entries[-1][0]

    # Determine resolution date (timestamp of first entry that sets a resolution)
    resolution_date = None
    resolution_name = None
    for ts, _, items in raw_entries:
        for item in items:
            if item["field"] == "resolution":
                resolution_date = ts
                resolution_name = item["toString"]
                break
        if resolution_date:
            break

    # --- Assemble history list ---
    history = []
    for ts, author, items in raw_entries:
        history.append({
            "author": author["name"],
            "created": fmt_dt(ts),
            "items": items,
        })

    # --- Build issue dict ---
    issue = {
        "summary": generate_summary(min_summary_words, max_summary_words),
        "reporter": reporter["accountId"],
        "assignee": final_assignee["accountId"],
        "issueType": issue_type,
        "priority": priority,
        "created": fmt_dt(issue_created),
        "updated": fmt_dt(last_ts),
        "status": final_status_name,
        "history": history,
    }

    if resolution_name:
        issue["resolution"] = resolution_name
        issue["resolutionDate"] = fmt_dt(resolution_date)

    return issue


def _assignee_at(initial_user: dict,
                 assignee_chain: list[tuple[dict, dict]],
                 assignee_times: list[datetime],
                 at_time: datetime) -> dict:
    """Return who is assigned at a given point in time."""
    current = initial_user
    for (from_user, to_user), ts in zip(assignee_chain, assignee_times):
        if ts <= at_time:
            current = to_user
        else:
            break
    return current


# ---------------------------------------------------------------------------
# Top-level builder
# ---------------------------------------------------------------------------

def build_import(num_issues: int,
                 start_date: datetime,
                 num_months: int,
                 min_status_trans: int,
                 max_status_trans: int,
                 min_assignee_trans: int,
                 max_assignee_trans: int,
                 min_hours_between: float,
                 max_hours_between: float,
                 focused_user_ratio: float,
                 min_focused_user_minutes: float,
                 max_focused_user_minutes: float,
                 project_key: str,
                 project_name: str,
                 last_user_account_id: str = None,
                 min_summary_words: int = 4,
                 max_summary_words: int = 8) -> dict:

    user_records = [
        {
            "name": u["name"],
            "accountId": u["accountId"],
            "groups": ["jira-administrators", "jira-core-users",
                       "jira-servicedesk-users", "jira-software-users"],
            "active": "true",
            "email": u["email"],
            "fullname": u["fullname"],
        }
        for u in USERS + FOCUSED_USERS
    ]

    last_user = None
    if last_user_account_id is not None:
        last_user = next(u for u in USERS + FOCUSED_USERS if u["accountId"] == last_user_account_id)

    creation_dates = distribute_issues_over_months(num_issues, num_months, start_date)

    issues = [
        generate_issue(i, creation_dates[i],
                       min_status_trans, max_status_trans,
                       min_assignee_trans, max_assignee_trans,
                       min_hours_between, max_hours_between,
                       focused_user_ratio,
                       min_focused_user_minutes, max_focused_user_minutes,
                       min_summary_words, max_summary_words,
                       last_user=last_user)
        for i in range(num_issues)
    ]

    return {
        "users": user_records,
        "projects": [
            {
                "name": project_name,
                "key": project_key,
                "description": "Generated project for Jira Cloud import testing",
                "lead": "admin",
                "type": "business",
                "issues": issues,
            }
        ],
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a Jira Cloud import JSON file with randomised issues.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--num-issues",               type=int,   default=5,
                        help="Total number of issues to generate")
    parser.add_argument("--start-date",               type=str,   default="2024-01-01",
                        help="Earliest possible issue created date (YYYY-MM-DD)")
    parser.add_argument("--num-months",               type=int,   default=24,
                        help="Number of months to spread issues over")
    parser.add_argument("--min-status-transitions",   type=int,   default=2,
                        help="Minimum number of status transitions per issue")
    parser.add_argument("--max-status-transitions",   type=int,   default=5,
                        help="Maximum number of status transitions per issue")
    parser.add_argument("--min-assignee-transitions", type=int,   default=2,
                        help="Minimum number of assignee transitions per issue")
    parser.add_argument("--max-assignee-transitions", type=int,   default=5,
                        help="Maximum number of assignee transitions per issue")
    parser.add_argument("--min-hours-between",        type=float, default=1.0,
                        help="Minimum hours between consecutive changelog entries (non-focused-user slots)")
    parser.add_argument("--max-hours-between",        type=float, default=48.0,
                        help="Maximum hours between consecutive changelog entries (non-focused-user slots)")
    parser.add_argument("--focused-user-ratio",          type=float, default=0.20,
                        help="Probability (0.00-1.00) that the next assignee is a focused user")
    parser.add_argument("--min-minutes-focused-user",    type=float, default=15.0,
                        help="Minimum minutes a focused user stays assigned before reassignment")
    parser.add_argument("--max-minutes-focused-user",    type=float, default=120.0,
                        help="Maximum minutes a focused user stays assigned before reassignment")
    parser.add_argument("--output",                   type=str,   default="JiraCloudImport_generated.json",
                        help="Output file path")
    parser.add_argument("--seed",                     type=int,   default=None,
                        help="Random seed for reproducible output")
    parser.add_argument("--project-key",              type=str,   default="SDP",
                        help="Jira project key")
    parser.add_argument("--project-name",             type=str,   default="Sample Data Project",
                        help="Jira project name")
    parser.add_argument("--min-summary-words",        type=int,   default=4,
                        help="Minimum number of random words in an issue summary")
    parser.add_argument("--max-summary-words",        type=int,   default=8,
                        help="Maximum number of random words in an issue summary")
    parser.add_argument("--last-user-account-id",     type=str,   default=None,
                        help="accountId of a user who will be the final assignee on every generated issue")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.num_issues < 1:
        raise ValueError("--num-issues must be >= 1")
    try:
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d").replace(tzinfo=TZ_OFFSET)
    except ValueError:
        raise ValueError("--start-date must be in YYYY-MM-DD format")
    if args.num_months < 1:
        raise ValueError("--num-months must be >= 1")
    if args.min_status_transitions < 1:
        raise ValueError("--min-status-transitions must be >= 1")
    if args.max_status_transitions < args.min_status_transitions:
        raise ValueError("--max-status-transitions must be >= --min-status-transitions")
    if args.min_assignee_transitions < 1:
        raise ValueError("--min-assignee-transitions must be >= 1")
    if args.max_assignee_transitions < args.min_assignee_transitions:
        raise ValueError("--max-assignee-transitions must be >= --min-assignee-transitions")
    if args.min_hours_between <= 0:
        raise ValueError("--min-hours-between must be > 0")
    if args.max_hours_between < args.min_hours_between:
        raise ValueError("--max-hours-between must be >= --min-hours-between")
    if not (0.0 <= args.focused_user_ratio <= 1.0):
        raise ValueError("--focused-user-ratio must be between 0.00 and 1.00")
    if args.min_minutes_focused_user <= 0:
        raise ValueError("--min-minutes-focused-user must be > 0")
    if args.max_minutes_focused_user < args.min_minutes_focused_user:
        raise ValueError("--max-minutes-focused-user must be >= --min-minutes-focused-user")
    if args.min_summary_words < 1:
        raise ValueError("--min-summary-words must be >= 1")
    if args.max_summary_words < args.min_summary_words:
        raise ValueError("--max-summary-words must be >= --min-summary-words")
    if args.last_user_account_id is not None:
        known_ids = {u["accountId"] for u in USERS + FOCUSED_USERS}
        if args.last_user_account_id not in known_ids:
            raise ValueError(f"--last-user-account-id '{args.last_user_account_id}' does not match any known user")

    if args.seed is not None:
        random.seed(args.seed)
        _SUMMARY_RNG.seed(args.seed)
        print(f"[info] Using random seed: {args.seed}")

    print(f"[info] Generating {args.num_issues} issues "
          f"(start: {args.start_date}, months: {args.num_months}, "
          f"status transitions: {args.min_status_transitions}-{args.max_status_transitions}, "
          f"assignee transitions: {args.min_assignee_transitions}-{args.max_assignee_transitions}, "
          f"hours between entries: {args.min_hours_between}-{args.max_hours_between}, "
          f"focused-user ratio: {args.focused_user_ratio:.2f}, "
          f"focused-user minutes: {args.min_minutes_focused_user}-{args.max_minutes_focused_user}, "
          f"summary words: {args.min_summary_words}-{args.max_summary_words}) ...")

    data = build_import(
        num_issues=args.num_issues,
        start_date=start_date,
        num_months=args.num_months,
        min_status_trans=args.min_status_transitions,
        max_status_trans=args.max_status_transitions,
        min_assignee_trans=args.min_assignee_transitions,
        max_assignee_trans=args.max_assignee_transitions,
        min_hours_between=args.min_hours_between,
        max_hours_between=args.max_hours_between,
        focused_user_ratio=args.focused_user_ratio,
        min_focused_user_minutes=args.min_minutes_focused_user,
        max_focused_user_minutes=args.max_minutes_focused_user,
        project_key=args.project_key,
        project_name=args.project_name,
        last_user_account_id=args.last_user_account_id,
        min_summary_words=args.min_summary_words,
        max_summary_words=args.max_summary_words,
    )

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    total_entries = sum(
        len(issue["history"])
        for issue in data["projects"][0]["issues"]
    )
    print(f"[info] Written {args.num_issues} issues "
          f"({total_entries} changelog entries) -> {args.output}")


if __name__ == "__main__":
    main()
