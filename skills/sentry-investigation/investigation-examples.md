# Investigation Examples

Complete investigation walkthroughs showing the end-to-end process.

## Complete Investigation Example

**Scenario:** User reports "Payment failed" error

### Step-by-Step Investigation

```bash
# User provides: https://employmenthero.sentry.io/issues/98765/

# Setup
ORG_SLUG="employmenthero"
ISSUE_ID="98765"

# Step 1: Fetch issue overview
sentry api /organizations/$ORG_SLUG/issues/$ISSUE_ID/?statsPeriod=24h | \
  jq '{error: .title, count, userCount, firstSeen, lastSeen, status, level}'

/**
 * Result:
 * - Error: "StripeAPIError: Card declined"
 * - Frequency: 47 events, 23 users affected (last 24h)
 * - First seen: 2026-02-03 14:00 UTC
 * - Last seen: 2026-02-04 10:30 UTC
 * - Trending: Increasing (was 5 events/day, now 47)
 */

# Step 2: Analyze stack trace
sentry api /organizations/$ORG_SLUG/issues/$ISSUE_ID/events/latest/ > event.json

jq '.entries[] | select(.type == "exception")' event.json

/**
 * Stack Trace:
 * 1. app/services/payment_processor.rb:42 in `charge_card`
 * 2. app/services/subscription_service.rb:28 in `process_payment`
 * 3. app/controllers/subscriptions_controller.rb:15 in `create`
 * 4. actionpack-7.0.0/lib/action_controller/metal/basic_implicit_render.rb:6
 *
 * Analysis:
 * - Error in our code: payment_processor.rb:42
 * - Call path: Controller → SubscriptionService → PaymentProcessor
 * - Top frame is application code (not library)
 */

# Step 3: Examine breadcrumbs
jq '.entries[] | select(.type == "breadcrumbs") | .data.values' event.json

/**
 * Breadcrumbs (latest event):
 * 1. [14:28:30] Navigation: /pricing
 * 2. [14:28:35] Click: "Upgrade to Premium" button
 * 3. [14:28:36] Navigation: /checkout
 * 4. [14:28:40] Input: Card details entered
 * 5. [14:28:42] Click: "Complete Payment" button
 * 6. [14:28:43] HTTP: POST /api/subscriptions (200 OK)
 * 7. [14:28:44] HTTP: POST https://api.stripe.com/v1/charges (402 Payment Required)
 * 8. [14:28:44] ERROR: StripeAPIError thrown
 *
 * Pattern: Normal checkout flow, Stripe API returned 402
 */

// Step 4: Review HTTP request
/**
 * Request (from event context):
 * - Method: POST
 * - URL: /api/subscriptions
 * - Headers:
 *   - Content-Type: application/json
 *   - Authorization: Bearer eyJ...
 * - Body:
 *   {
 *     "plan_id": "premium_monthly",
 *     "payment_method": "card_abc123",
 *     "amount": 2999
 *   }
 *
 * Observation: Request looks valid, amount is in cents (correct)
 */

// Step 5: Inspect tags and context
/**
 * Tags:
 * - environment: production
 * - release: v2.3.1 (deployed 2026-02-03 13:00)
 * - user_segment: trial_users
 * - payment_method: stripe
 *
 * Context:
 * - runtime: { name: "ruby", version: "3.2.0" }
 * - stripe_api_version: "2023-10-16"
 *
 * KEY FINDING: Error started after v2.3.1 deployment!
 * All affected users are trial_users converting to paid
 */

// Step 6: Examine additional data
/**
 * Extra data:
 * {
 *   "stripe_error_code": "card_declined",
 *   "stripe_error_message": "Your card was declined",
 *   "stripe_decline_code": "insufficient_funds",
 *   "user_id": "user_123",
 *   "subscription_plan": "premium_monthly",
 *   "amount_attempted": 2999,
 *   "idempotency_key": "sub_create_abc123"
 * }
 *
 * CRITICAL: All errors have decline_code "insufficient_funds"
 * But users report cards have funds available!
 */
```

### Investigation Output

```markdown
# Sentry Issue #98765: StripeAPIError - Card Declined

## 1. Overview
- **Error**: StripeAPIError: Card declined
- **Frequency**: 47 events in last 24h (23 users affected)
- **Trend**: ⬆️ Increasing (5/day → 47/day)
- **First Seen**: 2026-02-03 14:00 UTC
- **Deployment Correlation**: Started 1 hour after v2.3.1 release

## 2. Stack Trace Analysis
**Error Location**: app/services/payment_processor.rb:42
**Function**: `PaymentProcessor#charge_card`

**Call Chain**:
1. `PaymentProcessor#charge_card` (error here)
2. `SubscriptionService#process_payment`
3. `SubscriptionsController#create`

**Assessment**: Error in our payment processing code, not Stripe library

## 3. User Journey
1. User visits /pricing page
2. Clicks "Upgrade to Premium"
3. Enters card details on /checkout
4. Clicks "Complete Payment"
5. **Error occurs during Stripe charge**

**Pattern**: Consistent across all events - error during payment submission

## 4. HTTP Request
- **Endpoint**: POST /api/subscriptions
- **Payload Valid**: ✅ Amount in cents, valid plan_id
- **Auth**: ✅ Bearer token present
- **No issues with request format**

