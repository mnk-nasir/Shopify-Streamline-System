# Shopify-Streamline-System```markdown
# Shopify Orders Companion (n8n workflow emulator)

This small Python project mirrors the behavior of the n8n workflow "Shopify orders trigger"
(0081-shopify-pedidos-trigger.json). It is intended as a local/emulation companion so you can
test and iterate outside of n8n.

What it replicates
- "Set fields" node: extracts customer and shipping fields from Shopify order JSON.
- "Harvest" node: creates an invoice for the order (if HARVEST_TOKEN/HARVEST_ACCOUNT_ID set).
- "Trello" node: creates a Trello card for the order (if TRELLO_KEY/TRELLO_TOKEN/TRELLO_LIST_ID set).
- "Zoho" node: upserts a contact in Zoho CRM (if ZOHO_ACCESS_TOKEN set).
- "IF" node: checks order_value > COUPON_THRESHOLD (default 50). If true:
  - sends a coupon email and tags the customer in Mailchimp (if configured).
  Otherwise sends a thank-you email.
- Mailchimp: tags member with "high-order" (configurable) when coupon branch is executed.

Files
- main.py — main script to process orders (CLI + optional Flask webhook).
- config.py — central configuration loaded from .env.
- requirements.txt — Python dependencies.
- .env.example — example environment variables.

Quickstart
1. Copy files to a directory and create a virtual environment:
   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Create a `.env` (based on `.env.example`) and set any API keys you want to use:
   - For Harvest: HARVEST_TOKEN, HARVEST_ACCOUNT_ID
   - For Trello: TRELLO_KEY, TRELLO_TOKEN, TRELLO_LIST_ID
   - For Zoho: ZOHO_ACCESS_TOKEN
   - For Mailchimp: MAILCHIMP_API_KEY, MAILCHIMP_LIST_ID, MAILCHIMP_SERVER_PREFIX (e.g., us1)
   - For SMTP email sending: GMAIL_SMTP_USER, GMAIL_SMTP_PASS (Gmail with app password), or configure other SMTP settings

3. Run against a local order JSON file:
   ```
   python main.py --order-file sample_order.json
   ```

4. Run a local webhook receiver and POST Shopify webhooks to it:
   ```
   python main.py --run-server --port 5000
   # POST to http://localhost:5000/webhook/order-created with the Shopify JSON body
   ```

Notes and limitations
- This is an emulator/companion. Integrations are implemented with simple REST calls; you
  may need to adapt payloads to match your exact tenant/account settings (especially Zoho & Harvest).
- Email sending via SMTP uses username/password. For Gmail, prefer App Passwords or OAuth (not implemented here).
- Mailchimp tagging requires the member to exist (the endpoint will create/update member if needed).
- Trello requires a target list ID; get it from Trello UI or API.
- Harvest invoice payload is a simplified example — adjust to match your Harvest account details.

Extending
- Add OAuth token refresh for Zoho.
- Add error handling/retries and logging to external logs.
- Persist processed order IDs (dedupe).
- Add a test suite and example sample_order.json fixtures.

If you want, I can:
- Push these files into your GitHub repo (tell me owner/repo/branch and confirm the repo exists),
- Add an example sample_order.json that mimics Shopify webhook payload,
- Convert the webhook receiver into a Dockerized service for easy deployment.
```
