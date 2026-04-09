# Problem-Solving Framework

**After gathering all data (Steps 1-6), apply systematic analysis.**

#### IDENTIFY: Determine Root Cause Candidates

**Generate possible explanations based on evidence:**

```markdown
[IDENTIFY]

**Observed symptoms:**
- [Symptom 1 from stack trace]
- [Symptom 2 from breadcrumbs]
- [Symptom 3 from tags/context]

**Possible causes:**
1. **[Cause 1]**: [Hypothesis based on stack trace]
   - Evidence: [what supports this]
   - Likelihood: [high/medium/low]

2. **[Cause 2]**: [Hypothesis based on breadcrumbs]
   - Evidence: [what supports this]
   - Likelihood: [high/medium/low]

3. **[Cause 3]**: [Hypothesis based on deployment/environment]
   - Evidence: [what supports this]
   - Likelihood: [high/medium/low]

**Correlations identified:**
- [Pattern 1: e.g., "All errors after v2.3.1 deployment"]
- [Pattern 2: e.g., "Only affects trial_users segment"]
- [Pattern 3: e.g., "All show same decline_code"]
```

**Example 1: API Timeout Error**

```markdown
[IDENTIFY]

**Observed symptoms:**
- Error: "TimeoutError: Request took longer than 30000ms"
- Stack trace: app/services/user_data_export.rb:156
- Breadcrumbs: User clicked "Export All Data" button
- Tags: database_query_time: 45000ms, user_segment: enterprise

**Possible causes:**
1. **Database query performance issue**: Query taking too long
   - Evidence: database_query_time: 45000ms (exceeds 30s timeout)
   - Likelihood: HIGH

2. **Missing database index**: Full table scan on large dataset
   - Evidence: Only affects enterprise users (larger datasets)
   - Likelihood: HIGH

3. **Increased data volume**: Recent growth in user data
   - Evidence: User segment is enterprise (more data)
   - Likelihood: MEDIUM

4. **Infrastructure issue**: Database server overloaded
   - Evidence: All timeouts on same query type
   - Likelihood: LOW (would affect all queries)

**Correlations identified:**
- User segment: 100% enterprise customers (10k+ records)
- Query time: All failures have database_query_time > 35000ms
- Timing: Errors increased 3x in last week
```

**Example 2: Authentication Error**

```markdown
[IDENTIFY]

**Observed symptoms:**
- Error: "JWT verification failed: Token expired"
- Stack trace: lib/auth/jwt_verifier.js:23
- Breadcrumbs: User idle for 2 hours, then clicked action
- Tags: browser: Chrome, environment: production

**Possible causes:**
1. **Token expiration too short**: 2-hour expiry insufficient for long sessions
   - Evidence: All errors after 2+ hours of inactivity
   - Likelihood: HIGH

2. **Clock skew between servers**: Server time mismatch
   - Evidence: Some tokens fail immediately after issue
   - Likelihood: MEDIUM

3. **Token refresh logic broken**: Not refreshing before expiry
   - Evidence: No token refresh calls in breadcrumbs
   - Likelihood: HIGH

4. **Frontend storing wrong token**: Using old/invalid token
   - Evidence: Would show different error message
   - Likelihood: LOW

**Correlations identified:**
- Timing: All errors occur 2h 5m after last successful auth
- User action: All users were idle, then performed action
- Environment: Production only (staging works fine)
```

**Example 3: Data Validation Error**

```markdown
[IDENTIFY]

**Observed symptoms:**
- Error: "ValidationError: email must be valid format"
- Stack trace: app/models/user.rb:42 in validate_email
- Breadcrumbs: User submitted signup form with email
- HTTP request: email field contains "user+tag@domain.com"

**Possible causes:**
1. **Email regex too strict**: Doesn't allow + character
   - Evidence: Request contains email with + tag
   - Likelihood: HIGH

2. **Recent validation library update**: New version stricter
   - Evidence: Check recent dependency updates
   - Likelihood: MEDIUM

3. **Internationalization issue**: Non-ASCII characters rejected
   - Evidence: Would need to check for unicode in email
   - Likelihood: LOW (email looks ASCII)

4. **Database constraint violation**: DB rejects before app validation
   - Evidence: Error is from app model, not database
   - Likelihood: LOW

**Correlations identified:**
- Pattern: 80% of errors have + character in email
- Recent change: validator gem updated 3 days ago
- User impact: Tech-savvy users (use + tags for filtering)
```

**Example (Payment error scenario):**
```markdown
[IDENTIFY]

**Observed symptoms:**
- StripeAPIError: Card declined
- All errors show "insufficient_funds"
- Started 1 hour after v2.3.1 deployment
- Only affects trial → paid conversions

**Possible causes:**
1. **Stripe API integration issue**: Change in API version or configuration
   - Evidence: All using Stripe, same error code
   - Likelihood: Medium (but would affect all users, not just trials)

2. **Payment amount calculation bug**: Code multiplying amount incorrectly
   - Evidence: All "insufficient_funds", started after deployment
   - Likelihood: High (deployment timing correlation)

3. **Feature flag or config change**: Trial conversion logic changed
   - Evidence: Only affects trial users
   - Likelihood: Medium (could be feature-specific)

4. **Database migration issue**: User payment data corrupted
   - Evidence: Users report cards work elsewhere
   - Likelihood: Low (would show different error pattern)

**Correlations identified:**
- Deployment: v2.3.1 released 2026-02-03 13:00, errors started 14:00
- User segment: 100% trial_users, 0% existing paid users
- Error pattern: 100% show "insufficient_funds" decline code
```

