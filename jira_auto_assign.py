#!/usr/bin/env python3
"""
Jira Auto-Assign Script
Scans a board for unassigned "Ready for Engineer" tickets and assigns them
to the team member with the most available capacity this week.
"""

import sys
import json
import copy
import math
import time
import getpass
from datetime import datetime, timedelta, timezone
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
import base64
import re
import os


# ---------------------------------------------------------------------------
# Constants — loaded from environment variables
# ---------------------------------------------------------------------------

JIRA_BASE_URL = os.environ.get("JIRA_BASE_URL", "")
JIRA_EMAIL = os.environ.get("JIRA_EMAIL", "")
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN", "")
JIRA_BOARD_URL = os.environ.get("JIRA_BOARD_URL", "")
JIRA_TEAM_URL = os.environ.get("JIRA_TEAM_URL", "")

WEEKLY_CAPACITY_POINTS = int(os.environ.get("WEEKLY_CAPACITY_POINTS") or "10")
OVERLOAD_THRESHOLD = float(os.environ.get("OVERLOAD_THRESHOLD") or "0.70")

# Comma-separated emails/accountIds in env, e.g.:
#   EXCLUDE_MEMBERS="alice@co.com,bob@co.com"
EXCLUDE_MEMBERS: list[str] = [
    e.strip() for e in os.environ.get("EXCLUDE_MEMBERS", "").split(",") if e.strip()
]

LOW_PRIORITY_MEMBERS: list[str] = [
    e.strip()
    for e in os.environ.get("LOW_PRIORITY_MEMBERS", "").split(",")
    if e.strip()
]
LOW_PRIORITY_THRESHOLD = float(os.environ.get("LOW_PRIORITY_THRESHOLD") or "0.30")

