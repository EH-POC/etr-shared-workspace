# Jira Wiki Markup — Quick Reference

> Use this when writing Jira ticket descriptions or comments.
> Output must be Jira wiki markup, **not** Markdown.

---

## Text Formatting

| Output        | Jira markup       | NOT (Markdown)      |
| ------------- | ----------------- | ------------------- |
| **Bold**      | `*bold*`          | `**bold**`          |
| _Italic_      | `_italic_`        | `*italic*`          |
| `inline code` | `{{inline code}}` | `` `inline code` `` |
| ~~Strike~~    | `-strikethrough-` | `~~strike~~`        |
| Underline     | `+underline+`     |                     |
| Superscript   | `^super^`         |                     |
| Subscript     | `~sub~`           |                     |

---

## Headings

```
h1. Page Title
h2. Section
h3. Subsection
h4. Detail
```

> A space after the period is required: `h2. Title` ✓ — `h2.Title` ✗

---

## Lists

**Bullet list:**

```
* First item
* Second item
** Nested item
** Another nested
* Third item
```

**Numbered list:**

```
# Step one
# Step two
## Sub-step
# Step three
```

**Mixed:**

```
# Step one
#* Bullet under step one
# Step two
```

---

## Links

| Purpose          | Syntax                         |
| ---------------- | ------------------------------ |
| Issue link       | `[PROJ-123]`                   |
| Named issue link | `[See ticket\|PROJ-123]`       |
| URL              | `[https://example.com]`        |
| Named URL        | `[Label\|https://example.com]` |
| User mention     | `[~username]`                  |
| Attachment       | `[^filename.png]`              |
| Anchor           | `{anchor:name}` / `[#name]`    |

---

## Code Blocks

**Inline:**

```
{{someVariable}}
```

**Block (with language):**

```
{code:javascript}
const x = 1;
{code}
```

Supported languages: `java`, `javascript`, `typescript`, `python`, `ruby`, `go`, `bash`, `sql`, `xml`, `json`, `yaml`

**Plain preformatted (no highlighting):**

```
{noformat}
raw text here
{noformat}
```

---

## Tables

```
||Column A||Column B||Column C||
|Row 1 A  |Row 1 B  |Row 1 C  |
|Row 2 A  |Row 2 B  |Row 2 C  |
```

> `||` = header cell, `|` = data cell

---

## Panels & Callouts

**Info panel:**

```
{panel:title=Note|bgColor=#DEEBFF|borderColor=#4C9AFF}
Content here.
{panel}
```

**Warning panel:**

```
{panel:title=Warning|bgColor=#FFFAE6|borderColor=#FFE380}
Content here.
{panel}
```

**Error panel:**

```
{panel:title=Error|bgColor=#FFEBE9|borderColor=#FF5630}
Content here.
{panel}
```

**Block quote:**

```
{quote}
Quoted text here.
{quote}
```

**Collapsible section:**

```
{expand:Click to expand}
Hidden content here.
{expand}
```

---

## Misc

| Purpose           | Syntax                                                   |
| ----------------- | -------------------------------------------------------- |
| Horizontal rule   | `----`                                                   |
| Forced line break | `\\`                                                     |
| Color text        | `{color:red}text{color}` or `{color:#FF0000}text{color}` |

---

## Common Mistakes

| Wrong (Markdown) | Correct (Jira)             |
| ---------------- | -------------------------- |
| `## Heading`     | `h2. Heading`              |
| `**bold**`       | `*bold*`                   |
| ` ```code``` `   | `{code:language}...{code}` |
| `[text](url)`    | `[text\|url]`              |
| `- bullet`       | `* bullet`                 |
| `1. numbered`    | `# numbered`               |
| `@username`      | `[~username]`              |