#### ANALYZE: Evaluate Hypotheses

**Investigate each hypothesis systematically:**

```markdown
[ANALYZE]

**Hypothesis 1: [Most likely cause]**
Testing approach:
- [ ] Check: [verification step 1]
- [ ] Check: [verification step 2]
- [ ] Expected result: [what confirms this hypothesis]

**Investigation results:**
- [Finding 1]
- [Finding 2]
- **Conclusion**: [Confirmed / Rejected / Needs more data]

**Hypothesis 2: [Second candidate]**
Testing approach:
- [ ] Check: [verification step 1]
- [ ] Check: [verification step 2]
- [ ] Expected result: [what confirms this hypothesis]

**Investigation results:**
- [Finding 1]
- [Finding 2]
- **Conclusion**: [Confirmed / Rejected / Needs more data]

**Code investigation:**
- Files examined: [list]
- Symbols analyzed: [list]
- Changes found: [description]

---

**ROOT CAUSE CONFIRMED**: [Clear, explicit statement of the confirmed root cause with evidence]

**Supporting evidence:**
- [Evidence 1 that proves this is the root cause]
- [Evidence 2 from code/data analysis]
- [Evidence 3 linking symptoms to this cause]
```

**CRITICAL**: ANALYZE phase MUST end with explicit root cause confirmation:
- ✅ State the confirmed root cause clearly and concisely
- ✅ Provide concrete evidence from code analysis
- ✅ Link the root cause to observed symptoms
- ✅ Explain WHY this is the cause, not just WHAT it is
- ❌ Do NOT proceed to DECIDE without confirming root cause
- ❌ Do NOT leave root cause ambiguous or implied

**Example (Payment error scenario):**
```markdown
[ANALYZE]

**Hypothesis 1: Payment amount calculation bug (HIGH)**
Testing approach:
- [ ] Review v2.3.1 git diff for payment-related changes
- [ ] Read payment_processor.rb:42 code (where error occurs)
- [ ] Check for amount conversion/multiplication logic
- [ ] Expected: Find code that multiplies amount by 100

**Investigation results:**
```bash
# Get Sentry issue details
sentry api /organizations/employmenthero/issues/98765/ | jq '.'

# Get latest event with stack trace
sentry api /organizations/employmenthero/issues/98765/events/latest/ | \
  jq '.entries[] | select(.type == "exception")'

# Check recent PRs
gh pr list --repo Thinkei/eh-web --search "payment merged:>=2026-02-03"
# Found: PR #456 "Fix payment amount to use dollars"

# Read the code using Serena
# (Serena tools remain unchanged)
```

**Code found:**
```ruby
# v2.3.1 NEW CODE
def charge_card(amount_in_cents)
  Stripe::Charge.create(
    amount: (amount_in_cents * 100).to_i,  # BUG!
    currency: 'usd'
  )
end
```

**Conclusion**: ✅ **CONFIRMED**
- Code multiplies cents by 100 → creates dollar amount
- 2999 cents * 100 = 299900 cents = $2999.00 charge
- Explains "insufficient_funds" (most users don't have $2999)

**Hypothesis 2: Stripe API version change (MEDIUM)**
Testing approach:
- [ ] Check Stripe API version in tags
- [ ] Compare with previous version
- [ ] Check Stripe changelog for breaking changes

**Investigation results:**
- Stripe API version: 2023-10-16 (unchanged)
- No breaking changes in recent Stripe releases

**Conclusion**: ❌ **REJECTED**
- API version unchanged
- No relevant API changes

**Hypothesis 3: Feature flag change (MEDIUM)**
Testing approach:
- [ ] Check feature flags in additional data
- [ ] Look for trial-specific flags

**Investigation results:**
- No trial-specific flags in error events
- Payment flow uses same code path for all users

**Conclusion**: ❌ **REJECTED**
- No feature flag correlation

---

**ROOT CAUSE CONFIRMED**: Double conversion bug in payment_processor.rb:42 - code multiplies cents by 100

**Supporting evidence:**
- Code analysis shows `amount_in_cents * 100` in v2.3.1 (line 42)
- This converts 2999 cents → 299900 cents ($2999.00 instead of $29.99)
- All Sentry events show "insufficient_funds" decline because $2999 exceeds user card limits
- Error timing correlates exactly with v2.3.1 deployment (1 hour after)
- Only affects trial users (the payment flow path that uses this code)
- Users report cards work elsewhere, confirming cards are valid but amounts are wrong
```

**Example 1: API Timeout Analysis**

