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
import traceback
import json
import time
import logging
import secrets
import hashlib

from prompts.vip_prompt import VIP_PROMPT
from prompts.default_prompt import DEFAULT_PROMPT
from prompts.pro_prompt import PRO_PROMPT
import requests
from flask import Flask, request, jsonify, render_template_string, Response
from flask_cors import CORS
from PIL import Image
from dotenv import load_dotenv 
from google import genai
from google.genai import types
from datetime import datetime, timedelta
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
MODEL_NAME = os.environ.get("GEMINI_MODEL", "models/gemma-4-26b-a4b-it")
FALLBACK_MODEL_NAME = os.environ.get("GEMINI_FALLBACK_MODEL", "models/gemma-4-26b-a4b-it")
MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8MB upload cap
MAX_HISTORY_PER_USER = 50
NEWS_HEADLINE_LIMIT = 8
NEWS_CACHE_TTL_SECONDS = 300  # avoid hammering Finnhub if several users ask in a row

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


def _load_json(path, default):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
def get_usage():
    return _load_json("usage.json", {})


def save_usage(data):
    _save_json("usage.json", data)   
def initialize_user_usage(usage, email):

    if email not in usage:

        usage[email] = {

            "charts_used": 0,
            "questions_used": 0,

            "charts_reset": (
                datetime.utcnow() + timedelta(days=1)
            ).isoformat(),

            "questions_reset": (
                datetime.utcnow() + timedelta(hours=12)
            ).isoformat()

        }

    return usage    
def reset_usage_if_needed(usage, email):

    # -----------------------------
    # Reset chart usage (24h)
    # -----------------------------

    chart_reset = datetime.fromisoformat(
        usage[email]["charts_reset"]
    )

    if datetime.utcnow() >= chart_reset:

        usage[email]["charts_used"] = 0

        usage[email]["charts_reset"] = (
            datetime.utcnow() + timedelta(days=1)
        ).isoformat()

    # -----------------------------
    # Reset question usage (12h)
    # -----------------------------

    question_reset = datetime.fromisoformat(
        usage[email]["questions_reset"]
    )

    if datetime.utcnow() >= question_reset:

        usage[email]["questions_used"] = 0

        usage[email]["questions_reset"] = (
            datetime.utcnow() + timedelta(hours=12)
        ).isoformat()

    return usage
def check_user_limits(usage, email, plan, request_type):

    usage = initialize_user_usage(usage, email)
    usage = reset_usage_if_needed(usage, email)

    # VIP = unlimited
    if plan == "vip":
        return True, None

    # -----------------------------
    # CHART REQUEST
    # -----------------------------
    if request_type == "chart":

        chart_limits = {
            "default": 2,
            "pro": 15
        }

        limit = chart_limits.get(plan, 2)

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
                    "Upgrade for Pro/VIP plan to upload more / ask more."
                )
            }

        usage[email]["charts_used"] += 1

    # -----------------------------
    # QUESTION REQUEST
    # -----------------------------
    elif request_type == "question":

        question_limits = {
            "default": 10,
            "pro": 100
        }

        limit = question_limits.get(plan, 10)

        if usage[email]["questions_used"] >= limit:

            remaining = int(
                (
                    datetime.fromisoformat(
                        usage[email]["questions_reset"]
                    ) - datetime.utcnow()
                ).total_seconds()
            )

            return False, {
                "success": False,
                "limit": True,
                "type": "question",
                "remaining_seconds": max(0, remaining),
                "upgrade_required": True,
                "upgrade_reason": "rate_limit",
                "retry_after_seconds": max(0, remaining),
                "error": (
                    "You've used all your questions for your current plan. "
                    "Upgrade for Pro/VIP plan to upload more / ask more."
                )
            }

        usage[email]["questions_used"] += 1

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