ON_LEAVE_THRESHOLD = float(os.environ.get("ON_LEAVE_THRESHOLD") or "0.10")

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
# Comma-separated channel IDs, e.g.: SLACK_CHANNEL_IDS="C066UGGS2PJ,C07SPAT5RM0"
SLACK_CHANNEL_IDS: list[str] = [
    e.strip() for e in os.environ.get("SLACK_CHANNEL_IDS", "").split(",") if e.strip()
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def parse_board_url(url: str) -> tuple[str, str, str]:
    """
    Parse a Jira board URL and return (base_url, project_key, board_id).

    Supports both formats:
      https://org.atlassian.net/jira/software/c/projects/KEY/boards/1234
      https://org.atlassian.net/secure/RapidBoard.jspa?rapidView=1234
    """
    url = url.strip()

    # Format: /projects/KEY/boards/ID
    m = re.search(
        r"(https://[^/]+)/jira/software(?:/[^/]+)?/projects/([^/]+)/boards/(\d+)",
        url,
    )
    if m:
        return m.group(1), m.group(2), m.group(3)

    # Format: ?rapidView=ID  (classic board URL, no project key in URL)
    m2 = re.search(r"(https://[^/]+).*[?&]rapidView=(\d+)", url)
    if m2:
        return m2.group(1), "", m2.group(2)

    # Bare numeric board ID
    if url.isdigit():
        return "", "", url

    raise ValueError(
        f"Could not parse board URL: {url!r}\n"
        "Expected format: https://org.atlassian.net/jira/software/c/projects/KEY/boards/ID"
    )


def parse_team_url(url: str) -> tuple[str, str, str]:
    """
    Parse an Atlassian Teams URL and return (org_id, team_id, cloud_id).

    Format:
      https://home.atlassian.com/o/<org_id>/people/team/<team_id>?cloudId=<cloud_id>
    """
    url = url.strip()
    m = re.search(
        r"home\.atlassian\.com/o/([^/]+)/people/team/([^?&#]+)",
        url,
    )
    if not m:
        return "", "", ""
    org_id = m.group(1)
    team_id = m.group(2)
    cloud_m = re.search(r"[?&]cloudId=([^&]+)", url)
    cloud_id = cloud_m.group(1) if cloud_m else ""
    return org_id, team_id, cloud_id


def make_auth_header(email: str, api_token: str) -> str:
    creds = base64.b64encode(f"{email}:{api_token}".encode()).decode()
    return f"Basic {creds}"


def _urlopen_with_retry(req: Request, retries: int = 3, backoff: float = 2.0):
    """urlopen with exponential backoff on transient network errors."""
    for attempt in range(1, retries + 1):
        try:
            return urlopen(req)
        except URLError as e:
            if attempt == retries:
                raise
            print(
                f"  [WARN] Network error ({e.reason}), retrying in {int(backoff**attempt)}s..."
            )
            time.sleep(backoff**attempt)


def jira_get(base_url: str, path: str, auth: str, params: dict | None = None) -> dict:
    url = f"{base_url.rstrip('/')}{path}"
    if params:
        url += "?" + urlencode(params)
    req = Request(
        url, headers={"Authorization": auth, "Content-Type": "application/json"}
    )
    try:
        with _urlopen_with_retry(req) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        body = e.read().decode()
        print(f"\n[ERROR] HTTP {e.code} on {url}\n{body}")
        sys.exit(1)


def jira_post(base_url: str, path: str, auth: str, payload: dict) -> dict:
    url = f"{base_url.rstrip('/')}{path}"
    data = json.dumps(payload).encode()
    req = Request(
        url,
        data=data,
        method="POST",
        headers={"Authorization": auth, "Content-Type": "application/json"},
    )
    try:
        with _urlopen_with_retry(req) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        body = e.read().decode()
        print(f"\n[ERROR] HTTP {e.code} on {url}\n{body}")
        sys.exit(1)


def jira_put(base_url: str, path: str, auth: str, payload: dict) -> None:
    url = f"{base_url.rstrip('/')}{path}"
    data = json.dumps(payload).encode()
    req = Request(
        url,
        data=data,
        method="PUT",
        headers={"Authorization": auth, "Content-Type": "application/json"},
    )
    try:
        with _urlopen_with_retry(req) as resp:
            return
    except HTTPError as e:
        body = e.read().decode()
        print(f"\n[ERROR] HTTP {e.code} assigning issue\n{body}")


def lookup_slack_user_id(token: str, email: str) -> str | None:
    """Return the Slack user ID for an email address, or None if not found."""
    if not token or not email:
        return None
    req = Request(
        f"https://slack.com/api/users.lookupByEmail?email={quote(email)}",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urlopen(req) as resp:
            data = json.loads(resp.read())
            if data.get("ok"):
                return data["user"]["id"]
    except Exception:
        pass
    return None


def build_slack_user_map(token: str, members: list[dict]) -> dict[str, str]:
    """
    Return {email: slack_user_id} for every member that can be resolved.
    Prints a warning for any email that can't be found.
    """
    mapping: dict[str, str] = {}
    for m in members:
        email = m.get("emailAddress", "")
        if not email:
            continue
        uid = lookup_slack_user_id(token, email)
        if uid:
            mapping[email] = uid
        else:
            print(f"  [WARN] Slack: no user found for {email}")
    return mapping


ON_LEAVE_EMOJI = "🌴"


def fetch_slack_status_emoji(token: str, user_id: str) -> str:
    """Return the user's current Slack status emoji, or empty string on failure."""
    if not token or not user_id:
        return ""
    req = Request(
        f"https://slack.com/api/users.profile.get?user={user_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urlopen(req) as resp:
            data = json.loads(resp.read())
            if data.get("ok"):
                return data.get("profile", {}).get("status_emoji", "")
    except Exception:
        pass
    return ""


def detect_on_leave_from_slack(
    token: str, members_workload: list[dict], user_map: dict[str, str]
) -> None:
    """
    Check each member's Slack status. If it contains 🌴, mark them on_leave=True.
    Mutates members_workload in place.
    """
    for m in members_workload:
        email = m.get("emailAddress", "")
        uid = user_map.get(email)
        if not uid:
            continue
        emoji = fetch_slack_status_emoji(token, uid)
        if ON_LEAVE_EMOJI in emoji:
            if not m.get("on_leave"):
                print(
                    f"  🌴 {m.get('displayName', email)} is on leave (detected from Slack status)."
                )
                m["on_leave"] = True


def slack_mention(email: str, display: str, user_map: dict[str, str]) -> str:
    """Return <@USER_ID> if resolvable, otherwise fall back to display name."""
    uid = user_map.get(email)
    return f"<@{uid}>" if uid else display


def send_slack_message(
    token: str, channel: str, text: str, blocks: list | None = None
) -> None:
    """Post a message to Slack via chat.postMessage."""
    if not token or not channel:
        return
    payload: dict = {
        "channel": channel,
        "text": text,
        "username": "Weekly Summary Bot",
        "icon_emoji": ":robot_face:",
    }
    if blocks:
        payload["blocks"] = blocks
    data = json.dumps(payload).encode()
    req = Request(
        "https://slack.com/api/chat.postMessage",
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(req) as resp:
            result = json.loads(resp.read())
            if not result.get("ok"):
                print(f"  [WARN] Slack error: {result.get('error', 'unknown')}")
            else:
                print(f"  Slack notification sent to {channel}.")
    except Exception as exc:
        print(f"  [WARN] Could not send Slack message: {exc}")


def _workload_status_emoji(m: dict) -> str:
    if m.get("excluded"):
        return ":no_entry:"
    if m.get("on_leave") and m["overloaded"]:
        return ":beach_with_umbrella: Capped"
    if m.get("on_leave"):
        return ":beach_with_umbrella:"
    if m.get("low_priority") and m["overloaded"]:
        return ":yellow-card: Capped"
    if m["overloaded"]:
        return ":red_circle:"
    if m.get("low_priority"):
        return ":yellow_card:"
    return ":green_circle:"


_FUNNY_MESSAGES = [
    "🤖 Beep boop. I have consulted the ancient scrolls of Jira and distributed suffering evenly.",
    "🎲 Tickets have been assigned! No engineers were harmed in the making of this message. Probably.",
    "📬 Your friendly neighbourhood bot has done the dirty work so your SM doesn't have to.",
    "🧙 The algorithm has spoken. Fate is sealed. Resistance is futile.",
    "🎯 Tickets assigned! Remember: estimation is an art, not a science. Good luck with that.",
    "🏋️ Fresh tickets, just delivered! Think of it as a workout for your brain.",
    "🎰 The ticket lottery results are in! Everyone's a winner! (Results may vary.)",
    "☕ Grab a coffee. You're going to need it. Tickets have landed.",
    "📦 Tickets assigned with surgical precision by a robot who has never written a line of code.",
    "🚀 Houston, we have assignments. Godspeed, engineers.",
    "🍕 Tickets distributed more fairly than pizza at a team lunch.",
    "🎪 Step right up! Your Jira tickets await! No refunds, no exchanges.",
]

import random as _random


def build_slack_blocks(
    assignments: list[
        tuple[str, str, str]
    ],  # (ticket_key, assignee_label, assignee_email)
    skipped: list[str],
    base_url: str,
    week_start: str,
    week_end: str,
    members_workload: list[dict] | None = None,
    user_map: dict[str, str] | None = None,
) -> list:
    """Build Slack Block Kit payload for the assignment summary + workload table."""
    user_map = user_map or {}
    assignment_rows = "\n".join(
        f"• <{base_url}/browse/{key}|{key}>  →  {slack_mention(email, label, user_map)}"
        for key, label, email in assignments
    )

    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": _random.choice(_FUNNY_MESSAGES)},
        },
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Jira Auto-Assign Summary",
                "emoji": True,
            },
        },
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"Week {week_start} → {week_end}"}],
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": assignment_rows or "_No assignments made._",
            },
        },
    ]

    if skipped:
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f":warning: Skipped (no capacity): {', '.join(skipped)}",
                    }
                ],
            }
        )

    # Workload section
    if members_workload:
        blocks.append({"type": "divider"})
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*Team Workload This Week*"},
            }
        )
        workload_lines = []
        for m in sorted(
            members_workload, key=lambda x: x["total_week_points"], reverse=True
        ):
            pct = m["total_week_points"] / WEEKLY_CAPACITY_POINTS * 100
            filled = int(pct / 10)
            bar = "█" * filled + "░" * (10 - filled)
            emoji = _workload_status_emoji(m)
            mention = slack_mention(
                m.get("emailAddress", ""), member_label(m), user_map
            )
            ready = m.get("ready_tickets", [])
            ready_lines = "".join(
                f"\n     :ticket: <{base_url}/browse/{t['key']}|{t['key']}>: {t['summary']}"
                for t in ready
            )
            workload_lines.append(
                f"{emoji}  *{mention}*\n"
                f"     `{bar}` {pct:.0f}%  —  {m['total_week_points']:.1f} pts"
                f"  ({m['in_dev_points']:.1f} in dev)" + ready_lines
            )
        # Slack section blocks cap at ~3000 chars; split into chunks of 10 members
        chunk = "\n\n".join(workload_lines)
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": chunk},
            }
        )

    blocks.append({"type": "divider"})
    blocks.append(
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": "cc <!subteam^S06DU7PTYLW>"}],
        }
    )

    return blocks


