# Technical Specification

This document describes the output produced by the scripts in this repository and the rules the generated data follows. For an overview of capabilities, parameters and examples, see [README.md](README.md).

- [1. File format](#1-file-format)
- [2. Built-in users](#2-built-in-users)
- [3. Reference values](#3-reference-values)
- [4. Generation behaviour](#4-generation-behaviour)
- [5. Data-integrity rules](#5-data-integrity-rules)
- [6. Combining files](#6-combining-files)
- [7. Runtime and validation](#7-runtime-and-validation)

---

## 1. File format

Both scripts write a single UTF-8 JSON file (indented by 2 spaces, non-ASCII characters kept as-is) in the Jira Cloud **JSON importer** format.

### 1.1 Top level

```json
{
  "users":    [ ... ],
  "projects": [ ... ]
}
```

### 1.2 `users[]`

```json
{
  "name": "ahmet",
  "accountId": "cf7f00d16f8f6eb353b7daee",
  "groups": ["jira-administrators", "jira-core-users", "jira-servicedesk-users", "jira-software-users"],
  "active": "true",
  "email": "ahmet@example.com",
  "fullname": "Ahmet"
}
```

| Field | Type | Notes |
|---|---|---|
| `name` | string | Username. Referenced by `history[].author`. |
| `accountId` | string | 24-character hex ID. Referenced by `reporter`, `assignee` and assignee changelog items. |
| `groups` | string[] | Always the four groups shown above. |
| `active` | string | Always the string `"true"`. |
| `email` | string | Always on the `example.com` domain. |
| `fullname` | string | Display name. Used in `fromString` / `toString` of assignee changelog items. |

### 1.3 `projects[]`

The generator writes exactly one project per file.

```json
{
  "name": "Sample Data Project",
  "key": "SDP",
  "description": "Generated project for Jira Cloud import testing",
  "lead": "admin",
  "type": "business",
  "issues": [ ... ]
}
```

| Field | Source |
|---|---|
| `name` | `--project-name` |
| `key` | `--project-key` |
| `description` | Fixed text |
| `lead` | Fixed: `admin` |
| `type` | Fixed: `business` |

### 1.4 `issues[]`

| Field | Type | Notes |
|---|---|---|
| `summary` | string | Random words from a built-in word list, first letter capitalised. Word count is in `[--min-summary-words, --max-summary-words]`. |
| `reporter` | string | `accountId` of a regular user. |
| `assignee` | string | `accountId` of the final assignee (the `to` of the last assignee changelog item). |
| `issueType` | string | See [3.1](#31-issue-fields). |
| `priority` | string | See [3.1](#31-issue-fields). |
| `created` | string | Timestamp, see [5.4](#54-general). |
| `updated` | string | Equal to the timestamp of the last changelog entry. |
| `status` | string | Final status name: `Resolved` or `Closed`. |
| `history` | object[] | Changelog, see [1.5](#15-history). |
| `resolution` | string | Name of the resolution set by the final status change. |
| `resolutionDate` | string | Timestamp of the final status change (the entry that sets the resolution). |

### 1.5 `history[]`

Each entry is one point-in-time change:

```json
{
  "author": "emre",
  "created": "2025-09-09T13:13:01+0300",
  "items": [ ... ]
}
```

`author` is a `name` from `users[]`. Each entry holds exactly one of these change types.

**Status change** (optionally followed by a resolution item in the same entry):

```json
{ "fieldType": "jira", "field": "status", "from": "1", "fromString": "Open", "to": "3", "toString": "In Progress" }
```

**Resolution** (only together with a status change into Resolved or Closed):

```json
{ "fieldType": "jira", "field": "resolution", "to": "test-res-1", "toString": "Won't Do" }
```

**Assignee change** (`from` / `to` are `accountId`s, `fromString` / `toString` are `fullname`s):

```json
{ "fieldType": "jira", "field": "assignee", "from": "9c2d12ca4c5fb2dfb3ab4545", "fromString": "Emre", "to": "070b051a09adbbc806c6e789", "toString": "Ömer" }
```

### 1.6 Complete issue example

Generated with `--num-issues 1 --seed 7`, 3 status and 3 assignee transitions, `--focused-user-ratio 0.5`:

```json
{
  "summary": "Copper lunar thunder banner birch planet",
  "reporter": "c49c89193c6c83813d52dc79",
  "assignee": "9c2d12ca4c5fb2dfb3ab4545",
  "issueType": "Improvement",
  "priority": "Highest",
  "created": "2025-09-08T00:04:09+0300",
  "updated": "2025-09-12T13:04:18+0300",
  "status": "Closed",
  "history": [
    { "author": "ahmet", "created": "2025-09-08T23:56:40+0300",
      "items": [{ "fieldType": "jira", "field": "assignee", "from": "cf7f00d16f8f6eb353b7daee", "fromString": "Ahmet", "to": "9c2d12ca4c5fb2dfb3ab4545", "toString": "Emre" }] },
    { "author": "emre", "created": "2025-09-09T13:13:01+0300",
      "items": [{ "fieldType": "jira", "field": "status", "from": "1", "fromString": "Open", "to": "3", "toString": "In Progress" }] },
    { "author": "emre", "created": "2025-09-10T10:50:54+0300",
      "items": [{ "fieldType": "jira", "field": "assignee", "from": "9c2d12ca4c5fb2dfb3ab4545", "fromString": "Emre", "to": "070b051a09adbbc806c6e789", "toString": "Ömer" }] },
    { "author": "omer", "created": "2025-09-11T04:56:08+0300",
      "items": [{ "fieldType": "jira", "field": "status", "from": "3", "fromString": "In Progress", "to": "1", "toString": "Open" }] },
    { "author": "omer", "created": "2025-09-12T06:29:15+0300",
      "items": [{ "fieldType": "jira", "field": "assignee", "from": "070b051a09adbbc806c6e789", "fromString": "Ömer", "to": "9c2d12ca4c5fb2dfb3ab4545", "toString": "Emre" }] },
    { "author": "emre", "created": "2025-09-12T13:04:18+0300",
      "items": [
        { "fieldType": "jira", "field": "status", "from": "1", "fromString": "Open", "to": "6", "toString": "Closed" },
        { "fieldType": "jira", "field": "resolution", "to": "test-res-1", "toString": "Won't Do" }
      ] }
  ],
  "resolution": "Won't Do",
  "resolutionDate": "2025-09-12T13:04:18+0300"
}
```

---

## 2. Built-in users

All users are fictional. Emails use the reserved `example.com` domain and account IDs are random.

### 2.1 Regular users

Can be reporter, initial assignee, any intermediate assignee and final assignee.

| name | fullname | accountId |
|---|---|---|
| `ahmet` | Ahmet | `cf7f00d16f8f6eb353b7daee` |
| `emre` | Emre | `9c2d12ca4c5fb2dfb3ab4545` |
| `oguzhan` | Oğuzhan | `15b27e2d2ac76ba5ec5aa299` |
| `berk` | Berk | `a373f3b0df91d8086d0c2728` |
| `orkun` | Orkun | `c49c89193c6c83813d52dc79` |
| `omer` | Ömer | `070b051a09adbbc806c6e789` |

### 2.2 Focused users

Short-lived assignees (triage/support). Never the reporter, initial assignee or final assignee, unless `--last-user-account-id` explicitly names one as the final assignee.

| name | fullname | accountId |
|---|---|---|
| `triage_agent` | Triage Agent | `52bae79fee106ecb689df363` |
| `support1_agent` | Support Agent 1 | `1263e99cc41b88a829350e7d` |
| `support2_agent` | Support Agent 2 | `7e8148f90daa359198c98e41` |

Every generated file contains all 9 users, whether or not they appear in an issue.

---

## 3. Reference values

### 3.1 Issue fields

Each value is chosen with equal probability.

| Field | Values |
|---|---|
| `issueType` | Task, Bug, Story, Epic, Improvement |
| `priority` | Highest, High, Medium, Low, Lowest |

### 3.2 Statuses

| ID | Name | Terminal |
|---|---|---|
| `1` | Open | |
| `3` | In Progress | |
| `4` | Reopened | |
| `5` | Resolved | ✓ |
| `6` | Closed | ✓ |

### 3.3 Resolutions

| ID | Name | Weight |
|---|---|---|
| `1` | Resolved | 3 / 6 |
| `test-res-1` | Won't Do | 1 / 6 |
| `test-res-2` | Duplicate | 1 / 6 |
| `test-res-3` | Cannot Reproduce | 1 / 6 |

---

## 4. Generation behaviour

### 4.1 Creation dates

The `[--start-date, --start-date + --num-months)` window is split into calendar months. Each month gets a random weight in `[0.8, 1.2]`, issues are allocated to months in proportion to those weights (largest-remainder rounding, so the total is exact), and each issue gets a uniformly random second within its month. The issue list is then shuffled. Timestamps use a fixed `+0300` offset.

Only `created` is bounded by the window; history events after creation may extend beyond it.

### 4.2 Status chain

- Starts at `Open` (`1`); the initial status is implicit and not written to `history`.
- The number of transitions is uniform in `[--min-status-transitions, --max-status-transitions]`.
- Allowed transitions:

  ```
  Open        → In Progress, Resolved, Closed
  In Progress → Open, Reopened, Resolved
  Reopened    → In Progress, Resolved
  Resolved    → Closed, Reopened
  Closed      → Reopened
  ```

- Non-final transitions never enter a terminal status, so issues move only between Open, In Progress and Reopened until the last transition.
- The final transition always lands in Resolved or Closed and carries a randomly chosen resolution item in the same entry. Each issue therefore has exactly one resolution item.

### 4.3 Assignee chain

- The initial assignee is a random regular user and is implicit (only visible as the `from` of the first assignee change).
- The number of transitions is uniform in `[--min-assignee-transitions, --max-assignee-transitions]`.
- For every transition except the last, the next assignee is a focused user with probability `--focused-user-ratio`, otherwise a regular user. The last transition always goes to a regular user.
- The next assignee is always different from the current one (when the pool allows).
- `--last-user-account-id` replaces the target of the final transition with the given user. It must match a built-in `accountId`, otherwise the script exits with an error.

### 4.4 Timing

Status and assignee timelines are built independently from `created`, then merged and sorted by timestamp.

| Timeline | Gap before each event |
|---|---|
| Status | Uniform in `[--min-hours-between, --max-hours-between]` hours |
| Assignee, while a regular user is assigned | Uniform in `[--min-hours-between, --max-hours-between]` hours |
| Assignee, while a focused user is assigned | Uniform in `[--min-minutes-focused-user, --max-minutes-focused-user]` minutes |

Gaps have one-second resolution.

### 4.5 Changelog authors

| Change | Author |
|---|---|
| Status change | The user assigned at that moment |
| Assignee change | The user being unassigned (`from`) |

### 4.6 Randomness and reproducibility

`--seed` seeds two independent generators: one for dates, users, statuses and timing, and a separate one for summaries. Changing the summary logic or word counts therefore does not change any other part of the output for the same seed. Without `--seed`, every run is different.

---

## 5. Data-integrity rules

These rules hold for generated files and should be respected in any hand-made or edited import file.

### 5.1 Dates

1. `history[]` entries are in ascending `created` order.
2. Every changelog entry is later than the issue's `created`.
3. `updated` equals the timestamp of the last changelog entry, so no entry is later than `updated`.
4. `resolutionDate` equals the timestamp of the entry that sets the resolution, which is the last entry carrying a status change.

> Status and assignee timelines are generated independently, so two entries can in rare cases share the exact same second. Jira accepts this, but tools that require strictly increasing timestamps should check for it.

### 5.2 Status workflow

5. The implicit starting status is `Open` (`1`).
6. Every transition follows the allowed paths in [4.2](#42-status-chain).
7. The chain is continuous: each status item's `from` equals the previous status item's `to` (or `1` for the first).
8. The final status is terminal (Resolved or Closed), and the issue-level `status` equals the `toString` of the last status item.
9. A resolution item appears in the same entry as the transition into Resolved or Closed.

### 5.3 Assignees

10. Assignee item `from` / `to` values are `accountId`s, and `fromString` / `toString` are the matching `fullname`s.
11. The chain is continuous: each assignee item's `from` equals the previous one's `to`.
12. The issue-level `assignee` equals the `to` of the last assignee item. `reporter` and `assignee` are `accountId`s.

### 5.4 General

13. Timestamps use the format `YYYY-MM-DDTHH:MM:SS+0300` (ISO 8601 with a fixed offset). Jira also accepts epoch milliseconds, but the generator does not produce them.
14. Every `author` matches a `name` in `users[]`, and every `accountId` reference matches a user in `users[]`.

---

## 6. Combining files

`combine_jira_imports.py` reads each input file and writes one file in the same format.

| Section | Merge rule |
|---|---|
| `users` | Deduplicated by `accountId`; the first occurrence wins. |
| `projects` | Grouped by `key`. Project metadata (`name`, `description`, `lead`, `type`) comes from the first file that defines the key. Issues from all files with the same key are concatenated in input-file order. Projects with different keys stay separate, in order of first appearance. |

Notes:

- Issues are not deduplicated. Passing the same file twice duplicates its issues.
- Issues are not re-sorted by date; they keep file order.
- A missing `users` or `projects` section in an input file is treated as empty.
- At least two input files are required, and every file must exist; otherwise the script exits with status `1` and an `[error]` message on stderr.
- On success it prints the number of users, projects and issues written.

---

## 7. Runtime and validation

### 7.1 Requirements

Python 3.9 or later, standard library only.

### 7.2 Parameter validation (`generate_jira_import.py`)

The script stops with an error if any of these do not hold:

| Rule |
|---|
| `--num-issues` ≥ 1 |
| `--start-date` is a valid `YYYY-MM-DD` date |
| `--num-months` ≥ 1 |
| `--min-status-transitions` ≥ 1 and `--max-status-transitions` ≥ `--min-status-transitions` |
| `--min-assignee-transitions` ≥ 1 and `--max-assignee-transitions` ≥ `--min-assignee-transitions` |
| `--min-hours-between` > 0 and `--max-hours-between` ≥ `--min-hours-between` |
| `0.00` ≤ `--focused-user-ratio` ≤ `1.00` |
| `--min-minutes-focused-user` > 0 and `--max-minutes-focused-user` ≥ `--min-minutes-focused-user` |
| `--min-summary-words` ≥ 1 and `--max-summary-words` ≥ `--min-summary-words` |
| `--last-user-account-id`, if given, matches a built-in user |

### 7.3 Console output

```
[info] Using random seed: 42
[info] Generating 10 issues (start: 2024-01-01, months: 24, status transitions: 2-5, assignee transitions: 2-5, hours between entries: 1.0-48.0, focused-user ratio: 0.20, focused-user minutes: 15.0-120.0, summary words: 4-8) ...
[info] Written 10 issues (63 changelog entries) -> JiraCloudImport_generated.json
```

The first line appears only when `--seed` is given.
