# Investigation Best Practices

Quality standards and systematic approaches for thorough Sentry investigations.

## Investigation Best Practices

### Systematic Approach

**Always follow the 6-step workflow:**
1. ✅ Overview first → Understand scope and impact
2. ✅ Stack trace second → Identify code location
3. ✅ Breadcrumbs third → Understand user journey
4. ✅ HTTP request fourth → Check request validity
5. ✅ Tags/context fifth → Identify environmental factors
6. ✅ Additional data last → Custom app-specific insights

**Don't skip steps even if cause seems obvious** → Full context prevents misdiagnosis

### Stack Trace Analysis

- **Read top-down**: Start from error point, trace back through call chain
- **Identify app vs. framework code**: Focus on application frames first
- **Look for patterns**: Recursive calls, unexpected code paths, missing error handling
- **Map to codebase**: Use file paths and line numbers to locate exact code
- **Check multiple events**: Stack trace might vary across different occurrences

### Breadcrumb Analysis

- **Look for trigger patterns**: Specific sequence of user actions
- **Check timing**: Time between actions (rapid clicks, timeouts)
- **Examine failed requests**: API calls that returned errors before the crash
- **Note state changes**: Data mutations that might have caused invalid state
- **Consider async operations**: Promises, timers, event handlers

### Context Correlation

**Cross-reference findings:**
- Stack trace location + Breadcrumbs → What user action triggered code path?
- HTTP request + Tags → Is error environment/browser specific?
- Additional data + Context → Do feature flags or config affect behavior?
- Frequency + Tags → Is error increasing after deployment?

### Rate Limiting Awareness

- **Fetch events judiciously**: Default to `limit: 5` for latest events
- **Don't fetch all events**: 100+ events consume rate limits
- **Use search wisely**: Broad searches can return many results
- **Cache investigation data**: Don't re-fetch same issue multiple times

### Code Investigation Integration

**After Sentry analysis, use code tools:**

```typescript
// 1. Extract file path from stack trace
const filePath = "app/services/payment_processor.rb";
const lineNumber = 42;

// 2. Use Serena to read the symbol at that location
mcp__serena__find_symbol({
  name_path_pattern: "PaymentProcessor/process_payment",
  relative_path: filePath,
  include_body: true
});

// 3. Find what calls this function (to understand call chain)
mcp__serena__find_referencing_symbols({
  name_path: "PaymentProcessor/process_payment",
  relative_path: filePath
});

// 4. Search for related code patterns
mcp__serena__search_for_pattern({
  substring_pattern: "process_payment",
  restrict_search_to_code_files: true
});
```

### Sentry Investigation

- Always fetch full issue context before proposing fixes
- Use breadcrumbs to understand user journey
- Check error frequency/trend before prioritizing
- Link Sentry issues to code locations using stack traces
- Combine Sentry data with code exploration (Serena) for root cause analysis
- Follow the 6-step investigation workflow systematically
- Don't assume cause without examining all data sources
- Cross-reference stack trace, breadcrumbs, and context for complete picture

### Jira + Sentry Integration

- ✅ Scan Jira description, comments, AND custom fields for Sentry URLs
- ✅ Fetch Sentry context for all unique issue IDs found
- ✅ Present combined view with both business and technical context
- ❌ Don't fetch Sentry for every Jira issue (only when URLs detected)
- ❌ Don't block Jira investigation if Sentry fails (treat as optional)
- ❌ Don't fetch more than 5 Sentry issues (rate limiting, context bloat)

## OAuth Flow

- First use triggers OAuth authentication
- Browser opens for authorization
- Token stored securely by MCP server
- Subsequent requests use cached token

## Error Handling

### Sentry API Troubleshooting

**SECURITY**: Never echo or display the auth token. Check it's set without revealing it.

```bash
# Check authentication status
sentry auth status

# Test authentication - list organizations
sentry api /organizations/ | jq -r '.[].slug'

# Test organization access
if sentry api /organizations/ | jq -e '.[0]' > /dev/null 2>&1; then
  echo "✓ Authentication successful"
else
  echo "✗ Authentication failed - run: sentry auth login"
fi

# Test project access
sentry api /organizations/YOUR_ORG/projects/ | jq -r '.[].slug'

# Test issue access
sentry api /organizations/YOUR_ORG/issues/ISSUE_ID/ | jq '.title'
```

**Common Issues:**

- **401 Unauthorized**: Run `sentry auth login` to authenticate
- **403 Forbidden**: Token doesn't have required scopes (`event:read`, `org:read`, `project:read`); create new token with correct scopes
- **404 Not Found**: Wrong organization slug or issue ID; verify from Sentry URL
- **429 Too Many Requests**: Rate limit exceeded (typically 1000 requests/hour); wait before retrying
- **Invalid issue ID**: Verify numeric issue ID from Sentry URL (after `/issues/`)
- **JSON parsing errors**: Ensure `jq` is installed (`brew install jq` on macOS)
- **Empty response**: Issue may be in different organization or project; check organization slug
- **Authentication expired**: Run `sentry auth login` to re-authenticate

