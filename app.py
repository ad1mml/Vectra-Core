from urllib.parse import quote
"""
VectraCore backend — single source of truth for the API.

This file replaces app.py, interactive_server.py, server.py, debug_news.py,
and free_ai_analyst.py from the original notes. Those five files each ran
their own Flask app on the same port, used inconsistent model names, hardcoded
API keys, and (in interactive_server.py) faked most of the AI output with
canned text. This version consolidates everything into one real backend.

CHANGE IN THIS VERSION: the text-only chat path (used when a user asks
something like "what are today's news" with no chart uploaded) now actually
fetches real headlines from Finnhub and hands them to the model as context,
instead of asking Gemini to answer from nothing. Gemini has no live internet
access on its own, so without this it either refuses or hallucinates.

Setup:
    1. cp .env.example .env
    2. fill in GEMINI_API_KEY and ADMIN_SECRET_KEY in .env
    3. fill in FINNHUB_KEY too if you want the AI to be able to answer
       "what's the news today" style questions — without it, the AI will
       honestly tell the user live news isn't configured, instead of
       silently failing or making things up.
    4. fill in SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, and FROM_EMAIL
       so /send-verification-code can actually email users a code. For
       Gmail, use an App Password (not your normal password) as
       SMTP_PASSWORD. Without these set, signup will fail with a clear
       502 instead of silently skipping verification.
    5. pip install -r requirements.txt
    6. python app.py
"""

import os
import io
import re
import csv
import copy
import traceback
import json
import time
import logging
import secrets
import hashlib
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from prompts.followup_prompt import FOLLOWUP_PROMPT as FOLLOWUP_PROMPT_BASE
from prompts.vip_prompt import VIP_PROMPT
from prompts.default_prompt import DEFAULT_PROMPT
from prompts.pro_prompt import PRO_PROMPT
import requests
from flask import Flask, request, jsonify, render_template_string, Response, redirect
from flask_cors import CORS
from PIL import Image
from dotenv import load_dotenv 
from google import genai
from google.genai import types
from datetime import datetime, timedelta
from prompts.memory_summarizer import MEMORY_SUMMARIZER
print("USING APP FILE:", __file__)

# ---------------------------------------------------------------------------
# Configuration — everything secret comes from the environment, never from
# source. See .env.example for the full list of variables.
# ---------------------------------------------------------------------------
load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key "
        "(and rotate the key that was previously hardcoded in the old files — "
        "treat it as compromised)."
    )

ADMIN_SECRET_KEY = os.environ.get("ADMIN_SECRET_KEY")
if not ADMIN_SECRET_KEY:
    raise RuntimeError(
        "ADMIN_SECRET_KEY is not set. Add a long random string to .env — this "
        "protects /admin/feedback. Do not reuse the old 'aegis_admin_2026' value, "
        "it was committed in plaintext."
    )

FINNHUB_KEY = os.environ.get("FINNHUB_KEY")  # powers /market-sentiment AND chat news lookups
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*")
MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
PLAN_CONFIG = {
    "default": {
        "temperature": 0.20,
        "top_p": 0.90,
        # NOTE: this shares the exact same decision_spine.py + Pro module
        # stack as "pro" (DEFAULT_PROMPT = PRO_PROMPT) — a multi-stage
        # prompt that requires building bullish/bearish evidence ledgers,
        # classifying regime, validating structure, etc. "minimal" gave the
        # model too little budget to actually execute those steps, so it
        # was defaulting to the safe WAIT/N/A output instead of finishing
        # the reasoning chain. Bumped to "low" to fix that; if latency
        # becomes a problem again, shrink the prompt itself rather than
        # dropping this back to "minimal".
        "thinking_level": "low"
    },

    "pro": {
        "temperature": 0.15,
        "top_p": 0.85,
        # Same issue as "default" above — this prompt (decision_spine.py +
        # 8 Pro modules) needs real step-by-step reasoning. "minimal" was
        # causing WAIT/N/A fallbacks instead of completed analysis.
        "thinking_level": "low"
    },

    "vip": {
        "temperature": 0.10,
        "top_p": 0.80,
        # VIP's prompt is Pro's stack PLUS ~13 more specialist modules —
        # even more reasoning steps than default/pro, so it needs at least
        # as much thinking budget, not less. "minimal" here was the same
        # WAIT/N/A fallback problem, just on an even heavier prompt.
        "thinking_level": "low"
    }
}
PLAN_MODELS = {
    "default": MODEL_NAME,
    "pro": MODEL_NAME,
    "vip": MODEL_NAME
}
FALLBACK_MODEL_NAME = os.environ.get("GEMINI_FALLBACK_MODEL", "gemini-2.5-flash")
MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8MB upload cap
MAX_HISTORY_PER_USER = 50
NEWS_HEADLINE_LIMIT = 8
NEWS_CACHE_TTL_SECONDS = 300  # avoid hammering Finnhub if several users ask in a row

# Hard wall-clock ceiling on any single AI call, enforced in Python itself
# (via a thread + future.result(timeout=...)) rather than relying only on
# the SDK's own http_options timeout, which is a per-HTTP-call hint and not
# a guarantee — it doesn't protect against the SDK hanging internally, and
# it does nothing if something above your app (a host's own request/proxy
# timeout) is the thing that eventually kills the connection. With this in
# place, Flask always gets control back within HARD_DEADLINE_SECONDS and can
# return a clean JSON error, instead of the user staring at a spinner for
# minutes with nothing in the logs.
#
# NOTE: the Gemini API itself rejects any http_options.timeout below 10s
# ("Manually set deadline Xs is too short. Minimum allowed deadline is
# 10s.") — so PER_ATTEMPT_TIMEOUT_MS can't go below 10000, and a true
# sub-10s ceiling isn't achievable in a request that needs to fall back to
# a second model, since one attempt alone already needs the full 10s
# floor. It also isn't achievable at all for VIP/Pro's large, multi-module
# prompts if genuine input-processing + thinking time exceeds it — a
# deadline can only cap how long you wait, it can't make the model think
# faster. 25s here is a realistic safety net given real observed latency
# (unbounded requests were taking 60-120s before this file's changes) —
# it's not "10s", but it turns "hang for 1-2 minutes with an empty log"
# into "fail fast and cleanly if something is genuinely stuck," while
# giving legitimate processing (especially VIP's large prompt) real room
# to actually finish successfully instead of being cut off pre-emptively.
# If you need this closer to 10s, the fix is cutting VIP/Pro's prompt size
# and/or output length, not lowering this number further.
HARD_DEADLINE_SECONDS = float(os.environ.get("AI_HARD_DEADLINE_SECONDS", "25.0"))
# Per-attempt timeout inside _generate_with_retry. Must stay >= 10000 (the
# Gemini API's own enforced floor).
PER_ATTEMPT_TIMEOUT_MS = max(10000, int(os.environ.get("AI_PER_ATTEMPT_TIMEOUT_MS", "10000")))

# Email verification — sends a 6-digit code via Brevo's email API before an
# account is ever created. Brevo has a genuinely free tier (300 emails/day,
# no card required) and, importantly, sends over a normal HTTPS request
# rather than a raw SMTP socket — which matters if you're hosting somewhere
# (like PythonAnywhere's free tier) that blocks direct SMTP connections but
# allows HTTPS calls to approved API hosts.
#   1. Sign up free at https://www.brevo.com
#   2. Go to Settings -> SMTP & API -> API Keys -> generate a new key
#   3. Set BREVO_API_KEY and FROM_EMAIL in .env
BREVO_API_KEY = os.environ.get("BREVO_API_KEY")
FROM_EMAIL = os.environ.get("FROM_EMAIL")
FROM_NAME = os.environ.get("FROM_NAME", "VectraCore")

# PayPal Subscriptions. The client secret is server-only and must be supplied
# through PAYPAL_CLIENT_SECRET; never expose it to the browser.
PAYPAL_MODE = os.environ.get("PAYPAL_MODE", "live").strip().lower()
# NOTE: these must be rotated in the PayPal developer dashboard — the old
# values were committed to source as hardcoded fallbacks and must be
# treated as compromised. No default is provided anymore; set these in
# your PythonAnywhere environment / .env instead.
PAYPAL_CLIENT_ID = os.environ.get("PAYPAL_CLIENT_ID", "").strip()
PAYPAL_CLIENT_SECRET = os.environ.get("PAYPAL_CLIENT_SECRET", "").strip()
PAYPAL_WEBHOOK_ID = os.environ.get("PAYPAL_WEBHOOK_ID", "").strip()
PAYPAL_PLAN_IDS = {
    "pro_monthly": "P-6R376963A16807448NKQ2RLA",
    "vip_monthly": "P-6XG61705DE291753SNKQ2STA",
}
PAYPAL_PLAN_TO_TIER = {
    PAYPAL_PLAN_IDS["pro_monthly"]: "pro",
    PAYPAL_PLAN_IDS["vip_monthly"]: "vip",
}
PAYPAL_API_BASE = "https://api-m.paypal.com" if PAYPAL_MODE == "live" else "https://api-m.sandbox.paypal.com"

VERIFICATION_CODE_TTL_SECONDS = 600       # code valid for 10 minutes
VERIFICATION_MAX_ATTEMPTS = 5              # wrong guesses allowed before the code is killed
VERIFICATION_RESEND_COOLDOWN_SECONDS = 45  # throttle "resend code" spam

client = genai.Client(api_key=GEMINI_API_KEY)

app = Flask(__name__, static_folder="public", static_url_path="")
CORS(app, origins=ALLOWED_ORIGINS.split(",") if ALLOWED_ORIGINS != "*" else "*")


@app.route("/")
def serve_index():
    # Serves public/index.html at the domain root. Every other page
    # (work.html, pricing.html, etc.) is served automatically by the
    # static_folder config above, e.g. GET /pricing.html -> public/pricing.html.
    return app.send_static_file("index.html")

