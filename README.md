# AI Sales Agency V1.5 — Email First + Gemini Batch

Flow:

PROSPECTOR -> email validation -> Gemini Batch -> READY -> Gmail -> WhatsApp link -> human closing

Important:
- `gemini-3.1-flash-lite` is used for high-volume AI analysis.
- Gemini Batch API is asynchronous; target turnaround is 24 hours, often faster.
- Start with `TEST_MODE=true` to generate messages into the Sheet without sending email.
- Use only public business contact emails and honor opt-out requests.

Variables:
- `GEMINI_MODEL=gemini-3.1-flash-lite`
- `PORTFOLIO_URL=https://reynaldi-sonjaya.lynk.id/p/Reylandingpage`
- `DAILY_OUTREACH_LIMIT=100`
- `DISCOVERY_PER_RUN=30`
- `BATCH_MAX_PROSPECTS=500`
- `EMAILS_PER_RUN=12`
- `SEND_DELAY_SECONDS=60`
- `SHEET_TAB=Prospects`
- `TEST_MODE=true`

After checking test messages, change `TEST_MODE` to `false` for real sending.

A personal Gmail account has sending limits and Google may limit or block spam-like traffic. The 500/day figure is a maximum technical limit, not a promise that 500 unsolicited messages are safe to send.
