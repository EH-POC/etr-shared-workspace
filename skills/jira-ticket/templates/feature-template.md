# Feature / Story / Chore Template

Use this template for features, user stories, and chores.
For bugs, use `bug-template.md`.
For spikes, use this template but replace the Acceptance Criteria section with `h2. Definition of Done`.

All content must be in _Jira wiki markup_. Do not use Markdown.

---

## Template

```
h2. Overview

[1–3 sentences. What is being delivered? State the outcome at a high level.
No implementation details. Answer: "What are we building or changing?"]

h2. Context

[Why this work is needed. Include:]

* *Problem or opportunity:* [what pain point or value does this address]
* *Background:* [relevant system behaviour, prior decisions, related tickets [PROJ-XXX]]
* *Affected users/systems:* [who or what is impacted]
* *Constraints:* [technical, business, or timeline constraints]
* *Out of scope:* [explicitly list what this ticket does NOT cover]
* *References:* [design link, spec, Confluence page — use placeholder if unknown]

h2. Acceptance Criteria

# [AC written from the user or system perspective, not as an implementation task]
# [Each item is independently verifiable — a tester can confirm it pass/fail]
# [Cover the happy path]
# [Cover edge cases and error states where relevant]
# [No ambiguous language — "must" not "should", specific behaviour not "works correctly"]
```

---

## Good Example

```
h2. Overview

Add a "Forgot Password" flow so users who have lost access to their account can
reset their password via a verified email link without contacting support.

h2. Context

* *Problem:* Users who forget their password have no self-service recovery path.
  Support receives ~50 password reset requests per week, taking ~5 min each.
* *Background:* Auth is handled by the {{AuthService}} module [AUTH-12]. Email
  delivery uses SendGrid via [~platform-team].
* *Affected users:* All registered users with email-based accounts.
* *Constraints:* Reset links must expire after 1 hour. Only one active link per user.
* *Out of scope:* SMS-based recovery, social login recovery, admin-triggered resets.
* *References:* [Figma designs|https://figma.com/placeholder]

h2. Acceptance Criteria

# User sees a "Forgot password?" link on the login page.
# Submitting the form with a registered email triggers a reset email within 30 seconds.
# Submitting the form with an unregistered email shows "If this email exists, a link has been sent" (no enumeration).
# The reset link expires after 60 minutes; attempting to use an expired link shows an error message.
# Only the most recently issued link is valid; using an older link shows an error.
# After a successful password reset, the user is redirected to the login page with a confirmation message.
# Resetting a password invalidates all existing sessions for that user.
```

_Why this works:_

- Overview is outcome-focused — no implementation details
- Context explains the business pain with a concrete metric (~50 requests/week)
- Out of scope prevents scope creep before the ticket is even picked up
- Every AC item is independently verifiable by a tester who did not write the code
- "must" language is implicit through numbered assertions — no ambiguous "should"
- Security edge case (no email enumeration) is explicitly called out as a requirement

---

## Writing Checklist

Before submitting:

- [ ] All sections use Jira wiki markup (no Markdown headings, bold, bullets, or links)
- [ ] Overview is 1–3 sentences, no implementation details
- [ ] Context explains _why_ this is needed, not _how_ to build it
- [ ] Every AC item is independently verifiable
- [ ] "Out of scope" is explicitly stated