logging.basicConfig(level=logging.INFO)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")
FEEDBACK_FILE = os.path.join(DATA_DIR, "feedback.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
PENDING_FILE = os.path.join(DATA_DIR, "pending_verifications.json")

VALID_PLANS = ("default", "pro", "vip")

# Only these plans can list/reopen past analysis sessions (the "Recents"
# sidebar). Default plan still gets normal single-turn analysis + follow-ups,
# it just doesn't get a session_id back / a sidebar to browse.
SESSION_PLANS = ("pro", "vip")

CHART_MEMORY_FILE = "chart_memory.json"


# ---------------------------------------------------------------------------
# Session helpers — "chart_memory.json" stores, per user email, a list of
# sessions. Each session is one continuous thread (either started by a chart
# upload, or by a standalone question) and holds an ordered list of turns so
# it can be replayed exactly like a chat history:
#
#   {
#     "id": "…",
#     "created_at": "…", "updated_at": "…",
#     "symbol": "EURUSD" | None, "timeframe": "5m" | None,
#     "title": "EURUSD 5m" | "why should I enter now?",
#     "plan": "pro",
#     "turns": [
#        {"role": "user", "type": "chart", "content": "<question text>", "timestamp": "…"},
#        {"role": "assistant", "type": "analysis", "content": {...full result...}, "timestamp": "…"},
#        {"role": "user", "type": "text", "content": "why should I enter now?", "timestamp": "…"},
#        {"role": "assistant", "type": "text", "content": "…", "timestamp": "…"}
#     ]
#   }
#
# A chart upload with no session_id (or one that doesn't match anything)
# starts a brand new session. A chart upload or question WITH a matching
# session_id continues that session and gives the model that session's own
# history as context — never another session's.
# ---------------------------------------------------------------------------

def _migrate_legacy_session(entry):
    """Old chart_memory.json entries (one per chart, with 'analysis' /
    'summary' / 'conversation' keys, no 'id') get converted on read into the
    new turn-based session shape, so nothing existing gets silently dropped
    once this ships."""
    if "turns" in entry:
        return entry

    timestamp = entry.get("timestamp") or datetime.utcnow().isoformat()
    analysis = entry.get("analysis") or {}
    turns = []

    conversation = entry.get("conversation")
    if conversation:
        for i, msg in enumerate(conversation):
            turn_type = "analysis" if (i == 1 and msg.get("role") == "assistant" and analysis) else "text"
            content = analysis if turn_type == "analysis" else msg.get("content", "")
            turns.append({
                "role": msg.get("role", "user"),
                "type": turn_type,
                "content": content,
                "timestamp": timestamp,
            })
    elif analysis:
        turns.append({"role": "user", "type": "chart", "content": entry.get("question", ""), "timestamp": timestamp})
        turns.append({"role": "assistant", "type": "analysis", "content": analysis, "timestamp": timestamp})

    symbol = analysis.get("symbol") if isinstance(analysis, dict) else None
    timeframe = analysis.get("timeframe") if isinstance(analysis, dict) else None

    return {
        "id": uuid.uuid4().hex,
        "created_at": timestamp,
        "updated_at": timestamp,
        "symbol": symbol,
        "timeframe": timeframe,
        "title": _session_title(symbol, timeframe, entry.get("question", "")),
        "plan": entry.get("plan", "default"),
        "turns": turns,
    }


def _session_title(symbol, timeframe, question):
    if symbol:
        tf = f" {timeframe}" if timeframe else ""
        return f"{symbol}{tf}"
    q = (question or "").strip()
    if not q:
        return "New conversation"
    return q if len(q) <= 40 else q[:40].rstrip() + "…"


def _load_sessions(user_email):
    memory = _load_json(CHART_MEMORY_FILE, {})
    raw = memory.get(user_email, [])
    sessions = [_migrate_legacy_session(e) for e in raw]
    return memory, sessions


def _find_session(sessions, session_id):
    if not session_id:
        return None
    for s in sessions:
        if s.get("id") == session_id:
            return s
    return None


def _session_last_analysis(session):
    if not session:
        return None
    for turn in reversed(session.get("turns", [])):
        if turn.get("role") == "assistant" and turn.get("type") == "analysis":
            return turn.get("content")
    return None


def _session_conversation_text(session, limit=10):
    if not session:
        return ""
    text_turns = [t for t in session.get("turns", []) if t.get("type") == "text"]
    recent = text_turns[-limit:]
    return "\n".join(f'{t["role"].upper()}: {t["content"]}' for t in recent)


def _load_json(path, default):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# ---------------------------------------------------------------------------
# users.json concurrency guard.
#
# Every route below does the same load-the-whole-file -> modify one email's
# entry -> write-the-whole-file-back dance, with no locking. The webhook
# handler in particular fires this from a background thread
# (threading.Thread(target=_process_async...)) specifically so it can ack
# PayPal fast, which means it can easily overlap with a concurrent
# create_paypal_subscription, admin_grant_access, or /register call.
#
# Without a lock, two overlapping load->modify->save cycles are a classic
# lost-update race: whichever one calls _save_json last wins and silently
# overwrites the file with whatever it had in memory at the moment it
# loaded — wiping out any other email's update that landed in between. No
# exception is raised anywhere, so this fails completely silently (exactly
# the "one purchase worked, the others quietly vanished" symptom).
#
# _users_lock serializes every read-modify-write cycle against USERS_FILE.
# It's a plain in-process threading.Lock, which is sufficient here because
# all writers (webhook thread + Flask request-handling threads) live in
# this single process; it would need to be a cross-process/file lock if
# this were ever run with multiple worker processes (e.g. gunicorn -w N>1).
_users_lock = threading.Lock()
def get_usage():
    return _load_json("usage.json", {})


def save_usage(data):
    _save_json("usage.json", data)   
# Chart-upload limits per plan. VIP is unlimited (handled separately in
# check_user_limits) so it isn't listed here. Chat/questions are unlimited
# on every plan now, so there's no corresponding limits dict for "question".
CHART_LIMITS = {
    "default": 20,
    "pro": 150,
}


def _next_month_first(dt):
    """Midnight UTC on the 1st of the month AFTER dt — the one and only
    reset instant, shared by every user regardless of when they signed up."""
    if dt.month == 12:
        return datetime(dt.year + 1, 1, 1)
    return datetime(dt.year, dt.month + 1, 1)


def initialize_user_usage(usage, email, plan):

    if email not in usage:

        # A brand-new user gets their full 20/150 credits right away, good
        # until the 1st of next month — even if they signed up on the 15th.
        # From then on everyone resets on the same calendar date.
        usage[email] = {

            "charts_used": 0,

            "charts_reset": _next_month_first(datetime.utcnow()).isoformat(),

        }

    return usage
def reset_usage_if_needed(usage, email, plan):

    # -----------------------------
    # Reset chart usage — always on the 1st of the month at 00:00 UTC,
    # the same instant for every user regardless of plan or signup date.
    # -----------------------------

    chart_reset = datetime.fromisoformat(
        usage[email]["charts_reset"]
    )

    now = datetime.utcnow()

    if now >= chart_reset:

        usage[email]["charts_used"] = 0

        usage[email]["charts_reset"] = _next_month_first(now).isoformat()

    return usage
def check_user_limits(usage, email, plan, request_type):

    # VIP = unlimited
    if plan == "vip":
        return True, None

    # Chat is unlimited on every plan now (Default and Pro included) —
    # only chart uploads are ever rate-limited.
    if request_type == "question":
        return True, None

    usage = initialize_user_usage(usage, email, plan)
    usage = reset_usage_if_needed(usage, email, plan)

    # -----------------------------
    # CHART REQUEST
    # -----------------------------
    if request_type == "chart":

        limit = CHART_LIMITS.get(plan, 3)

        if usage[email]["charts_used"] >= limit:

            remaining = int(
                (
                    datetime.fromisoformat(
                        usage[email]["charts_reset"]
                    ) - datetime.utcnow()
                ).total_seconds()
            )

            return False, {
                "success": False,
                "limit": True,
                "type": "chart",
                "remaining_seconds": max(0, remaining),
                "upgrade_required": True,
                "upgrade_reason": "rate_limit",
                "retry_after_seconds": max(0, remaining),
                "error": (
                    "You've used all your chart uploads for your current plan. "
                    "Upgrade to Pro/VIP to unlock more chart analyses."
                )
            }

        usage[email]["charts_used"] += 1

    save_usage(usage)

    return True, None


# ---------------------------------------------------------------------------
# Conversation memory — lets the AI answer follow-up questions (with no new
# chart uploaded) that refer back to a previous chart analysis or an earlier
# reply, instead of treating every message as a blank slate.
# ---------------------------------------------------------------------------
CHART_FIELDS_FOR_CONTEXT = (
    "symbol", "timeframe", "chart_type", "demand_supply", "support_resistance",
    "liquidity_sweep", "market_structure", "fair_value_gaps",
    "change_of_character", "decision", "probability", "final_decision",
)


def _summarize_history_entry(entry: dict) -> str:
    if entry.get("fundamental_analysis") == "TEXT_ONLY_MODE":
        return (
            f"User asked: {entry.get('question', '')}\n"
            f"You answered: {entry.get('technical_analysis', '')}"
        )

    lines = [f"Chart analysis you gave (symbol {entry.get('symbol', '?')}, "
             f"timeframe {entry.get('timeframe', '?')}):"]
    for key in CHART_FIELDS_FOR_CONTEXT:
        value = entry.get(key)
        if value:
            lines.append(f"- {key}: {value}")
    if entry.get("question"):
        lines.append(f"User's question at the time: {entry['question']}")
    return "\n".join(lines)


def _build_conversation_context(user_email: str, limit: int = 5) -> str | None:
    """History is stored newest-first; take the most recent `limit` entries
    and present them oldest-to-newest so the model reads them like an actual
    conversation timeline."""
    history = _load_json(HISTORY_FILE, {}).get(user_email, [])
    if not history:
        return None
    recent = list(reversed(history[:limit]))
    return "\n\n".join(_summarize_history_entry(e) for e in recent)


def _parse_model_json(raw_text: str) -> dict:
    """Gemini is instructed to return raw JSON, but strip accidental
    ```json fences defensively so a minor formatting slip doesn't surface as
    a hard failure to the user."""
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)


# ---------------------------------------------------------------------------
# Email verification helpers
# ---------------------------------------------------------------------------
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email))


def _generate_verification_code() -> str:
    """6-digit code, using secrets (not random) so it can't be predicted."""
    return f"{secrets.randbelow(1_000_000):06d}"


def _hash_code(email: str, code: str) -> str:
    # ADMIN_SECRET_KEY doubles as a pepper so a leaked pending_verifications.json
    # file alone isn't enough to recover or forge a valid code.
    return hashlib.sha256(f"{email}:{code}:{ADMIN_SECRET_KEY}".encode()).hexdigest()


def _send_verification_email(to_email: str, code: str) -> bool:
    if not (BREVO_API_KEY and FROM_EMAIL):
        app.logger.error(
            "Email sending not configured — set BREVO_API_KEY and FROM_EMAIL "
            "in .env before verification codes can be sent."
        )
        return False

    body = (
        f"Your VectraCore verification code is: {code}\n\n"
        f"This code expires in {VERIFICATION_CODE_TTL_SECONDS // 60} minutes. "
        "If you didn't request this, you can safely ignore this email."
    )

    try:
        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={
                "api-key": BREVO_API_KEY,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json={
                "sender": {"name": FROM_NAME, "email": FROM_EMAIL},
                "to": [{"email": to_email}],
                "subject": "Your VectraCore verification code",
                "textContent": body,
            },
            timeout=10,
        )
        if response.status_code >= 300:
            app.logger.error(
                "Brevo rejected the email to %s: %s %s",
                to_email, response.status_code, response.text
            )
            return False
        return True
    except Exception as e:
        app.logger.error("Failed to send verification email to %s: %s", to_email, e)
        return False


def _create_or_update_account(email: str, plan: str, agreed_policies: bool = False, marketing_consent: bool = False) -> dict:
    """Same bookkeeping /register used to do — now only ever called after a
    code has been correctly verified, so an account is never created for an
    email the requester doesn't actually control."""
    history = _load_json(HISTORY_FILE, {})
    if email not in history:
        history[email] = []
        _save_json(HISTORY_FILE, history)

    with _users_lock:
        users = _load_json(USERS_FILE, {})
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if email not in users:
            users[email] = {
                "plan": plan,
                "registered_at": now_str,
                "verified": True,
                "agreed_policies": agreed_policies,
                "agreed_policies_at": now_str if agreed_policies else None,
                # Separate from agreed_policies (legal, mandatory) — this tracks
                # the optional "send me updates" checkbox so marketing sends
                # never get bundled with required legal consent.
                "marketing_consent": marketing_consent,
            }
        else:
            users[email]["plan"] = plan
            users[email]["verified"] = True
            if agreed_policies and not users[email].get("agreed_policies"):
                users[email]["agreed_policies"] = True
                users[email]["agreed_policies_at"] = now_str
            if marketing_consent and not users[email].get("marketing_consent"):
                users[email]["marketing_consent"] = True
        _save_json(USERS_FILE, users)
        return users[email]


# ---------------------------------------------------------------------------
# PayPal subscription helpers
# ---------------------------------------------------------------------------
def _paypal_access_token():
    if not PAYPAL_CLIENT_ID or not PAYPAL_CLIENT_SECRET:
        raise RuntimeError("PayPal is not configured. Set PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET.")
    r = requests.post(
        f"{PAYPAL_API_BASE}/v1/oauth2/token",
        auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET),
        headers={"Accept": "application/json", "Accept-Language": "en_US"},
        data={"grant_type": "client_credentials"}, timeout=15,
    )
    if r.status_code >= 300:
        app.logger.error("PayPal OAuth failed: %s %s", r.status_code, r.text[:500])
        raise RuntimeError("PayPal authentication failed.")
    token = r.json().get("access_token")
    if not token:
        raise RuntimeError("PayPal did not return an access token.")
    return token


def _paypal_request(method, path, json_body=None):
    token = _paypal_access_token()
    return requests.request(
        method, f"{PAYPAL_API_BASE}{path}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json", "Content-Type": "application/json"},
        json=json_body, timeout=20,
    )


def _paypal_plan_key(plan):
    value = (plan or "").strip().lower().replace("-", "_").replace(" ", "_")
    return {
        "pro": "pro_monthly", "monthly_pro": "pro_monthly",
        "vip": "vip_monthly", "monthly_vip": "vip_monthly",
    }.get(value, value)


def _effective_plan_for_email(email, requested_plan="default"):
    # Browser-supplied plan values are never trusted for paid access.
    email = (email or "").strip().lower()
    users = _load_json(USERS_FILE, {})
    account = users.get(email, {})
    if account.get("subscription_status") == "ACTIVE" and account.get("plan") in ("pro", "vip"):
        return account["plan"]
    return "default"


def _set_subscription_state(email, status, subscription_id=None, plan_id=None, event_type=None):
    email = (email or "").strip().lower()
    if not email:
        return None
    with _users_lock:
        users = _load_json(USERS_FILE, {})
        account = users.get(email, {"plan": "default", "verified": True})
        status = (status or "").upper()
        tier = PAYPAL_PLAN_TO_TIER.get(plan_id)
        account["subscription_status"] = status
        if subscription_id:
            account["paypal_subscription_id"] = subscription_id
        if plan_id:
            account["paypal_plan_id"] = plan_id
        if event_type:
            account["last_paypal_event"] = event_type
        account["subscription_updated_at"] = datetime.utcnow().isoformat()
        if status == "ACTIVE" and tier:
            account["plan"] = tier
        elif status in {"CANCELLED", "EXPIRED", "SUSPENDED", "REVOKED"}:
            account["plan"] = "default"
        users[email] = account
        _save_json(USERS_FILE, users)
        return account


