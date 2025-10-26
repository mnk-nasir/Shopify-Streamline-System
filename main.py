#!/usr/bin/env python3
"""
main.py

Companion script that implements the same logic as the provided n8n workflow
"Shopify orders trigger" (0081-shopify-pedidos-trigger.json).

Features implemented:
- Accepts a Shopify "order created" JSON (from a file or HTTP POST webhook).
- Extracts the same fields as the n8n "Set fields" node.
- Creates an invoice in Harvest (if configured) or simulates it.
- Creates a Trello card for the order (if configured) or simulates it.
- Upserts a contact in Zoho CRM (if configured) or simulates it.
- If order_value > coupon threshold (default 50) sends a coupon email and tags Mailchimp.
  Otherwise sends a thank-you email.
- Optional small Flask webhook to receive live Shopify POSTs (for local testing).

Usage (CLI):
  python main.py --order-file path/to/order.json
  python main.py --order-json '{"id":123,...}'    # pass JSON directly (shell-escaped)
  python main.py --run-server --port 5000         # run a webhook receiver for testing

The script relies on config.py for API keys and endpoints.
"""
from __future__ import annotations
import json
import argparse
import sys
import os
from pathlib import Path
from typing import Any, Dict, Optional
import requests
from datetime import datetime

try:
    # Optional dependency for webhook receiver
    from flask import Flask, request, jsonify  # type: ignore
except Exception:
    Flask = None  # type: ignore

import config

ROOT = Path(__file__).resolve().parent


def extract_fields(order_json: Dict[str, Any]) -> Dict[str, Any]:
    """Mimic the 'Set fields' node from n8n and return a flat mapping."""
    customer = order_json.get("customer", {}) or {}
    shipping = order_json.get("shipping_address", {}) or {}

    fields = {
        "customer_phone": (customer.get("default_address") or {}).get("phone")
        if customer.get("default_address")
        else None,
        "customer_zipcode": shipping.get("zip"),
        "order_value": float(order_json.get("current_total_price", 0) or 0),
        "customer_firstname": customer.get("first_name") or "",
        "customer_lastname": customer.get("last_name") or "",
        "customer_email": customer.get("email") or "",
        "customer_country": shipping.get("country") or "",
        "customer_street": shipping.get("address1") or "",
        "customer_city": shipping.get("city") or "",
        "customer_province": shipping.get("province") or "",
        "order_number": order_json.get("order_number") or order_json.get("id"),
        "order_status_url": order_json.get("order_status_url"),
        "currency": order_json.get("currency"),
        "processed_at": order_json.get("processed_at"),
    }
    return fields


# -------------------------
# External integrations
# -------------------------
def create_harvest_invoice(fields: Dict[str, Any]) -> Dict[str, Any]:
    """Create invoice in Harvest. If not configured, return simulated response."""
    token = config.HARVEST_TOKEN
    account_id = config.HARVEST_ACCOUNT_ID
    if not token or not account_id:
        return {"simulated": True, "message": "Harvest not configured. Invoice not created."}

    url = f"https://api.harvestapp.com/v2/invoices"  # Harvest API base (example)
    # Map fields to Harvest API shape as needed. This is a minimal example.
    payload = {
        "client_id": account_id,
        "currency": fields.get("currency"),
        "issue_date": fields.get("processed_at"),
        "purchase_order": str(fields.get("order_number")),
        "line_items": [
            {
                "kind": "Service",
                "description": f"Shopify Order {fields.get('order_number')}",
                "quantity": 1,
                "unit_price": fields.get("order_value"),
            }
        ],
    }
    headers = {"Authorization": f"Bearer {token}", "User-Agent": "shopify-n8n-companion/1.0"}
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=20)
        resp.raise_for_status()
        return {"simulated": False, "response": resp.json()}
    except Exception as e:
        return {"simulated": False, "error": str(e)}


