# Sentry API Reference

**Use Sentry REST API for all operations:**

- ✅ Fetch issue details
- ✅ Search error events
- ✅ Analyze stack traces
- ✅ Get breadcrumbs and user context
- ✅ Full access to all Sentry data
- ❌ **NEVER** use WebFetch on Sentry URLs (requires authentication)

### Common API Endpoints Reference

```bash
# Set up (run once)
ORG_SLUG="your-org-slug"  # e.g., "employmenthero"

# === ISSUES ===
# List issues for a project
sentry api /projects/$ORG_SLUG/PROJECT_SLUG/issues/ | jq '.'

# Get issue details by ID
sentry api /organizations/$ORG_SLUG/issues/ISSUE_ID/ | jq '.'

# Search issues with query
sentry api /organizations/$ORG_SLUG/issues/?query=is:unresolved&statsPeriod=24h | jq '.'

# === EVENTS ===
# List latest events for an issue
sentry api /organizations/$ORG_SLUG/issues/ISSUE_ID/events/ | jq '.'

# Get specific event details (includes stack trace, breadcrumbs, context)
sentry api /organizations/$ORG_SLUG/issues/ISSUE_ID/events/latest/ | jq '.'

# Get event by event ID
sentry api /organizations/$ORG_SLUG/issues/ISSUE_ID/events/EVENT_ID/ | jq '.'

# === DATA EXTRACTION ===
# Get latest event with full details
LATEST_EVENT=$(sentry api /organizations/$ORG_SLUG/issues/ISSUE_ID/events/latest/)

# Extract stack trace
echo "$LATEST_EVENT" | jq '.entries[] | select(.type == "exception")'

# Extract breadcrumbs
echo "$LATEST_EVENT" | jq '.entries[] | select(.type == "breadcrumbs") | .data.values'

# Extract request data
echo "$LATEST_EVENT" | jq '.request'

# Extract tags and context
echo "$LATEST_EVENT" | jq '{tags, contexts, extra}'

# === ORGANIZATIONS & PROJECTS ===
# List organizations
sentry api /organizations/ | jq '.'

# List projects in organization
sentry api /organizations/$ORG_SLUG/projects/ | jq '.'
```

### Working with API Responses

```bash
# Get issue with specific fields
sentry api /organizations/$ORG_SLUG/issues/ISSUE_ID/ | jq '{
  id,
  title,
  status,
  count,
  userCount,
  firstSeen,
  lastSeen,
  level
}'

# Get latest event stack trace
sentry api /organizations/$ORG_SLUG/issues/ISSUE_ID/events/latest/ | jq '
  .entries[] |
  select(.type == "exception") |
  .data.values[0].stacktrace.frames[] |
  {filename, function, lineNo, context_line}
'

# Pretty print for human reading
sentry api /organizations/$ORG_SLUG/issues/ISSUE_ID/ | jq '.'
```

### Helper Function (Optional)

```bash
# Convenient wrapper function (optional - sentry-cli already handles auth)
sentry_api() {
  local endpoint="$1"
  sentry api "/$endpoint" | jq '.'
}

# Usage
sentry_api "organizations/$ORG_SLUG/issues/ISSUE_ID"
sentry_api "organizations/$ORG_SLUG/issues/ISSUE_ID/events/latest"
```

### URL Pattern Recognition

When given Sentry URLs like `https://[organization].sentry.io/issues/[issue-id]/`:

1. **Extract** organization slug and issue ID
2. **Use Sentry API** to fetch full context
3. **Analyze** stack trace to identify code location
4. **Get event context** for user actions and breadcrumbs

### Common Operations

```bash
# Example: User provides Sentry URL
# https://employmenthero.sentry.io/issues/12345/

# Extract:
# - organization: "employmenthero"
# - issue_id: "12345"

# Set up
ORG_SLUG="employmenthero"
ISSUE_ID="12345"

# Get issue details
sentry api /organizations/$ORG_SLUG/issues/$ISSUE_ID/ | jq '.'

# Get latest event with full details
sentry api /organizations/$ORG_SLUG/issues/$ISSUE_ID/events/latest/ | jq '.'

# Get event list
sentry api /organizations/$ORG_SLUG/issues/$ISSUE_ID/events/ | jq '.'
```

## Sentry API Quick Reference

**Core API endpoints for investigation:**

```bash
# Setup
ORG_SLUG="your-org"
PROJECT_SLUG="your-project"
ISSUE_ID="12345"

# === ISSUE DETAILS ===
# Get issue overview
sentry api /organizations/$ORG_SLUG/issues/$ISSUE_ID/ | jq '.'

# === EVENTS ===
# Get latest event (includes breadcrumbs, stack trace, context, tags)
sentry api /organizations/$ORG_SLUG/issues/$ISSUE_ID/events/latest/ | jq '.'

# Get event list
sentry api /organizations/$ORG_SLUG/issues/$ISSUE_ID/events/?limit=10 | jq '.'

# === SEARCH ===
# Search issues (using Sentry search syntax)
sentry api /organizations/$ORG_SLUG/issues/?query=is:unresolved+environment:production&limit=50 | jq '.'

# === STATS ===
# Get issue stats (last 24h)
sentry api /organizations/$ORG_SLUG/issues/$ISSUE_ID/?statsPeriod=24h | jq '.stats'
```

**Quick extraction patterns:**

```bash
# Save latest event
EVENT=$(sentry api /organizations/$ORG_SLUG/issues/$ISSUE_ID/events/latest/)

# Get breadcrumbs
echo "$EVENT" | jq '.entries[] | select(.type == "breadcrumbs") | .data.values'

# Get stack trace
echo "$EVENT" | jq '.entries[] | select(.type == "exception")'

# Get request details
echo "$EVENT" | jq '.request'

# Get tags and context
echo "$EVENT" | jq '{tags, contexts, extra}'

# Get user info
echo "$EVENT" | jq '.user'
```