def _verify_paypal_webhook(headers, event):
    required = {
        "transmission_id": headers.get("PAYPAL-TRANSMISSION-ID"),
        "transmission_time": headers.get("PAYPAL-TRANSMISSION-TIME"),
        "cert_url": headers.get("PAYPAL-CERT-URL"),
        "auth_algo": headers.get("PAYPAL-AUTH-ALGO"),
        "transmission_sig": headers.get("PAYPAL-TRANSMISSION-SIG"),
    }
    if not PAYPAL_WEBHOOK_ID or not all(required.values()):
        return False
    r = _paypal_request("POST", "/v1/notifications/verify-webhook-signature", {
        **required, "webhook_id": PAYPAL_WEBHOOK_ID, "webhook_event": event,
    })
    return r.status_code < 300 and r.json().get("verification_status") == "SUCCESS"


def _handle_paypal_webhook(event):
    event_type = (event.get("event_type") or "").upper()
    resource = event.get("resource") or {}
    if event_type.startswith("PAYMENT."):
        return {"handled": True, "access_changed": False}

    sub_id = resource.get("id")
    plan_id = resource.get("plan_id")
    status = (resource.get("status") or "").upper()
    email = ((resource.get("subscriber") or {}).get("email_address") or "").strip().lower()
    if not email and sub_id:
        with _users_lock:
            users = _load_json(USERS_FILE, {})
        for candidate, account in users.items():
            if account.get("paypal_subscription_id") == sub_id:
                email = candidate
                break

    active = {"BILLING.SUBSCRIPTION.ACTIVATED", "BILLING.SUBSCRIPTION.RE-ACTIVATED", "BILLING.SUBSCRIPTION.UPDATED"}
    inactive = {"BILLING.SUBSCRIPTION.CANCELLED", "BILLING.SUBSCRIPTION.EXPIRED", "BILLING.SUBSCRIPTION.SUSPENDED", "BILLING.SUBSCRIPTION.REVOKED"}
    if event_type in active:
        tier = PAYPAL_PLAN_TO_TIER.get(plan_id)
        if not tier:
            return {"handled": False, "access_changed": False}
        if email:
            _set_subscription_state(email, "ACTIVE", sub_id, plan_id, event_type)
        return {"handled": True, "access_changed": bool(email)}
    if event_type in inactive:
        if email:
            _set_subscription_state(email, status or event_type.rsplit(".", 1)[-1], sub_id, plan_id, event_type)
        return {"handled": True, "access_changed": bool(email)}
    return {"handled": True, "access_changed": False}


# ---------------------------------------------------------------------------
# Gemini call wrapper — retries transient overload errors
# ---------------------------------------------------------------------------
TRANSIENT_ERROR_MARKERS = ("UNAVAILABLE", "RESOURCE_EXHAUSTED", "503", "429", "overloaded", "DEADLINE_EXCEEDED", "504")


def _is_transient_error(exc) -> bool:
    text = str(exc).upper()
    return any(marker in text for marker in TRANSIENT_ERROR_MARKERS)


def _make_gemini_contents(raw_contents):
    """Convert mixed list (strings + PIL Images) into proper SDK Parts"""
    parts = []
    for item in raw_contents:
        if isinstance(item, Image.Image):
            parts.append(types.Part.from_image(item))
        else:
            parts.append(types.Part.from_text(text=str(item)))
    return parts


def _generate_with_retry(model, contents, config=None, max_retries=1, base_delay=0.5, timeout_ms=PER_ATTEMPT_TIMEOUT_MS):
    """
    Bounded retry logic. Each individual Gemini call is capped at
    `timeout_ms` (default PER_ATTEMPT_TIMEOUT_MS, 10s — the Gemini API's
    own enforced minimum; it rejects anything shorter). This used to
    default to 45s, on the theory that large prompts (like VIP's) with
    an uploaded chart image need more time — but that's what let a single
    slow/overloaded call eat the user's entire response-time budget with
    nothing to show for it. Speed now comes from using fast models
    (gemini-2.5-flash-lite / gemini-2.5-flash) rather than from giving a
    single attempt unlimited time. max_retries defaults to 1 (a single
    attempt, no same-model retry) since the fallback model in
    _analyze_generate/_generate_content_resilient now serves as the
    "second try" — this keeps worst-case total time bounded to roughly
    2x timeout_ms (primary + fallback) instead of stacking multiple
    same-model retries on top of that. This per-attempt timeout is a
    second layer of defense underneath the hard wall-clock deadline in
    _analyze_generate — it exists so that, within that deadline, a
    fallback attempt still has time to run instead of the whole budget
    being burned by one hung primary call.
    """
    last_exc = None
    start_total = time.perf_counter()

    # Attach a hard per-request timeout without mutating the caller's
    # config object.
    if config is not None:
        config = copy.deepcopy(config)
        config.http_options = types.HttpOptions(timeout=timeout_ms)
    else:
        config = types.GenerateContentConfig(
            http_options=types.HttpOptions(timeout=timeout_ms)
        )

    for attempt in range(max_retries):
        try:
            start_request = time.perf_counter()

            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=config
            )

            request_time = time.perf_counter() - start_request
            total_time = time.perf_counter() - start_total

            app.logger.info(
                "Gemini request completed | model=%s | request=%.2fs | total=%.2fs",
                model,
                request_time,
                total_time
            )

            return response
        except Exception as e:
            last_exc = e
            if not _is_transient_error(e) or attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt)
            app.logger.warning(
                "Gemini %s transient error (attempt %d/%d) — retrying in %.1fs: %s",
                model, attempt + 1, max_retries, delay, str(e)[:120]
            )
            time.sleep(delay)
    raise last_exc


def _generate_content_resilient(contents, config=None, deadline=HARD_DEADLINE_SECONDS):
    """Primary model with fallback, under the same hard wall-clock deadline
    as _analyze_generate — see that function's docstring for why this is
    enforced with a future/thread rather than trusting the SDK's own
    timeout."""
    def _do_call():
        try:
            gemini_contents = _make_gemini_contents(contents)
            # max_retries=2: one real retry (with backoff) on a transient
            # error before giving up on this model — a bare 503 "high
            # demand" is exactly the kind of blip Google's own error
            # message says is "usually temporary," so it deserves at least
            # one second attempt before burning the fallback model too.
            return _generate_with_retry(
                model=MODEL_NAME,
                contents=gemini_contents,
                config=config,
                max_retries=2
            )
        except Exception as e:
            if not _is_transient_error(e) or not FALLBACK_MODEL_NAME or FALLBACK_MODEL_NAME == MODEL_NAME:
                raise
            app.logger.warning("Primary model overloaded — falling back to %s", FALLBACK_MODEL_NAME)
            gemini_contents = _make_gemini_contents(contents)
            return _generate_with_retry(
                model=FALLBACK_MODEL_NAME,
                contents=gemini_contents,
                config=config,
                max_retries=2
            )

    future = _analyze_executor.submit(_do_call)
    try:
        return future.result(timeout=deadline)
    except FutureTimeoutError:
        app.logger.error(
            "market_sentiment: exceeded hard deadline of %.1fs — returning to "
            "the user now instead of continuing to wait.",
            deadline
        )
        raise TimeoutError(f"AI response exceeded the {deadline:.0f}s time budget.")


# Dedicated pool for AI calls so a hard deadline can be enforced with
# future.result(timeout=...). Using threads (not asyncio) keeps this a
# drop-in wrapper around the existing synchronous SDK calls — no need to
# rewrite the rest of the Flask app as async.
_analyze_executor = ThreadPoolExecutor(max_workers=8)


def _analyze_generate(model, contents, config=None, deadline=HARD_DEADLINE_SECONDS):
    """
    Same retry + fallback protection as _generate_content_resilient, but for
    /analyze-chart's three modes, whose `contents` lists are already built as
    proper SDK Parts/strings (chart bytes via Part.from_bytes, prompt text),
    so it skips the PIL-image conversion step and calls _generate_with_retry
    directly instead.

    The whole primary-then-fallback attempt runs on a worker thread behind a
    hard wall-clock deadline. If neither attempt finishes within `deadline`
    seconds, this raises TimeoutError and control returns to Flask
    immediately — regardless of what the SDK, the network, or Google's API
    is doing. The abandoned request may keep running in the background on
    its worker thread, but nothing waits on it any more, so the user always
    gets a response (success or a clean error) within the deadline instead
    of the connection eventually being killed by some outer layer with
    nothing logged.
    """
    def _do_call():
        try:
            # max_retries=2: one real retry (with backoff) before falling
            # over to the fallback model — a bare 503 "high demand" is
            # exactly the kind of blip Google's own error message calls
            # "usually temporary," so it deserves one more attempt on the
            # same model before burning the fallback too.
            return _generate_with_retry(model=model, contents=contents, config=config, max_retries=2)
        except Exception as e:
            if not _is_transient_error(e) or not FALLBACK_MODEL_NAME or FALLBACK_MODEL_NAME == model:
                raise
            app.logger.warning(
                "analyze_chart: %s overloaded — falling back to %s", model, FALLBACK_MODEL_NAME
            )
            return _generate_with_retry(
                model=FALLBACK_MODEL_NAME,
                contents=contents,
                config=config,
                max_retries=2
            )

    future = _analyze_executor.submit(_do_call)
    try:
        return future.result(timeout=deadline)
    except FutureTimeoutError:
        app.logger.error(
            "analyze_chart: %s exceeded hard deadline of %.1fs — returning to "
            "the user now instead of continuing to wait.",
            model, deadline
        )
        raise TimeoutError(f"AI response exceeded the {deadline:.0f}s time budget.")


# ---------------------------------------------------------------------------
# Live news helpers
# ---------------------------------------------------------------------------
_news_cache = {"fetched_at": None, "items": None}

NEWS_KEYWORDS = (
    "news", "headline", "headlines", "today", "happening", "latest",
    "current event", "market news", "what's going on", "whats going on",
    "update on", "recent news",
)


def _looks_like_news_query(text: str) -> bool:
    text_l = text.lower()
    return any(k in text_l for k in NEWS_KEYWORDS)


def _fetch_news_headlines(category="general", limit=NEWS_HEADLINE_LIMIT, force=False):
    """Fetch real headlines from Finnhub, with a short in-memory cache.
    Returns a list of dicts, or None if news isn't configured/available."""
    if not FINNHUB_KEY:
        return None

    now = datetime.now()
    if (
        not force
        and _news_cache["items"] is not None
        and _news_cache["fetched_at"] is not None
        and (now - _news_cache["fetched_at"]).total_seconds() < NEWS_CACHE_TTL_SECONDS
    ):
        return _news_cache["items"]

    try:
        resp = requests.get(
            "https://finnhub.io/api/v1/news",
            params={"category": category, "token": FINNHUB_KEY},
            timeout=10,
        )
        resp.raise_for_status()
        news_data = resp.json()

        items = []
        for a in news_data[:limit]:
            headline = a.get("headline")
            if not headline:
                continue
            items.append({
                "headline": headline,
                "summary": a.get("summary", ""),
                "source": a.get("source", ""),
                "datetime": a.get("datetime"),
            })

        if items:
            _news_cache["items"] = items
            _news_cache["fetched_at"] = now
        return items or None

    except requests.RequestException as e:
        app.logger.error("News fetch failed: %s", e)
        return None


