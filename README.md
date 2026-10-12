# Jira Cloud Import Data Generator

Generate realistic, randomised Jira Cloud import files with complete issue histories. Useful for seeding demo or test sites, load-testing Jira apps, and validating reports that depend on issue history, such as time-in-status, assignee-time or cycle-time analytics.

> Technical details (output file format, field values, workflow and data-integrity rules) are in [SPEC.md](SPEC.md).

---

## Capabilities

**Generate issues with full change history** — `generate_jira_import.py`

- Creates any number of issues with a random type, priority, reporter and a summary made of random words.
- Spreads issue creation dates across a configurable number of months, starting from a date you choose, with natural month-to-month variation.
- Builds a **status history** for each issue that follows a realistic workflow (Open → In Progress → Resolved/Closed, including reopen loops). Every issue ends resolved or closed, with a resolution set.
- Builds an **assignee history** for each issue, handing the issue between team members a configurable number of times.
- Supports **focused users**: short-lived assignees such as triage or support agents. You control how often they appear and how long (in minutes) they keep an issue, independently of regular users (in hours). A focused user is never the first or last assignee.
- Controls the time between history events, so issues can move fast (hours) or slowly (days).
- Can force one specific user to be the final assignee on every issue.
- Produces **reproducible output** with a random seed: the same seed and parameters always give the same file.
- Includes a built-in set of fictional users (all emails use the reserved `example.com` domain, all account IDs are randomly generated).

**Combine import files** — `combine_jira_imports.py`

- Merges two or more import files into a single file that can be imported in one pass.
- Removes duplicate users and keeps each user once.
- Merges issues that belong to the same project key into one project, and keeps different project keys as separate projects.
- Lets you build datasets with different characteristics per period (for example, more focused-user involvement in later months) by generating each period separately and combining the results.

---

## Requirements

- Python 3.9 or later
- No third-party packages (standard library only)

---

## Quick start

```bash
# Generate 5 issues with default settings -> JiraCloudImport_generated.json
python generate_jira_import.py

# Combine several generated files -> combined_import.json
python combine_jira_imports.py first.json second.json
```

Import the resulting JSON file in Jira Cloud via **Jira settings → System → External System Import → JSON**.

---

## `generate_jira_import.py` parameters

All parameters are optional.

### Volume and time range

| Parameter | Type | Default | Description |
|---|---|---|---|
| `--num-issues` | int | `5` | Number of issues to generate |
| `--start-date` | date | `2024-01-01` | Earliest issue creation date (`YYYY-MM-DD`) |
| `--num-months` | int | `24` | Number of months to spread issue creation over |

### Issue history

| Parameter | Type | Default | Description |
|---|---|---|---|
| `--min-status-transitions` | int | `2` | Minimum status changes per issue |
| `--max-status-transitions` | int | `5` | Maximum status changes per issue |
| `--min-assignee-transitions` | int | `2` | Minimum assignee changes per issue |
| `--max-assignee-transitions` | int | `5` | Maximum assignee changes per issue |
| `--min-hours-between` | float | `1.0` | Minimum hours between consecutive history events (while a regular user is assigned) |
| `--max-hours-between` | float | `48.0` | Maximum hours between consecutive history events (while a regular user is assigned) |
| `--last-user-account-id` | str | *(none)* | Account ID of a user who becomes the final assignee on every issue |

### Focused users

| Parameter | Type | Default | Description |
|---|---|---|---|
| `--focused-user-ratio` | float | `0.20` | Probability (`0.00`–`1.00`) that the next assignee is a focused user |
| `--min-minutes-focused-user` | float | `15.0` | Minimum minutes a focused user keeps an issue before it is reassigned |
| `--max-minutes-focused-user` | float | `120.0` | Maximum minutes a focused user keeps an issue before it is reassigned |

### Content and output

