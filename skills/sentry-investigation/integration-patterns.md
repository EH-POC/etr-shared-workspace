# Integration Patterns

How Sentry Investigation integrates with other skills for comprehensive error resolution.

## Integration with Other Skills

### With Context Discovery

When investigating errors:
1. Use Sentry Investigation to get error details
2. Use Context Discovery to find related documentation in Confluence
3. Combine error context + documentation for comprehensive understanding

### With Serena Semantic Code

After fetching Sentry stack trace:
1. Extract file path and line number from stack trace
2. Use Serena to find symbol at that location
3. Use Serena to find references and related code
4. Propose fix based on code structure understanding

### With GitHub CLI Integration

If error relates to recent changes:
1. Extract file path from Sentry stack trace
2. Use gh CLI to find recent PRs affecting that file
3. Review PR changes for potential regression
4. Link Sentry error to specific code change

**Enhanced workflow with ticket tracking:**

```bash
# 1. Find recent commits affecting the error location
gh api repos/Thinkei/repo-name/commits \
  --jq '.[] | select(.commit.message | contains("file_name")) | {sha, message, author: .commit.author.name, date: .commit.author.date}'

# 2. Extract ticket ID from commit message (e.g., "PROJ-123: Fix payment bug")
# Pattern: [A-Z]+-\d+
# Example: "PROJ-123", "BUG-456", "FEAT-789"

# 3. Find related PRs
gh pr list --repo Thinkei/repo-name --search "PROJ-123" --state all --json number,title,mergedAt,url

# 4. Get PR details including description
gh pr view 456 --repo Thinkei/repo-name --json title,body,mergedAt,author,files
```

**Ticket ID extraction patterns:**

```typescript
// Common patterns in commits/PRs:
// - "PROJ-123: Fix authentication bug"
// - "[PROJ-123] Update payment validation"
// - "Fix payment issue (PROJ-123)"
// - "PROJ-123 - Refactor auth flow"

const ticketPattern = /([A-Z]+-\d+)/g;
const commitMessage = "PROJ-123: Fix payment amount calculation";
const matches = commitMessage.match(ticketPattern);
// Result: ["PROJ-123"]
```

### With Atlassian MCP Integration

**After finding ticket IDs from commits/PRs, fetch business context:**

```typescript
// 1. Extract ticket ID from commit/PR
const ticketId = "PROJ-123";  // From commit message or PR title

// 2. Fetch Jira issue for business context
const jiraIssue = await mcp__atlassian__getJiraIssue({
  cloudId: "employmenthero",  // Your Atlassian org
  issueIdOrKey: ticketId
});

/**
 * Jira issue provides:
 * - Summary: What was the intended change
 * - Description: Why the change was needed
 * - Acceptance criteria: What should work
 * - Comments: Discussion and context
 * - Custom fields: Additional metadata
 */

// 3. Scan Jira description for Confluence page links
const confluencePattern = /https:\/\/[^/]+\.atlassian\.net\/wiki\/spaces\/([^/]+)\/pages\/(\d+)/g;
const confluenceLinks = [];

const descMatches = jiraIssue.description?.matchAll(confluencePattern);
for (const match of descMatches || []) {
  confluenceLinks.push({
    space: match[1],
    pageId: match[2],
    url: match[0]
  });
}

// 4. Fetch Confluence pages for additional context
for (const link of confluenceLinks) {
  const page = await mcp__atlassian__getConfluencePage({
    cloudId: "employmenthero",
    pageId: link.pageId,
    contentFormat: "markdown"
  });

  /**
   * Confluence page may contain:
   * - Architecture diagrams
   * - Implementation guides
   * - API documentation
   * - Decision records
   * - Related tickets and context
   */
}
```

**Complete investigation flow with all integrations:**

```markdown
## Investigation: Sentry Error → Commits → Tickets → Confluence

### 1. Sentry Error Analysis
- Error: `StripeAPIError: Card declined`
- Location: app/services/payment_processor.rb:42
- First seen: 2026-02-03 14:00 UTC (1 hour after v2.3.1 deployment)

### 2. Find Related Commits
```bash
gh api repos/Thinkei/eh-web/commits \
  --jq '.[] | select(.commit.message | contains("payment_processor")) | {sha: .sha[0:7], message: .commit.message, date: .commit.author.date}' \
  | head -5
```

**Result:**
- `abc1234` - "PROJ-456: Fix payment amount to use dollars" (2026-02-03 12:30)
- `def5678` - "PROJ-123: Update Stripe integration" (2026-02-01 10:00)

### 3. Fetch Jira Ticket Context
```typescript
const ticket = await mcp__atlassian__getJiraIssue({
  cloudId: "employmenthero",
  issueIdOrKey: "PROJ-456"
});
```

**PROJ-456: Fix payment amount to use dollars**
- **Type**: Bug
- **Priority**: Medium
- **Status**: Done
- **Description**:
  > Payment amounts should be in dollars, not cents. Update PaymentProcessor to convert.
  >
  > **Acceptance Criteria:**
  > - [ ] Payment amounts passed in dollars
  > - [ ] Stripe receives amount in cents (multiply by 100)
  >
  > **Architecture Reference:**
  > https://employmenthero.atlassian.net/wiki/spaces/ENG/pages/12345/Payment-Processing-Guide

### 4. Fetch Confluence Documentation
```typescript
const page = await mcp__atlassian__getConfluencePage({
  cloudId: "employmenthero",
  pageId: "12345",
  contentFormat: "markdown"
});
```

**Payment Processing Guide (Confluence)**
```
# Payment Amount Handling

⚠️ **IMPORTANT**: PaymentProcessor always expects amounts in CENTS.

## Correct Usage
```ruby
# Amount already in cents
PaymentProcessor.charge_card(2999)  # $29.99

# Convert dollars to cents first
amount_in_dollars = 29.99
PaymentProcessor.charge_card((amount_in_dollars * 100).to_i)
```

## ❌ Common Mistake
```ruby
# DON'T multiply inside charge_card if amount already in cents!
def charge_card(amount_in_cents)
  Stripe::Charge.create(amount: amount_in_cents * 100)  # WRONG!
end
```
```

### 5. Root Cause Analysis
**Smoking gun found:**
- Ticket PROJ-456 asked to "multiply by 100"
- But the code ALREADY received cents
- Developer misunderstood: multiplied cents by 100 again
- Confluence docs explicitly warn against this mistake
- Result: $29.99 became $2999.00

### 6. Solution
Revert the multiplication in payment_processor.rb:42
```ruby
def charge_card(amount_in_cents)
  Stripe::Charge.create(
    amount: amount_in_cents,  # Already in cents, don't multiply!
    currency: 'usd'
  )
end
```
```

**When to use Atlassian MCP integration:**

- ✅ Error correlates with recent deployment/release
- ✅ Stack trace points to specific files modified recently
- ✅ Need business context about why change was made
- ✅ Want to understand acceptance criteria or requirements
- ✅ Confluence pages linked for architecture/implementation guides
- ⚠️ **Optional enrichment** - Don't block if Atlassian MCP unavailable
- ⚠️ **Check availability** - Only use if MCP tools are enabled

**Benefits:**

- **Full context chain**: Sentry → Commits → PRs → Jira → Confluence
- **Understand intent**: Why was the change made vs what went wrong
- **Catch misunderstandings**: Developer intent vs actual requirements
- **Find documentation**: Architecture guides that explain correct patterns
- **Prevent recurrence**: Link to docs/guides to educate team
