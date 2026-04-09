# Jira + Sentry Integration

**Automatic Context Enrichment:**

When investigating Jira issues, automatically detect and fetch Sentry context from linked errors using Atlassian MCP + Sentry CLI.

---

### Workflow

1. **User provides Jira URL** → Extract issue key
2. **Fetch Jira issue** (Atlassian MCP) → Get description, comments, custom fields
3. **Regex scan for Sentry URLs** → Pattern: `https://[^/]+\.sentry\.io/issues/(\d+)`
4. **Extract Sentry issue IDs** → Parse matched URLs
5. **Fetch Sentry details** (Sentry CLI) → Get error context as optional enrichment
6. **Combined analysis** → Jira context + Sentry errors + code investigation

### URL Pattern Detection

```typescript
// Jira issue contains:
// Description: "Error reported in production: https://employmenthero.sentry.io/issues/12345/"
// Comment: "Related to https://employmenthero.sentry.io/issues/67890/"

// Claude automatically:
// 1. Fetches Jira issue
// 2. Scans description + comments for Sentry URLs
// 3. Extracts issue IDs: ["12345", "67890"]
// 4. Fetches each Sentry issue for context
// 5. Presents combined view: Jira ticket + Sentry errors
```

### Implementation Pattern

```bash
# 1. Fetch Jira issue using Atlassian MCP
# (Use mcp__atlassian__getJiraIssue tool)

# 2. Extract Sentry URLs from Jira description/comments
# Pattern: https://[org].sentry.io/issues/[ISSUE_ID]

# Example Jira issue contains:
# Description: "Error in production: https://employmenthero.sentry.io/issues/12345/"
# Comment: "Related to https://employmenthero.sentry.io/issues/67890/"

# 3. Extract issue IDs: 12345, 67890

# 4. Fetch Sentry context for each unique issue using API
ORG_SLUG="employmenthero"

for ISSUE_ID in 12345 67890; do
  echo "=== Sentry Issue $ISSUE_ID ==="

  # Get issue details
  sentry api /organizations/$ORG_SLUG/issues/$ISSUE_ID/ | jq '.'

  # Get latest event for detailed context
  sentry api /organizations/$ORG_SLUG/issues/$ISSUE_ID/events/latest/ | jq '{
    error: .title,
    stack: .entries[] | select(.type == "exception"),
    breadcrumbs: .entries[] | select(.type == "breadcrumbs")
  }'
done

# 5. Present combined context:
# - Jira business context (why, what, acceptance criteria)
# - Sentry technical details (stack trace, breadcrumbs, user journey)
# - Code investigation (Serena + GitHub CLI)
```

### When to Apply

- ✅ User provides Jira URL/key explicitly
- ✅ Investigating production bugs reported in Jira
- ✅ Jira issue type is "Bug" or "Incident"
- ⚠️ **Optional enrichment** - Don't fail if Sentry fetch fails
- ⚠️ **Rate limit aware** - Limit to first 3-5 Sentry URLs to avoid rate limiting

### Benefits

- **Single entry point**: Start from Jira ticket, get full error context
- **Reduced context switching**: No manual Sentry URL clicking
- **Complete picture**: Business context (Jira) + technical details (Sentry) + code (Serena)
- **Faster resolution**: All investigation data in one place

### Example Output

```markdown
## Jira Issue: PROJ-123 - Fix login failure

**Status**: In Progress
**Priority**: High
**Assignee**: @developer

**Description**:
Users reporting login failures in production. Error: https://employmenthero.sentry.io/issues/12345/

---

## Related Sentry Errors (Auto-fetched)

### Sentry Issue #12345
**Error**: `AuthenticationError: Invalid token format`
**Frequency**: 247 events in last 24h
**First seen**: 2026-02-03 14:23 UTC
**Last seen**: 2026-02-04 09:45 UTC

**Stack trace**:
```
File "app/auth/token_validator.py", line 42, in validate_token
  raise AuthenticationError("Invalid token format")
```

**Breadcrumbs**:
1. User navigated to /login
2. Submitted credentials
3. Token validation failed

---

## Investigation Plan

1. Check token validation logic in app/auth/token_validator.py:42
2. Review recent changes to authentication flow
3. Verify token format expectations
```