def _create_or_update_account(email: str, plan: str, agreed_policies: bool = False) -> dict:
    """Same bookkeeping /register used to do — now only ever called after a
    code has been correctly verified, so an account is never created for an
    email the requester doesn't actually control."""
    history = _load_json(HISTORY_FILE, {})
    if email not in history:
        history[email] = []
        _save_json(HISTORY_FILE, history)

    users = _load_json(USERS_FILE, {})
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if email not in users:
        users[email] = {
            "plan": plan,
            "registered_at": now_str,
            "verified": True,
            "agreed_policies": agreed_policies,
            "agreed_policies_at": now_str if agreed_policies else None,
        }
    else:
        users[email]["plan"] = plan
        users[email]["verified"] = True
        if agreed_policies and not users[email].get("agreed_policies"):
            users[email]["agreed_policies"] = True
            users[email]["agreed_policies_at"] = now_str
    _save_json(USERS_FILE, users)
    return users[email]


# ---------------------------------------------------------------------------
# Gemini call wrapper — retries transient overload errors
# ---------------------------------------------------------------------------
TRANSIENT_ERROR_MARKERS = ("UNAVAILABLE", "RESOURCE_EXHAUSTED", "503", "429", "overloaded")


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


def _generate_with_retry(model, contents, config=None, max_retries=6, base_delay=2.0):
    """Improved retry logic"""
    last_exc = None
    for attempt in range(max_retries):
        try:
            return client.models.generate_content(
                model=model,
                contents=contents,
                config=config
            )
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