def create_trello_card(fields: Dict[str, Any]) -> Dict[str, Any]:
    """Create a Trello card. If not configured, return simulated response."""
    key = config.TRELLO_KEY
    token = config.TRELLO_TOKEN
    list_id = config.TRELLO_LIST_ID
    if not (key and token and list_id):
        return {"simulated": True, "message": "Trello not configured. Card not created."}

    url = f"https://api.trello.com/1/cards"
    name = f"Shopify order {fields.get('order_number')}"
    params = {
        "key": key,
        "token": token,
        "idList": list_id,
        "name": name,
        "desc": f"Order URL: {fields.get('order_status_url') or 'N/A'}",
    }
    try:
        resp = requests.post(url, params=params, timeout=10)
        resp.raise_for_status()
        return {"simulated": False, "response": resp.json()}
    except Exception as e:
        return {"simulated": False, "error": str(e)}


def upsert_zoho_contact(fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    Upsert a Zoho CRM contact.
    This implementation assumes you have an access token in config.ZOHO_ACCESS_TOKEN.
    Zoho's API may require refresh tokens and different endpoints depending on your setup.
    """
    token = config.ZOHO_ACCESS_TOKEN
    if not token:
        return {"simulated": True, "message": "Zoho not configured. Contact not upserted."}

    # Minimal example using Zoho CRM v2 endpoint
    url = "https://www.zohoapis.com/crm/v2/Contacts/upsert"
    contact_data = {
        "Last_Name": fields.get("customer_lastname") or "Unknown",
        "First_Name": fields.get("customer_firstname") or "",
        "Email": fields.get("customer_email") or "",
        "Phone": fields.get("customer_phone") or "",
        "Mailing_City": fields.get("customer_city") or "",
        "Mailing_Street": fields.get("customer_street") or "",
        "Mailing_Zip": fields.get("customer_zipcode") or "",
        "Mailing_Country": fields.get("customer_country") or "",
    }
    headers = {"Authorization": f"Zoho-oauthtoken {token}", "Content-Type": "application/json"}
    payload = {"data": [contact_data], "duplicate_check_fields": ["Email"]}
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        return {"simulated": False, "response": resp.json()}
    except Exception as e:
        return {"simulated": False, "error": str(e)}


def mailchimp_add_tag(fields: Dict[str, Any], tag: str) -> Dict[str, Any]:
    """Tag a Mailchimp member. Requires MAILCHIMP_API_KEY and MAILCHIMP_SERVER_PREFIX and LIST_ID."""
    api_key = config.MAILCHIMP_API_KEY
    list_id = config.MAILCHIMP_LIST_ID
    server = config.MAILCHIMP_SERVER_PREFIX
    if not (api_key and list_id and server):
        return {"simulated": True, "message": "Mailchimp not configured. Tag not added."}
    email = fields.get("customer_email")
    if not email:
        return {"simulated": True, "message": "No email provided."}

    # Mailchimp uses subscriber hash (MD5 lowercase of email) for member endpoint
    import hashlib

    member_hash = hashlib.md5(email.lower().encode("utf-8")).hexdigest()
    url = f"https://{server}.api.mailchimp.com/3.0/lists/{list_id}/members/{member_hash}/tags"
    payload = {"tags": [{"name": tag, "status": "active"}]}
    auth = ("anystring", api_key)
    try:
        resp = requests.post(url, json=payload, auth=auth, timeout=10)
        resp.raise_for_status()
        return {"simulated": False, "response": resp.json()}
    except Exception as e:
        return {"simulated": False, "error": str(e)}


def send_email_smtp(to_email: str, subject: str, message: str) -> Dict[str, Any]:
    """Send email via SMTP (simple implementation)."""
    smtp_server = config.GMAIL_SMTP_SERVER
    smtp_port = config.GMAIL_SMTP_PORT
    smtp_user = config.GMAIL_SMTP_USER
    smtp_pass = config.GMAIL_SMTP_PASS
    if not (smtp_server and smtp_port and smtp_user and smtp_pass):
        return {"simulated": True, "message": "SMTP not configured. Email not sent."}

    import smtplib
    from email.mime.text import MIMEText

    msg = MIMEText(message)
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to_email

    try:
        with smtplib.SMTP(smtp_server, int(smtp_port), timeout=20) as s:
            s.starttls()
            s.login(smtp_user, smtp_pass)
            s.sendmail(smtp_user, [to_email], msg.as_string())
        return {"simulated": False, "message": "Email sent via SMTP"}
    except Exception as e:
        return {"simulated": False, "error": str(e)}


# -------------------------
# Core orchestration
# -------------------------
COUPON_THRESHOLD = float(os.getenv("COUPON_THRESHOLD", "50"))
COUPON_CODE = os.getenv("COUPON_CODE", "COUPON15")
MAILCHIMP_HIGH_ORDER_TAG = os.getenv("MAILCHIMP_HIGH_ORDER_TAG", "high-order")


def process_order(order_json: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single Shopify order payload (mimic the n8n flow)."""
    result = {"started_at": datetime.utcnow().isoformat()}
    fields = extract_fields(order_json)
    result["fields"] = fields

    # 1) Create Harvest invoice
    harvest_result = create_harvest_invoice(fields)
    result["harvest"] = harvest_result

    # 2) Create Trello card (Harvest -> Trello connection in workflow)
    trello_result = create_trello_card(fields)
    result["trello"] = trello_result

    # 3) Upsert Zoho contact
    zoho_result = upsert_zoho_contact(fields)
    result["zoho"] = zoho_result

    # 4) IF order_value > threshold -> coupon email + mailchimp tag
    order_value = fields.get("order_value", 0) or 0
    to_email = fields.get("customer_email") or ""
    if order_value > COUPON_THRESHOLD:
        # send coupon email
        message = (
            f"Hi {fields.get('customer_firstname')},\n\n"
            f"Thank you for your order! Here's a 15% coupon code to use for your next order: {COUPON_CODE}\n\nBest,\nShop Owner"
        )
        send_res = send_email_smtp(to_email, "Your Shopify order - coupon", message)
        result["coupon_email"] = send_res

        # tag Mailchimp
        mc_res = mailchimp_add_tag(fields, MAILCHIMP_HIGH_ORDER_TAG)
        result["mailchimp"] = mc_res
    else:
        # send thank-you email
        message = (
            f"Hi {fields.get('customer_firstname')},\n\n"
            f"Thank you for your order! We're getting it ready for shipping it to you.\n\nBest,\nShop Owner"
        )
        send_res = send_email_smtp(to_email, "Your Shopify order - thank you", message)
        result["thankyou_email"] = send_res

    result["finished_at"] = datetime.utcnow().isoformat()
    return result


# -------------------------
# CLI and optional webhook
# -------------------------
def cli_main():
    parser = argparse.ArgumentParser(description="Shopify order -> integrations companion (n8n flow emulator)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--order-file", "-f", help="Path to a Shopify order JSON file")
    group.add_argument("--order-json", "-j", help="Order JSON string (shell-escaped)")
    group.add_argument("--run-server", action="store_true", help="Run a local Flask webhook receiver")
    parser.add_argument("--port", type=int, default=5000, help="Port for webhook server (when --run-server)")
    parser.add_argument("--save-output", action="store_true", help="Save the processing result to outputs/")
    args = parser.parse_args()

    if args.run_server:
        if not Flask:
            print("Flask is not installed. Install Flask to use --run-server:", file=sys.stderr)
            sys.exit(1)
        run_server(args.port)
        return

    if args.order_file:
        p = Path(args.order_file)
        if not p.exists():
            print("Order file not found:", args.order_file, file=sys.stderr)
            sys.exit(2)
        order = json.loads(p.read_text(encoding="utf-8"))
    else:
        order = json.loads(args.order_json)  # type: ignore

    result = process_order(order)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if args.save_output:
        out_dir = ROOT / "outputs"
        out_dir.mkdir(exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        out_path = out_dir / f"{ts}_order_{order.get('order_number', order.get('id', 'unknown'))}.json"
        out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print("Saved result to", out_path)


def run_server(port: int = 5000):
    """Simple Flask webhook to receive Shopify 'order created' events for local testing."""
    app = Flask("shopify-n8n-companion")

    @app.route("/webhook/order-created", methods=["POST"])
    def webhook_order_created():
        try:
            order = request.get_json(force=True)
        except Exception:
            return jsonify({"error": "invalid json"}), 400
        res = process_order(order)
        return jsonify(res)

    print(f"Starting webhook receiver on http://0.0.0.0:{port}/webhook/order-created")
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    cli_main()
