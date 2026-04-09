---
name: "sentry-investigation"
description: "Use when: user provides Sentry URL (*.sentry.io/issues/*), investigating production errors, analyzing stack traces, Jira issues contain Sentry links, or combining business context with technical error details."
model: sonnet
---

# Sentry Investigation

Systematic approach for investigating Sentry errors by combining technical analysis (stack traces, breadcrumbs), business context (Jira tickets, Confluence docs), and code investigation (Serena semantic navigation).

## When to Use

- User provides Sentry URL (`*.sentry.io/issues/*`)
- Investigating production errors or exceptions
- Analyzing stack traces and error context
- User provides Jira URL that may contain Sentry links
- Need to understand error frequency, impact, or user journey
- Combining business context (Jira) with technical details (Sentry)

## Quick Reference

| Phase | File | Purpose |
|-------|------|---------|
| **Setup** | [sentry-cli-setup.md](sentry-cli-setup.md) | Install Sentry CLI, authenticate with OAuth or API token |
| **Phase 0** | [investigation-workflow.md](investigation-workflow.md) | Find related commits → Extract ticket IDs → Fetch Jira/Confluence context |
| **Phase 1** | [investigation-workflow.md](investigation-workflow.md) | Data collection: issue overview, stack trace, breadcrumbs, HTTP request, tags, context |
| **Phase 2** | [problem-solving-framework.md](problem-solving-framework.md) | Systematic analysis: IDENTIFY → ANALYZE → DECIDE → PLAN |
| **Integration** | [integration-patterns.md](integration-patterns.md) | Combine with Context Discovery, Serena, GitHub CLI, Atlassian MCP |
| **API Reference** | [sentry-api-reference.md](sentry-api-reference.md) | Sentry REST API endpoints and common operations |
| **Examples** | [investigation-examples.md](investigation-examples.md) | Complete investigation walkthroughs |
| **Best Practices** | [best-practices.md](best-practices.md) | Quality standards and systematic approach |
| **Jira Integration** | [jira-integration.md](jira-integration.md) | Auto-detect and fetch Sentry errors from Jira tickets |

## Core Pattern

```bash
# ❌ WRONG - Requires authentication
WebFetch("https://org.sentry.io/issues/123/")

# ✅ CORRECT - Use Sentry REST API
sentry api /organizations/org/issues/123/ | jq '.'
```

## Implementation

### 1. Setup (First Time Only)

See sentry-cli-setup.md for:
- Installing Sentry CLI via npm or script
- Authenticating with OAuth device flow or API token
- Verifying authentication works

### 2. Investigation Workflow

**Phase 0: Business Context** (See [investigation-workflow.md](investigation-workflow.md))
- Find commits affecting error location → Extract ticket IDs → Fetch Jira + Confluence context

**Phase 1: Data Collection** (See [investigation-workflow.md](investigation-workflow.md))
1. Fetch issue overview (frequency, impact, timeline)
2. Analyze stack trace (CRITICAL - identify code location)
3. Examine breadcrumbs (user journey before error)
4. Review HTTP request details
5. Inspect tags and context (environment, release)
6. Examine additional data (custom app-specific)

**Phase 2: Systematic Analysis** (See [problem-solving-framework.md](problem-solving-framework.md))
1. **IDENTIFY**: Determine root cause candidates based on evidence
2. **ANALYZE**: Evaluate hypotheses through code investigation (use Serena)
3. **DECIDE**: Choose the best approach (quick fix vs comprehensive solution)
4. **PLAN**: Create actionable steps with testing strategy

### 3. Output Format

See [investigation-workflow.md](investigation-workflow.md) for complete structured output template including all sections.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Using WebFetch on Sentry URLs | Always use `sentry api` - Sentry requires authentication |
| Skipping business context (Phase 0) | Find related Jira tickets first - reveals "why" behind the change |
| Reading only latest event | Check multiple events - stack trace may vary |
| Not using Serena for code investigation | After identifying file/line from stack trace, use Serena to examine code |
| Incomplete output | Use structured template with all 11 sections from investigation-workflow.md |

## Integration with Other Skills

- **Context Discovery**: Find related Confluence documentation after identifying error pattern
- **Serena Semantic Code**: Navigate to error location, find references, propose fixes
- **GitHub CLI**: Find recent commits/PRs affecting error location, link errors to code changes
- **Atlassian MCP**: Auto-fetch Sentry errors when investigating Jira tickets

See [integration-patterns.md](integration-patterns.md) for detailed workflows.

## Getting Started

1. Authenticate: `sentry auth login` (see [sentry-cli-setup.md](sentry-cli-setup.md))
2. Test: `sentry api /organizations/ | jq '.[].slug'`
3. Follow [investigation-workflow.md](investigation-workflow.md) for first investigation