def _generate_content_resilient(contents, config=None):
    """Primary model with fallback"""
    try:
        gemini_contents = _make_gemini_contents(contents)
        return _generate_with_retry(
            model=MODEL_NAME,
            contents=gemini_contents,
            config=config
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
            max_retries=3
        )


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


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
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

    # All plans are free during the beta — this just records which tier the
    # user picked so a per-plan AI agent can be routed to later.
    users = _load_json(USERS_FILE, {})
    if email not in users:
        users[email] = {
            "plan": plan,
            "registered_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    else:
        users[email]["plan"] = plan
    _save_json(USERS_FILE, users)

    return jsonify({"status": "success", "email": email, "plan": users[email]["plan"]}), 200


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

    if not email or not _valid_email(email):
        return jsonify({"error": "Please enter a valid email address."}), 400

    if not agreed_policies:
        return jsonify({"error": "You must agree to the policies to continue."}), 400

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
    account = _create_or_update_account(email, record["plan"], record.get("agreed_policies", False))
    del pending[email]
    _save_json(PENDING_FILE, pending)

    return jsonify({"status": "success", "email": email, "plan": account["plan"]}), 200


@app.route("/account", methods=["GET"])
def get_account():
    """Look up which plan an email is on — useful once each plan routes to
    its own AI agent."""
    email = (request.args.get("email") or "").strip().lower()
    if not email:
        return jsonify({"error": "Email required"}), 400

    users = _load_json(USERS_FILE, {})
    account = users.get(email, {"plan": "default", "registered_at": None})
    return jsonify({"email": email, **account}), 200


@app.route("/history", methods=["GET"])
def get_history():
    email = (request.args.get("email") or "guest@vectracore.ai").strip().lower()
    history = _load_json(HISTORY_FILE, {})
    return jsonify(history.get(email, [])), 200





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
            model="models/gemma-4-26b-a4b-it",
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

        plan = request.form.get(
            "plan",
            "default"
        ).lower().strip()

        chart = request.files.get("chart")

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

        print(f"ACTIVE AI -> {plan.upper()}")

        # ==========================================================
        # LOAD MEMORY
        # ==========================================================

        memory = _load_json(
            "chart_memory.json",
            {}
        )

        memory.setdefault(user_email, [])

        previous_analysis = ""

        previous_question = ""

        if memory[user_email]:

            previous_analysis = json.dumps(
                memory[user_email][-1]["analysis"],
                indent=2
            )

            previous_question = memory[user_email][-1].get(
                "question",
                ""
            )

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

            SYSTEM_PROMPT = f"""
{ACTIVE_PROMPT}

==========================================================
USER PLAN
==========================================================

{plan.upper()}

==========================================================
PREVIOUS ANALYSIS
==========================================================

{previous_analysis}

==========================================================
USER REQUEST
==========================================================

{question}
"""

            response = client.models.generate_content(

                model=MODEL_NAME,

                contents=[

                    types.Part.from_bytes(
                        data=image_bytes,
                        mime_type=chart.content_type
                    ),

                    SYSTEM_PROMPT

                ],

                config=types.GenerateContentConfig(

                    response_mime_type="application/json",

                    temperature=0.15,

                    top_p=0.85

                )

            )

            result = json.loads(response.text)

            memory[user_email].append({

                "timestamp": datetime.utcnow().isoformat(),

                "question": question,

                "analysis": result

            })

            _save_json(
                "chart_memory.json",
                memory
            )

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

        chart_keywords = [

            "why",
            "probability",
            "buy",
            "sell",
            "entry",
            "sl",
            "tp",
            "stop loss",
            "take profit",
            "liquidity",
            "sweep",
            "order block",
            "choch",
            "bos",
            "market structure",
            "fvg",
            "fair value gap",
            "confirmation"

        ]

        is_chart_followup = (

            previous_analysis != ""

            and any(

                keyword in question.lower()

                for keyword in chart_keywords

            )

        )

        if is_chart_followup:

            FOLLOWUP_PROMPT = f"""
{ACTIVE_PROMPT}

==========================================================
PREVIOUS USER REQUEST
==========================================================

{previous_question}

==========================================================
PREVIOUS ANALYSIS
==========================================================

{previous_analysis}

==========================================================
FOLLOW-UP QUESTION
==========================================================

{question}

Answer ONLY the user's question.

Do NOT regenerate the whole analysis.

Return JSON:

{{
    "answer":""
}}
"""
            response = client.models.generate_content(

                model=MODEL_NAME,

                contents=[FOLLOWUP_PROMPT],

                config=types.GenerateContentConfig(

                    response_mime_type="application/json",

                    temperature=0.25

                )

            )

            result = _parse_model_json(response.text)

            return jsonify(result)

        # ==========================================================
        # MODE 3
        # GENERAL TRADING ASSISTANT
        # ==========================================================

        # ------------------------------------------------------------
        # Live news context — only default/pro/vip actually get to use
        # this; the DEFAULT_PROMPT and PRO_PROMPT text already contains
        # their own rules about when news is/isn't allowed, so we just
        # make the real data available and let the plan's own prompt
        # decide what to do with it.
        # ------------------------------------------------------------

        news_context = ""

        if plan in ("pro", "vip") and _looks_like_news_query(question):

            news_items = _fetch_news_headlines()

            if news_items:

                news_context = f"""
==========================================================
LIVE NEWS CONTEXT (real, current headlines — treat as fact)
==========================================================

{_format_news_for_prompt(news_items)}
"""

            elif not FINNHUB_KEY:

                news_context = """
==========================================================
LIVE NEWS CONTEXT
==========================================================

NOTE: Live news is not configured on this server (missing
FINNHUB_KEY). Tell the user plainly that live news isn't
available right now — do not invent headlines.
"""

            else:

                news_context = """
==========================================================
LIVE NEWS CONTEXT
==========================================================

NOTE: Live news could not be fetched right now (temporary
issue reaching the news provider). Tell the user plainly
that live news isn't available right now — do not invent
headlines.
"""

        GENERAL_PROMPT = f"""
{ACTIVE_PROMPT}
{news_context}
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

        response = client.models.generate_content(

            model=MODEL_NAME,

            contents=[GENERAL_PROMPT],

            config=types.GenerateContentConfig(

                response_mime_type="application/json",

                temperature=0.45

            )

        )

        result = _parse_model_json(response.text)

        return jsonify(result)

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