# ---------------------------------------------------------------------------
# Jira queries
# ---------------------------------------------------------------------------


def get_board_project_key(base_url: str, auth: str, board_id: str) -> str:
    """Return the project key tied to a board."""
    data = jira_get(base_url, f"/rest/agile/1.0/board/{board_id}/configuration", auth)
    # The location field holds the project key for most board types
    location = data.get("location", {})
    key = location.get("projectKey") or location.get("key")
    if not key:
        # Fall back to parsing the filter JQL
        jql = data.get("filter", {}).get("query", "")
        for token in jql.split():
            if token.startswith("project"):
                key = jql.split("=")[1].strip().strip('"').split()[0]
                break
    if not key:
        print(
            "[WARN] Could not auto-detect project key from board. "
            "Some JQL queries will use board ID directly."
        )
    return key or ""


def fetch_unassigned_ready_tickets(
    base_url: str, auth: str, board_id: str, project_key: str = ""
) -> list[dict]:
    """Fetch all unassigned tickets in 'Ready for Engineer' status on the board."""
    # next-gen (team-managed) projects don't support `board =` in JQL;
    # use `project =` when we have the key, otherwise fall back to board filter.
    if project_key:
        scope = f'project = "{project_key}"'
    else:
        scope = f"board = {board_id}"

    jql = (
        f"{scope} "
        'AND status = "Ready for engineer" '
        "AND assignee is EMPTY "
        'AND issuetype != "Story" '
        "ORDER BY priority ASC, created ASC"
    )
    tickets = []
    start = 0
    page = 50
    while True:
        data = jira_get(
            base_url,
            "/rest/api/3/search/jql",
            auth,
            {
                "jql": jql,
                "startAt": start,
                "maxResults": page,
                "fields": "summary,priority,issuetype,customfield_10014,parent",
            },
        )
        issues = data.get("issues", [])
        tickets.extend(issues)
        if start + len(issues) >= data.get("total", 0):
            break
        start += page
    return tickets


