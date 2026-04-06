# Bug Report Template

Use this template for bugs, regressions, and unexpected behaviour.
For features and stories, use `feature-template.md`.

All content must be in _Jira wiki markup_. Do not use Markdown.

---

## Template

```
h2. Overview

[1–3 sentences. Describe the bug and its impact clearly.
Answer: "What is broken and who is affected?"]

h2. Context

* *Affected users/systems:* [who experiences this and how often]
* *Environment:* [production / staging / local; browser, OS, version if relevant]
* *Severity:* [critical / high / medium / low]
* *First observed:* [date or version]
* *Related tickets:* [[PROJ-XXX]]
* *References:* [Sentry link, logs, screenshot — use placeholder if unknown]

h2. Steps to Reproduce

# [Step 1 — e.g. "Log in as a standard user"]
# [Step 2 — e.g. "Navigate to Settings > Notifications"]
# [Step 3 — e.g. "Toggle 'Email alerts' off and save"]
# [Step N — the action that triggers the bug]

*Expected:* [what should happen]

*Actual:* [what actually happens]

{panel:title=Error / Log Output|bgColor=#FFEBE9|borderColor=#FF5630}
[Paste error message, stack trace, or log snippet here]
{panel}

h2. Acceptance Criteria

# The bug described above is no longer reproducible following the steps above.
# [Any related edge case that must also be verified]
# [Regression test added or updated to cover this scenario]
# No existing functionality is broken by the fix (smoke test passes).
```

---

## Good Example

```
h2. Overview

Users are unable to save notification preferences — clicking "Save" shows a
spinner indefinitely and the settings revert on page reload. This affects all
users who try to update their notification settings.

h2. Context

* *Affected users:* All users on notification settings page (~200 visits/day).
* *Environment:* Production; confirmed on Chrome 121, Firefox 122, Safari 17.
* *Severity:* High — core settings functionality is non-functional.
* *First observed:* 2025-01-15 (after deploy v3.4.2).
* *Related tickets:* [NOTIF-88] (related settings refactor), [INFRA-41] (recent DB migration).
* *References:* [Sentry: NOTIF-ABC123|https://sentry.io/placeholder], [Slack thread|https://placeholder]

h2. Steps to Reproduce

# Log in as any standard user.
# Navigate to *Settings* > *Notifications*.
# Change any toggle (e.g. turn off "Email alerts").
# Click *Save*.

*Expected:* Settings are saved. User sees a success confirmation.

*Actual:* The save button shows a spinner. No confirmation appears.
Refreshing the page shows the original (unsaved) values.

{panel:title=Console Error|bgColor=#FFEBE9|borderColor=#FF5630}
{code:javascript}
POST /api/v1/user/notifications 422 Unprocessable Entity
{"error": "Invalid preference key: 'email_alerts_v2'"}
{code}
{panel}

h2. Acceptance Criteria

# Users can save notification preferences; settings persist on page reload.
# A success toast is shown after a successful save.
# The API returns 200 with the saved preferences in the response body.
# Submitting with invalid data (e.g. missing required fields) shows an inline error, not a spinner.
# A regression test is added covering the save flow end-to-end.
```

---

## Writing Checklist

Before submitting:

- [ ] All sections use Jira wiki markup (no Markdown headings, bold, bullets, or links)
- [ ] Steps to Reproduce are clear enough for someone unfamiliar with the feature to follow
- [ ] Expected vs Actual behaviour is explicitly stated
- [ ] Error output or logs are included in a panel or code block
- [ ] AC includes a regression test criterion