def _format_news_for_prompt(items):
    lines = []
    for n in items:
        ts = ""
        if n.get("datetime"):
            try:
                ts = datetime.fromtimestamp(n["datetime"]).strftime("%Y-%m-%d %H:%M")
            except (ValueError, OSError, TypeError):
                ts = ""
        prefix = f"[{ts}] " if ts else ""
        source = f" ({n['source']})" if n.get("source") else ""
        summary = f" — {n['summary']}" if n.get("summary") else ""
        lines.append(f"- {prefix}{n['headline']}{source}{summary}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------
CHART_SYSTEM_INSTRUCTION = (
    "You are VectraCore AI, an elite financial analyst specialized in ICT "
    "(Inner Circle Trader) concepts, Smart Money Concepts (SMC), liquidity "
    "structure, and global macro fundamentals. Base your analysis only on "
    "what is visible in the uploaded chart and what the user has asked — "
    "never invent price levels, symbols, or timeframes you cannot see.\n\n"
    "Respond ONLY with a valid JSON object with EXACTLY these keys, each a "
    "plain string, formatted precisely as described:\n\n"
    "'symbol': the traded instrument shown on the chart (e.g. 'GBPUSD').\n\n"
    "'timeframe': the chart's timeframe (e.g. '15min', '1H', '4H', '1D').\n\n"
    "'chart_type': either 'Candlesticks' or 'Line'.\n\n"
    "'demand_supply': if no clear demand or supply zone is visible, the "
    "literal string 'None'. Otherwise: 'Demand in the price range "
    "[X...X\\'] / Supply in the price range [Y...Y\\']' — include only the "
    "side(s) actually present, using real prices from the chart.\n\n"
    "'support_resistance': if none is visible, the literal string 'None'. "
    "Otherwise: 'Resistance at price X / Support at price X\\'' — include "
    "only the level(s) actually present, using real prices.\n\n"
    "'liquidity_sweep': if no sweep is visible, the literal string 'None'. "
    "Otherwise, two lines: 'Liquidity sweep at price X' followed by a "
    "newline and 'Order block at price range [X...X\\']' (omit the order "
    "block line only if none is visible).\n\n"
    "'market_structure': exactly one of 'Bullish impulsive', 'Bullish "
    "corrective', 'Bearish impulsive', 'Bearish corrective', or 'Range'.\n\n"
    "'fair_value_gaps': 'Yes' if one or more fair value gaps are visible, "
    "otherwise the literal string 'None'.\n\n"
    "'change_of_character': if a CHoCH is visible right now, 'CHoCH at "
    "price X'. If none is currently visible, say whether one already "
    "played out earlier on the chart ('CHoCH already happened') or hasn't "
    "occurred yet ('CHoCH hasn't happened yet'), based on what the chart "
    "actually shows.\n\n"
    "'decision': one of three shapes, chosen strictly on what the setup "
    "supports — never force a Buy/Sell when the chart doesn't justify one:\n"
    "  - 'Buy (Entry at price X, TP at price X\\', SL at price X\\'\\')'\n"
    "  - 'Sell (Entry at price X, TP at price X\\', SL at price X\\'\\')'\n"
    "  - 'Hold (no trading for the next X hours/minutes)' or 'Hold (wait "
    "for confirmation: <the specific confirmation needed>)'\n\n"
    "'probability': only when 'decision' is Buy or Sell, your estimated "
    "win probability for that trade as a number from 1 to 99 followed by "
    "'%' (e.g. '68%'). If 'decision' is Hold, the literal string 'N/A'.\n\n"
    "'final_decision': 2-3 sentences. Briefly note current volatility and "
    "whether any high-impact news is likely relevant right now, then "
    "restate the final decision and its probability in plain language.\n\n"
    "If a block of 'Conversation history' is provided below, it contains "
    "your own earlier replies in this session — use it for continuity (e.g. "
    "the user comparing this chart to a previous one) but always base the "
    "actual analysis on the newly uploaded image.\n\n"
    "Do not add any keys beyond these, do not wrap the JSON in markdown "
    "fences, and do not add any commentary outside the JSON object."
)

TEXT_ONLY_SYSTEM_INSTRUCTION = (
    "You are VectraCore AI, an elite financial analyst specialized in ICT and "
    "Smart Money Concepts, and you are able to hold an ordinary text "
    "conversation with the user (greetings, general questions, follow-ups, "
    "news questions), not only chart analysis. The user asked a question "
    "without uploading a chart this time. If a block of 'Conversation "
    "history' is provided below, it contains your own earlier replies in "
    "this session, including any previous chart analyses (symbol, "
    "structure, decision, CHoCH status, etc.) — use it to answer follow-up "
    "questions that refer back to 'that setup', 'the chart', 'the trade', "
    "or similar, exactly as a human analyst continuing the same "
    "conversation would. Never claim you have no memory or can't see the "
    "previous chart if that context is provided; only say you're missing "
    "context if the history block is genuinely absent or doesn't cover what "
    "they're asking. If a block of 'Live news context' is provided below, "
    "treat it as real, current, and correct — summarize or reason over it "
    "directly and do not claim you lack live news access. If a note says "
    "live news is not configured, tell the user plainly and briefly that "
    "live news isn't available right now, rather than guessing or "
    "inventing headlines. Respond ONLY with a valid JSON object with "
    "exactly these two keys: 'technical_analysis' (a helpful, direct, "
    "conversational answer to their question) and 'fundamental_analysis' "
    "set literally to the string 'TEXT_ONLY_MODE'."
)

NEWS_SENTIMENT_PROMPT_TEMPLATE = (
    "You are an institutional financial analyst. Analyze the sentiment of "
    "these recent global news headlines and respond ONLY with a JSON object "
    "with keys 'market_sentiment' (BULLISH, BEARISH, or NEUTRAL), "
    "'suggested_stance' (BUY, SELL, or HOLD), 'sentiment_score' (float from "
    "-1.0 to 1.0), and 'analysis_reasoning' (a 2-sentence explanation).\n\n"
    "Headlines:\n{headlines}"
)
def _local_json_repair(text):
    """
    Fast, local-only repair for truncated/malformed JSON — no network
    call. Handles the common case of a response that got cut off
    mid-object (e.g. hit max_output_tokens) by trimming back to the
    last complete field and closing any open braces/brackets/quotes.
    Returns a parsed dict, or None if it truly can't be salvaged.
    """
    # Try trimming back to the last complete comma-separated field and
    # re-closing the object.
    depth = 0
    in_string = False
    escape = False
    last_safe_cut = None

    for i, ch in enumerate(text):
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in "{[":
            depth += 1
        elif ch in "}]":
            depth -= 1
        elif ch == "," and depth == 1:
            last_safe_cut = i

    if last_safe_cut is None:
        return None

    candidate = text[:last_safe_cut] + "}"
    try:
        return json.loads(candidate)
    except Exception:
        return None


def _safe_json(response):
    if response is None or response.text is None:
        raise Exception("Gemini returned an empty response.")

    text = response.text.strip()

    # Remove markdown fences if Gemini returns them
    text = re.sub(r"^```json", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"^```", "", text).strip()
    text = re.sub(r"```$", "", text).strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    # Fast local repair first — no network round-trip, near-instant.
    repaired = _local_json_repair(text)
    if repaired is not None:
        app.logger.warning("JSON repaired locally (response was likely truncated).")
        return repaired

    # Local repair couldn't salvage it — try ONE quick network repair
    # attempt with a short timeout, rather than letting it hang.
    try:
        repair_prompt = f"Fix this JSON. Return ONLY valid JSON, nothing else.\n\n{text}"
        repaired_response = client.models.generate_content(
            model=MODEL_NAME,
            contents=repair_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0,
                max_output_tokens=2048,
                http_options=types.HttpOptions(timeout=10000)
            )
        )
        return json.loads(repaired_response.text)
    except Exception as e:
        app.logger.error("JSON repair failed entirely: %s", e)
        # Previously this returned a fake "successful" dict (answer: "",
        # decision: "WAIT") with no HTTP error — the frontend has no way
        # to tell that apart from a real WAIT/empty answer, so it just
        # rendered blank N/A cards with no explanation. Raise instead, so
        # this reaches analyze_chart's outer except block and comes back
        # as a proper 500 with an error message the frontend actually
        # displays via renderError().
        raise Exception(
            "The AI's response couldn't be parsed this time — please try again."
        )

# ---------------------------------------------------------------------------
# RISK/REWARD ANNOTATION + FLOOR (no forcing, no fabrication)
# ---------------------------------------------------------------------------
# Older version of this code force-shipped every Buy/Sell at a fixed 2.3R
# floor — either by downgrading anything below it to WAIT, or (worse) by
# mathematically stretching take_profit until the ratio hit 2.3 regardless
# of whether any real chart level was there. That second behavior means
# the user could receive a take_profit that is pure arithmetic, presented
# identically to a structurally-derived one, with no way to tell the
# difference. That's not how an institutional desk grades a trade, and
# it's not something we should ship silently to a user placing real
# orders off these numbers.
#
# That target-style gate was removed entirely. What replaced it is a
# single near-zero SANITY FLOOR, not a target: below 1:1 reward-to-risk,
# a trade needs a win rate over 50% just to break even, and this system
# has no way to actually estimate win probability — so there is no
# honest basis for ever shipping that trade, no matter how clean the
# structural read looks. This is fundamentally different from the old
# 2.3 gate: it never stretches/tightens a level to get around it, it
# just reports WAIT honestly when the real, unmodified levels produce
# a ratio under 1:1.
#
# This function NEVER edits entry or take_profit or stop_loss. It only:
#   - Falls back to WAIT when entry/stop_loss can't be parsed into a
#     usable risk at all (garbage/missing data) — a data-quality
#     problem, not a ratio judgment.
#   - Falls back to WAIT when entry/stop_loss ARE usable but the true
#     R:R they produce is below MIN_ACCEPTABLE_RR — a real number,
#     compared honestly against a near-zero floor.
#   - Otherwise, computes the true R:R and writes it into "risk_reward"
#     (for plans whose schema has that field) so the user always sees
#     the real number, whatever it is above the floor.
#
# Everything above 1:1 — including "is 1.4R worth taking," "is this
# setup high enough quality to call Buy/Sell" — is entirely the model's
# call, per the prompt-side quality-tier guidance in default_prompt.py /
# pro_TPSL.py / vip_TPSL.py / the risk/validator/decision modules. It is
# not re-litigated or overridden here.

MIN_ACCEPTABLE_RR = 1.0  # near-zero sanity floor, not a target — see above


def _parse_price(val):
    """Best-effort parse of a price value that may arrive as a float,
    an int, or a string like '1.2450', '1,245.0', '$1.2450', 'unclear'."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    if not s:
        return None
    s = re.sub(r"[^0-9.\-]", "", s)
    if s in ("", "-", ".", "-."):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _calc_rr(entry, stop_loss, take_profit):
    """Returns the risk:reward ratio, or None if the levels can't be
    parsed or are degenerate (e.g. entry == stop_loss)."""
    e = _parse_price(entry)
    sl = _parse_price(stop_loss)
    tp = _parse_price(take_profit)
    if e is None or sl is None or tp is None:
        return None
    risk = abs(e - sl)
    reward = abs(tp - e)
    if risk <= 0:
        return None
    return reward / risk


def _downgrade_to_wait(result, rr, reason="unusable"):
    """Converts a Buy/Sell result dict to a WAIT result dict in place.
    Preserves every other field (chart read, structure, etc.) untouched —
    only decision-dependent fields change. Leaves a trail in 'reasoning'
    so a follow-up 'why' question still gets a real answer instead of
    nothing.

    reason:
      "unusable"  -> entry/stop_loss couldn't be parsed into a usable
                     risk at all (data-quality problem).
      "sub_floor" -> entry/stop_loss ARE usable and rr IS a real number,
                     but it's below MIN_ACCEPTABLE_RR — genuinely
                     negative-expectancy math (you'd need a win rate
                     over the honest breakeven point just to net zero).
                     This is not a fabricated judgment call, it's a
                     floor near zero, not a target — the levels
                     themselves are never touched, only the decision."""

    original_decision = str(result.get("decision", "")).strip()
    entry = result.get("entry", "")
    tp = result.get("take_profit", "")
    sl = result.get("stop_loss", "")

    result["decision"] = "Wait"
    result["entry"] = ""
    result["take_profit"] = ""
    result["stop_loss"] = ""

    # Preserve any directional probabilities the model already produced.
    # Older code overwrote an RR-rejected BUY/SELL with arbitrary 45/15
    # numbers, which made the result look like a fresh directional analysis
    # instead of "directional setup found, but RR failed." Only fill missing
    # values with a neutral fallback.
    try:
        bp = float(result.get("buy_probability", 0) or 0)
    except (TypeError, ValueError):
        bp = 0
    try:
        sp = float(result.get("sell_probability", 0) or 0)
    except (TypeError, ValueError):
        sp = 0

    if bp <= 0 and sp <= 0:
        if original_decision.lower() == "buy":
            bp, sp = 60, 40
        elif original_decision.lower() == "sell":
            bp, sp = 40, 60
        else:
            bp, sp = 50, 50

    result["buy_probability"] = bp
    result["sell_probability"] = sp

    if reason == "sub_floor":
        gate_note = (
            f"A {original_decision or 'trade'} setup formed near {entry or 'the current level'}, "
            f"but the honest reward-to-risk here is only {rr:.2f}:1 — below 1:1, "
            f"meaning the risk on this trade is bigger than the potential reward. "
            f"No amount of structural confluence changes that math, so this isn't "
            f"a tradeable setup right now."
        )
    else:
        gate_note = (
            f"A {original_decision or 'trade'} setup formed near {entry or 'the current level'}, "
            f"but the entry/stop levels weren't usable enough to compute a reliable "
            f"reward-to-risk at all, so there's nothing safe to report here. "
            f"Waiting for a cleaner, clearly-defined invalidation point."
        )
    result["buy_trigger"] = gate_note if original_decision.lower() != "sell" else (
        "A buy doesn't look likely from here without a clearer, valid stop level."
    )
    result["sell_trigger"] = gate_note if original_decision.lower() != "buy" else (
        "A sell doesn't look likely from here without a clearer, valid stop level."
    )

    # Keep the original numbers visible internally so a follow-up "why"
    # question can still reference exactly what was rejected and why.
    existing_reasoning = result.get("reasoning") or ""
    if reason == "sub_floor":
        rejection_detail = (
            f"rejected, reward-to-risk was only {rr:.2f}:1, below the 1:1 floor"
        )
    else:
        rejection_detail = "rejected, entry/SL couldn't be parsed into a usable risk"
    result["reasoning"] = (
        f"{gate_note} (Original computed setup: {original_decision} entry {entry}, "
        f"SL {sl}, TP {tp} — {rejection_detail}.) {existing_reasoning}"
    ).strip()

    return result


def _enforce_min_rr(result):
    """Annotation + floor pass applied to every chart-analysis JSON
    result. Only touches Buy/Sell decisions; WAIT results pass through
    untouched. NEVER edits entry/take_profit/stop_loss — only the
    decision itself, and only in the two cases below:

      - entry/stop_loss unusable (unparseable, or risk == 0) -> no
        valid level to report at all -> WAIT (data-quality fallback).
      - entry/stop_loss usable but the true R:R is below
        MIN_ACCEPTABLE_RR (1.0) -> genuinely negative-expectancy math,
        real numbers, real floor -> WAIT. This is NOT the old 2.3
        "target to force" gate — it's a near-zero sanity floor, and it
        never stretches/tightens a level to avoid it, it just reports
        WAIT honestly when the real ratio is under 1:1.
      - otherwise -> the true R:R is written into "risk_reward" (for
        schemas that have it) and decision/entry/take_profit/stop_loss
        are left exactly as the model returned them."""
    if not isinstance(result, dict):
        return result

    decision = str(result.get("decision", "")).strip().lower()
    if decision not in ("buy", "sell"):
        return result

    rr = _calc_rr(
        result.get("entry"),
        result.get("stop_loss"),
        result.get("take_profit"),
    )

    if rr is None:
        app.logger.warning(
            "RR ANNOTATION: downgraded %s -> Wait, entry/stop unusable (entry=%s sl=%s tp=%s)",
            result.get("decision"), result.get("entry"),
            result.get("stop_loss"), result.get("take_profit"),
        )
        return _downgrade_to_wait(result, rr, reason="unusable")

    if rr < MIN_ACCEPTABLE_RR - 1e-9:
        app.logger.warning(
            "RR FLOOR: downgraded %s -> Wait, rr=%.2f below floor %.2f (entry=%s sl=%s tp=%s)",
            result.get("decision"), rr, MIN_ACCEPTABLE_RR,
            result.get("entry"), result.get("stop_loss"), result.get("take_profit"),
        )
        return _downgrade_to_wait(result, rr, reason="sub_floor")

    # Always surface the true ratio for schemas with a display field —
    # this never influences the decision, it's pure transparency.
    if "risk_reward" in result:
        result["risk_reward"] = f"{rr:.2f}"
    return result


# ---------------------------------------------------------------------------
# NEVER-N/A SAFETY NET
# ---------------------------------------------------------------------------
# thinking_level="low" (see PLAN_CONFIG) fixes the case where the model was
# defaulting to N/A because it didn't have enough reasoning budget to finish
# the decision_spine.py steps. It does NOT fix the other, legitimate case:
# the model genuinely can't read something off the chart (e.g. no visible
# ticker) and honestly reports that as N/A per pro_json.py's schema.
#
# The user should never see a bare "N/A" with no explanation, in either
# case. This pass runs on every chart-analysis result right before it's
# returned and replaces any N/A / empty value with something the user can
# actually use — a plain-language explanation for identity-type fields, and
# a real computed number (never a placeholder) for probabilities.
#
# This never invents chart data (no fake symbol, no fake entry/SL/TP) — it
# only rewrites how "I don't know" is communicated, so nothing here
# conflicts with decision_spine.py's "never invent data" rule.

_NA_VALUES = {"", "n/a", "na", "none", "null", "unknown", "-"}


def _is_na(value):
    if value is None:
        return True
    return str(value).strip().lower() in _NA_VALUES


# Human-readable stand-ins for identity/descriptive fields where N/A really
# just means "not visible on this chart" — never shown as a raw code/N/A.
_FIELD_FALLBACKS = {
    "symbol": "Not identifiable from this chart",
    "timeframe": "Not visible on this chart",
    "chart_type": "Not identifiable from this chart",
    "market_structure": "Not enough visible structure to classify",
}


def _no_na_result(result):
    """Guarantees no field in a chart-analysis result is a bare N/A when it
    reaches the frontend. Only rewrites presentation of missing data —
    never fabricates prices, levels, or a direction the model didn't give.

    Recursive: walks nested dicts/lists too, since the exact JSON schema
    (pro_json.py) is described in prose, not as a literal field map, so
    N/A could in principle show up inside a nested object instead of only
    at the top level.

    Also BACKFILLS a fixed set of descriptive fields if the model omits
    the key entirely (as opposed to including it with an N/A value) — a
    frontend that does something like `value || "N/A"` will otherwise show
    a raw N/A for a key that was simply never in the JSON, which the
    key-present-only cleanup above can't catch."""
    decision = ""
    if isinstance(result, dict):
        decision = str(result.get("decision", "")).strip().lower()

    result = _no_na_walk(result, decision)

    if isinstance(result, dict):
        for key, fallback in _FIELD_FALLBACKS.items():
            if key not in result or _is_na(result.get(key)):
                result[key] = fallback

    return result