def fetch_user_profile(base_url: str, auth: str, account_id: str) -> dict:
    """Return {accountId, displayName, emailAddress} for a single user."""
    try:
        data = jira_get(base_url, "/rest/api/3/user", auth, {"accountId": account_id})
        return {
            "accountId": account_id,
            "displayName": data.get("displayName", account_id),
            "emailAddress": data.get("emailAddress", ""),
        }
    except Exception:
        return {"accountId": account_id, "displayName": account_id, "emailAddress": ""}


def fetch_user_profiles_bulk(
    base_url: str, auth: str, account_ids: list[str]
) -> list[dict]:
    """
    Fetch profiles for multiple users in batches of 50 via /rest/api/3/user/bulk.
    Reduces N individual API calls to ceil(N/50) calls.
    Falls back to individual fetches if the bulk endpoint fails.
    """
    if not account_ids:
        return []
    profiles: list[dict] = []
    batch_size = 50
    for i in range(0, len(account_ids), batch_size):
        batch = account_ids[i : i + batch_size]
        query = urlencode(
            [("accountId", aid) for aid in batch] + [("maxResults", batch_size)]
        )
        url = f"{base_url.rstrip('/')}/rest/api/3/user/bulk?{query}"
        req = Request(
            url, headers={"Authorization": auth, "Content-Type": "application/json"}
        )
        try:
            with _urlopen_with_retry(req) as resp:
                data = json.loads(resp.read())
                for user in data.get("values", []):
                    profiles.append(
                        {
                            "accountId": user.get("accountId", ""),
                            "displayName": user.get("displayName", ""),
                            "emailAddress": user.get("emailAddress", ""),
                        }
                    )
        except HTTPError as e:
            body = e.read().decode()
            print(
                f"\n[WARN] Bulk user fetch HTTP {e.code} — falling back to individual fetches"
            )
            for aid in batch:
                profiles.append(fetch_user_profile(base_url, auth, aid))
    return profiles


def fetch_team_members_by_team_id(
    base_url: str, auth: str, org_id: str, team_id: str
) -> list[dict]:
    """
    Fetch members via the Atlassian Teams API (POST) using a parsed team URL.
    Endpoint: POST /gateway/api/public/teams/v1/org/<org_id>/teams/<team_id>/members
    Then enriches each member with displayName and emailAddress via the user API.
    """
    path = f"/gateway/api/public/teams/v1/org/{org_id}/teams/{team_id}/members"
    cursor = None
    account_ids = []
    while True:
        body = {"maxResults": 50}
        if cursor:
            body["cursor"] = cursor
        data = jira_post(base_url, path, auth, body)
        for m in data.get("results", []):
            acc = m.get("accountId") or m.get("memberId")
            if acc:
                account_ids.append(acc)
        cursor = data.get("nextCursor") or data.get("cursor")
        if not cursor or not data.get("results"):
            break

    return fetch_user_profiles_bulk(base_url, auth, account_ids)


def fetch_team_members(
    base_url: str,
    auth: str,
    team_input: str,
    org_id: str = "",
    team_id: str = "",
) -> list[dict]:
    """
    Try (in order):
      1. Atlassian Teams API by team_id (when URL was supplied)
      2. Jira group picker by name
      3. User search by name
    Returns list of {accountId, displayName} dicts.
    """
    # Attempt 1: Atlassian Teams API (URL-based)
    if org_id and team_id:
        try:
            members = fetch_team_members_by_team_id(base_url, auth, org_id, team_id)
            if members:
                print(f"  Fetched {len(members)} member(s) via Atlassian Teams API.")
                return members
        except Exception as exc:
            print(f"  [WARN] Teams API failed ({exc}), falling back to group search.")

    # Attempt 2: Jira group picker
    try:
        teams_data = jira_get(
            base_url,
            "/rest/api/3/groups/picker",
            auth,
            {"query": team_input, "maxResults": 5},
        )
        groups = teams_data.get("groups", [])
        if groups:
            group_name = groups[0]["name"]
            print(f"  Found group: '{group_name}'")
            members_data = jira_get(
                base_url,
                "/rest/api/3/group/member",
                auth,
                {"groupname": group_name, "maxResults": 100},
            )
            values = members_data.get("values", [])
            if values:
                return [
                    {"accountId": u["accountId"], "displayName": u["displayName"]}
                    for u in values
                    if not u.get("inactive", False)
                ]
    except Exception:
        pass

    # Attempt 3: User search by name
    print(
        f"\n  [INFO] Group lookup returned no results. Searching users matching '{team_input}'..."
    )
    search_data = jira_get(
        base_url,
        "/rest/api/3/user/search",
        auth,
        {"query": team_input, "maxResults": 50},
    )
    return [
        {"accountId": u["accountId"], "displayName": u["displayName"]}
        for u in search_data
        if u.get("active") is not False
    ]