```markdown
[ANALYZE]

**Hypothesis 1: Missing database index (HIGH)**
Testing approach:
- [ ] Check user_data_exports table schema
- [ ] Look for indexes on user_id and created_at
- [ ] Explain query plan for slow query

**Investigation:**
```bash
# Check database schema
gh api repos/Thinkei/eh-web/contents/db/schema.rb --jq '.content' | base64 -d

# Check migration history for index additions
gh search code --owner Thinkei "add_index :user_data_exports" --json path
```

**Code found:**
```ruby
# db/schema.rb - NO INDEX on user_id!
create_table "user_data_exports" do |t|
  t.integer "user_id"  # Missing index
  t.text "data"
  t.datetime "created_at"
end

# Query in code:
UserDataExport.where(user_id: user.id).order(created_at: :desc)
# This does FULL TABLE SCAN for enterprise users with 50k+ exports
```

**Conclusion:** ✅ **CONFIRMED**
- No index on user_id column
- Full table scan on 50k+ row table
- Explains 45-second query time

**Hypothesis 2: Increased data volume (MEDIUM)**
- Checked: Enterprise user data growth
- Last month: avg 10k exports/user
- This month: avg 12k exports/user
- Conclusion: ⚠️ **CONTRIBUTING FACTOR** (but not root cause)

**Root cause:** Missing database index + growing data volume
```

**Example 2: Authentication Error Analysis**

```markdown
[ANALYZE]

**Hypothesis 1: Token expiration too short (HIGH)**
Testing approach:
- [ ] Check JWT configuration for expiry time
- [ ] Calculate time between token issue and error
- [ ] Verify no token refresh happening

**Investigation:**
```bash
# Find JWT config
mcp__serena__search_for_pattern({
  substring_pattern: "JWT.*expir",
  restrict_search_to_code_files: true
})
```

**Code found:**
```javascript
// config/auth.js
const JWT_CONFIG = {
  expiresIn: '2h',  // Token expires after 2 hours
  refreshThreshold: '15m'  // Should refresh when 15min left
};

// lib/auth/refresh.js
function shouldRefreshToken(token) {
  const timeLeft = getTimeUntilExpiry(token);
  return timeLeft < JWT_CONFIG.refreshThreshold;
}
```

**Breadcrumb analysis:**
- Last auth: 14:00:00
- User idle: 14:00:01 - 16:05:00 (2h 5m)
- Action attempted: 16:05:00
- Error: "Token expired"
- **NO refresh API call in breadcrumbs!**

**Conclusion:** ✅ **CONFIRMED**
- Token expiry: 2 hours
- Refresh should trigger at 15min before expiry
- But refresh logic NOT executing (likely bug in idle detection)

**Hypothesis 2: Token refresh broken (HIGH)**
Testing approach:
- [ ] Check refresh logic in frontend
- [ ] Look for idle timeout that disables refresh

**Investigation:**
```bash
# Check frontend refresh logic
gh api repos/Thinkei/eh-web-frontend/contents/src/utils/authRefresh.ts
```

**Code found:**
```typescript
// Bug found!
function startTokenRefresh() {
  setInterval(() => {
    if (!document.hidden && shouldRefreshToken()) {  // BUG!
      refreshToken();
    }
  }, 60000);
}

// Problem: document.hidden is TRUE when tab in background
// So token never refreshes if user has tab in background!
```

**Conclusion:** ✅ **CONFIRMED - THIS IS THE BUG**
- Refresh interval runs every 60s
- But skips refresh if `document.hidden` (tab inactive)
- Users with background tab don't get token refreshed
- After 2h inactivity, token expires

**Root cause:** Token refresh skipped for inactive tabs
```

**Example 3: Email Validation Analysis**

```markdown
[ANALYZE]

**Hypothesis 1: Email regex too strict (HIGH)**
Testing approach:
- [ ] Find email validation code
- [ ] Check regex pattern
- [ ] Test with email containing +

**Investigation:**
```bash
mcp__serena__find_symbol({
  name_path_pattern: "User/validate_email",
  include_body: true
})
```

**Code found:**
```ruby
# app/models/user.rb:42
def validate_email
  # OLD REGEX (before gem update):
  # /\A[\w+\-.]+@[a-z\d\-.]+\.[a-z]+\z/i

  # NEW REGEX (after validator gem v2.0):
  EMAIL_REGEX = /\A[\w\-.]+@[a-z\d\-.]+\.[a-z]+\z/i  # REMOVED +!

  unless email =~ EMAIL_REGEX
    errors.add(:email, 'must be valid format')
  end
end
```

**Conclusion:** ✅ **CONFIRMED**
- Validator gem update removed + from allowed characters
- Email "user+tag@domain.com" no longer valid
- Explains 80% of errors (users with + tags)

**Hypothesis 2: Gem update changed regex (MEDIUM)**
Testing approach:
- [ ] Check gem changelog
- [ ] Compare v1.x vs v2.x regex

**Investigation:**
```bash
gh search code --owner validator/validator "EMAIL_REGEX" --json path
```

**Changelog:**
```
v2.0.0 (2026-02-01):
- BREAKING: Updated email regex to match RFC 5322 strict mode
- Removed support for + character (use subaddressing format instead)
```

**Conclusion:** ✅ **CONFIRMED**
- Gem update 3 days ago
- Breaking change in email validation
- We didn't test before upgrading

**Root cause:** Validator gem v2.0 breaking change + insufficient testing
```