**Documentation:**
- Sentry CLI: https://cli.sentry.dev/
- API reference: https://docs.sentry.io/api/
- Rate limits: https://docs.sentry.io/api/rate-limits/


## Investigation Workflow Summary

**Complete investigation process:**

### Phase 0: Business Context (Optional but Recommended)
0. 🔍 Find related commits, PRs, Jira tickets, and Confluence pages
   - Extract ticket IDs from commit messages
   - Fetch Jira issue for requirements and acceptance criteria
   - Fetch Confluence pages for architecture/implementation guides
   - Understand **why** the change was made vs **what** went wrong

### Phase 1: Data Collection (Steps 1-6)
1. ✅ Fetch issue overview
2. ✅ Analyze stack trace
3. ✅ Examine breadcrumbs
4. ✅ Review HTTP request
5. ✅ Inspect tags/context
6. ✅ Examine additional data

### Phase 2: Systematic Analysis (4-step framework)
1. 🔍 **IDENTIFY**: Generate hypotheses from evidence
2. 🔬 **ANALYZE**: Test each hypothesis systematically → **MUST end with explicit root cause confirmation**
3. ✅ **DECIDE**: Choose best solution approach → **MUST reference confirmed root cause**
4. 📋 **PLAN**: Create actionable implementation steps → **Each action MUST link to root cause**

### When to Use 4-Step Framework

**Always use for:**
- Production errors affecting users
- Deployment-related regressions
- Complex errors requiring code investigation
- Issues needing stakeholder communication

**Can skip for:**
- Obvious configuration errors (clear fix)
- Known issues with documented solutions
- Errors with single, unambiguous cause

### Output Quality Standards

**Good investigation includes:**
- ✅ All 6 data collection steps completed
- ✅ Multiple hypotheses considered (not just first idea)
- ✅ Code examined to confirm root cause
- ✅ **ANALYZE ends with explicit "ROOT CAUSE CONFIRMED" statement**
- ✅ **Root cause includes supporting evidence from code/data**
- ✅ **DECIDE explicitly references the confirmed root cause**
- ✅ **Solution approach explains HOW it addresses root cause**
- ✅ **Each action in PLAN includes detailed "Why this helps" explanation**
- ✅ **"Why this helps" directly links to root cause and error symptoms**
- ✅ **Explanations show mechanism/reasoning, not just assertions**
- ✅ Rollback plan defined
- ✅ Prevention measures identified

**Poor investigation:**
- ❌ Jumping to conclusions without data
- ❌ Skipping breadcrumbs or context analysis
- ❌ No code verification
- ❌ **Root cause stated ambiguously or not at all**
- ❌ **No explicit confirmation at end of ANALYZE phase**
- ❌ **DECIDE doesn't reference what root cause is being addressed**
- ❌ **Solution chosen without explaining how it fixes root cause**
- ❌ No rollback plan
- ❌ No consideration of alternatives
- ❌ **Vague action explanations ("this should fix it", "best practice")**
- ❌ **Missing "Why this helps" for any action in the plan**
- ❌ **Actions not linked to specific root cause identified**

## Summary

**Primary use cases:**
- Sentry error investigation (standalone)
- Jira issue investigation (with automatic Sentry enrichment)
- Combined business + technical error analysis

**Key patterns:**
- URL pattern detection and extraction
- Sentry REST API for authenticated error data access
- Atlassian MCP for Jira/Confluence integration
- GitHub CLI for commit/PR analysis
- Serena MCP for code investigation
- Optional enrichment (don't fail if Sentry API unavailable)
- Rate limit awareness (Sentry API: 1000 requests/hour)
- Systematic 4-step analysis with explicit root cause linkage:
  1. **IDENTIFY** → Generate hypotheses
  2. **ANALYZE** → Test hypotheses + **CONFIRM root cause**
  3. **DECIDE** → Select solution that **addresses confirmed root cause**
  4. **PLAN** → Define actions that **link to root cause**

**Tools used:**
- **Sentry REST API** (`curl` + API endpoints) - Error data retrieval and analysis
- **Atlassian MCP** (`mcp__atlassian__*`) - Jira tickets and Confluence docs
- **GitHub CLI** (`gh`) - Commit history and PR analysis
- **Serena MCP** (`mcp__serena__*`) - Code investigation
- **jq** - JSON parsing and data extraction
- **curl** - HTTP requests to Sentry API

**API Documentation:**
- Sentry API: https://docs.sentry.io/api/
- Authentication: https://docs.sentry.io/api/auth/
- Issues endpoint: https://docs.sentry.io/api/events/list-an-organizations-issues/
- Events endpoint: https://docs.sentry.io/api/events/list-a-projects-events/

**Result:** Faster error resolution with complete context, structured analysis, explicit root cause confirmation, and actionable plans with clear rationale.