| Parameter | Type | Default | Description |
|---|---|---|---|
| `--project-key` | str | `SDP` | Jira project key |
| `--project-name` | str | `Sample Data Project` | Jira project name |
| `--min-summary-words` | int | `4` | Minimum number of words in an issue summary |
| `--max-summary-words` | int | `8` | Maximum number of words in an issue summary |
| `--seed` | int | *(none)* | Random seed for reproducible output |
| `--output` | path | `JiraCloudImport_generated.json` | Output file path |

Run `python generate_jira_import.py --help` to see the same list from the command line.

---

## `combine_jira_imports.py` parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `FILE [FILE ...]` | paths | *(required)* | Two or more import files to combine, in order |
| `--output`, `-o` | path | `combined_import.json` | Output file path |

---

## Examples

### Generate

```bash
# Defaults: 5 issues spread over 24 months from 2024-01-01
python generate_jira_import.py

# Reproducible: the same seed always produces the same file
python generate_jira_import.py --num-issues 10 --seed 42

# A specific project
python generate_jira_import.py --num-issues 15 --project-key DEMO --project-name "Demo Data Project"

# Fast-moving issues with frequent, short triage/support hand-offs
python generate_jira_import.py \
  --num-issues 20 \
  --start-date 2025-01-01 \
  --num-months 3 \
  --min-hours-between 1 \
  --max-hours-between 8 \
  --focused-user-ratio 0.50 \
  --min-minutes-focused-user 5 \
  --max-minutes-focused-user 30 \
  --output fast_moving.json

# Long-running issues with many status changes and no focused users
python generate_jira_import.py \
  --num-issues 30 \
  --min-status-transitions 4 \
  --max-status-transitions 10 \
  --min-hours-between 24 \
  --max-hours-between 120 \
  --focused-user-ratio 0 \
  --output long_running.json

# Every issue ends up assigned to the same user (Emre)
python generate_jira_import.py --num-issues 10 --last-user-account-id 9c2d12ca4c5fb2dfb3ab4545
```

### Combine

```bash
# Combine two files into combined_import.json
python combine_jira_imports.py fast_moving.json long_running.json

# Combine every file that matches a pattern, with a custom output name
python combine_jira_imports.py demo_import_*.json --output demo_full.json
```

### End to end: a dataset that changes over time

Generate one file per half-year, with focused users becoming more involved each period, then combine them into a single import for the `DEMO` project:

```bash
python generate_jira_import.py --project-key DEMO --project-name "Demo Data Project" --seed 95 --num-issues 20 --start-date 2023-07-01 --num-months 6 --focused-user-ratio 0.10 --output demo_import_2023H2.json
python generate_jira_import.py --project-key DEMO --project-name "Demo Data Project" --seed 95 --num-issues 40 --start-date 2024-01-01 --num-months 6 --focused-user-ratio 0.20 --output demo_import_2024H1.json
python generate_jira_import.py --project-key DEMO --project-name "Demo Data Project" --seed 95 --num-issues 60 --start-date 2024-07-01 --num-months 6 --focused-user-ratio 0.35 --output demo_import_2024H2.json
python generate_jira_import.py --project-key DEMO --project-name "Demo Data Project" --seed 95 --num-issues 80 --start-date 2025-01-01 --num-months 6 --focused-user-ratio 0.50 --output demo_import_2025H1.json

python combine_jira_imports.py demo_import_2023H2.json demo_import_2024H1.json demo_import_2024H2.json demo_import_2025H1.json --output demo_import_all.json
```

The result is one `DEMO` project with 200 issues spanning two years.

---

## Repository contents

| File | Purpose |
|---|---|
| [generate_jira_import.py](generate_jira_import.py) | Generates a Jira Cloud import file with randomised issues and history |
| [combine_jira_imports.py](combine_jira_imports.py) | Merges several import files into one |
| [SPEC.md](SPEC.md) | Output format, field values, workflow and data-integrity rules |
| README.md | This file |