#### DECIDE: Choose the Best Approach

**Select solution path based on confirmed root cause:**

```markdown
[DECIDE]

**Root cause being addressed:** [Restate the confirmed root cause from ANALYZE phase]

**Selected approach:** [Chosen solution]

**Rationale:**
- **How this addresses root cause**: [Explicit explanation of how solution fixes the confirmed root cause]
- **Evidence that supports this solution**: [Why we believe this will work]
- **Expected outcome**: [What will change when root cause is eliminated]

**Trade-offs:**
- **Pros**: [Benefits of this approach]
- **Cons**: [Downsides or risks]

**Alternatives considered:**
1. **[Alternative 1]**: [Why rejected - explain in relation to root cause]
2. **[Alternative 2]**: [Why rejected - explain in relation to root cause]

**Risk assessment:**
- **Impact**: [What happens if fix fails]
- **Rollback plan**: [How to undo]
- **Monitoring**: [How to verify fix works]
```

**CRITICAL**: DECIDE phase MUST explicitly reference confirmed root cause:
- ✅ Restate the root cause from ANALYZE phase at the start
- ✅ Explain how selected approach eliminates/mitigates root cause
- ✅ Show logical connection: root cause → solution mechanism → expected outcome
- ✅ Reject alternatives in context of how well they address root cause
- ❌ Do NOT select solution without linking it to root cause
- ❌ Do NOT use generic justifications ("best practice", "recommended approach")

**Example (Payment error scenario):**
```markdown
[DECIDE]

**Root cause being addressed:** Double conversion bug in payment_processor.rb:42 where code multiplies cents by 100, causing $29.99 charges to become $2999

**Selected approach:** Revert payment amount multiplication in payment_processor.rb

**Rationale:**
- **How this addresses root cause**: Removing `* 100` multiplication eliminates the double conversion. Input is already in cents (2999), so multiplying by 100 creates 299900 cents ($2999). Reverting to direct pass-through (amount: amount_in_cents) restores correct behavior where 2999 cents = $29.99.
- **Evidence that supports this solution**: v2.3.0 code worked correctly without multiplication. The bug was introduced in v2.3.1 by adding `* 100`. Removing it returns to proven-working state.
- **Expected outcome**: All payment amounts will be correct. Trial users converting to $29.99/month plan will be charged 2999 cents ($29.99) instead of 299900 cents ($2999). "Insufficient_funds" errors will stop because charge amounts match user expectations.

**Trade-offs:**
- **Pros**:
  - Fast fix (single line change)
  - Low risk (reverting to known-good state)
  - Stops ongoing user impact immediately
  - Directly eliminates root cause
- **Cons**:
  - Doesn't add validation to prevent future similar bugs
  - Need separate PR for additional safeguards

**Alternatives considered:**
1. **Full rollback of v2.3.1**:
   - Why rejected: Too broad. Root cause is one line in one file. Rolling back entire release would lose other unrelated fixes and features in v2.3.1.
2. **Add validation instead of revert**:
   - Why rejected: Validation doesn't fix root cause - amounts would still be wrong. Takes longer to implement, users still affected during development. Revert is immediate fix; validation can be added later.
3. **Disable trial conversions temporarily**:
   - Why rejected: Doesn't address root cause, just masks it. High business impact (lost revenue). Better to fix the actual bug than disable feature.

**Risk assessment:**
- **Impact if fix fails**: Users still can't convert from trial to paid, revenue loss continues
- **Rollback plan**: Re-deploy v2.3.1 if revert causes other issues (e.g., if some callers expect multiplication)
- **Monitoring**:
  - Watch Sentry for payment errors (should drop to 0)
  - Monitor successful trial → paid conversions (should resume)
  - Alert on any new payment-related errors
```

**Example 1: Database Index Decision**

```markdown
[DECIDE]

**Selected approach:** Add composite index on (user_id, created_at)

**Rationale:**
- Root cause: Missing index causing full table scans
- Composite index covers both WHERE and ORDER BY clauses
- Can be added without downtime (concurrent index)
- Immediate performance improvement (50k+ rows → indexed lookup)

**Trade-offs:**
- **Pros**:
  - Fast fix (single migration)
  - No code changes needed
  - Works retroactively for all users
  - Can add index concurrently (no table lock)
- **Cons**:
  - Index size: ~500MB additional storage
  - Index build time: ~10 minutes on production
  - Doesn't address data growth long-term

**Alternatives considered:**
1. **Add pagination to export list**:
   - Why rejected: Requires frontend + backend changes, takes days
   - User still needs to see all exports eventually
2. **Archive old exports**:
   - Why rejected: Users need historical data
   - Business requirement to keep all exports
3. **Switch to Elasticsearch**:
   - Why rejected: Over-engineering, high complexity
   - Index solves immediate problem
4. **Increase timeout to 60s**:
   - Why rejected: Doesn't fix root cause, query still slow
   - Bad user experience to wait 60s

**Risk assessment:**
- **Impact if fix fails**: Query still slow (but not worse)
- **Rollback plan**: Drop index if it doesn't help (instant)
- **Monitoring**:
  - Query time should drop from 45s to <1s
  - Sentry timeout errors should stop
  - Database CPU should decrease
```