def get_current_week_range() -> tuple[str, str]:
    tz_utc7 = timezone(timedelta(hours=7))
    today = datetime.now(tz=tz_utc7)
    monday = today - timedelta(days=today.weekday())
    friday = monday + timedelta(days=4)
    return monday.strftime("%Y-%m-%d"), friday.strftime("%Y-%m-%d")


def _fetch_issues_by_jql(base_url: str, auth: str, jql: str) -> list[dict]:
    data = jira_get(
        base_url,
        "/rest/api/3/search/jql",
        auth,
        {
            "jql": jql,
            "maxResults": 100,
            "fields": "summary,customfield_10016,customfield_10028",
        },
    )
    return data.get("issues", [])


def fetch_member_workload(base_url: str, auth: str, account_id: str) -> dict:
    """
    Workload is counted only from tickets currently In development.
    Also fetches Ready for engineer tickets for display purposes.
    """

    def points(issue: dict) -> float:
        fields = issue.get("fields", {})
        sp = fields.get("customfield_10016") or fields.get("customfield_10028") or 1
        try:
            return float(sp)
        except (TypeError, ValueError):
            return 1.0

    def ticket_label(issue: dict) -> dict:
        return {"key": issue["key"], "summary": issue["fields"].get("summary", "")}

    in_dev_issues = _fetch_issues_by_jql(
        base_url,
        auth,
        f'assignee = "{account_id}" AND status = "In development"',
    )
    ready_issues = _fetch_issues_by_jql(
        base_url,
        auth,
        f'assignee = "{account_id}" AND status = "Ready for engineer"',
    )

    total = sum(points(i) for i in in_dev_issues)

    return {
        "in_dev_points": total,
        "total_week_points": total,
        "in_dev_tickets": [ticket_label(i) for i in in_dev_issues],
        "ready_tickets": [ticket_label(i) for i in ready_issues],
    }


def fetch_all_members_workload(
    base_url: str, auth: str, account_ids: list[str]
) -> dict[str, dict]:
    """
    Fetch workload for all members in two paginated JQL queries instead of 2N queries.
    Returns {account_id: {in_dev_points, total_week_points, in_dev_tickets, ready_tickets}}.
    """
    result: dict[str, dict] = {
        aid: {
            "in_dev_points": 0.0,
            "total_week_points": 0.0,
            "in_dev_tickets": [],
            "ready_tickets": [],
        }
        for aid in account_ids
    }
    if not account_ids:
        return result

    ids_jql = ", ".join(f'"{aid}"' for aid in account_ids)

    def _points(issue: dict) -> float:
        return ticket_points(issue)

    def _label(issue: dict) -> dict:
        return {"key": issue["key"], "summary": issue["fields"].get("summary", "")}

    def _fetch_all_pages(jql: str) -> list[dict]:
        issues: list[dict] = []
        start = 0
        page = 100
        while True:
            data = jira_get(
                base_url,
                "/rest/api/3/search/jql",
                auth,
                {
                    "jql": jql,
                    "startAt": start,
                    "maxResults": page,
                    "fields": "summary,issuetype,assignee,customfield_10014,parent",
                },
            )
            batch = data.get("issues", [])
            issues.extend(batch)
            if start + len(batch) >= data.get("total", 0):
                break
            start += page
        return issues

    in_dev_issues = _fetch_all_pages(
        f'assignee in ({ids_jql}) AND status = "In development"'
    )

    # Pass 1: collect each member's in-dev Epic keys so child Tasks can be excluded.
    member_epic_keys: dict[str, set[str]] = {aid: set() for aid in account_ids}
    for issue in in_dev_issues:
        aid = (issue.get("fields", {}).get("assignee") or {}).get("accountId", "")
        itype = (
            (issue.get("fields", {}).get("issuetype") or {}).get("name") or ""
        ).lower()
        if aid in member_epic_keys and itype == "epic":
            member_epic_keys[aid].add(issue["key"])

    # Pass 2: count points, skipping Tasks whose parent Epic is also in-dev.
    for issue in in_dev_issues:
        aid = (issue.get("fields", {}).get("assignee") or {}).get("accountId", "")
        if aid not in result:
            continue
        itype = (
            (issue.get("fields", {}).get("issuetype") or {}).get("name") or ""
        ).lower()
        if itype not in ("epic", "bug"):
            parent_epic = _epic_link(issue)
            if parent_epic and parent_epic in member_epic_keys.get(aid, set()):
                continue  # Epic already accounts for this Task's scope
        pts = _points(issue)
        result[aid]["in_dev_points"] += pts
        result[aid]["total_week_points"] += pts
        result[aid]["in_dev_tickets"].append(_label(issue))

    for issue in _fetch_all_pages(
        f'assignee in ({ids_jql}) AND status = "Ready for engineer"'
    ):
        aid = (issue.get("fields", {}).get("assignee") or {}).get("accountId", "")
        if aid in result:
            result[aid]["ready_tickets"].append(_label(issue))

    return result