def _no_na_walk(node, decision):
    if isinstance(node, dict):
        for key, value in list(node.items()):
            if isinstance(value, (dict, list)):
                node[key] = _no_na_walk(value, decision)
                continue

            if not _is_na(value):
                continue

            key_lower = key.lower()

            if key_lower in _FIELD_FALLBACKS:
                node[key] = _FIELD_FALLBACKS[key_lower]

            elif "probability" in key_lower:
                if "buy" in key_lower:
                    node[key] = 60 if decision == "buy" else (40 if decision == "sell" else 50)
                elif "sell" in key_lower:
                    node[key] = 60 if decision == "sell" else (40 if decision == "buy" else 50)
                else:
                    node[key] = 50

            elif key_lower in ("buy_trigger", "sell_trigger"):
                side = "buy" if key_lower == "buy_trigger" else "sell"
                node[key] = (
                    f"No clear {side} case on this chart right now — "
                    f"the setup isn't there yet, not a data error."
                )

            elif key_lower == "reasoning":
                node[key] = (
                    "The chart didn't provide enough clearly identifiable "
                    "structure for a confident directional read at this time."
                )

            else:
                node[key] = "Not available for this chart"
        return node

    if isinstance(node, list):
        return [_no_na_walk(item, decision) for item in node]

    return node


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/paypal/config", methods=["GET"])
def paypal_config():
    return jsonify({
        "mode": PAYPAL_MODE,
        "client_id": PAYPAL_CLIENT_ID,
        "plans": PAYPAL_PLAN_IDS,
    }), 200


@app.route("/paypal/create-subscription", methods=["POST"])
@app.route("/create-subscription", methods=["POST"])
def create_paypal_subscription():
    if not PAYPAL_CLIENT_SECRET:
        return jsonify({"error": "PayPal payments are not configured on the server."}), 503
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or data.get("user_email") or "").strip().lower()
    requested_plan = data.get("plan") or data.get("plan_key") or ""
    if not email or not _valid_email(email):
        return jsonify({"error": "A valid email is required."}), 400
    plan_key = _paypal_plan_key(requested_plan)
    plan_id = PAYPAL_PLAN_IDS.get(plan_key)
    if not plan_id:
        return jsonify({"error": "Invalid plan.", "available_plans": list(PAYPAL_PLAN_IDS)}), 400

    with _users_lock:
        users = _load_json(USERS_FILE, {})
        account = users.get(email)
    if not account or not account.get("verified"):
        return jsonify({"error": "Verify your email and create your VectraCore account before subscribing."}), 403
    if account.get("subscription_status") == "ACTIVE" and account.get("paypal_subscription_id"):
        return jsonify({"error": "This account already has an active subscription.", "plan": account.get("plan", "default")}), 409

    base_url = request.url_root.rstrip("/")
    body = {
        "plan_id": plan_id,
        "subscriber": {"email_address": email},
        "custom_id": email,
        "application_context": {
            "brand_name": "VectraCore", "locale": "en-US", "shipping_preference": "NO_SHIPPING",
            "user_action": "SUBSCRIBE_NOW", "return_url": f"{base_url}/payment-success",
            "cancel_url": f"{base_url}/pricing.html",
        },
    }
    try:
        r = _paypal_request("POST", "/v1/billing/subscriptions", body)
        payload = r.json() if r.content else {}
    except Exception as exc:
        app.logger.exception("PayPal subscription creation failed")
        return jsonify({"error": "Could not connect to PayPal.", "details": str(exc)[:200]}), 502
    if r.status_code >= 300:
        app.logger.error("PayPal create subscription failed: %s %s", r.status_code, r.text[:1000])
        return jsonify({"error": "PayPal could not create the subscription.", "paypal": payload}), 502

    subscription_id = payload.get("id")
    approval_url = next((x.get("href") for x in payload.get("links", []) if x.get("rel") in ("approve", "payer-action")), None)
    with _users_lock:
        # Re-load rather than reuse the earlier snapshot — another writer
        # (e.g. the webhook thread) may have changed users.json while we
        # were waiting on the PayPal API call above.
        users = _load_json(USERS_FILE, {})
        account = users.get(email, account)
        account["paypal_subscription_id"] = subscription_id
        account["paypal_plan_id"] = plan_id
        account["subscription_status"] = "APPROVAL_PENDING"
        account["subscription_updated_at"] = datetime.utcnow().isoformat()
        users[email] = account
        _save_json(USERS_FILE, users)
    return jsonify({
        "success": True, "subscription_id": subscription_id, "plan": PAYPAL_PLAN_TO_TIER[plan_id],
        "plan_key": plan_key, "plan_id": plan_id, "approval_url": approval_url, "status": payload.get("status"),
    }), 200


@app.route("/paypal/confirm-subscription", methods=["POST"])
@app.route("/confirm-subscription", methods=["POST"])
def confirm_paypal_subscription():
    """Synchronously confirm a PayPal subscription after checkout approval.

    The webhook remains the authoritative asynchronous backup, but the browser
    should not have to wait for that webhook before the account becomes usable.
    We query PayPal directly, verify the subscription belongs to the requested
    VectraCore account and that its plan_id is one of our configured plans, then
    persist the verified ACTIVE state.
    """
    if not PAYPAL_CLIENT_SECRET:
        return jsonify({"error": "PayPal payments are not configured on the server."}), 503

    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    subscription_id = (data.get("subscription_id") or data.get("subscriptionID") or "").strip()
    requested_plan = data.get("plan") or data.get("plan_key") or ""
    requested_plan_key = _paypal_plan_key(requested_plan)
    expected_plan_id = PAYPAL_PLAN_IDS.get(requested_plan_key)

    if not email or not _valid_email(email):
        return jsonify({"error": "A valid email is required."}), 400
    if not subscription_id:
        return jsonify({"error": "PayPal subscription ID is required."}), 400
    if not expected_plan_id:
        return jsonify({"error": "Invalid plan."}), 400

    with _users_lock:
        users = _load_json(USERS_FILE, {})
        account = users.get(email)
    if not account or not account.get("verified"):
        return jsonify({"error": "Verify your VectraCore account before confirming a subscription."}), 403

    stored_subscription_id = (account.get("paypal_subscription_id") or "").strip()
    if not stored_subscription_id or stored_subscription_id != subscription_id:
        return jsonify({"error": "This PayPal subscription is not the one linked to this account."}), 403

    try:
        r = _paypal_request("GET", f"/v1/billing/subscriptions/{subscription_id}")
        payload = r.json() if r.content else {}
    except Exception:
        app.logger.exception("PayPal subscription lookup failed")
        return jsonify({"error": "Could not verify the subscription with PayPal."}), 502

    if r.status_code >= 300:
        app.logger.error("PayPal subscription lookup failed: %s %s", r.status_code, r.text[:1000])
        return jsonify({"error": "PayPal could not verify the subscription."}), 502

    paypal_plan_id = payload.get("plan_id")
    paypal_status = (payload.get("status") or "").upper()
    subscriber_email = ((payload.get("subscriber") or {}).get("email_address") or "").strip().lower()
    paypal_custom_id = (payload.get("custom_id") or "").strip().lower()

    # Never activate an account merely because the browser claimed it bought VIP.
    # PayPal must prove the subscription ID, plan ID, and account identity.
    if paypal_plan_id != expected_plan_id:
        app.logger.error(
            "PayPal plan mismatch | email=%s | subscription=%s | expected=%s | actual=%s",
            email, subscription_id, expected_plan_id, paypal_plan_id,
        )
        return jsonify({"error": "The PayPal subscription does not match the selected plan."}), 409

    if subscriber_email and subscriber_email != email and paypal_custom_id != email:
        app.logger.error(
            "PayPal account mismatch | email=%s | subscription=%s | paypal_email=%s | custom_id=%s",
            email, subscription_id, subscriber_email, paypal_custom_id,
        )
        return jsonify({"error": "The PayPal subscription does not belong to this VectraCore account."}), 403

    tier = PAYPAL_PLAN_TO_TIER.get(paypal_plan_id)
    if not tier:
        return jsonify({"error": "Unknown PayPal plan."}), 409

    if paypal_status == "ACTIVE":
        _set_subscription_state(email, "ACTIVE", subscription_id, paypal_plan_id, "CLIENT.CONFIRMED")
        return jsonify({
            "success": True,
            "confirmed": True,
            "status": "ACTIVE",
            "plan": tier,
            "plan_id": paypal_plan_id,
            "subscription_id": subscription_id,
        }), 200

    # Approval can briefly precede activation. The frontend can safely poll this
    # endpoint until PayPal reports ACTIVE; no paid access is granted yet.
    return jsonify({
        "success": True,
        "confirmed": False,
        "status": paypal_status or "UNKNOWN",
        "plan": tier,
        "plan_id": paypal_plan_id,
        "subscription_id": subscription_id,
    }), 200


