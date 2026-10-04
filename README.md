# AI Sales Agency V1

Automated first-touch sales scout for an Indonesian landing-page service.

## Model
`gemini-3.6-flash` (stable model ID).

## What it does
1. Reads new prospects from Google Sheets.
2. Discovers public web prospects from rotating Indonesia city+niche queries.
3. Audits each prospect with Gemini.
4. Generates personalized first-touch email.
5. Appends a WhatsApp handoff link.
6. Stops AI involvement after first-touch. Human handles the WhatsApp conversation.
7. Runs on GitHub Actions on a schedule.

## Important limits
- This project is deliberately **not** a cold-DM bot for Instagram or WhatsApp.
- No system can guarantee a platform account will never be restricted.
- Respect applicable anti-spam, consent, and platform rules.
- Start small and monitor bounce/complaint rates.

## Google Sheet
Create a spreadsheet with a worksheet named `Prospects` and these columns:

`business_name, niche, city, province, website, instagram, email, phone, source_url, audit_score, audit_summary, outreach_status, outreach_at, wa_link, message_subject, message_body, notes, opt_out`

The agent discovers public prospects, writes new rows into Google Sheets, audits them, then sends first-touch only to rows with a valid email and blank/NEW/AUDITED status.

## GitHub Actions
Put the repository in GitHub. For a public repository, standard GitHub-hosted Actions are free; GitHub Free also includes monthly minutes for private repositories. See GitHub billing docs.

Add these repository secrets:
- GEMINI_API_KEY
- GOOGLE_SHEET_ID
- GOOGLE_SERVICE_ACCOUNT_JSON
- GMAIL_ADDRESS
- GMAIL_APP_PASSWORD
- WA_NUMBER

Add these repository variables:
- GEMINI_MODEL = gemini-3.6-flash
- PORTFOLIO_URL = https://reynaldi-sonjaya.lynk.id/p/Reylandingpage
- DAILY_OUTREACH_LIMIT = 50
- BATCH_SIZE = 5

## First test
1. Put one test prospect in the sheet using your own email.
2. Set `DAILY_OUTREACH_LIMIT=1` and `BATCH_SIZE=1`.
3. Run GitHub Actions manually.
4. Confirm the email and sheet status.
5. Only then increase the daily limit.


## Discovery reality
The discovery step uses a public web-search package. It is a simple free starting point, not a guaranteed complete index of all Indonesian businesses. Search engines can change result quality/rate limits. For higher coverage, feed additional prospect rows from your existing collector into the same Google Sheet.


## Operating model
The agent does not automatically cold-DM Instagram or WhatsApp. The automated first-touch channel in V1 is email; the email contains a direct WhatsApp handoff link. Once a person enters WhatsApp, you take over manually.