# ---------------------------------------------------------------------------
# Issue-type point weights
# Story points fields are unreliable; derive capacity cost from issue type instead.
# ---------------------------------------------------------------------------

_ISSUE_TYPE_POINTS: dict[str, float] = {
    "epic": 3.0,
    "bug": 1.0,
}
_DEFAULT_TASK_POINTS = 2.0


def ticket_points(issue: dict) -> float:
    """Return capacity cost based on issue type (Epic=3, Bug=1, anything else=2)."""
    itype = ((issue.get("fields", {}).get("issuetype") or {}).get("name") or "").lower()
    return _ISSUE_TYPE_POINTS.get(itype, _DEFAULT_TASK_POINTS)


def _epic_link(issue: dict) -> str:
    """
    Return the parent Epic key for a task/story, or empty string if none.
    Checks customfield_10014 (classic) and fields.parent (next-gen).
    """
    fields = issue.get("fields", {})
    classic = fields.get("customfield_10014") or ""
    if classic:
        return classic
    parent = fields.get("parent") or {}
    parent_type = ((parent.get("fields") or {}).get("issuetype") or {}).get("name", "")
    if parent_type.lower() == "epic":
        return parent.get("key", "")
    return ""


# ---------------------------------------------------------------------------
# Assignment logic
# ---------------------------------------------------------------------------


def matches_member_list(m: dict, id_or_email_list: list[str]) -> bool:
    """Return True if the member's accountId or emailAddress appears in the list."""
    targets = {s.lower() for s in id_or_email_list}
    return (
        m.get("accountId", "").lower() in targets
        or m.get("emailAddress", "").lower() in targets
    )


def apply_member_policies(members_workload: list[dict]) -> list[dict]:
    """
    Stamp each member dict with policy flags and recalculate overloaded
    using the threshold appropriate for that member's policy.

      excluded     — in EXCLUDE_MEMBERS (never assigned)
      on_leave     — detected via Slack 🌴 status (never assigned)
      low_priority — in LOW_PRIORITY_MEMBERS (capped at LOW_PRIORITY_THRESHOLD)
      overloaded   — has exceeded their effective threshold
    """
    for m in members_workload:
        m["excluded"] = matches_member_list(m, EXCLUDE_MEMBERS)
        # on_leave is already set by detect_on_leave_from_slack(); preserve it
        m.setdefault("on_leave", False)
        m["low_priority"] = matches_member_list(m, LOW_PRIORITY_MEMBERS)

        # On-leave members are never eligible regardless of current workload.
        if m["on_leave"]:
            m["overloaded"] = True
            continue

        if m["low_priority"]:
            threshold = LOW_PRIORITY_THRESHOLD
        else:
            threshold = OVERLOAD_THRESHOLD

        if threshold == 0.0:
            m["overloaded"] = True
        else:
            m["overloaded"] = (
                m["in_dev_points"] > 0
                and m["total_week_points"] / WEEKLY_CAPACITY_POINTS >= threshold
            )
    return members_workload


def select_assignee(members_workload: list[dict]) -> dict | None:
    eligible = [
        m for m in members_workload if not m["excluded"] and not m["overloaded"]
    ]
    if not eligible:
        return None
    # Most free time = lowest total_week_points
    return min(eligible, key=lambda m: m["total_week_points"])


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------


def member_label(m: dict) -> str:
    """Return 'Display Name (email)' or just display name if no email."""
    name = m.get("displayName", m.get("accountId", "Unknown"))
    email = m.get("emailAddress", "")
    return f"{name} ({email})" if email else name