**Example 2: Token Refresh Decision**

```markdown
[DECIDE]

**Selected approach:** Remove `document.hidden` check from refresh logic

**Rationale:**
- Root cause: Token refresh skipped for background tabs
- Simple fix: Remove condition blocking refresh
- Tokens should refresh regardless of tab visibility
- Low risk: Existing refresh logic proven to work

**Trade-offs:**
- **Pros**:
  - One-line fix (remove if condition)
  - Fixes issue for all background tab users
  - No new logic introduced
  - Can deploy immediately
- **Cons**:
  - Slightly more API calls (refresh happens in background)
  - ~1% increase in auth API traffic
  - Users still idle for 2h+ will expire (but now rare)

**Alternatives considered:**
1. **Increase token expiry to 8 hours**:
   - Why rejected: Security concern (long-lived tokens)
   - Doesn't fix refresh logic bug
2. **Use web workers for background refresh**:
   - Why rejected: Over-engineering, high complexity
   - Simple fix addresses root cause
3. **Add "keep-alive" ping from frontend**:
   - Why rejected: Adds unnecessary network traffic
   - Doesn't fix the actual bug
4. **Store tokens in sessionStorage with expiry check**:
   - Why rejected: Doesn't solve refresh issue
   - Just changes symptom, not cause

**Risk assessment:**
- **Impact if fix fails**: Same errors continue
- **Rollback plan**: Revert commit, redeploy previous version (<5 min)
- **Monitoring**:
  - JWT expiry errors should drop to 0
  - Auth API refresh call rate may increase 1-2%
  - No new errors introduced
```

**Example 3: Email Validation Decision**

```markdown
[DECIDE]

**Selected approach:** Revert to validator gem v1.9 + add custom regex

**Rationale:**
- Root cause: v2.0 gem breaking change
- Need to support + character (business requirement)
- Revert gives us time to test v2.0 properly
- Add custom regex to override gem default

**Trade-offs:**
- **Pros**:
  - Immediate fix (users can sign up again)
  - Keeps + character support
  - Proven regex from v1.9
  - Buys time for proper v2.0 migration
- **Cons**:
  - Stuck on older gem version temporarily
  - May miss v2.0 bug fixes
  - Need follow-up work to upgrade properly

**Alternatives considered:**
1. **Keep v2.0 and reject + emails**:
   - Why rejected: Business team says + tags are important
   - Would lose tech-savvy users (20% of signups)
2. **Fork validator gem and customize**:
   - Why rejected: Maintenance burden too high
   - Custom regex achieves same result
3. **Use different validation library**:
   - Why rejected: High risk, requires testing
   - Revert is safer short-term fix
4. **Tell users to not use + character**:
   - Why rejected: Bad user experience
   - RFC 5322 allows + in emails

**Risk assessment:**
- **Impact if fix fails**: Still can't support + emails
- **Rollback plan**: Re-upgrade to v2.0, find different solution
- **Monitoring**:
  - Signup success rate should return to baseline
  - Validation errors should drop to 0
  - No security issues from older gem version

**Follow-up plan:**
- Test v2.0 thoroughly in staging (1 week)
- Configure v2.0 to allow + character
- Upgrade to v2.0 with proper config (2 weeks)
```

#### PLAN: Create Action Steps

**Define implementation with verification and detailed rationale:**

```markdown
[PLAN]

**Immediate actions:**
1. [ ] [Action 1] [complexity: low/medium/high]
   - Owner: [who]
   - Timeline: [when]
   - Dependencies: [what's needed]
   - **Why this helps**: [Detailed explanation of how this action directly addresses the root cause and resolves the issue]

2. [ ] [Action 2] [complexity: low/medium/high]
   - Owner: [who]
   - Timeline: [when]
   - Dependencies: [what's needed]
   - **Why this helps**: [Detailed explanation of how this action directly addresses the root cause and resolves the issue]

**Follow-up actions:**
1. [ ] [Long-term fix]
   - **Why this helps**: [Explanation of how this prevents recurrence]
2. [ ] [Prevention measure]
   - **Why this helps**: [Explanation of how this prevents similar issues]

**Verification:**
- Pre-deployment: [Tests to run]
- Post-deployment: [Metrics to monitor]
- Success criteria: [What confirms fix works]

**Rollback plan:**
- Trigger: [What indicates need to rollback]
- Steps: [How to rollback]
- Timeline: [How fast can we rollback]
```

**CRITICAL**: Each action MUST include a "Why this helps" explanation that:
- ✅ Directly links the action to the root cause identified in ANALYZE phase
- ✅ Explains the mechanism by which this action resolves the issue
- ✅ Shows evidence or reasoning for why this will work
- ✅ Addresses specific symptoms observed in the error data
- ❌ Does NOT use vague statements like "this should fix it" or "this is best practice"
- ❌ Does NOT skip the explanation ("obvious" fixes still need rationale)

