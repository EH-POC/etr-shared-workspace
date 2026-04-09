# Sentry CLI Setup

**Use Sentry CLI** (https://cli.sentry.dev/) to interact with the Sentry API.

### Installation

```bash
# Install globally via npm
npm install -g sentry

# Or install via script
curl https://cli.sentry.dev/install -fsS | bash

# Or use without installation
npx sentry --help
```

### Authentication

**Method 1: OAuth Device Flow (Recommended)**
```bash
# Start authentication flow
sentry auth login

# Follow prompts:
# 1. Visit the URL shown in terminal
# 2. Enter the code provided
# 3. Authorize in browser
# 4. Return to terminal - automatically authenticated
```

**Method 2: API Token**
```bash
# Create token at https://sentry.io/settings/account/api/auth-tokens/
# Required scopes: event:read, org:read, project:read

# Authenticate with token
sentry auth login --token YOUR_SENTRY_API_TOKEN
```

**Credentials Storage**:
- Credentials are stored in `~/.sentry/config.json` with mode 600 (secure permissions)
- One-time setup - persists across sessions
- No need to manage environment variables

### Verification

```bash
# Check authentication status
sentry auth status

# Test API access - list organizations
sentry api /organizations/ | jq -r '.[].slug'

# Verify authentication works
if sentry api /organizations/ | jq -e '.[0]' > /dev/null 2>&1; then
  echo "✓ Authentication successful"
else
  echo "✗ Authentication failed - run: sentry auth login"
fi
```

### Logout (Optional)

```bash
# Remove stored credentials
sentry auth logout
```