def print_workload_table(members_workload: list[dict]) -> None:
    print(
        f"\n{'Name (email)':<55} {'Week pts':>9} {'Capacity':>12} {'In Dev':>7}  {'Status'}"
    )
    print("-" * 100)
    for m in sorted(members_workload, key=lambda x: x["total_week_points"]):
        pct = m["total_week_points"] / WEEKLY_CAPACITY_POINTS * 100
        bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
        if m.get("excluded"):
            flag = "EXCLUDED"
        elif m.get("on_leave") and m["overloaded"]:
            flag = "ON-LEAVE capped"
        elif m.get("on_leave"):
            flag = "on-leave"
        elif m.get("low_priority") and m["overloaded"]:
            flag = "LOW-PRI  capped"
        elif m["overloaded"]:
            flag = "OVERLOADED"
        elif m.get("low_priority"):
            flag = "low-priority"
        else:
            flag = "available"
        label = member_label(m)
        print(
            f"{label:<55} {m['total_week_points']:>9.1f} "
            f"{bar} {pct:>5.0f}%  {m['in_dev_points']:>4.1f} in-dev  {flag}"
        )
        for t in m.get("ready_tickets", []):
            print(f"    {'':55}  → {t['key']}: {t['summary']}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    print("=" * 60)
    print("  Jira Auto-Assign: Ready for Engineer → Team")
    print("=" * 60)

    ci_mode = os.environ.get("CI", "").lower() in ("1", "true")

    def require_env(value: str, name: str, prompt_fn):
        if value:
            return value
        if ci_mode:
            print(f"[ERROR] Required environment variable {name} is not set.")
            sys.exit(1)
        return prompt_fn()

    # --- Credentials ---
    email = require_env(
        JIRA_EMAIL, "JIRA_EMAIL", lambda: input("\nJira email: ").strip()
    )
    api_token = require_env(
        JIRA_API_TOKEN,
        "JIRA_API_TOKEN",
        lambda: getpass.getpass(
            "Jira API token (from id.atlassian.net/manage-profile/security/api-tokens): "
        ),
    )
    auth = make_auth_header(email, api_token)

    # --- Board URL ---
    raw_board = require_env(
        JIRA_BOARD_URL,
        "JIRA_BOARD_URL",
        lambda: input(
            "\nBoard URL or ID\n"
            "  (e.g. https://org.atlassian.net/jira/software/c/projects/KEY/boards/1234): "
        ).strip(),
    )

    try:
        parsed_base, project_key, board_id = parse_board_url(raw_board)
    except ValueError as exc:
        print(f"[ERROR] {exc}")
        sys.exit(1)

    base_url = JIRA_BASE_URL or parsed_base
    if not base_url:
        base_url = require_env(
            "",
            "JIRA_BASE_URL",
            lambda: (
                input("Jira base URL (e.g. https://org.atlassian.net): ")
                .strip()
                .rstrip("/")
            ),
        )

    if project_key:
        print(f"  Detected project: {project_key}, board: {board_id}")

    # --- Team ---
    raw_team = require_env(
        JIRA_TEAM_URL,
        "JIRA_TEAM_URL",
        lambda: input(
            "Team URL or group name\n"
            "  (e.g. https://home.atlassian.com/o/<org>/people/team/<id>?cloudId=...): "
        ).strip(),
    )

    team_org_id, team_id, _ = (
        parse_team_url(raw_team) if raw_team.startswith("http") else ("", "", "")
    )
    team_label = raw_team if not team_id else f"team/{team_id}"

    # --- Fetch tickets ---
    print(
        f"\n[1/4] Fetching unassigned 'Ready for Engineer' tickets on board {board_id}..."
    )
    tickets = fetch_unassigned_ready_tickets(base_url, auth, board_id, project_key)
    if not tickets:
        print("  No unassigned 'Ready for Engineer' tickets found.")
    else:
        print(f"  Found {len(tickets)} ticket(s):")
        for t in tickets:
            print(f"    {t['key']:12}  {t['fields'].get('summary', '')[:60]}")

    # --- Fetch team members ---
    print(f"\n[2/4] Fetching members of '{team_label}'...")
    members = fetch_team_members(base_url, auth, raw_team, team_org_id, team_id)
    if not members:
        print(
            f"  [ERROR] No members found for '{team_label}'. Check the team URL or group name."
        )
        sys.exit(1)
    print(
        f"  Found {len(members)} member(s): {', '.join(member_label(m) for m in members)}"
    )

    # --- Workload check ---
    print(
        f"\n[3/4] Checking weekly workload (capacity = {WEEKLY_CAPACITY_POINTS} pts, "
        f"threshold = {int(OVERLOAD_THRESHOLD * 100)}%)..."
    )
    week_start, week_end = get_current_week_range()
    print(f"  Week range: {week_start} → {week_end}")

    account_ids = [m["accountId"] for m in members]
    all_wl = fetch_all_members_workload(base_url, auth, account_ids)
    members_workload = [
        {**m, **all_wl[m["accountId"]], "overloaded": False} for m in members
    ]

    if SLACK_BOT_TOKEN:
        print("  Checking Slack statuses for on-leave detection...")
        slack_user_map_early = build_slack_user_map(SLACK_BOT_TOKEN, members_workload)
        detect_on_leave_from_slack(
            SLACK_BOT_TOKEN, members_workload, slack_user_map_early
        )

    apply_member_policies(members_workload)
    print_workload_table(members_workload)

    assignments = []  # list of (ticket_key, display_label, email, account_id, summary)
    skipped = []

    if not tickets:
        print("\n[4/4] No tickets to assign — skipping planning step.")
    else:
        # --- Plan assignments (dry run) ---
        print(f"\n[4/4] Planning assignments...")
        planned = []

        wl_draft = copy.deepcopy(members_workload)
        assigned_epic_keys: set[str] = set()

        for ticket in tickets:
            ticket_key = ticket["key"]
            itype = (
                (ticket.get("fields", {}).get("issuetype") or {}).get("name") or ""
            ).lower()

            # Skip tasks whose parent Epic is already queued for assignment this run
            if itype not in ("epic", "bug"):
                parent_epic = _epic_link(ticket)
                if parent_epic and parent_epic in assigned_epic_keys:
                    print(
                        f"  ↷ {ticket_key} skipped — parent Epic {parent_epic} already assigned this run"
                    )
                    skipped.append(ticket_key)
                    continue

            assignee = select_assignee(wl_draft)
            if assignee is None:
                skipped.append(ticket_key)
                continue

            planned.append((ticket, assignee))
            pts = ticket_points(ticket)
            assignee["total_week_points"] += pts

            if itype == "epic":
                assigned_epic_keys.add(ticket_key)

            # Re-evaluate overloaded so subsequent tickets respect the new total
            apply_member_policies(wl_draft)

        # --- Show planned assignments for review ---
        print("\n" + "=" * 60)
        print("  Planned Assignments (review before confirming)")
        print("=" * 60)
        if planned:
            print(f"\n  {'Ticket':<12}  {'Summary':<40}  Assignee")
            print("  " + "-" * 90)
            for ticket, assignee in planned:
                summary = ticket["fields"].get("summary", "")[:40]
                print(f"  {ticket['key']:<12}  {summary:<40}  {member_label(assignee)}")
        if skipped:
            print(f"\n  Skipped (no capacity): {', '.join(skipped)}")

        if not planned:
            print("\n  Nothing to assign — all tickets skipped.")
        else:
            print()
            if ci_mode:
                confirm = "y"
                print("  [CI] Auto-confirming assignments.")
            else:
                confirm = (
                    input("  Proceed with all assignments above? [Y/n]: ")
                    .strip()
                    .lower()
                )
            if confirm not in ("", "y", "yes"):
                print("  Aborted. No changes made.")
            else:
                print()
                for ticket, assignee in planned:
                    ticket_key = ticket["key"]
                    jira_put(
                        base_url,
                        f"/rest/api/3/issue/{ticket_key}/assignee",
                        auth,
                        {"accountId": assignee["accountId"]},
                    )
                    print(f"  ✓ {ticket_key} → {member_label(assignee)}")
                    assignments.append(
                        (
                            ticket_key,
                            member_label(assignee),
                            assignee.get("emailAddress", ""),
                            assignee["accountId"],
                            ticket["fields"].get("summary", ""),
                        )
                    )

    # --- Summary ---
    print("\n" + "=" * 60)
    print("  Done")
    print("=" * 60)
    if assignments:
        for key, name, *_ in assignments:
            print(f"  {key:12} → {name}")
    else:
        print("  No assignments made.")
    print()

    # --- Slack notification ---
    if SLACK_BOT_TOKEN and SLACK_CHANNEL_IDS:
        # Build post-assignment workload from existing data — no re-fetch needed.
        # on_leave flags and policy stamps already set on members_workload.
        updated_workload = copy.deepcopy(members_workload)
        wl_by_account = {m["accountId"]: m for m in updated_workload}
        for ticket_key, _label, _email, account_id, summary in assignments:
            if account_id in wl_by_account:
                wl_by_account[account_id].setdefault("ready_tickets", []).append(
                    {"key": ticket_key, "summary": summary}
                )
        apply_member_policies(updated_workload)

        # Reuse the Slack user map resolved during the workload-check step.
        user_map = slack_user_map_early

        slack_assignments = [
            (key, label, email) for key, label, email, *_ in assignments
        ]
        blocks = build_slack_blocks(
            slack_assignments,
            skipped,
            base_url,
            week_start,
            week_end,
            updated_workload,
            user_map,
        )
        fallback = f"Jira Auto-Assign ({week_start}): " + ", ".join(
            f"{k} → {n}" for k, n, *_ in assignments
        )
        for channel in SLACK_CHANNEL_IDS:
            send_slack_message(SLACK_BOT_TOKEN, channel, fallback, blocks)


if __name__ == "__main__":
    main()