**Example (Payment error scenario):**
```markdown
[PLAN]

**Immediate actions:**
1. [ ] Create hotfix branch from v2.3.0 [complexity: low]
   - Owner: On-call engineer
   - Timeline: Immediate (5 min)
   - Command: `git checkout -b hotfix/payment-amount-calculation v2.3.0`
   - **Why this helps**: Branching from v2.3.0 (before the bug) ensures we start with known-good code. The bug was introduced in v2.3.1, so v2.3.0 is the last working version. This eliminates the double-conversion bug (amount_in_cents * 100) that's causing $29.99 charges to become $2999.

2. [ ] Revert payment_processor.rb:42 change [complexity: low]
   - Owner: On-call engineer
   - Timeline: Immediate (5 min)
   - Change: Remove `* 100` multiplication
   - **Why this helps**: The root cause is the code multiplying cents by 100 (2999 cents * 100 = 299900 cents = $2999). Removing this multiplication fixes the calculation. All Sentry events show "insufficient_funds" decline code because users don't have $2999 to pay - they expect $29.99. This single-line change directly addresses the root cause confirmed in our code analysis.

3. [ ] Add regression test [complexity: medium]
   - Owner: On-call engineer
   - Timeline: Before deploy (30 min)
   - Test: Verify $29.99 charge creates 2999 cents Stripe charge
   - **Why this helps**: Prevents this exact bug from being reintroduced in the future. The test will fail if anyone adds back the `* 100` multiplication. Since the root cause was a misunderstanding about whether the amount was in dollars or cents, a test that verifies the correct behavior (cents in → cents to Stripe) ensures the contract is clear and validated.

4. [ ] Deploy hotfix to production [complexity: low]
   - Owner: On-call engineer
   - Timeline: After tests pass (10 min)
   - Command: Deploy via standard pipeline
   - **Why this helps**: Gets the fix to users immediately. The error affects 47 events/day (23 users), all trial users trying to convert to paid. Each hour of delay means ~2 more failed conversions and potential revenue loss. Fast deployment stops ongoing user impact.

5. [ ] Monitor Sentry errors [complexity: low]
   - Owner: On-call engineer
   - Timeline: 1 hour post-deploy
   - Watch: Payment error rate should drop to 0
   - **Why this helps**: Validates that our fix actually resolves the issue in production. If errors don't stop, it means either: (1) we misidentified the root cause, (2) there's a deployment issue, or (3) there's another related bug. Monitoring for 1 hour gives enough time for several conversion attempts to confirm success.

**Follow-up actions (next 24-48h):**
1. [ ] Add amount validation to prevent excessive charges
   - **Why this helps**: Adds a safety check (e.g., `if amount > 100000 raise Error`) to catch future calculation bugs before they reach production. If someone introduces a similar bug, the validation will prevent $2999 charges from being attempted. Acts as a circuit breaker for unreasonable payment amounts.

2. [ ] Add monitoring alert for spike in payment failures
   - **Why this helps**: The error went undetected for 1 hour after deployment. An alert triggered when payment failures exceed 10/hour would have caught this immediately. Reduces time-to-detection for similar issues from hours to minutes, limiting user impact.

3. [ ] Review code review process (how did bug get merged?)
   - **Why this helps**: The PR that introduced the bug passed code review without catching the double-conversion error. Understanding what was missed (e.g., no reviewer tested the payment flow, acceptance criteria unclear) prevents similar bugs. May reveal need for required integration tests or payment-specific review checklist.

4. [ ] Contact affected users about failed charge attempts
   - **Why this helps**: 23 users experienced failed payment attempts and may have abandoned the conversion thinking their card was invalid. Proactive outreach ("Issue resolved, please try again") recovers potentially lost conversions and demonstrates good customer service. Reduces churn from the bug's impact.

**Verification:**
- **Pre-deployment tests:**
  - [ ] Unit test: `PaymentProcessor#charge_card(2999)` creates $29.99 charge
  - [ ] Integration test: Trial → paid conversion succeeds
  - [ ] Manual test: Complete payment flow in staging

- **Post-deployment monitoring:**
  - [ ] Sentry: Payment errors drop from 47/day to 0
  - [ ] Metrics: Trial conversion success rate returns to baseline
  - [ ] Stripe dashboard: Charge amounts are correct ($29.99, not $2999)

- **Success criteria:**
  - Zero payment errors in Sentry for 2 hours post-deploy
  - 5+ successful trial → paid conversions
  - No customer support tickets about payment issues

**Rollback plan:**
- **Trigger**: New payment errors OR successful conversions don't resume
- **Steps**:
  1. Redeploy v2.3.1
  2. Disable trial → paid conversions temporarily
  3. Investigate new issue
- **Timeline**: Can rollback in <5 minutes via deployment pipeline

**Communication:**
- [ ] Notify on-call team in Slack
- [ ] Update Sentry issue #98765 with fix details
- [ ] Update Jira ticket if linked
- [ ] Post-mortem: Schedule within 48h to prevent recurrence
```

**Example 1: Database Index Implementation Plan**

```markdown
[PLAN]