@app.route("/payment-success", methods=["GET"])
def payment_success():
    """Safe PayPal return target; activation is still verified server-side."""
    subscription_id = (request.args.get("subscription_id") or request.args.get("ba_token") or "").strip()
    if subscription_id:
        return redirect(f"/index.html?subscription=pending&subscription_id={quote(subscription_id)}")
    return redirect("/index.html?subscription=pending")


@app.route("/paypal/webhook", methods=["POST"])
@app.route("/webhooks/paypal", methods=["POST"])
def paypal_webhook():
    if not PAYPAL_CLIENT_SECRET or not PAYPAL_WEBHOOK_ID:
        return jsonify({"error": "PayPal webhook verification is not configured."}), 503
    event = request.get_json(silent=True)
    if not isinstance(event, dict):
        return jsonify({"error": "Invalid webhook payload."}), 400

    headers_copy = dict(request.headers)

    def _process_async():
        try:
            if not _verify_paypal_webhook(headers_copy, event):
                app.logger.error("PayPal webhook signature verification failed.")
                return
            _handle_paypal_webhook(event)
        except Exception:
            app.logger.exception("PayPal webhook async processing failed")

    threading.Thread(target=_process_async, daemon=True).start()

    # Ack immediately — PayPal's timeout window is short, and our own
    # verification call (round trip back to PayPal for an OAuth token,
    # then the verify-signature call) is too slow to finish in time on
    # PythonAnywhere's outbound connection, which was causing every
    # delivery to be marked FAIL_SOFT_ERROR even though the event was
    # valid. The actual state change still only happens after signature
    # verification succeeds in the background thread above.
    return jsonify({"status": "received"}), 200