## 5. Environment Context
- **Environment**: Production only (not in staging)
- **Release**: v2.3.1 (deployed 2026-02-03 13:00 UTC)
- **Affected Users**: 100% are trial_users converting to paid
- **Payment Method**: All using Stripe

**KEY INSIGHT**: Error started exactly 1 hour after v2.3.1 deployment

## 6. Additional Data
**Stripe Response**:
- Error code: `card_declined`
- Decline code: `insufficient_funds` (all events)
- API version: 2023-10-16

**SUSPICIOUS**: Users report cards work elsewhere, but all show "insufficient_funds"

## 7. IDENTIFY: Root Cause Candidates

**Possible causes:**
1. **Payment amount calculation bug**: Code multiplying amount incorrectly
   - Evidence: Started after v2.3.1, all "insufficient_funds", only trial users
   - Likelihood: **HIGH**

2. **Stripe API integration issue**: Change in API version or config
   - Evidence: All using Stripe, same error code
   - Likelihood: **MEDIUM** (but would affect all users)

3. **Feature flag or config change**: Trial conversion logic changed
   - Evidence: Only affects trial users
   - Likelihood: **MEDIUM**

4. **Database migration issue**: User payment data corrupted
   - Evidence: Users report cards work elsewhere
   - Likelihood: **LOW**

**Correlations:**
- Deployment: v2.3.1 @ 13:00, errors @ 14:00 (1hr correlation)
- User segment: 100% trial_users, 0% existing paid users
- Error pattern: 100% "insufficient_funds" decline code

## 8. ANALYZE: Hypothesis Investigation

**Hypothesis 1: Payment amount calculation bug (HIGH)**
```bash
# Check recent PRs
gh pr list --repo Thinkei/eh-web --search "payment merged:>=2026-02-03"
# Found: PR #456 "Fix payment amount to use dollars"

# Read code at error location
mcp__serena__find_symbol({
  name_path_pattern: "PaymentProcessor/charge_card",
  relative_path: "app/services/payment_processor.rb",
  include_body: true
})
```

**Code found:**
```ruby
def charge_card(amount_in_cents)
  Stripe::Charge.create(
    amount: (amount_in_cents * 100).to_i,  # BUG!
    currency: 'usd'
  )
end
```

**Conclusion:** ✅ **CONFIRMED**
- Code multiplies cents by 100 (2999 → 299900 cents = $2999)
- Explains "insufficient_funds" pattern

**Hypothesis 2: Stripe API version (MEDIUM)**
- Checked: API version 2023-10-16 (unchanged)
- Conclusion: ❌ **REJECTED**

**Root cause confirmed:** Double conversion bug in payment_processor.rb:42

## 9. DECIDE: Solution Approach

**Selected approach:** Revert `* 100` multiplication in payment_processor.rb

**Rationale:**
- Simple one-line fix
- Returns to known-good v2.3.0 behavior
- Can deploy immediately
- Low risk

**Trade-offs:**
- **Pros**: Fast, safe, stops user impact
- **Cons**: Doesn't add validation for future prevention

**Alternatives considered:**
1. **Full rollback of v2.3.1**: Too broad, loses other fixes
2. **Add validation**: Takes longer, users still affected
3. **Disable conversions**: Too high business impact

## 10. PLAN: Action Steps

**Immediate actions:**
1. [ ] Create hotfix branch from v2.3.0 [complexity: low]
2. [ ] Revert payment_processor.rb:42 change [complexity: low]
3. [ ] Add regression test for amount calculation [complexity: medium]
4. [ ] Deploy hotfix to production [complexity: low]
5. [ ] Monitor Sentry for 1 hour post-deploy [complexity: low]

**Verification:**
- Pre-deployment: Unit test $29.99 creates 2999 cents charge
- Post-deployment: Sentry errors drop to 0, conversions resume
- Success criteria: 0 errors + 5+ successful conversions in 2 hours

**Rollback plan:**
- Trigger: New errors OR conversions don't resume
- Steps: Redeploy v2.3.1, disable conversions, investigate
- Timeline: <5 minutes via deployment pipeline

## 11. Prevention

- Add amount validation (max charge sanity check)
- Add monitoring alert for payment failure spikes
- Improve code review process for payment changes
- Add integration test for trial → paid conversion flow
```

### Code Investigation Results

```typescript
// After investigation, using Serena to check the code:
const symbol = await mcp__serena__find_symbol({
  name_path_pattern: "PaymentProcessor/charge_card",
  relative_path: "app/services/payment_processor.rb",
  include_body: true
});

/**
 * Found bug in v2.3.1:
 *
 * OLD CODE (v2.3.0):
 * def charge_card(amount_in_cents)
 *   Stripe::Charge.create(
 *     amount: amount_in_cents,  # Already in cents
 *     currency: 'usd'
 *   )
 * end
 *
 * NEW CODE (v2.3.1 - BUG):
 * def charge_card(amount_in_cents)
 *   Stripe::Charge.create(
 *     amount: (amount_in_cents * 100).to_i,  # DOUBLE CONVERSION!
 *     currency: 'usd'
 *   )
 * end
 *
 * RESULT: $29.99 (2999 cents) becomes $2999.00 charge!
 * Root cause: Developer assumed amount was in dollars, not cents
 */
```

**Fix**: Revert the `* 100` multiplication in payment_processor.rb:42

**Lesson**: Comprehensive Sentry investigation revealed deployment correlation and suspicious pattern, leading to quick identification of regression.