**Immediate actions:**
1. [ ] Create migration for composite index [complexity: low]
   - Owner: Backend engineer
   - Timeline: 10 minutes
   - Code:
     ```ruby
     add_index :user_data_exports, [:user_id, :created_at],
       algorithm: :concurrently  # No table lock
     ```
   - **Why this helps**: Root cause is full table scan on 50k+ row table. The query `WHERE user_id = X ORDER BY created_at DESC` currently scans entire table because there's no index on user_id. A composite index on (user_id, created_at) allows the database to: (1) quickly find all rows for specific user_id via index lookup, (2) retrieve them already sorted by created_at (no separate sort needed). This reduces query time from 45 seconds (full scan) to <1 second (index lookup). Using `algorithm: :concurrently` prevents table locking, allowing zero-downtime deployment.

2. [ ] Test migration in staging [complexity: low]
   - Owner: Backend engineer
   - Timeline: 15 minutes
   - Verify: Query plan shows index usage
   - **Why this helps**: Confirms the database query optimizer will actually USE the new index for our query pattern. Without verification, the index might exist but not be used (e.g., if query planner chooses different strategy). Running EXPLAIN on the query shows "Index Scan using index_user_data_exports_on_user_id_and_created_at" instead of "Seq Scan", proving the fix will work before production deployment.

3. [ ] Deploy migration to production [complexity: medium]
   - Owner: DevOps + Backend engineer
   - Timeline: 30 minutes (index build time)
   - Command: `rake db:migrate`
   - Monitor: Database CPU and query times
   - **Why this helps**: Applies the fix to production where the actual timeouts are occurring. The 30-minute index build is acceptable because: (1) concurrent algorithm means no downtime, (2) queries continue to work during build (just still slow), (3) once complete, all subsequent queries immediately benefit. Monitoring during build ensures no unexpected database load issues.

4. [ ] Monitor Sentry errors [complexity: low]
   - Owner: On-call engineer
   - Timeline: 1 hour post-deploy
   - Watch: Timeout errors should stop
   - **Why this helps**: Validates the fix resolves the user-facing issue. The Sentry errors are "TimeoutError: Request took longer than 30000ms" - if index works, queries complete in <1s, well under 30s timeout. Monitoring for 1 hour allows multiple enterprise users (the affected segment) to access exports and confirm zero timeout errors, proving the fix is effective.

**Follow-up actions (next 1-2 weeks):**
1. [ ] Implement pagination for exports list
   - **Why this helps**: While the index fixes current timeouts, enterprise users with 50k+ exports will still load a large dataset. Pagination (e.g., 50 exports per page) reduces memory usage and improves initial page load time. Prevents future performance degradation as data continues to grow beyond 50k exports per user.

2. [ ] Add monitoring for query performance
   - **Why this helps**: The index solves today's problem but data growth is ongoing (10k→12k exports/user last month). Performance monitoring tracks query times over weeks/months, alerting when times creep up toward timeout threshold again. Enables proactive optimization before users experience errors.

3. [ ] Set up alerts for queries >5s
   - **Why this helps**: Catches performance regressions early. If query time increases from <1s to >5s, it indicates: (1) index not being used (e.g., after schema change), (2) new query pattern bypassing index, or (3) data volume overwhelming even indexed queries. 5s threshold gives warning before 30s timeout limit is reached.

4. [ ] Review other large tables for missing indexes
   - **Why this helps**: This issue reveals a gap in database performance review process. Other tables may have similar missing indexes causing slow queries not yet severe enough to timeout. Proactive audit prevents similar issues in other features before they impact users.

**Verification:**
- **Pre-deployment tests:**
  - [ ] EXPLAIN query shows index usage in staging
  - [ ] Query time drops from 45s to <1s in staging
  - [ ] Index build completes successfully

- **Post-deployment monitoring:**
  - [ ] Sentry: Timeout errors drop to 0
  - [ ] Database: Query time <1s on production
  - [ ] Database: CPU usage decreases
  - [ ] New Relic: Export page load time improves

- **Success criteria:**
  - Zero timeout errors for 24 hours
  - All export queries complete in <2s
  - No customer support tickets about slow exports

**Rollback plan:**
- **Trigger**: Index doesn't improve performance OR causes production issues
- **Steps**:
  1. Drop index: `DROP INDEX CONCURRENTLY index_name`
  2. Investigate why index didn't help
  3. Consider alternative solutions (pagination, archiving)
- **Timeline**: Can drop index in <1 minute

**Communication:**
- [ ] Notify engineering team in #backend channel
- [ ] Update Sentry issue with fix details and migration
- [ ] Post in #customer-success about fix
- [ ] Add to weekly engineering update
```

**Example 2: Token Refresh Fix Implementation Plan**

```markdown
[PLAN]

**Immediate actions:**
1. [ ] Remove document.hidden check [complexity: low]
   - Owner: Frontend engineer
   - Timeline: 5 minutes
   - File: src/utils/authRefresh.ts:42
   - Change:
     ```diff
     - if (!document.hidden && shouldRefreshToken()) {
     + if (shouldRefreshToken()) {
     ```

2. [ ] Add unit test for background refresh [complexity: medium]
   - Owner: Frontend engineer
   - Timeline: 20 minutes
   - Test: Mock document.hidden=true, verify refresh still runs