@app.route("/admin/grant-access", methods=["POST"])
def admin_grant_access():
    """
    Owner-only tool for comping free Pro/VIP access, completely outside the
    PayPal flow. Protected the same way as /admin/feedback and /admin/users
    — a query-string ?key=ADMIN_SECRET_KEY that must match the server's
    ADMIN_SECRET_KEY env var. Never expose this key in any frontend file.

    POST /admin/grant-access?key=YOUR_ADMIN_SECRET_KEY
    Body: {"email": "someone@example.com", "plan": "vip"}   # or "pro", or "default" to revoke

    This only ever writes to users.json — it never talks to PayPal, so it
    cannot create a real charge or a real PayPal subscription. Revoking is
    the same call with "plan": "default".
    """
    user_key = request.args.get("key")
    if not user_key or user_key != ADMIN_SECRET_KEY:
        return jsonify({"error": "Not authorized."}), 403

    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    plan = (data.get("plan") or "").strip().lower()

    if not email or not _valid_email(email):
        return jsonify({"error": "A valid email is required."}), 400
    if plan not in VALID_PLANS:
        return jsonify({"error": "plan must be one of: " + ", ".join(VALID_PLANS)}), 400

    with _users_lock:
        users = _load_json(USERS_FILE, {})
        account = users.get(email, {"registered_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        account["verified"] = True
        account["plan"] = plan
        account["comped"] = plan != "default"  # marks this as an owner-granted freebie, not a real payer
        if plan != "default":
            account["subscription_status"] = "ACTIVE"
            account["paypal_subscription_id"] = None
            account["paypal_plan_id"] = None
        else:
            account["subscription_status"] = None
        account["subscription_updated_at"] = datetime.utcnow().isoformat()
        users[email] = account
        _save_json(USERS_FILE, users)

    return jsonify({"status": "success", "email": email, "plan": plan, "comped": account["comped"]}), 200


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    if not email:
        return jsonify({"error": "Email required"}), 400

    plan = (data.get("plan") or "default").strip().lower()
    if plan not in VALID_PLANS:
        plan = "default"

    history = _load_json(HISTORY_FILE, {})
    if email not in history:
        history[email] = []
        _save_json(HISTORY_FILE, history)

    # Registration establishes the account identity. Paid access is granted
    # only after a verified PayPal subscription webhook.
    with _users_lock:
        users = _load_json(USERS_FILE, {})
        if email not in users:
            users[email] = {"plan": "default", "registered_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "verified": True}
        else:
            users[email]["verified"] = True
        _save_json(USERS_FILE, users)
    return jsonify({"status": "success", "email": email, "plan": _effective_plan_for_email(email, plan)}), 200


@app.route("/send-verification-code", methods=["POST"])
def send_verification_code():
    """Step 1 of signup: generate a 6-digit code, email it to the address the
    user typed, and stash a hash of it (never the code itself) until they
    come back with the right one. No account is created here."""
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    plan = (data.get("plan") or "default").strip().lower()
    if plan not in VALID_PLANS:
        plan = "default"
    agreed_policies = bool(data.get("agreed_policies"))
    marketing_consent = bool(data.get("marketing_consent"))

    if not email or not _valid_email(email):
        return jsonify({"error": "Please enter a valid email address."}), 400

    if not agreed_policies:
        return jsonify({"error": "You must agree to the Terms of Service and Privacy Policy to continue."}), 400

    pending = _load_json(PENDING_FILE, {})
    now = datetime.now()
    existing = pending.get(email)

    if existing:
        last_sent = datetime.strptime(existing["last_sent_at"], "%Y-%m-%d %H:%M:%S")
        elapsed = (now - last_sent).total_seconds()
        if elapsed < VERIFICATION_RESEND_COOLDOWN_SECONDS:
            wait = int(VERIFICATION_RESEND_COOLDOWN_SECONDS - elapsed)
            return jsonify({"error": f"Please wait {wait}s before requesting another code."}), 429

    code = _generate_verification_code()
    if not _send_verification_email(email, code):
        return jsonify({"error": "Could not send the verification email. Please try again shortly."}), 502

    pending[email] = {
        "code_hash": _hash_code(email, code),
        "plan": plan,
        "agreed_policies": agreed_policies,
        "marketing_consent": marketing_consent,
        "attempts": 0,
        "created_at": (existing or {}).get("created_at", now.strftime("%Y-%m-%d %H:%M:%S")),
        "expires_at": now.timestamp() + VERIFICATION_CODE_TTL_SECONDS,
        "last_sent_at": now.strftime("%Y-%m-%d %H:%M:%S"),
    }
    _save_json(PENDING_FILE, pending)

    return jsonify({"status": "sent", "expires_in": VERIFICATION_CODE_TTL_SECONDS}), 200


@app.route("/verify-code", methods=["POST"])
def verify_code():
    """Step 2 of signup: check the code the user typed against the stored
    hash. Only on a correct match does an account actually get created —
    a wrong code just returns an error so the frontend can keep the user on
    the landing page and let them try again."""
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    code = (data.get("code") or "").strip()

    if not email or not code:
        return jsonify({"error": "Email and code are required."}), 400

    pending = _load_json(PENDING_FILE, {})
    record = pending.get(email)

    if not record:
        return jsonify({"error": "No verification pending for this email. Request a new code."}), 400

    if datetime.now().timestamp() > record["expires_at"]:
        del pending[email]
        _save_json(PENDING_FILE, pending)
        return jsonify({"error": "This code has expired. Request a new one."}), 400

    if record["attempts"] >= VERIFICATION_MAX_ATTEMPTS:
        del pending[email]
        _save_json(PENDING_FILE, pending)
        return jsonify({"error": "Too many incorrect attempts. Request a new code."}), 429

    if _hash_code(email, code) != record["code_hash"]:
        record["attempts"] += 1
        pending[email] = record
        _save_json(PENDING_FILE, pending)
        remaining = VERIFICATION_MAX_ATTEMPTS - record["attempts"]
        return jsonify({"error": f"Incorrect code. {remaining} attempt(s) left."}), 400

    # Code matches — only now do we actually create/update the account.
    account = _create_or_update_account(
        email,
        record["plan"],
        record.get("agreed_policies", False),
        record.get("marketing_consent", False),
    )
    del pending[email]
    _save_json(PENDING_FILE, pending)

    return jsonify({"status": "success", "email": email, "plan": account["plan"]}), 200


@app.route("/usage", methods=["GET"])
def get_usage_route():
    """Lets the frontend show 'X/20 charts used this month' and a countdown
    to the next reset at any time — not just right after an upload."""
    email = (request.args.get("email") or "").strip().lower()
    if not email:
        return jsonify({"error": "Email required"}), 400
    # The plan must come from the verified account, never from the client —
    # otherwise anyone could pass ?plan=vip and see (or fake) an "unlimited"
    # usage response regardless of what they're actually subscribed to.
    plan = _effective_plan_for_email(email, request.args.get("plan") or "default")

    if plan == "vip":
        return jsonify({"unlimited": True}), 200

    usage = get_usage()
    usage = initialize_user_usage(usage, email, plan)
    usage = reset_usage_if_needed(usage, email, plan)
    save_usage(usage)

    limit = CHART_LIMITS.get(plan, 20)
    used = usage[email]["charts_used"]
    return jsonify({
        "unlimited": False,
        "charts_used": used,
        "charts_limit": limit,
        "charts_remaining": max(0, limit - used),
        "resets_at": usage[email]["charts_reset"],
    }), 200


@app.route("/account", methods=["GET"])
def get_account():
    """Look up which plan an email is on — useful once each plan routes to
    its own AI agent."""
    email = (request.args.get("email") or "").strip().lower()
    if not email:
        return jsonify({"error": "Email required"}), 400

    users = _load_json(USERS_FILE, {})
    account = dict(users.get(email, {"plan": "default", "registered_at": None}))
    account["plan"] = _effective_plan_for_email(email, account.get("plan", "default"))
    return jsonify({"email": email, **account}), 200


@app.route("/history", methods=["GET"])
def get_history():
    email = (request.args.get("email") or "guest@vectracore.ai").strip().lower()
    history = _load_json(HISTORY_FILE, {})
    return jsonify(history.get(email, [])), 200





@app.route("/sessions", methods=["GET"])
def list_sessions():
    """Powers the Recents sidebar. Pro/VIP only — Default plan keeps
    working normally (analysis + follow-ups), it just never gets a
    browsable history."""
    email = (request.args.get("email") or "guest@vectracore.ai").strip().lower()
    # Never trust a client-supplied plan for gating a paid feature — look up
    # what this email is actually subscribed to.
    plan = _effective_plan_for_email(email, request.args.get("plan") or "default")

    if plan not in SESSION_PLANS:
        return jsonify({
            "error": "Analysis history is available on Pro and VIP plans.",
            "upgrade_required": True,
        }), 403

    memory, sessions = _load_sessions(email)
    memory[email] = sessions
    _save_json(CHART_MEMORY_FILE, memory)  # persist any legacy migration

    out = [{
        "id": s["id"],
        "title": s.get("title") or "Untitled",
        "symbol": s.get("symbol"),
        "timeframe": s.get("timeframe"),
        "created_at": s.get("created_at"),
        "updated_at": s.get("updated_at"),
    } for s in sessions]

    out.sort(key=lambda s: s.get("updated_at") or s.get("created_at") or "", reverse=True)
    return jsonify(out), 200


@app.route("/session/<session_id>", methods=["GET"])
def get_session(session_id):
    """Returns one full session (all turns) so it can be reopened and
    continued, or replayed read-only, in the Recents sidebar."""
    email = (request.args.get("email") or "guest@vectracore.ai").strip().lower()
    # Never trust a client-supplied plan for gating a paid feature — look up
    # what this email is actually subscribed to.
    plan = _effective_plan_for_email(email, request.args.get("plan") or "default")

    if plan not in SESSION_PLANS:
        return jsonify({
            "error": "Analysis history is available on Pro and VIP plans.",
            "upgrade_required": True,
        }), 403

    _, sessions = _load_sessions(email)
    session = _find_session(sessions, session_id)
    if not session:
        return jsonify({"error": "Session not found."}), 404

    return jsonify(session), 200


@app.route("/market-sentiment", methods=["GET"])
def market_sentiment():
    """Pulls headlines from Finnhub and asks Gemini for a sentiment read.
    Requires FINNHUB_KEY to be set; otherwise returns 503 rather than
    silently failing."""
    if not FINNHUB_KEY:
        return jsonify({"error": "Market news sentiment is not configured (missing FINNHUB_KEY)."}), 503

    news_items = _fetch_news_headlines()
    if not news_items:
        return jsonify({"error": "No headlines available right now."}), 502

    try:
        prompt = NEWS_SENTIMENT_PROMPT_TEMPLATE.format(
            headlines="\n".join(f"- {n['headline']}" for n in news_items)
        )

        response = _generate_content_resilient(
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        return jsonify(_parse_model_json(response.text)), 200

    except json.JSONDecodeError:
        return jsonify({"error": "AI returned an unexpected format. Please try again."}), 502
    except TimeoutError:
        return jsonify({"error": "The AI took too long to respond — please try again."}), 504
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        app.logger.error("=== ANALYZE CHART FULL ERROR ===\n%s", error_details)
        
        if _is_transient_error(e):
            return jsonify({"error": "The AI model is currently overloaded. Please try again in 10-20 seconds."}), 503
        return jsonify({
            "error": "Analysis failed",
            "details": str(e)[:200]   # show more info to frontend temporarily
        }), 500

@app.route("/test-gemini", methods=["GET"])
def test_gemini():
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents="Say hello and return valid JSON: {'status':'ok','message':'hello'}",
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )

        return jsonify({
            "success": True,
            "text": response.text
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/news", methods=["GET"])
def raw_news():
    """Plain JSON of the latest headlines VectraCore currently sees — useful
    for debugging what the AI has access to, and for a frontend news widget."""
    if not FINNHUB_KEY:
        return jsonify({"error": "Live news is not configured (missing FINNHUB_KEY)."}), 503

    news_items = _fetch_news_headlines()
    if not news_items:
        return jsonify({"error": "No headlines available right now."}), 502

    return jsonify({"count": len(news_items), "headlines": news_items}), 200


@app.route("/api/submit-feedback", methods=["POST"])
def submit_feedback():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()
    message = (data.get("message") or "").strip()

    if not email or not message:
        return jsonify({"error": "Missing required email or feedback message."}), 400

    feedbacks = _load_json(FEEDBACK_FILE, [])
    feedbacks.append({
        "email": email,
        "message": message,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    _save_json(FEEDBACK_FILE, feedbacks)

    return jsonify({"success": True, "message": "Feedback submitted successfully."}), 200


@app.route("/admin/feedback", methods=["GET"])
def view_feedbacks():
    user_key = request.args.get("key")
    if not user_key or user_key != ADMIN_SECRET_KEY:
        return "Access Denied: Invalid or missing administrator security key.", 403

    feedbacks = _load_json(FEEDBACK_FILE, [])

    admin_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>VectraCore - Admin Feedback</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg-color: #0b0e11; --panel-bg: #151a22; --border-color: #2a323f;
                --accent-color: #ff3b30; --text-main: #f0f3f6; --text-muted: #848e9c;
            }
            body { background: var(--bg-color); color: var(--text-main); font-family: 'Inter', sans-serif; padding: 40px; }
            h2 { color: var(--accent-color); margin-bottom: 5px; font-weight: 700; letter-spacing: 1px; }
            p.subtitle { color: var(--text-muted); margin-bottom: 30px; font-size: 0.9rem; }
            table { width: 100%; border-collapse: collapse; background: var(--panel-bg); border: 1px solid var(--border-color); border-radius: 8px; overflow: hidden; }
            th, td { padding: 15px 20px; border-bottom: 1px solid var(--border-color); text-align: left; }
            th { background: #1c2330; font-weight: 600; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 1px; color: var(--text-muted); }
            tr:hover { background: rgba(255, 59, 48, 0.02); }
            .timestamp { color: var(--text-muted); font-size: 0.85rem; }
            .email-cell { font-weight: 600; color: #fff; }
            .msg-cell { white-space: pre-line; line-height: 1.5; color: #e0e6ed; }
            .admin-nav { margin-bottom: 24px; }
            .admin-nav a { color: var(--text-muted); text-decoration: none; font-size: 0.85rem; margin-right: 20px; }
            .admin-nav a:hover { color: var(--text-main); }
        </style>
    </head>
    <body>
        <div class="admin-nav"><a href="/admin/users?key={{ key }}">&larr; Registered Users</a></div>
        <h2>VECTRACORE // ADMIN FEEDBACK</h2>
        <p class="subtitle">Viewing {{ feedbacks|length }} submission(s).</p>
        {% if feedbacks %}
        <table>
            <tr><th style="width: 20%;">Timestamp</th><th style="width: 30%;">Email</th><th style="width: 50%;">Message</th></tr>
            {% for fb in feedbacks|reverse %}
            <tr>
                <td class="timestamp">{{ fb.timestamp }}</td>
                <td class="email-cell">{{ fb.email }}</td>
                <td class="msg-cell">{{ fb.message }}</td>
            </tr>
            {% endfor %}
        </table>
        {% else %}
        <p style="color: var(--text-muted);">No feedback records yet.</p>
        {% endif %}
    </body>
    </html>
    """
    return render_template_string(admin_template, feedbacks=feedbacks, key=user_key)


@app.route("/admin/users", methods=["GET"])
def view_users():
    """List every registered (i.e. code-verified) email so they can be
    pulled for welcome, discount, or announcement campaigns. Only emails
    that made it through /verify-code land in users.json — unverified
    addresses from an abandoned signup never get stored here."""
    user_key = request.args.get("key")
    if not user_key or user_key != ADMIN_SECRET_KEY:
        return "Access Denied: Invalid or missing administrator security key.", 403

    users = _load_json(USERS_FILE, {})
    rows = [
        {
            "email": email,
            "plan": info.get("plan", "default"),
            "registered_at": info.get("registered_at", ""),
            "verified": info.get("verified", False),
            "agreed_policies": info.get("agreed_policies", False),
        }
        for email, info in users.items()
    ]
    rows.sort(key=lambda r: r["registered_at"], reverse=True)

    admin_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>VectraCore - Admin Users</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg-color: #0b0e11; --panel-bg: #151a22; --border-color: #2a323f;
                --accent-color: #ff3b30; --text-main: #f0f3f6; --text-muted: #848e9c;
            }
            body { background: var(--bg-color); color: var(--text-main); font-family: 'Inter', sans-serif; padding: 40px; }
            h2 { color: var(--accent-color); margin-bottom: 5px; font-weight: 700; letter-spacing: 1px; }
            p.subtitle { color: var(--text-muted); margin-bottom: 20px; font-size: 0.9rem; }
            table { width: 100%; border-collapse: collapse; background: var(--panel-bg); border: 1px solid var(--border-color); border-radius: 8px; overflow: hidden; }
            th, td { padding: 15px 20px; border-bottom: 1px solid var(--border-color); text-align: left; }
            th { background: #1c2330; font-weight: 600; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 1px; color: var(--text-muted); }
            tr:hover { background: rgba(255, 59, 48, 0.02); }
            .timestamp { color: var(--text-muted); font-size: 0.85rem; }
            .email-cell { font-weight: 600; color: #fff; }
            .plan-badge {
                display: inline-block; padding: 3px 10px; border-radius: 50px; font-size: 0.75rem;
                font-weight: 700; text-transform: uppercase; background: rgba(255, 59, 48, 0.15); color: var(--accent-color);
            }
            .verified-yes { color: #4ade80; }
            .verified-no { color: var(--text-muted); }
            .admin-nav { margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center; }
            .admin-nav a { color: var(--text-muted); text-decoration: none; font-size: 0.85rem; }
            .admin-nav a:hover { color: var(--text-main); }
            .export-btn {
                background: var(--accent-color); color: #fff; text-decoration: none; padding: 10px 18px;
                border-radius: 6px; font-size: 0.85rem; font-weight: 700;
            }
        </style>
    </head>
    <body>
        <div class="admin-nav">
            <a href="/admin/feedback?key={{ key }}">&larr; Feedback</a>
            <a class="export-btn" href="/admin/users.csv?key={{ key }}">Download CSV</a>
        </div>
        <h2>VECTRACORE // REGISTERED USERS</h2>
        <p class="subtitle">{{ rows|length }} verified email(s) on file. Export the CSV to import into your email tool for welcome/discount/announcement campaigns.</p>
        {% if rows %}
        <table>
            <tr><th style="width: 35%;">Email</th><th style="width: 13%;">Plan</th><th style="width: 22%;">Registered At</th><th style="width: 15%;">Verified</th><th style="width: 15%;">Agreed Policies</th></tr>
            {% for r in rows %}
            <tr>
                <td class="email-cell">{{ r.email }}</td>
                <td><span class="plan-badge">{{ r.plan }}</span></td>
                <td class="timestamp">{{ r.registered_at }}</td>
                <td class="{{ 'verified-yes' if r.verified else 'verified-no' }}">{{ 'Yes' if r.verified else 'No' }}</td>
                <td class="{{ 'verified-yes' if r.agreed_policies else 'verified-no' }}">{{ 'Yes' if r.agreed_policies else 'No' }}</td>
            </tr>
            {% endfor %}
        </table>
        {% else %}
        <p style="color: var(--text-muted);">No registered users yet.</p>
        {% endif %}
    </body>
    </html>
    """
    return render_template_string(admin_template, rows=rows, key=user_key)


@app.route("/admin/users.csv", methods=["GET"])
def export_users_csv():
    """CSV of every verified email — built for importing into an actual
    email marketing tool (Mailchimp, Brevo, Resend Broadcasts, etc.) rather
    than sending bulk mail straight from this backend, since those tools
    handle unsubscribe links and delivery reputation properly."""
    user_key = request.args.get("key")
    if not user_key or user_key != ADMIN_SECRET_KEY:
        return "Access Denied: Invalid or missing administrator security key.", 403

    users = _load_json(USERS_FILE, {})

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["email", "plan", "registered_at", "verified", "agreed_policies", "agreed_policies_at"])
    for email, info in users.items():
        writer.writerow([
            email,
            info.get("plan", "default"),
            info.get("registered_at", ""),
            info.get("verified", False),
            info.get("agreed_policies", False),
            info.get("agreed_policies_at", ""),
        ])

    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=vectracore_users.csv"},
    )


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200
@app.route("/list-models", methods=["GET"])
def list_models():
    try:
        models = client.models.list()
        available = []
        for m in models:
            available.append({
                "name": m.name,
                "display_name": getattr(m, "display_name", ""),
                "supported_actions": getattr(m, "supported_actions", [])
            })
        return jsonify(available)
    except Exception as e:
        return jsonify({"error": str(e)}), 500 

@app.route("/analyze-chart", methods=["POST"])
def analyze_chart():

    print("=" * 60, flush=True)
    print("ANALYZE ROUTE HIT", flush=True)
    print("METHOD:", request.method, flush=True)
    print("FORM:", request.form.to_dict(), flush=True)
    print("FILES:", request.files, flush=True)
    print("=" * 60, flush=True)

    try:

        # ==========================================================
        # REQUEST DATA
        # ==========================================================

        question = request.form.get("question", "").strip()

        user_email = request.form.get(
            "user_email",
            "guest"
        ).lower().strip()

        requested_plan = request.form.get(
            "plan",
            "default"
        ).lower().strip()

        # Never trust a paid plan sent by the browser; PayPal state is authoritative.
        plan = _effective_plan_for_email(user_email, requested_plan)

        chart = request.files.get("chart")

        session_id = request.form.get("session_id", "").strip() or None

        print("PLAN:", plan)

        # ==========================================================
        # LOAD AI BASED ON PLAN
        # ==========================================================

        PLAN_PROMPTS = {
            "default": DEFAULT_PROMPT,
            "pro": PRO_PROMPT,
            "vip": VIP_PROMPT
        }

        ACTIVE_PROMPT = PLAN_PROMPTS.get(
            plan,
            DEFAULT_PROMPT
        )
        PLAN_SETTINGS = PLAN_CONFIG.get(
            plan,
            PLAN_CONFIG["default"]
        )
        ACTIVE_MODEL = PLAN_MODELS.get(
            plan,
            MODEL_NAME
        )

        print(f"ACTIVE AI -> {plan.upper()}")

        # ==========================================================
        # LOAD MEMORY (session-based — see _load_sessions / session
        # helpers near the top of the file)
        # ==========================================================

        memory, sessions = _load_sessions(user_email)

        # A session is only ever reused when the frontend explicitly sends
        # back a session_id (i.e. the user has that thread open / selected
        # in the Recents sidebar). A chart upload or question with no
        # session_id — or one that no longer matches anything — always
        # starts a brand new session instead of silently borrowing context
        # from whatever the user last did, which is what caused a follow-up
        # on EURUSD to sometimes answer using a leftover ETHUSD analysis.
        active_session = _find_session(sessions, session_id)

        last_analysis = _session_last_analysis(active_session)
        previous_analysis = json.dumps(last_analysis, indent=2) if last_analysis else ""
        previous_question = ""
        if active_session and active_session.get("turns"):
            for t in active_session["turns"]:
                if t.get("role") == "user":
                    previous_question = t.get("content", "")
        previous_conversation = _session_conversation_text(active_session)

        # ==========================================================
        # MODE 1
        # IMAGE ANALYSIS
        # ==========================================================

        if chart:
            usage = get_usage()

            allowed, response = check_user_limits(
                usage,
                user_email,
                plan,
                "chart"
            )

            if not allowed:
                return jsonify(response), 429

            image_bytes = chart.read()

            # Only VIP is allowed to combine chart analysis with real news
            # (Default and Pro must stay technical-only on charts — see
            # their own prompt files). So only fetch/attach live news here
            # when the active plan is VIP.
            chart_news_block = ""
            if plan == "vip":
                vip_news_items = _fetch_news_headlines()
                if vip_news_items:
                    chart_news_block = f"""
==========================================================
LIVE NEWS CONTEXT (real headlines, fetched just now)
==========================================================

{_format_news_for_prompt(vip_news_items)}

Treat the above as real, current, and correct. Weigh it alongside
the chart's technical picture as your vip_market_regime and
vip_fundamental modules describe.
"""
                else:
                    chart_news_block = """
==========================================================
LIVE NEWS CONTEXT
==========================================================

Live news is not currently available right now. Base this analysis
primarily on technical evidence and say so if the user asks about
news specifically.
"""

            SYSTEM_PROMPT = f"""
{ACTIVE_PROMPT}
{chart_news_block}
==========================================================
USER PLAN
==========================================================

{plan.upper()}

==========================================================
PREVIOUS ANALYSIS (CONTEXT ONLY — NEVER A DECISION)
==========================================================

{previous_analysis}

IMPORTANT FRESH-CHART RULE
--------------------------
The uploaded image in THIS request is authoritative and always overrides
the previous analysis. Treat previous_analysis as stale context only.
Re-read the new chart from scratch. Never preserve a previous BUY/SELL/WAIT
decision merely because the prior analysis said it. If price structure,
liquidity, momentum, or risk has changed, the NEW chart wins.

==========================================================
USER REQUEST
==========================================================

{question}
"""

            response = _analyze_generate(

                model=ACTIVE_MODEL,

                contents=[

                    types.Part.from_bytes(
                        data=image_bytes,
                        mime_type=chart.content_type
                    ),

                    SYSTEM_PROMPT

                ],

                config=types.GenerateContentConfig(

    response_mime_type="application/json",

    temperature=PLAN_SETTINGS["temperature"],

    top_p=PLAN_SETTINGS["top_p"],

    # Caps how long the JSON response is allowed to be — generating
    # output takes real time regardless of thinking_level, so this
    # keeps responses from running unnecessarily long.
    max_output_tokens=2048,

    thinking_config=types.ThinkingConfig(
        thinking_level=PLAN_SETTINGS["thinking_level"]
    )

)

            )

            result = _safe_json(response)
            result = _enforce_min_rr(result)
            result = _no_na_result(result)

            # The three plans' JSON schemas (default_prompt.py, pro_json.py,
            # vip_json.py) all use lowercase snake_case keys ("symbol",
            # "decision", "entry", "take_profit", "stop_loss", ...) and each
            # includes a different extra set of fields on top of that (VIP
            # has probability/geopolitical fields, Pro has
            # institutional_score, Default is bare-bones). The previous
            # version of this block read Title Case keys — "Symbol",
            # "Decision", "Win probability", "Entry", "Take Profit", "Stop
            # Loss" — that don't exist in ANY of the three schemas, so
            # `summary` was always just empty strings for every plan, and
            # since previous_analysis below prefers `summary` over
            # `analysis` whenever `summary` isn't None (and an all-empty
            # dict still isn't None), that broken summary silently shadowed
            # the real, full data sitting in `analysis` the whole time —
            # which is why follow-up answers had nothing real to work with.
            # Simplest correct fix: don't hand-pick fields at all, just
            # store the parsed result as-is. It stays correct automatically
            # no matter which fields a given plan's schema does or doesn't
            # include.
            app.logger.error("SUMMARY CREATED SUCCESSFULLY")

            now_iso = datetime.utcnow().isoformat()

            if active_session is None:
                active_session = {
                    "id": uuid.uuid4().hex,
                    "created_at": now_iso,
                    "symbol": result.get("symbol"),
                    "timeframe": result.get("timeframe"),
                    "title": _session_title(result.get("symbol"), result.get("timeframe"), question),
                    "plan": plan,
                    "turns": [],
                }
                sessions.append(active_session)

            active_session["updated_at"] = now_iso
            active_session["turns"].append({
                "role": "user",
                "type": "chart",
                "content": question or "(chart uploaded)",
                "timestamp": now_iso,
            })
            active_session["turns"].append({
                "role": "assistant",
                "type": "analysis",
                "content": result,
                "timestamp": now_iso,
            })

            memory[user_email] = sessions
            _save_json(CHART_MEMORY_FILE, memory)

            result["session_id"] = active_session["id"]

            # Chart-upload counter for the frontend to show (e.g. "7/20
            # charts used — resets in 12 days"). VIP has no limit, so it
            # gets no usage block at all.
            if plan != "vip":
                limit = CHART_LIMITS.get(plan)
                used = usage.get(user_email, {}).get("charts_used", 0)
                reset_at = usage.get(user_email, {}).get("charts_reset")
                if limit is not None:
                    result["usage"] = {
                        "charts_used": used,
                        "charts_limit": limit,
                        "charts_remaining": max(0, limit - used),
                        "resets_at": reset_at,
                    }

            return jsonify(result)
        # ==========================================================
        # QUESTION LIMIT CHECK (applies to MODE 2 + MODE 3 — any
        # text-only request that isn't a chart upload)
        # ==========================================================

        usage = get_usage()

        allowed, limit_response = check_user_limits(
            usage,
            user_email,
            plan,
            "question"
        )

        if not allowed:
            return jsonify(limit_response), 429

        # ==========================================================
        # MODE 2
        # FOLLOW-UP
        # ==========================================================

        # Any text-only question is treated as an interactive follow-up
        # as long as there's a previous chart/analysis in this user's
        # memory — for ALL plans (default, pro, vip). Keyword-matching
        # was too fragile (missed valid follow-ups like "what about the
        # trend now" that don't contain one of the listed words), so any
        # question with existing context now goes through this path.
        is_chart_followup = active_session is not None

        if is_chart_followup:

            # Pro and VIP are allowed to discuss news/macro (per their own
            # prompt files — vip_news/vip_macro modules, and Pro's
            # intended news capability) — but until this fix, that
            # capability only ever got wired in for Mode 1 (chart upload)
            # and Mode 3 (general question with no prior chart). The
            # moment a question became a follow-up (Mode 2 — by far the
            # most common path in real usage), Pro and VIP silently lost
            # all news access regardless of plan, which is why they were
            # answering "I don't track real-time news" even though their
            # own prompts say they can. Mirrors the same block used in
            # Mode 3 below.
            followup_news_block = ""
            if plan in ("pro", "vip"):
                followup_news_items = _fetch_news_headlines()
                if followup_news_items:
                    followup_news_block = f"""
==========================================================
LIVE NEWS CONTEXT (real headlines, fetched just now)
==========================================================

{_format_news_for_prompt(followup_news_items)}

Treat the above as real, current, and correct. Use it if the
follow-up question is about news, macro, or fundamentals.
"""
                else:
                    followup_news_block = """
==========================================================
LIVE NEWS CONTEXT
==========================================================

Live news is not currently available (FINNHUB_KEY missing, or the
news source failed to respond). If the user asks about news
specifically, tell them plainly that live news isn't available
right now rather than guessing or inventing headlines — but still
answer any part of their question that's about the chart/technical
picture.
"""

            FOLLOWUP_PROMPT = f"""
{FOLLOWUP_PROMPT_BASE}
{followup_news_block}
==========================================================
CURRENT ACTIVE CHART
==========================================================

The following chart analysis is the ACTIVE chart currently
being discussed.

Everything the user asks refers to THIS chart unless they
explicitly mention another asset.

==========================================================
PREVIOUS USER REQUEST
==========================================================

{previous_question}

==========================================================
PREVIOUS ANALYSIS
==========================================================

{previous_analysis}
==========================================================
CONVERSATION SO FAR
==========================================================

{previous_conversation}


==========================================================
IMPORTANT
==========================================================

Treat this as an ongoing conversation.

Never answer as if this is a brand new chat.

If the user asks:

- When should I enter?
- Is it still valid?
- Should I wait?
- What if price breaks?
- Is my TP still valid?
- What is my execution?
- Should I cancel the trade?

Always answer according to the previous chart analysis.

Only ignore previous analysis if the user explicitly asks about
another asset or uploads another chart.

==========================================================
FOLLOW-UP QUESTION
==========================================================

{question}

Answer ONLY the follow-up question.

Do NOT regenerate the full chart analysis.

Return JSON:

{{
    "answer":""
}}
"""
            response = _analyze_generate(

                model=ACTIVE_MODEL,
                

                contents=[FOLLOWUP_PROMPT],

                config=types.GenerateContentConfig(

                    response_mime_type="application/json",

                    temperature=PLAN_SETTINGS["temperature"],

                    top_p=PLAN_SETTINGS["top_p"],

                    # Follow-ups only return a short {"answer": "") object,
                    # but the PROMPT feeding into this call includes the
                    # full previous analysis + up to 10 turns of
                    # conversation history (+ news for pro/vip), which
                    # grows every follow-up in a session. 512 was too
                    # tight once combined with "low" thinking below — the
                    # model would spend the whole budget "thinking" through
                    # that context and have nothing left to write the
                    # actual answer, silently returning an empty response
                    # after a few follow-ups. Raised to give the answer
                    # itself room to exist.
                    max_output_tokens=1024,

                    # Follow-ups are meant to be quick answers, not a full
                    # re-analysis, so keep thinking minimal — matches every
                    # other call in this file (see PLAN_CONFIG) instead of
                    # the "low" level this used to hardcode, which was the
                    # actual cause of empty follow-up answers.
                    thinking_config=types.ThinkingConfig(
                        thinking_level="minimal"
                    )

                )
            )
            app.logger.error("FOLLOWUP RAW RESPONSE:\n%s", response.text)

            result = _safe_json(response)

            now_iso = datetime.utcnow().isoformat()
            active_session["updated_at"] = now_iso
            active_session["turns"].append({
                "role": "user",
                "type": "text",
                "content": question,
                "timestamp": now_iso,
            })
            active_session["turns"].append({
                "role": "assistant",
                "type": "text",
                "content": result.get("answer", ""),
                "timestamp": now_iso,
            })

            memory[user_email] = sessions
            _save_json(CHART_MEMORY_FILE, memory)

            result["session_id"] = active_session["id"]
            return jsonify(result)

        # ==========================================================
        # MODE 3
        # GENERAL TRADING ASSISTANT
        # ==========================================================

        # Pro and VIP plans are allowed to answer news/macro questions
        # (see pro_prompt.py MODE 2, and the vip_news / vip_macro modules
        # inside vip_prompt.py) — so fetch real headlines from Finnhub and
        # hand them to the model as grounded context. Without this block,
        # Gemini has no live internet access at all and will (correctly)
        # say it can't see real-time news.
        news_context_block = ""

        if plan in ("pro", "vip"):
            news_items = _fetch_news_headlines()

            if news_items:
                news_context_block = f"""
==========================================================
LIVE NEWS CONTEXT (real headlines, fetched just now)
==========================================================

{_format_news_for_prompt(news_items)}

Treat the above as real, current, and correct. Use it to answer
the user's question if relevant. Do not claim you lack live news
access when this section is present.
"""
            else:
                news_context_block = """
==========================================================
LIVE NEWS CONTEXT
==========================================================

Live news is not currently available (FINNHUB_KEY missing, or the
news source failed to respond). Tell the user plainly that live
news isn't available right now rather than guessing or inventing
headlines.
"""

        GENERAL_PROMPT = f"""
{ACTIVE_PROMPT}
{news_context_block}
==========================================================
USER MESSAGE
==========================================================

{question}

Respond naturally.

If the user is asking about trading,
markets,
risk management,
psychology,
ICT,
SMC,
economics,
or finance,

answer professionally.

Return JSON:

{{
    "answer":""
}}
"""

        response = _analyze_generate(

            model=ACTIVE_MODEL,

            contents=[GENERAL_PROMPT],

            config=types.GenerateContentConfig(

                response_mime_type="application/json",

                temperature=PLAN_SETTINGS["temperature"],

                top_p=PLAN_SETTINGS["top_p"],

                # General answers are just {"answer": ""} — cap output
                # length so a rambling answer can't add latency.
                max_output_tokens=1024,

                thinking_config=types.ThinkingConfig(
                    thinking_level=PLAN_SETTINGS["thinking_level"]
                )

            )

        )

        result = _safe_json(response)

        now_iso = datetime.utcnow().isoformat()
        new_session = {
            "id": uuid.uuid4().hex,
            "created_at": now_iso,
            "updated_at": now_iso,
            "symbol": None,
            "timeframe": None,
            "title": _session_title(None, None, question),
            "plan": plan,
            "turns": [
                {"role": "user", "type": "text", "content": question, "timestamp": now_iso},
                {"role": "assistant", "type": "text", "content": result.get("answer", ""), "timestamp": now_iso},
            ],
        }
        sessions.append(new_session)
        memory[user_email] = sessions
        _save_json(CHART_MEMORY_FILE, memory)

        result["session_id"] = new_session["id"]
        return jsonify(result)

    except TimeoutError as e:

        app.logger.error("analyze_chart: hard deadline hit: %s", e)

        return jsonify({

            "success": False,

            "error": "The AI took too long to respond — please try again.",

        }), 504

    except Exception as e:

        traceback.print_exc()

        return jsonify({

            "success": False,

            "error": str(e)

        }), 500

@app.route("/ping")
def ping():
    with open("ping_test.txt", "a") as f:
        f.write("PING RECEIVED\n")

    return "pong"
if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
