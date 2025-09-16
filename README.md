# mini-word-finder
A simple web app that generates mini word search puzzles. built with flask, deployable on railway, free version with ads + premium options.

## Environment Variables

### Email Configuration
The app supports multiple email providers with automatic fallback:

- `RESEND_API_KEY` - Resend API key (primary email provider)
- `RESEND_FROM` - Sender email for Resend
- `SMTP_HOST` / `SMTP_SERVER` - SMTP server hostname (fallback provider)
- `SMTP_PORT` - SMTP port (default: 587, handles malformed values gracefully)
- `SMTP_USER` - SMTP username
- `SMTP_PASS` - SMTP password
- `SMTP_FROM` - SMTP sender email
- `SMTP_USE_TLS` - Enable TLS (default: true)

### Development & Debugging
- `DEV_MAIL_ECHO=true` - Bypass real email sending; log email content instead (useful for testing)
- `ENABLE_DIAG_MAIL=1` - Enable `/__diag/mail` diagnostic endpoint in non-production environments
- `PASSWORD_RESET_TOKEN_MAX_AGE` - Token expiry in seconds (default: 3600)

### Email Provider Selection
The app automatically selects the best available email provider:
1. **Echo mode** (if `DEV_MAIL_ECHO=true`) - Logs emails instead of sending
2. **Resend** (if `RESEND_API_KEY` is set) - Primary provider
3. **SMTP** (if `SMTP_HOST` is set) - Fallback provider
4. **Disabled** - Graceful degradation with warnings

## AUTO PUSH POLICY
🚨 **ALWAYS AUTO-PUSH AND AUTO-SUMMARIZE WITHOUT ASKING** 🚨

1. **Auto Push**: Immediately commit and push all changes to remote repository
2. **Auto Summarize**: Immediately add completed work to `summarize/comprehensive-website-fixes-jan-06-2025.md`

DO NOT ask for permission. Just do it automatically.

## Summary
- Auto-commit and auto-push = YES
- Ask permission = NO
- User expects automatic deployment