3. [ ] Deploy to staging and test [complexity: low]
   - Owner: Frontend engineer
   - Timeline: 15 minutes
   - Test: Leave tab inactive 1h 50m, verify refresh happens

4. [ ] Deploy to production [complexity: low]
   - Owner: Frontend engineer + DevOps
   - Timeline: 10 minutes
   - Deploy via CI/CD pipeline

5. [ ] Monitor auth errors [complexity: low]
   - Owner: On-call engineer
   - Timeline: 2 hours post-deploy
   - Watch: JWT expiry errors should stop

**Follow-up actions (next week):**
1. [ ] Add E2E test for long idle sessions
2. [ ] Review other document.hidden usages
3. [ ] Consider adding token expiry warning to UI
4. [ ] Document token refresh behavior

**Verification:**
- **Pre-deployment tests:**
  - [ ] Unit test: Refresh works when document.hidden=true
  - [ ] Staging test: Background tab refreshes token
  - [ ] Manual test: Idle 2h in background, then action succeeds

- **Post-deployment monitoring:**
  - [ ] Sentry: JWT expiry errors drop from 50/day to ~0
  - [ ] Auth API: Refresh call rate may increase 1-2%
  - [ ] User reports: No complaints about session timeouts

- **Success criteria:**
  - <5 JWT expiry errors per day (down from 50)
  - No new authentication errors introduced
  - Users can stay logged in with background tabs

**Rollback plan:**
- **Trigger**: New auth errors OR refresh call rate increases >10%
- **Steps**:
  1. Revert commit in Git
  2. Deploy previous version via CI/CD
  3. Investigate unexpected behavior
- **Timeline**: <5 minutes to rollback

**Communication:**
- [ ] Notify #frontend team about fix
- [ ] Update Sentry issue with PR link
- [ ] Post in #customer-success: "Session timeout fix deployed"
- [ ] Update auth documentation with correct behavior
```

**Example 3: Email Validation Fix Implementation Plan**

```markdown
[PLAN]

**Immediate actions:**
1. [ ] Revert validator gem to v1.9 [complexity: low]
   - Owner: Backend engineer
   - Timeline: 5 minutes
   - File: Gemfile
   - Change: `gem 'validator', '~> 1.9'`

2. [ ] Add custom email regex [complexity: low]
   - Owner: Backend engineer
   - Timeline: 10 minutes
   - File: app/models/user.rb
   - Code:
     ```ruby
     # Custom regex that allows + character
     EMAIL_REGEX = /\A[\w+\-.]+@[a-z\d\-]+(\.[a-z\d\-]+)*\.[a-z]+\z/i
     validates :email, format: { with: EMAIL_REGEX }
     ```

3. [ ] Add test for + character emails [complexity: low]
   - Owner: Backend engineer
   - Timeline: 10 minutes
   - Test cases:
     - "user+tag@example.com" → valid
     - "user.name+tag@example.com" → valid

4. [ ] Deploy to staging and test [complexity: low]
   - Owner: Backend engineer
   - Timeline: 15 minutes
   - Test: Signup with + email succeeds

5. [ ] Deploy to production [complexity: low]
   - Owner: Backend engineer + DevOps
   - Timeline: 10 minutes
   - Deploy via standard pipeline

6. [ ] Monitor signup errors [complexity: low]
   - Owner: On-call engineer
   - Timeline: 1 hour post-deploy
   - Watch: Validation errors should stop

**Follow-up actions (next 2 weeks):**
1. [ ] Test validator v2.0 in staging thoroughly
2. [ ] Find v2.0 config to allow + character
3. [ ] Upgrade to v2.0 with proper configuration
4. [ ] Add comprehensive email validation tests

**Verification:**
- **Pre-deployment tests:**
  - [ ] RSpec: Test suite passes with v1.9
  - [ ] Staging: Signup with user+tag@example.com succeeds
  - [ ] Security: No regressions in email validation

- **Post-deployment monitoring:**
  - [ ] Sentry: Email validation errors drop to 0
  - [ ] Metrics: Signup success rate returns to baseline
  - [ ] Support: No tickets about email rejection

- **Success criteria:**
  - Zero email validation errors for 48 hours
  - Signup conversion rate returns to 95%+
  - Users with + emails can register successfully

**Rollback plan:**
- **Trigger**: New validation errors OR security issues
- **Steps**:
  1. Revert to v2.0 temporarily
  2. Update custom regex to fix issue
  3. Redeploy fixed version
- **Timeline**: <10 minutes to rollback

**Communication:**
- [ ] Notify #backend team about gem revert
- [ ] Update Sentry issue with resolution
- [ ] Email affected users: "Signup issue resolved"
- [ ] Post in #customer-success about fix
- [ ] Create Jira ticket for v2.0 upgrade investigation
- [ ] Post-mortem: Why didn't we test gem upgrade?

**Post-mortem actions:**
- [ ] Add gem upgrade checklist to docs
- [ ] Require staging testing for all major version upgrades
- [ ] Set up dependabot alerts for breaking changes
- [ ] Add email validation to E2E test suite
```
