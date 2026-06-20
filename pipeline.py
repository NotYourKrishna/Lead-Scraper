"""
Lead Qualification Pipeline — Stages 1, 2, and 3
=================================================
Stage 1: YouTube API discovery + filter → Playwright About-page link extraction
         Output: stage1_links.csv

Stage 2: Fetch and parse each discovered bio link (with URL normalization)
         Output: stage2_pages.csv

Stage 3: Creator-level classification — detect offer types, estimate funnel
         maturity, identify monetization gaps, suggest outreach angle
         Output: stage3_profiles.csv

Stage 4 (ICP scoring) runs after you verify Stage 3 output quality.

Runtime: 10-20 minutes for 50 candidates at reliability-first pace.
"""

import re
import os
import csv
import sys
import json
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, unquote

import requests
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv optional; fall back to real env vars

sys.stdout.reconfigure(encoding="utf-8")

# ══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════════════

API_KEY           = os.environ.get("YOUTUBE_API_KEY", "")
NICHE_QUERY       = "dropshipping business"
MIN_SUBS          = 500
MAX_DAYS_INACTIVE = 90
MAX_RESULTS       = 50

CHROME_PATH = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

STAGE1_CSV = "stage1_links.csv"
STAGE2_CSV = "stage2_pages_v2.csv"
STAGE3_CSV = "stage3_profiles_v7.csv"

DELAY_BETWEEN_CHANNELS = 4
DELAY_BETWEEN_PAGES    = 2        # seconds between page loads in the crawler
ABOUT_PAGE_SETTLE_MS   = 5000
PAGE_SETTLE_MS         = 3000     # ms to wait for JS to render on crawled pages
PAGE_FETCH_TIMEOUT_S   = 20
MAX_TEXT_LENGTH        = 1500

# Recursive crawler settings
MAX_CRAWL_DEPTH        = 2        # 0 = About-page links, 1 = pages behind those, 2 = one more hop
MAX_PAGES_PER_CREATOR  = 15       # hard stop to keep runtime reasonable

# ── Funnel opt-in form filling ────────────────────────────────────────────────
# Identity submitted to lead-magnet opt-in forms to advance past the gate and
# reveal the deeper funnel. NEVER used for payment or account/password forms.
LEAD_IDENTITY = {
    "email":      os.environ.get("LEAD_EMAIL", ""),
    "first_name": os.environ.get("LEAD_FIRST_NAME", ""),
    "full_name":  os.environ.get("LEAD_FULL_NAME", ""),
    "phone":      os.environ.get("LEAD_PHONE", ""),
}
MAX_FORM_SUBMITS_PER_CREATOR = 3   # bound runtime + avoid spamming a single funnel
ENABLE_FORM_FILL = True            # master switch for opt-in form submission
MAX_FORM_STEPS   = 7               # multi-step qualification forms (Typeform etc.)

# CAPTCHA: we cannot solve image challenges in code, and the service must run on
# autopilot — so we NEVER block the batch. When a CAPTCHA is hit we flag that creator,
# leave its page open in a tab, record it to CAPTCHA_PENDING_CSV, and continue with
# everyone else. You solve the flagged pages later, then re-run just those creators.
CAPTCHA_PENDING_CSV = "captcha_pending.csv"

# Plausible "ideal high-ticket student" answers, used to traverse qualification
# forms to their end (where a Calendly/booking link reveals the HT offer). Real
# contact fields use LEAD_IDENTITY; everything else gets harmless filler.
FORM_FILLER_TEXT = "Looking to scale and ready to invest in the right mentorship."

# ── Instagram-assisted funnel discovery ───────────────────────────────────────
# Secondary discovery ONLY: used when a creator survives filtering, no HT backend
# was found, and they'd otherwise be "Needs More Data" (e.g. About page exposes
# only an Instagram profile). Logs in once with a throwaway account, persists the
# session, and feeds discovered bio links back into the normal recursive crawler.
ENABLE_INSTAGRAM            = True
IG_CREDENTIALS_FILE         = "ig_credentials.json"   # {"username":..,"password":..}
IG_SESSION_FILE            = "ig_session.json"        # persisted Playwright storage_state
INSTAGRAM_META_CSV          = "instagram_meta.csv"    # per-creator IG discovery results
MAX_IG_PROFILES_PER_CREATOR = 3                       # seed profile + up to 2 tagged biz accts
IG_ACTION_DELAY             = 3.0                     # seconds between IG actions (be gentle)

# ── Funnel link filter ────────────────────────────────────────────────────────
# Always follow these platform domains (known funnel hosts)
FUNNEL_FOLLOW_DOMAINS = {
    "skool.com", "whop.com", "kajabi.com", "circle.so", "podia.com",
    "teachable.com", "thinkific.com", "gumroad.com", "payhip.com",
    "stan.store", "beacons.ai", "linktr.ee", "lnktr.ee",
    "beehiiv.com", "substack.com", "convertkit.com", "kit.com",
    "mailchimp.com", "klaviyo.com",
    "typeform.com", "jotform.com", "tally.so",               # form/application hosts
    "calendly.com", "cal.com", "tidycal.com", "savvycal.com",# booking
    "webflow.io", "carrd.co", "notion.so",                   # page builders
    "launchpass.com", "patreon.com", "ko-fi.com",
    "ecomhighticket.com",                                     # example from this run
}

# Never follow these social / generic domains
SOCIAL_SKIP_DOMAINS = {
    "instagram.com", "tiktok.com", "twitter.com", "x.com",
    "facebook.com", "youtube.com", "linkedin.com", "pinterest.com",
    "snapchat.com", "threads.net", "reddit.com", "quora.com",
    "medium.com", "wikipedia.org", "google.com", "apple.com",
    "spotify.com", "anchor.fm", "podbean.com",
    "shopify.com", "amazon.com", "ebay.com", "aliexpress.com",
    "trustpilot.com", "capterra.com", "getapp.com",
    "wordpress.org", "wp.com",
}

# Skip pages whose path contains these strings
SKIP_PATH_PATTERNS = re.compile(
    r"/(privacy|terms|legal|cookie|sitemap|404|login|signup|register|logout"
    r"|cart|checkout|contact|about-us|faq|press|careers|jobs|affiliate"
    r"|copyright|disclaimer|refund|support|help-center|unsubscribe)(/|$|\?)",
    re.I
)

# Follow same-domain subpages only if the path contains one of these funnel keywords
FUNNEL_PATH_KEYWORDS = re.compile(
    r"/(apply|course|program|coaching|mentorship|community|join|enroll"
    r"|offer|start|get-started|work-with|resources|products|store|free"
    r"|download|masterclass|workshop|training|guide|blueprint|playbook"
    r"|template|toolkit|ebook|newsletter|subscribe|webinar|challenge"
    r"|membership|members|cohort|accelerator|bootcamp|funnel|vsl|watch"
    r"|sales|pricing|checkout|buy|purchase|order|access|inside|the-course"
    r"|the-program|my-program|my-course|my-community)",
    re.I
)

# ══════════════════════════════════════════════════════════════════════════════
# GEOGRAPHY / PERSONAL-BRAND FILTERS
# ══════════════════════════════════════════════════════════════════════════════

HIGH_INCOME_COUNTRIES = {
    "US","CA","GB","AU","NZ","IE","DE","FR","NL","SE","NO","DK","FI",
    "CH","AT","BE","LU","SG","AE","JP","KR","IL","IT","ES","HK","TW","QA",
}
CURRENCY_SYMBOLS   = ["₹","₨","₦","₱"]
CURRENCY_WORDS     = [" rupee","rupees"," inr "," inr.","naira"," pkr ",
                      " bdt "," taka"," lkr","magkano"," peso"," pesos"]
LANGUAGE_RED_FLAGS = ["pinoy","tagalog","malayalam","malayali","telugu"," hindi",
                      " tamil"," urdu","bangla","kannada","marathi"," sinhala","mag-"]
PLATFORM_PATTERNS  = [
    r"\b(aliexpress|cjdropshipping|alidropship|dsers|zendrop|doba|spocket|oberlo|shopify|autods|salehoo|appscenic)\b",
    r"\b(llc|ltd|inc|corp)\b",
]
CORPORATE_WE = ["we give ","we help ","we offer ","we provide ","we teach ",
                "we are a ","we are an ","our mission is","our team ","our company"]

# ══════════════════════════════════════════════════════════════════════════════
# PAGE-TYPE DETECTION
# ══════════════════════════════════════════════════════════════════════════════

def detect_page_type(url):
    u = url.lower()
    rules = [
        ("linktr.ee",        "Linktree"),
        ("lnktr.ee",         "Linktree"),
        ("beacons.ai",       "Beacons"),
        ("stan.store",       "Stan Store"),
        ("skool.com",        "Skool"),
        ("whop.com",         "Whop"),
        ("kajabi.com",       "Kajabi"),
        ("circle.so",        "Circle"),
        ("podia.com",        "Podia"),
        ("teachable.com",    "Teachable"),
        ("thinkific.com",    "Thinkific"),
        ("gumroad.com",      "Gumroad"),
        ("payhip.com",       "Payhip"),
        ("calendly.com",     "Calendly (booking)"),
        ("cal.com",          "Cal.com (booking)"),
        ("tidycal.com",      "TidyCal (booking)"),
        ("acuityscheduling", "Acuity (booking)"),
        ("beehiiv.com",      "beehiiv (newsletter)"),
        ("substack.com",     "Substack (newsletter)"),
        ("convertkit.com",   "ConvertKit"),
        ("mailchimp.com",    "Mailchimp"),
        ("instagram.com",    "Instagram"),
        ("tiktok.com",       "TikTok"),
        ("twitter.com",      "Twitter/X"),
        ("x.com",            "Twitter/X"),
        ("facebook.com",     "Facebook"),
        ("discord.gg",       "Discord"),
        ("discord.com",      "Discord"),
        ("t.me",             "Telegram"),
        ("youtube.com",      "YouTube"),
        ("amazon.",          "Amazon"),
    ]
    for needle, label in rules:
        if needle in u:
            return label
    return "Website"

JS_HEAVY   = {"Linktree","Beacons","Stan Store","Skool","Whop","Kajabi","Circle"}
SKIP_FETCH = {"Instagram","TikTok","Twitter/X","Facebook","YouTube","Discord","Telegram","Amazon"}

# ══════════════════════════════════════════════════════════════════════════════
# URL NORMALIZATION
# ══════════════════════════════════════════════════════════════════════════════

def normalize_url(url):
    """Prepend https:// to bare domain/path URLs that have no scheme."""
    url = url.strip()
    if not url:
        return url
    if url.startswith("http://") or url.startswith("https://"):
        return url
    # Looks like an email — skip
    if re.match(r"^[^/]+@[^/]+\.[a-z]{2,}$", url, re.I):
        return url
    return "https://" + url

# ══════════════════════════════════════════════════════════════════════════════
# EMAIL EXTRACTION
# ══════════════════════════════════════════════════════════════════════════════

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
# Substrings that mark a non-contact / system / asset email we should ignore
EMAIL_JUNK = (
    "example.com", "sentry.io", "@sentry", "wixpress.com", ".wixpress",
    "domain.com", "yourdomain", "email.com", "no-reply@", "noreply@",
    "schema.org", "googleapis", "cloudfront", "godaddy", "wix.com",
    "sentry-next", "@2x", "@3x", "core-js", "react@",
)

def extract_emails(text):
    """Return plausible contact emails from free text, filtering junk/assets."""
    out = []
    for e in EMAIL_RE.findall(text or ""):
        el = e.lower()
        if any(j in el for j in EMAIL_JUNK):
            continue
        if el.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".js", ".css")):
            continue
        if e not in out:
            out.append(e)
    return out

def channel_id_from_url(url):
    m = re.search(r"/channel/([A-Za-z0-9_\-]+)", url or "")
    return m.group(1) if m else ""

# ══════════════════════════════════════════════════════════════════════════════
# YOUTUBE API HELPERS
# ══════════════════════════════════════════════════════════════════════════════

youtube = build("youtube", "v3", developerKey=API_KEY)

def search_channels(query, max_results):
    resp = youtube.search().list(
        part="snippet", q=query, type="channel",
        maxResults=min(max_results, 50), relevanceLanguage="en"
    ).execute()
    return [item["snippet"]["channelId"] for item in resp.get("items", [])]

def get_channel_details(channel_id):
    resp = youtube.channels().list(
        part="snippet,statistics,contentDetails", id=channel_id
    ).execute()
    if not resp.get("items"):
        return None
    item = resp["items"][0]
    return {
        "id":        channel_id,
        "title":     item["snippet"]["title"],
        "description": item["snippet"]["description"],
        "country":   item["snippet"].get("country",""),
        "subs":      int(item["statistics"].get("subscriberCount",0)),
        "uploads":   item["contentDetails"]["relatedPlaylists"]["uploads"],
        "url":       f"https://www.youtube.com/channel/{channel_id}",
        "about_url": f"https://www.youtube.com/channel/{channel_id}/about",
    }

def get_latest_upload(playlist_id):
    resp = youtube.playlistItems().list(
        part="contentDetails", playlistId=playlist_id, maxResults=1
    ).execute()
    if not resp.get("items"):
        return None
    ts = resp["items"][0]["contentDetails"]["videoPublishedAt"]
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)

# ══════════════════════════════════════════════════════════════════════════════
# FILTERS
# ══════════════════════════════════════════════════════════════════════════════

def passes_english(item):
    lang = item["snippet"].get("defaultLanguage","")
    if lang and not lang.startswith("en"):
        return False
    desc = item["snippet"].get("description","")
    if len(desc) > 20:
        if sum(1 for c in desc if ord(c)<128) / len(desc) < 0.7:
            return False
    return True

def passes_geography(country, text):
    t = text.lower()
    for s in CURRENCY_SYMBOLS:
        if s in text:
            return False, f"currency symbol '{s}'"
    for w in CURRENCY_WORDS:
        if w in t:
            return False, f"currency word '{w.strip()}'"
    for f in LANGUAGE_RED_FLAGS:
        if f in t:
            return False, f"language '{f.strip()}'"
    if country and country not in HIGH_INCOME_COUNTRIES:
        return False, f"country '{country}'"
    return True, ""

def passes_personal_brand(title, desc):
    tl, dl = title.lower(), desc.lower()
    for p in PLATFORM_PATTERNS:
        if re.search(p, tl):
            return False
    if re.match(r"^(dropshipping business|dropship store|ecom store)$", tl):
        return False
    corp = sum(1 for p in CORPORATE_WE if p in dl)
    fp   = len(re.findall(r"\b(i |i'm |i've |i'll |i'd )\b", dl))
    if corp >= 2:
        return False
    if corp >= 1 and fp == 0 and len(desc) > 100:
        return False
    return True

# ══════════════════════════════════════════════════════════════════════════════
# PLAYWRIGHT HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def dismiss_consent(page):
    try:
        btn = page.locator(
            "button:has-text('Accept all'), button:has-text('Reject all'), "
            "button:has-text('Accept & continue'), button:has-text('I agree')"
        )
        if btn.count() > 0:
            btn.first.click(timeout=3000)
            page.wait_for_timeout(1000)
    except Exception:
        pass

def unwrap_yt_redirect(href):
    if "youtube.com/redirect" in href:
        m = re.search(r"[?&]q=([^&]+)", href)
        if m:
            return unquote(m.group(1))
    return href

def extract_about_links(page, about_url, channel_name):
    try:
        page.goto(about_url, wait_until="domcontentloaded", timeout=30000)
        dismiss_consent(page)
        page.wait_for_timeout(ABOUT_PAGE_SETTLE_MS)
    except PWTimeout:
        print(f"    TIMEOUT: {channel_name}")
        return []
    except Exception as e:
        print(f"    ERROR: {channel_name}: {e}")
        return []

    links = []
    try:
        elements = page.locator("yt-channel-external-link-view-model")
        for i in range(elements.count()):
            el    = elements.nth(i)
            label = el.inner_text().strip().split("\n")[0].strip()
            anchor = el.locator("a[href]")
            href  = anchor.first.get_attribute("href") if anchor.count() > 0 else ""
            href  = unwrap_yt_redirect(href or "")
            href  = normalize_url(href)
            if href and not href.startswith("javascript"):
                links.append({"label": label, "url": href})
                print(f"      [{label}] → {href}")
    except Exception as e:
        print(f"    EXTRACT ERROR: {channel_name}: {e}")

    if not links:
        print(f"    (no external links on About page)")
    return links

def fetch_with_playwright(pw_page, url):
    try:
        pw_page.goto(url, wait_until="domcontentloaded", timeout=30000)
        pw_page.wait_for_timeout(3500)
        title = pw_page.title()
        text  = pw_page.locator("body").inner_text()
        text  = re.sub(r"\s{2,}", " ", text).strip()
        return title, text[:MAX_TEXT_LENGTH]
    except PWTimeout:
        return "", "timeout"
    except Exception as e:
        return "", f"error: {e}"

# ══════════════════════════════════════════════════════════════════════════════
# PAGE FETCH — REQUESTS
# ══════════════════════════════════════════════════════════════════════════════

FETCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

def fetch_with_requests(url):
    try:
        resp = requests.get(url, headers=FETCH_HEADERS,
                            timeout=PAGE_FETCH_TIMEOUT_S, allow_redirects=True)
        if resp.status_code != 200:
            return "", f"HTTP {resp.status_code}"
        if "text/html" not in resp.headers.get("Content-Type",""):
            return "", "non-HTML"
        soup = BeautifulSoup(resp.text, "html.parser")
        title = soup.title.string.strip() if soup.title else ""
        for tag in soup(["script","style","noscript","nav","footer","header"]):
            tag.decompose()
        text = re.sub(r"\s{2,}", " ", soup.get_text(separator=" ", strip=True))
        return title, text[:MAX_TEXT_LENGTH]
    except Exception as e:
        return "", f"error: {e}"

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 3 — OFFER CLASSIFICATION
# ══════════════════════════════════════════════════════════════════════════════

# ── HT signals (label-first, then page text) ──────────────────────────────
HT_LABEL_SIGNALS = [
    "mentorship", "coaching", "mastermind", "apply", "application",
    "strategy call", "book a call", "book a free", "work with me",
    "work 1-on-1", "1-on-1", "1 on 1", "1:1", "done with you",
    "done-with-you", "vip day", "apply now", "apply here",
]
HT_TEXT_SIGNALS = HT_LABEL_SIGNALS + [
    "high ticket", "high-ticket", "setters", "closers", "sales team",
    "vsll", "vsl", "application form", "qualification form",
]

# NOTE: HT detection is tier-based (price + sales structure), not label-based.
# See assess_ht_level() / HT_STRUCTURAL_SIGNALS in the tier-model section below.

# ── Funnel-depth tier model ───────────────────────────────────────────────────
# The crawler's job is to find the DEEPEST monetization layer, not to stop at a
# lead magnet. Each crawled page is classified into one of these tiers; the
# highest tier reached across the funnel decides qualification.
TIER_NONE        = 0
TIER_LEAD_MAGNET = 1   # free guide/webinar/opt-in — NOT an endpoint, keep crawling
TIER_LOW_TICKET  = 2   # cheap course / digital product / paid community  (< $100)
TIER_MID_TICKET  = 3   # membership / subscription / mid-priced product  ($100–997)
TIER_HIGH_TICKET = 4   # coaching / mentorship / mastermind / application / calls

TIER_LABELS = {
    TIER_NONE:        "None Found",
    TIER_LEAD_MAGNET: "Lead Magnet Only",
    TIER_LOW_TICKET:  "Low Ticket",
    TIER_MID_TICKET:  "Mid Ticket",
    TIER_HIGH_TICKET: "High Ticket",
}

# High-ticket ENDPOINT keywords (reaching one of these terminates the funnel as HT)
HT_ENDPOINT_KEYWORDS = [
    "coaching", "coach with", "mentorship", "mentoring", "mastermind",
    "work with me", "work with us", "1:1", "1-on-1", "one on one",
    "done for you", "done-for-you", "strategy call", "discovery call",
    "qualification call", "clarity call", "consultation call", "book a call",
    "application", "apply now", "apply here", "apply below", "apply today",
    "accelerator", "incubator", "private client", "high ticket", "high-ticket",
    "inner circle",
]
# Paid course / digital product keywords (low/mid-ticket endpoint)
PAID_PRODUCT_KEYWORDS = [
    "course", "program", "bootcamp", "workshop", "cohort", "curriculum",
    "module", "lessons", "masterclass", "digital product", "ebook",
    "e-book", "template", "toolkit", "blueprint", "playbook", "challenge",
    "buy now", "add to cart", "enroll", "get instant access to the",
]
# Community / membership / subscription keywords (low/mid-ticket endpoint)
COMMUNITY_ENDPOINT_KEYWORDS = [
    "community", "membership", "members area", "members-only", "subscription",
    "subscribe to", "monthly plan", "skool", "whop", "circle.so", "discord",
    "private group", "join the community",
]
# Lead magnet (funnel ENTRANCE, never an endpoint)
LEAD_MAGNET_KEYWORDS = [
    "free guide", "free ebook", "free e-book", "free pdf", "free checklist",
    "free training", "free download", "free resource", "lead magnet",
    "free webinar", "free course", "grab the free", "download the free",
    "get the free", "free blueprint", "free roadmap", "free playbook",
    "free template", "free toolkit", "free cheatsheet",
    "enter your email", "instant access", "opt-in", "optin", "sign up to get",
    "subscribe to get", "where should i send", "send it to your inbox",
    "join the free", "register for the free", "save my seat", "claim your free",
]

PRICE_RE = re.compile(r"[$£€]\s?(\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{2})?")

def extract_prices(text):
    """Return list of plausible dollar/pound/euro prices found in text."""
    out = []
    for m in PRICE_RE.finditer(text or ""):
        try:
            v = int(m.group(1).replace(",", ""))
        except ValueError:
            continue
        if 1 <= v <= 100000:
            out.append(v)
    return out

# ── Opaque funnel boundaries ──────────────────────────────────────────────────
# Pages the crawler CANNOT see past. If the funnel terminates at one of these,
# we cannot confirm whether an HT backend (upsell → community → coaching) exists
# beyond it. Detected on page TITLE and URL path only (not body) to avoid the
# false positive of every nav having a "Log In" link.
ENDPOINT_GATES = [
    ("checkout",    re.compile(r"(/checkout|/cart\b|cart-page|/order|/payment|/billing|"
                               r"complete your (order|purchase)|order summary|secure checkout|"
                               r"add to cart|proceed to (checkout|payment))", re.I)),
    ("login wall",  re.compile(r"(/login\b|/log-in\b|/sign[_-]?in\b|users/sign_in|/signin\b|"
                               r"\blog in to\b|\bsign in to\b|please log in|enter your password)", re.I)),
    ("member area", re.compile(r"(/members?\b|/membership-area|/dashboard\b|/my-account|/my-courses|"
                               r"member area|members area|member portal|customer portal|"
                               r"my dashboard|welcome back)", re.I)),
]

# ── Tier-based HT detection — classify by PRICE + SALES STRUCTURE, not by label ─
# A creator is disqualified only when the evidence points to a MATURE high-ticket
# backend. The bare word "coaching" is NOT enough: "$97 coaching" is a low-ticket
# product and a perfectly good prospect. High ticket means one of:
#   • an application / qualification funnel
#   • a sales / strategy / discovery call requirement
#   • private 1:1 / mentorship / mastermind positioning
#   • a $2,000+ offer price
HT_PRICE_THRESHOLD  = 2000   # offer at/above this = high ticket
MID_PRICE_THRESHOLD = 300    # $300–$1,999 = mid ticket; below = low ticket

HT_STRUCTURAL_SIGNALS = [
    ("application funnel", [
        "apply for", "apply now", "apply here", "apply today", "apply below",
        "apply to", "application form", "by application", "application required",
        "application only", "qualify for", "qualification form",
        "/apply", "/application", "fill out an application", "submit an application",
        "start your application",
        # "<program> application" titles are unambiguous HT apply funnels
        "mentorship application", "coaching application", "program application",
        "mastermind application", "application (main)", "application form"]),
    ("sales/strategy call", [
        "strategy call", "sales call", "discovery call", "qualification call",
        "clarity call", "consultation call", "book a call", "schedule a call",
        "book a free call", "hop on a call", "get on a call", "jump on a call",
        "free strategy session"]),
    ("private 1:1 offer", [
        "private coaching", "private mentorship", "1:1 coaching", "1-on-1 coaching",
        "one-on-one coaching", "1:1 mentorship", "private client",
        "work with me privately", "work with me 1:1", "vip day"]),
    ("mastermind",   ["mastermind"]),
    ("done-for-you", ["done for you", "done-for-you", "dfy "]),
    ("high-ticket",  ["high ticket", "high-ticket"]),
    ("accelerator",  ["accelerator", "incubator"]),
    ("sales team",   ["setters", "closers", "sales team", "appointment setter"]),
]
HT_PLATFORM_SIGNALS = [
    ("booking platform",  ["calendly.com", "cal.com", "tidycal.com",
                          "acuityscheduling", "savvycal.com", "oncehub.com"]),
    ("GoHighLevel funnel", ["gohighlevel", "go-high-level", "msgsndr.com", "ghl.link"]),
]
# Soft / ambiguous — coaching-ish language that needs a price to resolve.
# Present + a sub-$2,000 price → low/mid ticket (qualified). Present + no price →
# SUSPECTED → manual review. Never a disqualifier on its own.
SOFT_HT_SIGNALS = [
    "coaching", "coach with me", "group coaching", "mentorship", "mentoring",
    "1:1", "1-on-1", "one on one", "work with me", "work with us",
    "inner circle", "private group", "exclusive community",
]

# HT qualification-form language — forms that screen for a buyer's REVENUE and
# how much CAPITAL they can INVEST exist to qualify for a high-ticket program.
# These questions never appear on a low/mid-ticket checkout, so they are a strong
# HT signal on their own (this is what was hiding behind Saamir Mithwani's form).
HT_QUALIFIER_REVENUE = [
    "monthly revenue", "current revenue", "your revenue", "monthly income",
    "how much do you currently make", "how much money do you make",
    "what is your revenue", "current monthly", "how much are you making",
    "revenue from your", "income from your",
]
HT_QUALIFIER_INVEST = [
    "to invest in yourself", "invest in yourself and", "capital to invest",
    "cash to invest", "budget to invest", "set aside to invest", "able to invest",
    "ready to invest", "how much can you invest", "funds to invest", "to invest in the",
    "prepared to invest", "willing to invest", "cash on hand", "set aside to invest in",
    "invest in the business", "invest in the program",
]
# Distinguish an OFFER price from a revenue/testimonial figure.
REVENUE_CONTEXT = [
    "revenue", "/mo", "/month", "per month", "/day", "per day", "made ", "earned",
    "in sales", "profit", "generated", "income", "a month", "a day", "made over",
    "made $", "earning",
]
OFFER_CONTEXT = [
    "coaching", "program", "mentorship", "mastermind", "cohort", "course",
    "membership", "enroll", "join", "investment", "tuition", "payment plan",
    "pay in full", "one-time", "one time", "installment", "payments of",
    "to join", "to enroll", "package", "pricing", "only $", "just $",
    "get access", "buy", "purchase", "checkout", "per year",
]

def ht_offer_prices(text):
    """Offer prices >= HT_PRICE_THRESHOLD, excluding revenue/testimonial figures."""
    out = []
    low = (text or "").lower()
    for m in PRICE_RE.finditer(text or ""):
        try:
            v = int(m.group(1).replace(",", ""))
        except ValueError:
            continue
        if v < HT_PRICE_THRESHOLD or v > 100000:
            continue
        window = low[max(0, m.start()-45): m.end()+45]
        if any(r in window for r in REVENUE_CONTEXT):
            continue
        if any(o in window for o in OFFER_CONTEXT):
            out.append(v)
    return out

def _has_sub_ht_price(text):
    """True if a concrete sub-$2,000 price is present (resolves coaching → LT/MT)."""
    return any(1 <= p < HT_PRICE_THRESHOLD for p in extract_prices(text))

def assess_ht_level(blob):
    """
    Tier funnel text by sales STRUCTURE + PRICE rather than by label.
    Returns ('High'|'Medium'|'None', [reasons]).
      High   = mature HT backend  → DISQUALIFY
      Medium = ambiguous coaching with no price/structure → SUSPECTED → manual review
      None   = no HT evidence
    """
    blob = blob or ""
    reasons = []
    for label, kws in (HT_STRUCTURAL_SIGNALS + HT_PLATFORM_SIGNALS):
        hit = next((k for k in kws if k in blob), None)
        if hit:
            reasons.append(f"{label}: '{hit}'")
    for p in ht_offer_prices(blob):
        reasons.append(f"offer price ${p:,}")
        break
    # Qualification form screening for revenue / investment capital = HT funnel.
    # The investment question alone is HT-specific; revenue + invest together is certain.
    inv = next((k for k in HT_QUALIFIER_INVEST if k in blob), None)
    rev = next((k for k in HT_QUALIFIER_REVENUE if k in blob), None)
    if inv:
        reasons.append(f"HT qualification form (capital-to-invest screen): '{inv}'"
                       + (f" + revenue screen: '{rev}'" if rev else ""))
    if reasons:
        return "High", reasons
    soft = [s for s in SOFT_HT_SIGNALS if s in blob]
    if soft and not _has_sub_ht_price(blob):
        return "Medium", [f"ambiguous, no price/structure: '{s}'" for s in soft[:3]]
    return "None", []

def _paid_tier_from_price(prices):
    """
    Grade a confirmed paid product as low vs mid ticket using price.
    Ignores figures >= HT_PRICE_THRESHOLD (those are HT or revenue, handled elsewhere).
    LOW < $300 ; MID $300–$1,999.
    """
    offer_prices = [p for p in prices if p < HT_PRICE_THRESHOLD]
    if not offer_prices:
        return TIER_LOW_TICKET, None
    p = max(offer_prices)
    if p >= MID_PRICE_THRESHOLD:
        return TIER_MID_TICKET, p
    return TIER_LOW_TICKET, p

# ── LT / demand signals ───────────────────────────────────────────────────
COMMUNITY_DOMAINS = ["skool.com","whop.com","circle.so","discord","t.me","telegram",
                     "facebook.com/groups"]
COMMUNITY_TEXT    = ["community","members","skool","discord","telegram","facebook group",
                     "join the","join my"]

COURSE_DOMAINS    = ["gumroad.com","stan.store","payhip.com","podia.com","teachable.com",
                     "thinkific.com","kajabi.com","udemy.com","coursesbyowl","teachable",
                     "thinkific","kajabi","podia"]
COURSE_TEXT       = ["course","program","training","bootcamp","workshop","cohort",
                     "curriculum","module","lessons","masterclass"]

NEWSLETTER_DOMAINS = ["beehiiv.com","substack.com","convertkit.com","mailchimp.com",
                      "kit.com","klaviyo.com"]
NEWSLETTER_TEXT    = ["newsletter","email list","weekly email","subscribe","email updates",
                      "join my list","free email","my list"]

LEAD_MAGNET_TEXT  = ["free guide","free ebook","free e-book","free pdf","free checklist",
                     "free training","free download","free resource","lead magnet",
                     "free webinar","free course","grab the free","download the free",
                     "get the free","free blueprint","free roadmap","free playbook",
                     "free template","free toolkit","free cheatsheet"]

BOOKING_DOMAINS   = ["calendly.com","cal.com","tidycal.com","acuityscheduling.com",
                     "oncehub.com","hubspot.com/meetings","savvycal.com"]
BOOKING_TEXT      = ["book a call","book a free","schedule a call","schedule time",
                     "pick a time","book time","free consultation","discovery call",
                     "intro call","clarity call"]

APPLICATION_TEXT  = ["apply now","apply here","fill out","submit an application",
                     "apply to work","application form","apply for","apply below",
                     "apply today","start your application"]


def _in_labels(signals, labels_lower):
    return any(s in labels_lower for s in signals)

def _in_text(signals, text_lower):
    return any(s in text_lower for s in signals)

def _in_urls(domains, urls_lower):
    return any(d in urls_lower for d in domains)

def _find_matches(signals, text_lower):
    return [s for s in signals if s in text_lower]

# ── Data sufficiency ──────────────────────────────────────────────────────────
# Platforms that carry meaningful funnel information when fetched
FUNNEL_PAGE_TYPES = {
    "Website", "Linktree", "Beacons", "Stan Store", "Skool", "Whop",
    "Kajabi", "Circle", "Podia", "Teachable", "Thinkific", "Gumroad",
    "Payhip", "beehiiv (newsletter)", "Substack (newsletter)",
    "ConvertKit", "Calendly (booking)", "Cal.com (booking)",
}
# Text length thresholds
THIN_TEXT_THRESHOLD      = 150   # chars — page loaded but near-empty
SUBSTANTIAL_TEXT_THRESHOLD = 350 # chars — enough to scan for signals

def measure_data_sufficiency_v2(rows, max_depth_reached, pages_fetched_ok):
    """
    Replacement for measure_data_sufficiency that understands the recursive crawl schema.
    Rows are crawled page dicts (URL, Depth, Page Title, Extracted Text, Page Type).

    High confidence requires BOTH:
      - ≥2 pages with substantial text, AND
      - Navigation/CTA links were explored (source contains 'nav/cta')
    Without nav exploration, cap at Medium even if many pages were fetched.
    """
    pages_inspected = 0
    pages_thin      = 0
    pages_failed    = 0
    total_text      = 0
    inspected_types = []

    for r in rows:
        ptype    = r.get("Page Type","")
        title    = r.get("Page Title","")
        text     = r.get("Extracted Text","")
        text_len = len(text) if text else 0

        if "Instagram" in ptype or "(no links" in ptype:
            continue   # not a fetched page

        if not title:
            pages_failed += 1
        elif text_len < THIN_TEXT_THRESHOLD:
            pages_thin += 1
        elif ptype in FUNNEL_PAGE_TYPES or "Website" in ptype:
            pages_inspected += 1
            total_text += text_len
            inspected_types.append(ptype)

    # Check whether nav/CTA links were explored this crawl
    nav_explored = any("nav/cta" in r.get("Source","").lower() for r in rows)

    if pages_inspected >= 3 and total_text >= SUBSTANTIAL_TEXT_THRESHOLD * 3:
        raw_confidence = "High"
        notes = (f"{pages_inspected} pages inspected across {max_depth_reached+1} depth(s): "
                 f"{', '.join(dict.fromkeys(inspected_types[:4]))}")
    elif pages_inspected >= 2 and total_text >= SUBSTANTIAL_TEXT_THRESHOLD:
        raw_confidence = "High"
        notes = (f"{pages_inspected} funnel pages inspected "
                 f"({', '.join(dict.fromkeys(inspected_types[:3]))})")
    elif pages_inspected >= 1 and total_text >= SUBSTANTIAL_TEXT_THRESHOLD:
        raw_confidence = "Medium"
        notes = f"1 funnel page inspected ({', '.join(dict.fromkeys(inspected_types[:2]))})"
        if pages_failed:
            notes += f"; {pages_failed} failed"
        if pages_thin:
            notes += f"; {pages_thin} thin"
    elif pages_inspected >= 1:
        raw_confidence = "Medium"
        notes = f"Page loaded but content thin ({total_text} chars total)"
    elif pages_thin > 0:
        raw_confidence = "Low"
        notes = "Pages loaded but all content thin — likely JS-rendered or bot-blocked"
    elif pages_failed > 0:
        raw_confidence = "Low"
        notes = f"All {pages_failed} page fetches failed — site may block scraping"
    else:
        raw_confidence = "Low"
        notes = "No crawlable links found — only social profiles or no About-page links"

    # ── Nav-exploration confidence gate ──────────────────────────────────────
    # High confidence is only valid if navigation was explored.
    # A crawler that only saw the homepage cannot conclude "no monetization".
    if raw_confidence == "High" and not nav_explored:
        confidence = "Medium"
        notes += " | Navigation menus not explored — may have hidden offers"
    else:
        confidence = raw_confidence

    return {"confidence": confidence, "notes": notes, "nav_explored": nav_explored}


def measure_data_sufficiency(rows):
    """
    Examine what was actually collected for a creator and return sufficiency metrics.

    Returns a dict with:
      pages_inspected    — funnel-relevant pages that loaded with substantial text
      pages_thin         — pages that loaded but had very little text
      pages_failed       — pages that failed entirely (no title, no text)
      pages_social_only  — all discovered links were social profiles (nothing to fetch)
      total_text_chars   — total chars of extracted text across all pages
      inspected_types    — list of page types successfully read
      failed_urls        — list of URLs that failed
      confidence         — "High" / "Medium" / "Low"
      sufficiency_notes  — human-readable explanation
    """
    pages_inspected = 0
    pages_thin      = 0
    pages_failed    = 0
    total_text      = 0
    inspected_types = []
    failed_urls     = []
    has_fetchable   = False

    for r in rows:
        url       = r.get("Destination URL","")
        ptype     = r.get("Page Type","")
        title     = r.get("Page Title","")
        text      = r.get("Extracted Text","")
        text_len  = len(text) if text else 0

        # Rows with no URL at all (e.g. email address or placeholder)
        if not url or ptype in SKIP_FETCH or ptype == "":
            continue

        has_fetchable = True

        if not title:
            # Fetch failed entirely
            pages_failed += 1
            failed_urls.append(url)
        elif text_len < THIN_TEXT_THRESHOLD:
            # Loaded but thin — could be a redirect page, splash, or JS wall
            pages_thin += 1
        elif ptype in FUNNEL_PAGE_TYPES:
            # Loaded with substantial text from a funnel-relevant page type
            pages_inspected += 1
            total_text      += text_len
            inspected_types.append(ptype)
        else:
            # Generic website with content — still counts
            pages_inspected += 1
            total_text      += text_len
            inspected_types.append("Website")

    # ── Confidence scoring ──
    # High: ≥2 funnel pages read with substantial text
    # Medium: 1 funnel page read, OR multiple thin pages
    # Low: nothing fetched, all failed/thin, or only social links
    if pages_inspected >= 2 and total_text >= SUBSTANTIAL_TEXT_THRESHOLD * 2:
        confidence = "High"
        notes = f"{pages_inspected} funnel pages inspected ({', '.join(inspected_types[:3])})"
    elif pages_inspected >= 1 and total_text >= SUBSTANTIAL_TEXT_THRESHOLD:
        confidence = "Medium"
        notes = f"1 funnel page inspected ({', '.join(inspected_types[:2])})"
        if pages_failed:
            notes += f"; {pages_failed} page(s) failed to load"
        if pages_thin:
            notes += f"; {pages_thin} page(s) returned thin content"
    elif pages_inspected >= 1:
        confidence = "Medium"
        notes = f"Page loaded but text was thin ({total_text} chars total)"
    elif pages_thin > 0 and not pages_failed:
        confidence = "Low"
        notes = f"Pages loaded but all content was thin — likely JS-rendered or blocked"
    elif pages_failed > 0 and has_fetchable:
        confidence = "Low"
        notes = f"All {pages_failed} page fetch(es) failed — site may block scraping"
    elif not has_fetchable:
        confidence = "Low"
        notes = "No fetchable links found — only social profiles or no links at all"
    else:
        confidence = "Low"
        notes = "Insufficient data collected"

    if failed_urls:
        notes += f" | Failed: {'; '.join(failed_urls[:2])}"

    return {
        "pages_inspected": pages_inspected,
        "pages_thin":      pages_thin,
        "pages_failed":    pages_failed,
        "total_text":      total_text,
        "inspected_types": inspected_types,
        "confidence":      confidence,
        "notes":           notes,
    }


def compute_ht_score(labels_equiv, page_titles, page_texts, urls, confidence):
    """
    Tier-based HT assessment over the creator's combined funnel text.

    Disqualifies (High) only on a mature HT backend — an application/qualification
    funnel, a sales/strategy call requirement, private 1:1 / mentorship / mastermind
    positioning, or a $2,000+ offer. The bare word "coaching" is NOT a disqualifier:
    "$97 coaching" prices out as low-ticket; coaching with no price/structure is
    flagged Medium (suspected → manual review), never auto-disqualified.

    Returns (score: int, hits: list[str], level: str)  — score is a display proxy.
    """
    scan_body = confidence != "Low"
    blob = " ".join([labels_equiv, page_titles,
                     page_texts if scan_body else "", urls]).lower()
    level, hits = assess_ht_level(blob)
    score = {"High": 50, "Medium": 25, "None": 0}[level]
    return score, hits, level


def _detect_page_tier(page_title, page_text, url):
    """
    Classify a single crawled page into the highest monetization tier it represents.
    Returns (tier_rank, label, price_or_None).
    """
    blob   = (page_title + " " + page_text + " " + url).lower()
    prices = extract_prices(page_title + " " + page_text)

    # High ticket — only on sales STRUCTURE or a $2,000+ offer, not on a bare label
    level, reasons = assess_ht_level(blob)
    if level == "High":
        label = reasons[0].split(": '")[0].strip().title() if reasons else "High-Ticket Offer"
        return TIER_HIGH_TICKET, label, (max(prices) if prices else None)

    # Community / membership / subscription endpoint
    if any(k in blob for k in COMMUNITY_ENDPOINT_KEYWORDS):
        tier, price = _paid_tier_from_price(prices)
        return tier, ("Membership" if ("membership" in blob or "subscription" in blob)
                      else "Community"), price

    # Priced coaching / mentorship / group coaching / program / cohort (NOT
    # high-ticket — already cleared the HT check above) → low/mid ticket
    if any(k in blob for k in ["coaching", "coach with me", "group coaching",
                               "mentorship", "mentoring", "cohort", "program"]):
        tier, price = _paid_tier_from_price(prices)
        return tier, "Coaching/Mentorship", price

    # Paid course / digital product endpoint
    if any(k in blob for k in PAID_PRODUCT_KEYWORDS):
        tier, price = _paid_tier_from_price(prices)
        return tier, "Course/Digital Product", price

    # Lead magnet (funnel entrance, not an endpoint)
    if any(k in blob for k in LEAD_MAGNET_KEYWORDS):
        return TIER_LEAD_MAGNET, "Lead Magnet", None

    return TIER_NONE, None, None


def analyze_funnel_depth(rows, ht_level):
    """
    Walk every crawled page and determine the DEEPEST monetization layer reached.
    A lead magnet is treated as a funnel entrance, never an endpoint.

    Returns dict with:
      deepest_layer, funnel_path, highest_offer_type, highest_offer_confidence,
      lead_magnet_present, highest_tier, qualified (bool), form_crossed (bool)
    """
    detections = []   # (depth, tier, label, price, source)
    lead_magnet_present = False
    form_crossed        = False

    for r in rows:
        ptype = r.get("Page Type", "")
        if "Instagram" in ptype or "(no links" in ptype:
            continue
        title  = r.get("Page Title", "") or ""
        text   = r.get("Extracted Text", "") or ""
        url    = r.get("URL", "") or ""
        source = (r.get("Source", "") or "").lower()
        depth  = int(r.get("Depth", 0) or 0)
        if "form-submit" in source or "opt-in submitted" in source:
            form_crossed = True
        if not title:
            continue

        tier, label, price = _detect_page_tier(title, text, url)
        if tier == TIER_LEAD_MAGNET:
            lead_magnet_present = True
        if tier > TIER_NONE:
            detections.append((depth, tier, label, price, source))

    # Build the funnel path: order by depth, dedupe by label preserving sequence
    path_items = []
    seen = set()
    for depth, tier, label, price, source in sorted(detections, key=lambda x: x[0]):
        disp = label
        if price and tier in (TIER_LOW_TICKET, TIER_MID_TICKET):
            disp = f"${price} {label}"
        elif tier == TIER_LEAD_MAGNET:
            disp = "Free Lead Magnet"
        if disp not in seen:
            path_items.append(disp)
            seen.add(disp)

    # Highest tier reached — HT level High forces tier 4 even if keyword matching missed
    highest_tier = max((d[1] for d in detections), default=TIER_NONE)
    if ht_level == "High":
        highest_tier = TIER_HIGH_TICKET

    # Deepest layer label = the label of a detection at the highest tier
    deepest_label = TIER_LABELS[highest_tier]
    top_dets = [d for d in detections if d[1] == highest_tier]
    if top_dets:
        # prefer the deepest-depth instance
        top = max(top_dets, key=lambda x: x[0])
        deepest_label = top[2]
        if top[3] and highest_tier in (TIER_LOW_TICKET, TIER_MID_TICKET):
            deepest_label = f"${top[3]} {top[2]}"

    funnel_path = " → ".join(path_items) if path_items else "No funnel detected"

    # Qualification: HT endpoint disqualifies; low/mid-ticket qualifies
    qualified = highest_tier in (TIER_LOW_TICKET, TIER_MID_TICKET)

    return {
        "deepest_layer":            deepest_label,
        "funnel_path":              funnel_path,
        "highest_offer_type":       TIER_LABELS[highest_tier],
        "lead_magnet_present":      lead_magnet_present,
        "highest_tier":             highest_tier,
        "qualified":                qualified,
        "form_crossed":             form_crossed,
    }


def assess_endpoint(rows, nav_explored, ht_level):
    """
    Determine how certain we are that the funnel's visible end is its TRUE end.

    The crawler is blind past a checkout / login wall / member area, so a funnel
    that terminates at one of those could hide post-purchase upsells → community
    → coaching. Returns endpoint confidence + an 'uncertain' flag.

    Returns dict: endpoint_confidence ('High'|'Medium'|'Low'),
                  endpoint_uncertain (bool), boundary (str), boundary_url (str)
    """
    pages_inspected   = 0
    pages_failed_thin = 0
    gate_type         = ""
    gate_url          = ""

    for r in rows:
        ptype = r.get("Page Type", "")
        if "Instagram" in ptype or "(no links" in ptype:
            continue
        title = r.get("Page Title", "") or ""
        text  = r.get("Extracted Text", "") or ""
        url   = r.get("URL", "") or ""

        if not title:
            pages_failed_thin += 1
            continue
        if len(text) < THIN_TEXT_THRESHOLD:
            pages_failed_thin += 1
        else:
            pages_inspected += 1

        # Gate detection — title + URL only (avoids nav "Log In" link false positives)
        probe = title + " " + url
        if not gate_type:
            for name, pat in ENDPOINT_GATES:
                if pat.search(probe):
                    gate_type = name
                    gate_url  = url
                    break

    hit_gate = bool(gate_type)

    # Endpoint confidence
    if hit_gate:
        endpoint_confidence = "Low"
    elif pages_inspected >= 3 and nav_explored and ht_level in ("None", "Low"):
        endpoint_confidence = "High"
    else:
        # Funnel appears complete but coverage is partial (thin/failed pages,
        # no nav, or too few pages to be sure nothing lies deeper)
        endpoint_confidence = "Medium"

    # Endpoint uncertainty: a gate hides whatever is beyond. Only meaningful when
    # we have NOT already confirmed an HT backend (if HT found, certainty is moot).
    endpoint_uncertain = hit_gate and ht_level != "High"

    return {
        "endpoint_confidence": endpoint_confidence,
        "endpoint_uncertain":  endpoint_uncertain,
        "boundary":            gate_type if gate_type else "none",
        "boundary_url":        gate_url,
    }


def classify_creator(channel_name, rows):
    """
    rows = list of Stage 2 page dicts for one creator (one row per crawled page).
    Returns a classification dict that separates data confidence from conclusions.
    """
    # Stage 2 now uses "URL" (not "Destination URL") and has no "Link Label"
    # (labels were in Stage 1; Stage 2 rows are crawled pages).
    # We reconstruct useful text blobs from what we actually fetched.
    page_types  = [r.get("Page Type","") for r in rows]
    page_titles = " ".join(r.get("Page Title","") for r in rows).lower()
    page_texts  = " ".join(r.get("Extracted Text","") for r in rows).lower()
    urls        = " ".join(r.get("URL","") or r.get("Destination URL","") for r in rows).lower()
    sources     = " ".join(r.get("Source","") for r in rows).lower()   # includes About-page labels
    page_combined = page_titles + " " + page_texts
    all_text      = sources + " " + page_combined + " " + urls

    # Crawl stats
    max_depth     = max((int(r.get("Depth", 0)) for r in rows), default=0)
    pages_visited = len(rows)
    pages_fetched = sum(1 for r in rows if r.get("Page Title"))

    # ── Data sufficiency ────────────────────────────────────────────────────
    suf = measure_data_sufficiency_v2(rows, max_depth, pages_fetched)
    confidence = suf["confidence"]

    # "labels" in the old schema = source text (About-page link labels) in the new schema
    # sources contains e.g. "found on https://..." but also the seed label from Stage 1
    labels_equiv = sources + " " + urls  # best proxy for the old "link labels"

    # ── Multi-signal HT confidence scoring ───────────────────────────────────
    ht_score, ht_hits, ht_level = compute_ht_score(
        labels_equiv, page_titles, page_texts, urls, confidence
    )
    ht_signals_found = ht_hits   # full scored signal list for reporting

    # ── Funnel-depth analysis (deepest monetization layer) ───────────────────
    fd = analyze_funnel_depth(rows, ht_level)
    highest_tier = fd["highest_tier"]

    # ── Endpoint certainty: can we trust the funnel's visible end? ───────────
    nav_explored_now = any("nav/cta" in r.get("Source","").lower() for r in rows)
    ep = assess_endpoint(rows, nav_explored_now, ht_level)

    # Highest offer confidence: how sure are we about the deepest layer?
    if highest_tier == TIER_NONE:
        offer_conf = "Low" if confidence == "Low" else "Medium"
    elif confidence == "High":
        offer_conf = "High"
    elif confidence == "Medium":
        offer_conf = "Medium"
    else:
        offer_conf = "Low"

    # ── LT / demand detection ────────────────────────────────────────────────
    scan_body = confidence != "Low"

    coaching_present = _in_text(["coaching","coach with","coach me"],
                                 all_text if scan_body else labels_equiv + " " + page_titles)
    mentorship_present = _in_text(["mentorship","mentoring"],
                                   all_text if scan_body else labels_equiv + " " + page_titles)
    book_call_present = (
        _in_urls(BOOKING_DOMAINS, urls) or
        _in_text(BOOKING_TEXT, labels_equiv) or
        _in_text(BOOKING_TEXT, page_titles)
    )
    application_present = (
        _in_text(["apply","application"], labels_equiv) or
        (scan_body and _in_text(APPLICATION_TEXT, page_combined))
    )
    community_present = (
        _in_urls(COMMUNITY_DOMAINS, urls) or
        _in_text(COMMUNITY_TEXT, labels_equiv) or
        (scan_body and _in_text(["skool.com","whop.com","circle.so"], page_combined))
    )
    course_present = (
        _in_urls(COURSE_DOMAINS, urls) or
        _in_text(COURSE_TEXT, labels_equiv) or
        _in_text(COURSE_TEXT, page_titles)
    )
    newsletter_present = (
        _in_urls(NEWSLETTER_DOMAINS, urls) or
        _in_text(NEWSLETTER_TEXT, labels_equiv) or
        _in_text(NEWSLETTER_TEXT, page_titles)
    )
    lead_magnet_present = (
        scan_body and _in_text(LEAD_MAGNET_TEXT, all_text)
    ) or _in_text(LEAD_MAGNET_TEXT, labels_equiv + " " + page_titles)

    # ── Monetization conclusion — gated by confidence ────────────────────────
    any_mono_signal = any([
        coaching_present, mentorship_present, book_call_present,
        application_present, community_present, course_present,
        newsletter_present, lead_magnet_present,
    ])

    if any_mono_signal:
        mono_conclusion = "Monetization Confirmed"
    elif confidence == "High":
        # We looked thoroughly and found nothing
        mono_conclusion = "Monetization Not Found"
    else:
        # We didn't look thoroughly enough to conclude either way
        mono_conclusion = "Insufficient Data"

    # ── Existing monetization types list ────────────────────────────────────
    mono = []
    if community_present:    mono.append("Community")
    if course_present:       mono.append("Course/Program")
    if newsletter_present:   mono.append("Newsletter/Email List")
    if lead_magnet_present:  mono.append("Lead Magnet/Free Resource")
    if book_call_present:    mono.append("Paid/Free Calls")
    if coaching_present:     mono.append("Coaching")
    if mentorship_present:   mono.append("Mentorship")
    if application_present:  mono.append("Application Funnel")

    # ── Funnel maturity (only meaningful at Medium+ confidence) ─────────────
    if confidence == "Low" and not any_mono_signal:
        maturity = "Unknown — Insufficient data"
    elif ht_level in ("High", "Medium") or coaching_present or mentorship_present:
        maturity = "High — HT offer present or strongly suspected"
    elif (course_present or community_present) and (newsletter_present or lead_magnet_present):
        maturity = "Medium-High — LT stack with email capture"
    elif course_present or community_present:
        maturity = "Medium — LT offer exists"
    elif newsletter_present or lead_magnet_present:
        maturity = "Medium-Low — Lead capture only, no paid product"
    elif mono:
        maturity = "Low — Minimal signals"
    else:
        maturity = "Unknown — Insufficient data"

    # ── Monetization gaps (only state gaps we can actually confirm) ──────────
    # Suppress gap reporting when HT is confirmed — gaps aren't the story there
    gaps = []
    if ht_level not in ("High", "Medium") and confidence != "Low":
        if not coaching_present and not mentorship_present:
            gaps.append("No high-ticket offer detected")
        if not application_present:
            gaps.append("No application or qualification funnel")
        if not newsletter_present and not lead_magnet_present:
            gaps.append("No email list or lead magnet")
    if community_present and not course_present:
        gaps.append("Community exists but no course to upsell")
    if course_present and not community_present:
        gaps.append("Course exists but no community to retain buyers")
    if (course_present or community_present) and not newsletter_present:
        gaps.append("Selling products with no visible email nurture")
    if confidence == "Low":
        gaps.append("Data insufficient — gaps cannot be confirmed without more inspection")

    # ── Outreach angle — driven by the DEEPEST funnel layer reached ──────────
    # Decision order:
    #   1. HT confirmed              → DISQUALIFY (we found the backend)
    #   2. HT suspected              → review
    #   3. Endpoint uncertain (gate) → FLAG, neither qualify nor disqualify
    #   4. Low/mid endpoint, clear   → QUALIFIED
    #   5. lead-magnet / none        → provisional / needs data
    top_signals = "; ".join(ht_signals_found[:2])
    if highest_tier == TIER_HIGH_TICKET:
        angle = (f"DISQUALIFY — funnel ends in HT ({fd['deepest_layer']}). "
                 f"Path: {fd['funnel_path']}")
    elif ht_level == "Medium":
        angle = f"SUSPECTED HT (score {ht_score}) — review manually: {top_signals}"
    elif ep["endpoint_uncertain"]:
        angle = (f"ENDPOINT UNCERTAIN — funnel continues behind a {ep['boundary']} "
                 f"we cannot see past; HT backend NOT ruled out. Manual review required. "
                 f"Path so far: {fd['funnel_path']}")
    elif highest_tier in (TIER_LOW_TICKET, TIER_MID_TICKET):
        angle = (f"QUALIFIED — funnel ends at {fd['highest_offer_type']} "
                 f"({fd['deepest_layer']}), no HT backend found (endpoint conf "
                 f"{ep['endpoint_confidence']}). Path: {fd['funnel_path']} "
                 f"— pitch HT ascension offer")
    elif highest_tier == TIER_LEAD_MAGNET:
        if confidence == "Low":
            angle = "NEEDS MORE DATA — lead magnet found but funnel not fully reachable: " + suf["notes"]
        else:
            angle = ("QUALIFIED (provisional) — lead capture only, no paid endpoint reached "
                     "after crawl; verify funnel manually then pitch")
    elif confidence == "Low":
        angle = "NEEDS MORE DATA — Inspect manually: " + suf["notes"]
    elif mono_conclusion == "Monetization Not Found":
        angle = "Large audience, no monetization found — verify manually then pitch first offer"
    else:
        angle = "Partial signals — review manually before outreach"

    # ── Pages visited summary (with NAV tags and signal hits) ────────────────
    def _page_signals(r):
        """Return a short string of monetization signals found on this page."""
        t = (r.get("Page Title","") + " " + r.get("Extracted Text","")).lower()
        hits = []
        for sig in HT_TEXT_SIGNALS:
            if sig in t:
                hits.append(sig)
                break  # one HT hit is enough to flag
        for sig in COURSE_TEXT + COMMUNITY_TEXT + NEWSLETTER_TEXT:
            if sig in t:
                hits.append(sig)
                break
        return f" [{', '.join(hits[:2])}]" if hits else ""

    pages_summary = " | ".join(
        "[d{d}] {pt}{nav} — {url}{sigs}".format(
            d   = r.get("Depth", 0),
            pt  = r.get("Page Type",""),
            nav = " [NAV]" if "nav/cta" in r.get("Source","").lower() else "",
            url = r.get("URL","")[:55],
            sigs= _page_signals(r),
        )
        for r in rows if r.get("URL") and r.get("Page Type","") not in {"(no links found)"}
    )

    needs_instagram = any("Instagram" in r.get("Page Type","") for r in rows)
    instagram_note  = " | ⚠ Instagram bio link needed for full picture" if needs_instagram else ""
    nav_explored    = suf.get("nav_explored", False)

    return {
        "Data Confidence":            confidence,
        "Data Sufficiency Notes":     suf["notes"],
        "Nav Explored":               "Y" if nav_explored else "N",
        "Pages Visited":              pages_visited,
        "Max Depth Reached":          max_depth,
        "Pages Fetched OK":           pages_fetched,
        "Monetization Conclusion":    mono_conclusion,
        "Deepest Monetization Layer": fd["deepest_layer"],
        "Funnel Path":                fd["funnel_path"],
        "Highest Offer Type Found":   fd["highest_offer_type"],
        "Highest Offer Confidence":   offer_conf,
        "Endpoint Confidence":        ep["endpoint_confidence"],
        "Endpoint Uncertain":         "Y" if ep["endpoint_uncertain"] else "N",
        "Endpoint Boundary":          ep["boundary"] + (f" ({ep['boundary_url'][:50]})" if ep["boundary_url"] else ""),
        "Lead Magnet Present (Y/N)":  "Y" if (fd["lead_magnet_present"] or lead_magnet_present) else "N",
        "Opt-in Form Crossed":        "Y" if fd["form_crossed"] else "N",
        "HT Score":                   ht_score,
        "HT Level":                   ht_level,
        "Coaching Present":           "Y" if coaching_present    else "N",
        "Mentorship Present":         "Y" if mentorship_present  else "N",
        "Community Present":          "Y" if community_present   else "N",
        "Course Present":             "Y" if course_present      else "N",
        "Newsletter Present":         "Y" if newsletter_present  else "N",
        "Lead Magnet Present":        "Y" if lead_magnet_present else "N",
        "Book A Call Present":        "Y" if book_call_present   else "N",
        "Application Funnel Present": "Y" if application_present else "N",
        "HT Signals Found":           " | ".join(ht_signals_found) if ht_signals_found else "None",
        "Existing Monetization":      ", ".join(mono) if mono else "None confirmed",
        "Funnel Maturity":            maturity,
        "Monetization Gaps":          " | ".join(gaps) if gaps else "None identified",
        "Outreach Angle":             angle,
        "Pages Crawled":              pages_summary + instagram_note,
    }

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 1 — DISCOVERY + ABOUT PAGE LINK EXTRACTION
# ══════════════════════════════════════════════════════════════════════════════

def run_stage1():
    print("\n" + "═"*70)
    print("STAGE 1 — Discovery + About-page link extraction")
    print("═"*70)

    print(f"\nSearching YouTube: '{NICHE_QUERY}' ({MAX_RESULTS} candidates)")
    channel_ids = search_channels(NICHE_QUERY, MAX_RESULTS)
    print(f"API returned {len(channel_ids)} channel IDs\n")

    cutoff   = datetime.now(timezone.utc) - timedelta(days=MAX_DAYS_INACTIVE)
    surviving = []
    counts    = {"english":0,"geo":0,"subs":0,"inactive":0,"company":0}

    for cid in channel_ids:
        d = get_channel_details(cid)
        if not d:
            continue
        resp = youtube.channels().list(part="snippet", id=cid).execute()
        raw  = resp["items"][0] if resp.get("items") else None
        if raw and not passes_english(raw):
            counts["english"] += 1
            print(f"  skip [non-English]  {d['title']}")
            continue
        geo_ok, geo_why = passes_geography(d["country"], d["description"])
        if not geo_ok:
            counts["geo"] += 1
            print(f"  skip [geo: {geo_why}]  {d['title']}")
            continue
        if d["subs"] < MIN_SUBS:
            counts["subs"] += 1
            continue
        latest = get_latest_upload(d["uploads"])
        if not latest or latest < cutoff:
            counts["inactive"] += 1
            continue
        if not passes_personal_brand(d["title"], d["description"]):
            counts["company"] += 1
            print(f"  skip [company]      {d['title']}")
            continue
        print(f"  PASS                {d['title']} ({d['subs']:,} subs)")
        surviving.append(d)
        time.sleep(0.3)

    print(f"\nFilters: english={counts['english']} geo={counts['geo']} "
          f"subs={counts['subs']} inactive={counts['inactive']} company={counts['company']}")
    print(f"Surviving for Playwright scan: {len(surviving)}\n")

    rows = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False, slow_mo=150, executable_path=CHROME_PATH,
            args=["--disable-blink-features=AutomationControlled","--no-sandbox"],
        )
        ctx  = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="en-US", viewport={"width":1280,"height":900},
        )
        page = ctx.new_page()
        print("Browser warm-up ...")
        page.goto("https://www.youtube.com", wait_until="domcontentloaded", timeout=20000)
        dismiss_consent(page)
        page.wait_for_timeout(2000)

        for ch in surviving:
            print(f"\n  → {ch['title']}")
            links = extract_about_links(page, ch["about_url"], ch["title"])
            if links:
                for lk in links:
                    rows.append({
                        "Channel Name":    ch["title"],
                        "Channel URL":     ch["url"],
                        "Subscribers":     ch["subs"],
                        "Country":         ch["country"] or "unknown",
                        "Link Label":      lk["label"],
                        "Destination URL": lk["url"],
                        "Page Type":       detect_page_type(lk["url"]),
                    })
            else:
                rows.append({
                    "Channel Name":    ch["title"],
                    "Channel URL":     ch["url"],
                    "Subscribers":     ch["subs"],
                    "Country":         ch["country"] or "unknown",
                    "Link Label":      "(none found)",
                    "Destination URL": "",
                    "Page Type":       "",
                })
            time.sleep(DELAY_BETWEEN_CHANNELS)

        browser.close()

    fields = ["Channel Name","Channel URL","Subscribers","Country",
              "Link Label","Destination URL","Page Type"]
    with open(STAGE1_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(rows)

    link_count = sum(1 for r in rows if r["Destination URL"])
    print(f"\n✓ Stage 1 — {len(surviving)} channels, {link_count} links → {STAGE1_CSV}")
    return rows

# ══════════════════════════════════════════════════════════════════════════════
# INSTAGRAM-ASSISTED DISCOVERY (secondary, gated)
# ══════════════════════════════════════════════════════════════════════════════

IG_CHALLENGE_MARKERS = [
    "/challenge/", "/auth_platform/", "/accounts/suspended", "two-factor",
    "confirm it's you", "we detected an unusual", "enter the code", "enter the 6-digit",
    "verify it's you", "suspicious login", "help us confirm", "we've detected",
    "your account has been", "please wait a few minutes", "try again later",
]

def load_ig_credentials():
    try:
        with open(IG_CREDENTIALS_FILE, encoding="utf-8") as f:
            c = json.load(f)
        if c.get("username") and c.get("password"):
            return c["username"], c["password"]
    except Exception as e:
        print(f"  [IG] credentials unavailable: {e}")
    return None, None


def ig_handle_from_url(url):
    """Extract a clean handle from an instagram.com URL or @mention."""
    u = url.strip()
    if u.startswith("@"):
        return u[1:].strip("/")
    m = re.search(r"instagram\.com/([A-Za-z0-9_.]+)", u, re.I)
    if m:
        h = m.group(1)
        if h.lower() in ("p", "reel", "reels", "explore", "stories", "accounts", "tv"):
            return ""
        return h
    return ""


def ig_unwrap_link(href):
    """Unwrap Instagram's l.instagram.com/?u=<encoded> redirect wrapper."""
    if "l.instagram.com" in href or "/redirect" in href:
        m = re.search(r"[?&]u=([^&]+)", href)
        if m:
            return unquote(m.group(1))
    return href


def _ig_json_field(html, key):
    """
    Pull a string field (e.g. 'biography', 'external_url') out of the profile
    JSON embedded in the page HTML and decode its \\uXXXX / \\n escapes properly
    (so '\\u0040aicomacademy' becomes '@aicomacademy'). Returns '' if absent.
    """
    m = re.search(rf'"{key}":\s*"((?:[^"\\]|\\.)*)"', html or "")
    if not m:
        return ""
    try:
        return json.loads('"' + m.group(1) + '"')
    except Exception:
        return m.group(1)


def ig_detect_challenge(page):
    """Return a challenge reason string if IG is showing a verification wall, else ''."""
    try:
        url = (page.url or "").lower()
        for mk in IG_CHALLENGE_MARKERS:
            if mk in url:
                return f"IG challenge (url: {mk})"
        body = page.locator("body").inner_text(timeout=4000).lower()
        for mk in IG_CHALLENGE_MARKERS:
            if mk in body:
                return f"IG challenge ('{mk}')"
    except Exception:
        pass
    return ""


def ig_dismiss_dialogs(page):
    """Dismiss 'Save login info', 'Turn on notifications', cookie prompts."""
    for label in ("Not now", "Not Now", "Allow all cookies", "Decline optional cookies",
                  "Save info", "Dismiss"):
        try:
            btn = page.locator(f"button:has-text('{label}'), div[role='button']:has-text('{label}')")
            if btn.count() > 0:
                btn.first.click(timeout=2500)
                page.wait_for_timeout(800)
        except Exception:
            pass


def ig_is_logged_in(page):
    try:
        page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2500)
        ig_dismiss_dialogs(page)
        # Logged-in home shows nav links to /direct/ or a 'Create' control; login page has a password field
        if page.locator("input[name='password']").count() > 0:
            return False
        nav = page.eval_on_selector_all(
            "a[href*='/direct/'], a[href*='/explore/'], svg[aria-label='Home'], a[href='/']",
            "els => els.length"
        )
        return bool(nav and nav > 0)
    except Exception:
        return False


def ig_login(page, username, password):
    """
    Fresh login. Returns 'ok', or a challenge/error status. Never solves CAPTCHA,
    never bypasses MFA, never touches account recovery.
    """
    try:
        page.goto("https://www.instagram.com/accounts/login/",
                  wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2500)
        ig_dismiss_dialogs(page)

        if page.locator("input[name='username']").count() == 0:
            # Already logged in (session cookie) or unexpected page
            if ig_is_logged_in(page):
                return "ok"
        page.locator("input[name='username']").first.fill(username, timeout=5000)
        page.locator("input[name='password']").first.fill(password, timeout=5000)
        page.locator("button[type='submit'], button:has-text('Log in')").first.click(timeout=5000)
        page.wait_for_timeout(6000)

        challenge = ig_detect_challenge(page)
        if challenge:
            return challenge   # REVIEW_REQUIRED — do not attempt to solve
        ig_dismiss_dialogs(page)
        page.wait_for_timeout(1500)

        if ig_is_logged_in(page):
            return "ok"
        # Still seeing a password field → bad creds or soft block
        if page.locator("input[name='password']").count() > 0:
            return "login failed (credentials rejected or blocked)"
        return "login uncertain (no logged-in markers)"
    except Exception as e:
        return f"login error: {e}"


def ensure_ig_context(browser):
    """
    Lazily create a logged-in Instagram context, reusing a saved session if present.
    Returns (context, page, status). status 'ok' means usable; anything else means
    Instagram is unavailable this run (callers mark creators REVIEW_REQUIRED).
    """
    username, password = load_ig_credentials()
    if not username:
        return None, None, "no credentials"

    storage = IG_SESSION_FILE if os.path.exists(IG_SESSION_FILE) else None
    try:
        ctx = browser.new_context(
            storage_state=storage,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="en-US", viewport={"width": 1280, "height": 900},
        )
    except Exception as e:
        return None, None, f"context error: {e}"

    page = ctx.new_page()

    # Reuse saved session if it's still valid
    if storage and ig_is_logged_in(page):
        print("  [IG] reused saved session (no login needed)")
        return ctx, page, "ok"

    print("  [IG] logging in ...")
    status = ig_login(page, username, password)
    if status == "ok":
        try:
            ctx.storage_state(path=IG_SESSION_FILE)
            print("  [IG] login ok — session saved")
        except Exception:
            pass
        return ctx, page, "ok"

    print(f"  [IG] login unavailable: {status}")
    return ctx, page, status   # keep ctx/page so caller can close; status != ok


def ig_extract_profile(page, handle, creator_handle=""):
    """
    Visit one IG profile and extract bio text, external bio links, and @mentioned
    business accounts. Returns dict(status, bio_text, bio_links[], biz_accounts[]).
    """
    handle = handle.strip("@/ ").strip()
    result = {"status": "ok", "handle": handle, "bio_text": "",
              "bio_links": [], "biz_accounts": []}
    if not handle:
        result["status"] = "empty handle"
        return result
    try:
        page.goto(f"https://www.instagram.com/{handle}/",
                  wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(IG_ACTION_DELAY * 1000)
    except Exception as e:
        result["status"] = f"profile load error: {e}"
        return result

    challenge = ig_detect_challenge(page)
    if challenge:
        result["status"] = challenge
        return result

    try:
        html = page.content()
    except Exception:
        html = ""

    # ── Bio text — embedded JSON 'biography' is the reliable source.
    # ('header section' returns empty in current IG DOM; full 'header' is the fallback.)
    bio = _ig_json_field(html, "biography")
    if not bio:
        try:
            bio = page.locator("header").first.inner_text(timeout=4000)
        except Exception:
            bio = ""
    result["bio_text"] = bio[:600]

    # ── External bio link(s) — JSON external_url first, then header anchors.
    links = []
    for k in ("external_url", "external_lynx_url"):
        v = _ig_json_field(html, k)
        if v:
            links.append(ig_unwrap_link(v))
    try:
        raw = page.eval_on_selector_all("header a[href]", "els => els.map(e => e.href)")
    except Exception:
        raw = []
    links += [ig_unwrap_link(h) for h in raw]
    for h2 in links:
        if h2.startswith("http") and "instagram.com" not in get_base_domain(h2):
            if h2 not in result["bio_links"]:
                result["bio_links"].append(h2)

    # ── Tagged business accounts — @mentions in BIO TEXT ONLY.
    # Deliberately NOT scraping profile anchors: those include the "Accounts you
    # might like" suggestion rail, which are not bio tags. Bio text gives only the
    # creator's genuinely tagged accounts (e.g. @aicomacademy @1800bankroll @2up).
    IG_SYS = {"p","reel","reels","explore","stories","accounts","tv","direct","s","about"}
    for mh in re.findall(r"@([A-Za-z0-9_][A-Za-z0-9_.]{1,})", bio):
        ml = mh.lower().rstrip(".")
        if ml in IG_SYS:
            continue
        if ml in (handle.lower(), (creator_handle or "").lower()):
            continue
        if ml not in [b.lower() for b in result["biz_accounts"]]:
            result["biz_accounts"].append(mh.rstrip("."))

    return result


def discover_via_instagram(ig_page, seed_ig_url, creator_name):
    """
    Orchestrate IG discovery for one creator:
      seed profile → bio links + tagged biz accounts → (visit up to MAX-1 biz accts)
    Returns dict(used, profiles_visited[], bio_links[], biz_accounts[], status).
    Respects MAX_IG_PROFILES_PER_CREATOR and never exceeds it.
    """
    out = {"used": True, "profiles_visited": [], "bio_links": [],
           "biz_accounts": [], "status": "ok"}
    creator_handle = ig_handle_from_url(seed_ig_url)
    if not creator_handle:
        out["status"] = "no IG handle in seed"
        out["used"] = False
        return out

    queue = [creator_handle]
    while queue and len(out["profiles_visited"]) < MAX_IG_PROFILES_PER_CREATOR:
        handle = queue.pop(0)
        if handle in out["profiles_visited"]:
            continue
        print(f"  [IG] visiting profile: @{handle}")
        prof = ig_extract_profile(ig_page, handle, creator_handle)
        out["profiles_visited"].append(handle)

        if prof["status"] != "ok":
            # Challenge / verification mid-crawl → stop and flag
            out["status"] = prof["status"]
            if any(m in prof["status"].lower() for m in ("challenge", "verify", "suspicious", "code")):
                out["status"] = "REVIEW_REQUIRED — " + prof["status"]
                return out
            continue

        for bl in prof["bio_links"]:
            if bl not in out["bio_links"]:
                out["bio_links"].append(bl)
        # Queue tagged business accounts (respecting the profile cap)
        for biz in prof["biz_accounts"]:
            if biz not in out["biz_accounts"]:
                out["biz_accounts"].append(biz)
            if (biz not in out["profiles_visited"] and biz not in queue
                    and len(out["profiles_visited"]) + len(queue) < MAX_IG_PROFILES_PER_CREATOR):
                queue.append(biz)
        time.sleep(IG_ACTION_DELAY)

    if not out["bio_links"] and out["status"] == "ok":
        out["status"] = "no bio links found"
    return out


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 2 — RECURSIVE FUNNEL CRAWLER
# ══════════════════════════════════════════════════════════════════════════════

def get_base_domain(url):
    """Return just the registered domain (e.g. 'jordanwelch.com')."""
    try:
        host = urlparse(url).netloc.lower().lstrip("www.")
        return host
    except Exception:
        return ""

def is_followable(url, creator_domains, visited):
    """
    Return True if this URL should be added to the crawl queue.
    creator_domains: set of base domains already seen for this creator.
    """
    if not url or url in visited:
        return False
    url = normalize_url(url)
    if not url.startswith("http"):
        return False

    parsed = urlparse(url)
    domain = parsed.netloc.lower().lstrip("www.")
    path   = parsed.path

    # Hard skip — social and generic domains
    for skip in SOCIAL_SKIP_DOMAINS:
        if domain == skip or domain.endswith("." + skip):
            return False

    # Hard skip — boring path types
    if SKIP_PATH_PATTERNS.search(path):
        return False

    # Skip file downloads
    if re.search(r"\.(pdf|mp4|mp3|zip|exe|dmg|png|jpg|gif|svg|css|js|woff)$", path, re.I):
        return False

    # Always follow known funnel platform domains
    for fd in FUNNEL_FOLLOW_DOMAINS:
        if domain == fd or domain.endswith("." + fd):
            return True

    # Follow same-domain subpages IF path looks funnel-relevant
    if domain in creator_domains:
        if FUNNEL_PATH_KEYWORDS.search(path):
            return True
        # Also follow top-level path (the homepage / root of the creator's site)
        if path in ("", "/", "/index.html"):
            return True

    return False


def fetch_page_and_links(pw_page, url):
    """
    Fetch a page with Playwright.
    Returns (title, text, all_hrefs, nav_cta_hrefs).
    nav_cta_hrefs = links from nav/header elements + CTA-text anchors — these
    are followed on creator-owned domains without a path-keyword requirement.
    All four values are always returned — empty on failure.
    """
    try:
        pw_page.goto(url, wait_until="domcontentloaded", timeout=PAGE_FETCH_TIMEOUT_S * 1000)
        pw_page.wait_for_timeout(PAGE_SETTLE_MS)
        title = pw_page.title() or ""

        # Extract body text
        body_text = pw_page.locator("body").inner_text()
        body_text = re.sub(r"\s{2,}", " ", body_text).strip()

        # Extract all anchor hrefs (browser resolves relative → absolute)
        raw_hrefs = pw_page.eval_on_selector_all(
            "a[href]", "els => els.map(e => e.href)"
        )
        hrefs = [
            h for h in raw_hrefs
            if h and h.startswith("http") and "#" not in h.split("?")[0][-1:]
        ]
        hrefs = [unwrap_yt_redirect(h) for h in hrefs]
        hrefs = list(dict.fromkeys(hrefs))

        # ── Nav / CTA link extraction ─────────────────────────────────────────
        # These bypass the path-keyword filter so we explore navigation menus
        # and CTA buttons on creator-owned domains even when the URL path is
        # unconventional (e.g. /online-business, /academy, /sell-with-me).
        try:
            nav_raw = pw_page.eval_on_selector_all(
                "nav a[href], header a[href], [class*='nav'] a[href], "
                "[class*='menu'] a[href], [id*='nav'] a[href], "
                "[role='navigation'] a[href], [class*='header'] a[href]",
                "els => [...new Set(els.map(e => e.href).filter(h => h && h.startsWith('http')))]"
            )
            cta_pattern = (
                "apply now|apply here|apply|learn more|get started|get instant access|"
                "join now|join the|enroll|watch training|view program|see courses|"
                "sign up|get access|start now|start here|book a call|book a|"
                "work with me|work with|online business|academy|coaching|mentorship|"
                "program|courses|community|resources|training|masterclass|download|"
                "grab the free|free course|free training|free guide|"
                "scale your|scale my|build my|grow my|claim your|let's|"
                "yes i want|next step|take the|get the|join us|i'm ready|im ready"
            )
            cta_raw = pw_page.eval_on_selector_all(
                "a[href]",
                f"els => els.filter(e => /{cta_pattern}/i.test(e.innerText.trim())).map(e => e.href).filter(h => h && h.startsWith('http'))"
            )
            nav_cta_hrefs = list(dict.fromkeys(nav_raw + cta_raw))
        except Exception:
            nav_cta_hrefs = []

        return title, body_text[:MAX_TEXT_LENGTH], hrefs, nav_cta_hrefs

    except PWTimeout:
        return "", "", [], []
    except Exception:
        return "", "", [], []


def is_nav_followable(url, creator_domains, visited):
    """
    Like is_followable() but for nav/header/CTA links on creator-owned domains.
    Skips the FUNNEL_PATH_KEYWORDS requirement — any non-boring path is followed.
    """
    if not url or url in visited:
        return False
    url = normalize_url(url)
    if not url.startswith("http"):
        return False
    parsed = urlparse(url)
    domain = parsed.netloc.lower().lstrip("www.")
    path   = parsed.path
    for skip in SOCIAL_SKIP_DOMAINS:
        if domain == skip or domain.endswith("." + skip):
            return False
    if SKIP_PATH_PATTERNS.search(path):
        return False
    if re.search(r"\.(pdf|mp4|mp3|zip|exe|dmg|png|jpg|gif|svg|css|js|woff)$", path, re.I):
        return False
    for fd in FUNNEL_FOLLOW_DOMAINS:
        if domain == fd or domain.endswith("." + fd):
            return True
    # On creator-owned domains: follow any path (no keyword restriction)
    if domain in creator_domains:
        return True
    return False


def page_has_captcha(pw_page):
    """
    True only for a REAL, visible interactive CAPTCHA challenge (reCAPTCHA v2
    checkbox, hCaptcha, Cloudflare Turnstile). Deliberately ignores reCAPTCHA v3
    badges (invisible, non-blocking) and stray '[class*=captcha]' elements, which
    caused false positives that flagged clean creators (e.g. Austin/LaunchPass).
    """
    try:
        n = pw_page.eval_on_selector_all(
            "iframe[src*='recaptcha'], iframe[src*='hcaptcha'], "
            "iframe[src*='challenges.cloudflare.com/turnstile']",
            """els => els.filter(e => {
                const s = e.getAttribute('src') || '';
                if (s.includes('/bframe')) return false;          // challenge popup, only when shown
                const r = e.getBoundingClientRect();
                return r.width > 60 && r.height > 40;              // visible widget, not a v3 badge
            }).length"""
        )
        return bool(n and n > 0)
    except Exception:
        return False


def open_captcha_tab(pw_page, url):
    """
    Leave the CAPTCHA page open in a new browser tab so the user can solve it later
    (best-effort). Never blocks. Returns True if a tab was opened.
    """
    try:
        tab = pw_page.context.new_page()
        tab.goto(url, wait_until="domcontentloaded", timeout=20000)
        return True
    except Exception:
        return False


def page_form_blocker(pw_page):
    """
    Detect conditions under which we must NOT auto-fill a form:
      'captcha'  — reCAPTCHA/hCaptcha/Turnstile present (manual-solve, never bypass)
      'payment'  — credit-card / payment fields present
      'password' — account creation or login (not a lead opt-in)
    Returns '' if the page is safe to fill.
    """
    try:
        if page_has_captcha(pw_page):
            return "captcha"
        pay = pw_page.eval_on_selector_all(
            "input[name*='card' i], input[name*='cc-'], input[autocomplete*='cc-'], "
            "input[placeholder*='card number' i], input[name*='cvc' i], "
            "iframe[src*='stripe'], iframe[name*='card' i], iframe[src*='paypal']",
            "els => els.length"
        )
        if pay and pay > 0:
            return "payment"
        pw = pw_page.eval_on_selector_all("input[type='password']", "els => els.length")
        if pw and pw > 0:
            return "password"
    except Exception:
        return ""
    return ""


# Domains where an email field means "start a SaaS trial", not "creator lead magnet".
# Never auto-fill opt-in forms on these — they are not the creator's own funnel.
OPTIN_SKIP_DOMAINS = SOCIAL_SKIP_DOMAINS | {
    "shopify.com", "pxf.io", "shopify.pxf.io", "go.shopify.com",
    "myshopify.com", "stripe.com", "paypal.com", "gumroad.com",
}

def is_optin_fillable_domain(url):
    """False for third-party SaaS / affiliate redirectors (Shopify trial, etc.)."""
    domain = get_base_domain(url)
    if not domain:
        return False
    for skip in OPTIN_SKIP_DOMAINS:
        if domain == skip or domain.endswith("." + skip):
            return False
    return True


def looks_like_optin_gate(title, text):
    """Does this page primarily exist to capture an email for a free offer?"""
    blob = (title + " " + text).lower()
    return any(k in blob for k in [
        "free guide", "free ebook", "free e-book", "free training", "free webinar",
        "free download", "free course", "free pdf", "free checklist", "free masterclass",
        "free workshop", "enter your email", "get instant access", "download now",
        "get the free", "where should i send", "save my seat", "claim your free",
        "join the free", "register for the free", "subscribe to get", "sign up to get",
    ])


BOOKING_DOMAINS_HT = ["calendly.com", "cal.com", "tidycal.com", "acuityscheduling",
                      "savvycal.com", "oncehub.com", "hubspot.com/meetings"]

def _fill_form_fields(pw_page, identity):
    """
    Fill all visible inputs on the current form step. Real contact fields get the
    identity; everything else gets harmless filler. Radio/select/option-button
    answers prefer the 'most qualified' choice (highest $ / yes) so the form routes
    us to its end (a booking page) rather than a rejection page.
    """
    # Contact fields
    for sel, val in (
        ("input[type='email'], input[name*='email' i], input[placeholder*='email' i]", identity["email"]),
        ("input[type='tel'], input[name*='phone' i], input[placeholder*='phone' i]", identity["phone"]),
        ("input[name*='name' i], input[placeholder*='name' i], input[id*='name' i]", identity["full_name"]),
    ):
        try:
            loc = pw_page.locator(sel)
            for i in range(min(loc.count(), 3)):
                el = loc.nth(i)
                if el.is_visible() and not (el.input_value() or "").strip():
                    el.fill(val, timeout=1500)
        except Exception:
            pass
    # Other free-text inputs + textareas → filler
    try:
        loc = pw_page.locator(
            "input[type='text']:not([name*='name' i]):not([name*='email' i]):not([name*='phone' i]), "
            "input[type='url'], input:not([type]), textarea")
        for i in range(min(loc.count(), 8)):
            el = loc.nth(i)
            try:
                if el.is_visible() and not (el.input_value() or "").strip():
                    el.fill(FORM_FILLER_TEXT, timeout=1200)
            except Exception:
                pass
    except Exception:
        pass
    # Native radio groups + selects → highest-value option
    try:
        groups = pw_page.eval_on_selector_all(
            "input[type='radio']", "els => [...new Set(els.map(e => e.name))]")
        for name in groups:
            if not name:
                continue
            opts = pw_page.locator(f"input[type='radio'][name='{name}']")
            best = _best_option_index(pw_page, opts)
            try:
                opts.nth(best).check(timeout=1200, force=True)
            except Exception:
                pass
    except Exception:
        pass
    try:
        sels = pw_page.locator("select")
        for i in range(min(sels.count(), 5)):
            try:
                sels.nth(i).select_option(index=1)  # first real (non-placeholder) option
            except Exception:
                pass
    except Exception:
        pass
    # Typeform / custom button-style options (no radio inputs)
    try:
        btns = pw_page.locator("[role='radio'], [data-qa*='choice'], button[class*='choice'], li[role='option']")
        if btns.count() > 0:
            best = _best_option_index(pw_page, btns)
            try:
                btns.nth(best).click(timeout=1200)
            except Exception:
                pass
    except Exception:
        pass


def _best_option_index(pw_page, loc):
    """Pick the option index that looks 'most qualified' (highest $ figure, else 'yes', else last)."""
    try:
        n = loc.count()
        texts = []
        for i in range(n):
            try:
                t = loc.nth(i).inner_text(timeout=600) or ""
            except Exception:
                t = ""
            texts.append(t.lower())
        best, best_val = n - 1, -1     # default: last option (usually the highest range)
        for i, t in enumerate(texts):
            prices = extract_prices(t)
            v = max(prices) if prices else (1 if ("yes" in t or "ready" in t) else 0)
            if v > best_val:
                best_val, best = v, i
        return best
    except Exception:
        return 0


def _click_advance(pw_page):
    """Click a Next/Continue/Submit/OK control (or press Enter). Returns True if clicked."""
    sel = (
        "button[type='submit'], input[type='submit'], "
        "button:has-text('Continue'), button:has-text('Next'), button:has-text('Submit'), "
        "button:has-text('OK'), button:has-text('Get Started'), button:has-text('Apply'), "
        "button:has-text('Book'), button:has-text('Get'), button:has-text('Send'), "
        "button:has-text('Yes'), button:has-text('Instant Access'), button:has-text('Access'), "
        "[data-qa*='submit'], a:has-text('Continue'), a:has-text('Next')")
    try:
        btn = pw_page.locator(sel)
        if btn.count() > 0:
            btn.first.click(timeout=3000)
            return True
        pw_page.keyboard.press("Enter")
        return True
    except Exception:
        try:
            pw_page.keyboard.press("Enter")
            return True
        except Exception:
            return False


def fill_and_advance_form(pw_page, identity, max_steps=MAX_FORM_STEPS):
    """
    Traverse a (possibly multi-step) form to its end to reveal where the funnel
    leads. Fills contact fields with the identity and qualification questions with
    'ideal HT student' answers. Detects HT qualification screening (revenue / capital
    -to-invest) and whether the funnel ends at a booking page (Calendly = HT offer).

    Returns dict: status, final_url, qualification_form (bool), booking_reached (bool),
                  collected_text (str), steps (int).
    """
    out = {"status": "no-form", "final_url": pw_page.url, "qualification_form": False,
           "booking_reached": False, "collected_text": "", "steps": 0}
    collected = []

    # Need at least one fillable field to bother
    try:
        has_input = pw_page.locator(
            "input[type='email'], input[type='text'], input[type='tel'], textarea, "
            "input[type='radio'], [role='radio'], select").count() > 0
    except Exception:
        has_input = False
    if not has_input:
        return out

    for step in range(max_steps):
        out["steps"] = step + 1

        # CAPTCHA → never block the batch. Flag and bail; the creator is recorded
        # as captcha-pending for a later manual solve + targeted re-run.
        if page_has_captcha(pw_page):
            out["status"] = "captcha-deferred"
            break

        blk = page_form_blocker(pw_page)
        if blk in ("payment", "password"):     # never fill these
            out["status"] = blk
            break

        # Collect text + detect HT qualification language / booking destination
        try:
            txt = pw_page.locator("body").inner_text(timeout=3000)
        except Exception:
            txt = ""
        collected.append(txt)
        low = txt.lower()
        if (any(k in low for k in HT_QUALIFIER_INVEST)
                or any(k in low for k in HT_QUALIFIER_REVENUE)):
            out["qualification_form"] = True
        if any(d in pw_page.url.lower() for d in BOOKING_DOMAINS_HT):
            out["booking_reached"] = True
            out["status"] = "advanced"
            break

        url_before = pw_page.url
        _fill_form_fields(pw_page, identity)
        if not _click_advance(pw_page):
            out["status"] = "submit-failed"
            break
        try:
            pw_page.wait_for_load_state("domcontentloaded", timeout=8000)
        except Exception:
            pass
        pw_page.wait_for_timeout(2800)

        url_after = pw_page.url
        if any(d in url_after.lower() for d in BOOKING_DOMAINS_HT):
            out["booking_reached"] = True
            out["status"] = "advanced"
            break
        if url_after != url_before:
            out["status"] = "advanced"
            # keep looping — multi-step forms keep the same or new URL
        elif step > 0:
            # No navigation and not the first submit → likely stuck / reached end
            out["status"] = out["status"] if out["status"] != "no-form" else "no-advance"
            # one more pass may reveal an inline thank-you; otherwise stop
            if not out["qualification_form"]:
                break

    out["final_url"] = pw_page.url
    out["collected_text"] = " ".join(collected)[:MAX_TEXT_LENGTH]
    if out["status"] == "no-form":
        out["status"] = "advanced" if out["steps"] else "no-form"
    return out


def crawl_creator_funnel(channel_name, seed_urls, pw_page,
                         max_depth=MAX_CRAWL_DEPTH,
                         max_pages=MAX_PAGES_PER_CREATOR):
    """
    BFS crawl starting from seed_urls (About-page link destinations).
    Returns list of page dicts, one per visited URL.
    """
    # Infer creator's own domain ecosystem from seed URLs
    creator_domains = set()
    for url in seed_urls:
        d = get_base_domain(normalize_url(url))
        if d and d not in SOCIAL_SKIP_DOMAINS:
            creator_domains.add(d)

    visited = set()
    queued  = set()  # track what's been added to queue to avoid duplicates
    # Queue: (url, depth, label)  — label is human-readable source for logging
    queue   = []
    for u in seed_urls:
        nu = normalize_url(u)
        if nu and not any(s in nu.lower() for s in SOCIAL_SKIP_DOMAINS):
            queue.append((nu, 0, "About page link"))
            queued.add(nu)

    pages        = []
    nav_explored = False  # becomes True once a nav/CTA link is successfully fetched
    form_submits = 0      # opt-in forms filled for this creator (budget-capped)
    instagram_seeds = [u for u in seed_urls if "instagram.com" in u.lower()]

    while queue and len(pages) < max_pages:
        url, depth, source = queue.pop(0)

        url = normalize_url(url)
        if not url or url in visited:
            continue
        visited.add(url)

        page_type = detect_page_type(url)

        # Skip social pages at any depth
        domain = get_base_domain(url)
        if any(s == domain or domain.endswith("." + s) for s in SOCIAL_SKIP_DOMAINS):
            continue

        is_nav_page = "nav/" in source or "cta/" in source
        if is_nav_page:
            nav_explored = True

        indent = "  " + ("  " * depth)
        nav_tag = " [NAV]" if is_nav_page else ""
        print(f"{indent}[d{depth}] {page_type:18} {url[:65]}{nav_tag}")

        title, text, hrefs, nav_cta_hrefs = fetch_page_and_links(pw_page, url)
        ok = "✓" if title else "✗"
        print(f"{indent}       {ok} '{title[:55]}'  ({len(hrefs)} links found)")

        pages.append({
            "Channel Name":    channel_name,
            "Depth":           depth,
            "Source":          source,
            "Page Type":       page_type,
            "URL":             url,
            "Page Title":      title,
            "Extracted Text":  text,
            "Outbound Links":  len(hrefs),
        })

        # Only expand creator_domains from known funnel platform seeds, not all hrefs
        # (prevents drift into meta.com, autods.com etc.)
        for h in hrefs:
            d = get_base_domain(h)
            if d and d not in SOCIAL_SKIP_DOMAINS:
                for fd in FUNNEL_FOLLOW_DOMAINS:
                    if d == fd or d.endswith("." + fd):
                        creator_domains.add(d)
                        break

        # Enqueue links below depth limit
        if depth < max_depth:
            budget = max_pages * 3
            new_regular = 0
            new_nav     = 0

            # 1. Nav/CTA links get priority — insert at front of queue
            for href in nav_cta_hrefs:
                if len(queue) + len(pages) >= budget:
                    break
                if href not in queued and is_nav_followable(href, creator_domains, visited):
                    source_tag = f"nav/cta on {url[:45]}"
                    queue.insert(new_nav, (href, depth + 1, source_tag))
                    queued.add(href)
                    new_nav += 1

            # 2. Regular anchor links
            for href in hrefs:
                if len(queue) + len(pages) >= budget:
                    break
                if href not in queued and is_followable(href, creator_domains, visited):
                    queue.append((href, depth + 1, f"found on {url[:50]}"))
                    queued.add(href)
                    new_regular += 1

            parts = []
            if new_nav:     parts.append(f"{new_nav} nav/CTA")
            if new_regular: parts.append(f"{new_regular} regular")
            if parts:
                print(f"{indent}       → queued {', '.join(parts)} link(s)")

        # ── Funnel form traversal ─────────────────────────────────────────────
        # If this page has a real form (opt-in OR a qualification questionnaire),
        # fill it to the end to see where the funnel leads. A form that screens for
        # revenue / capital-to-invest, or that ends at a booking page, is a high-
        # ticket backend — this is what was hiding behind Saamir Mithwani's button.
        has_form = False
        try:
            has_form = (
                pw_page.locator("input[type='email'], input[type='radio'], "
                                "[role='radio'], select, textarea").count() > 0
                or pw_page.locator("input[type='text']").count() >= 2
                or any(d in url.lower() for d in ["typeform.com", "jotform.com", "tally.so"])
            )
        except Exception:
            has_form = False

        if (ENABLE_FORM_FILL and title and depth < max_depth
                and form_submits < MAX_FORM_SUBMITS_PER_CREATOR
                and is_optin_fillable_domain(url)
                and (has_form or looks_like_optin_gate(title, text))):
            fr = fill_and_advance_form(pw_page, LEAD_IDENTITY)
            form_submits += 1
            flags = []
            if fr["qualification_form"]: flags.append("HT revenue/invest screen")
            if fr["booking_reached"]:    flags.append("→ booking page (HT)")
            print(f"{indent}       ✉ form: {fr['status']} ({fr['steps']} step(s))"
                  + (f"  [{', '.join(flags)}]" if flags else ""))

            if fr["status"] == "captcha-deferred":
                # Never block the batch — flag, leave the page open, keep going.
                pages[-1]["Source"] += " | CAPTCHA — manual solve pending"
                pages.append({
                    "Channel Name":   channel_name,
                    "Depth":          depth,
                    "Source":         f"captcha-deferred on {url[:40]}",
                    "Page Type":      "CAPTCHA pending",
                    "URL":            url,
                    "Page Title":     "reCAPTCHA — manual solve needed",
                    "Extracted Text": "",
                    "Outbound Links": 0,
                })
                open_captcha_tab(pw_page, url)
                print(f"{indent}       ⚠ CAPTCHA — flagged for manual solve, continuing")
            elif fr["qualification_form"] or fr["booking_reached"]:
                # Record the HT funnel as a page so Stage 3 disqualifies the creator
                pages[-1]["Source"] += " | form traversed → HT funnel"
                ev = fr["collected_text"]
                if fr["booking_reached"]:
                    ev += " | reached booking page: " + fr["final_url"]
                pages.append({
                    "Channel Name":   channel_name,
                    "Depth":          depth + 1,
                    "Source":         f"form-traversal from {url[:40]}",
                    "Page Type":      "HT qualification funnel",
                    "URL":            fr["final_url"],
                    "Page Title":     "Qualification form → booking (high-ticket funnel)",
                    "Extracted Text": ev,
                    "Outbound Links": 0,
                })
            elif fr["status"] == "advanced" and fr["final_url"]:
                nu = normalize_url(fr["final_url"])
                ndom = get_base_domain(nu)
                is_social = any(s == ndom or ndom.endswith("." + s) for s in SOCIAL_SKIP_DOMAINS)
                if nu and nu not in queued and nu not in visited and not is_social:
                    queue.insert(0, (nu, depth + 1, f"form-submit on {url[:40]}"))
                    queued.add(nu)
                    pages[-1]["Source"] += " | opt-in submitted → next layer"

        time.sleep(DELAY_BETWEEN_PAGES)

    # Report Instagram links we couldn't follow
    if instagram_seeds:
        pages.append({
            "Channel Name":   channel_name,
            "Depth":          0,
            "Source":         "About page link",
            "Page Type":      "Instagram (manual seed needed)",
            "URL":            instagram_seeds[0],
            "Page Title":     "",
            "Extracted Text": "",
            "Outbound Links": 0,
        })
        print(f"  ⚠ Instagram link skipped (manual bio URL needed): {instagram_seeds[0]}")

    return pages


def creator_needs_instagram(seeds, pages):
    """
    Instagram is a secondary source. Trigger it only when the creator would
    otherwise be 'Needs More Data': they have an Instagram seed but the normal
    crawl found no real funnel page AND no HT signal surfaced.
    """
    ig_seeds = [u for u in seeds if "instagram.com" in u.lower()]
    if not ig_seeds:
        return False, ""

    real_pages = 0
    ht_found   = False
    for p in pages:
        ptype = p.get("Page Type", "")
        title = p.get("Page Title", "")
        text  = p.get("Extracted Text", "") or ""
        if "Instagram" in ptype or ptype in ("(no links found)", ""):
            continue
        if title and len(text) >= THIN_TEXT_THRESHOLD:
            real_pages += 1
        if any(k in (title + " " + text).lower() for k in HT_ENDPOINT_KEYWORDS):
            ht_found = True

    if ht_found:
        return False, ""
    if real_pages == 0:
        return True, ig_seeds[0]
    return False, ""


def run_stage2(stage1_rows=None, extra_seeds=None):
    """
    extra_seeds: dict mapping channel_name → [additional_url, ...]
    e.g. {"Jordan Welch": ["https://linktr.ee/jordanwelch"]}
    """
    print("\n" + "═"*70)
    print("STAGE 2 — Recursive funnel crawler")
    print("═"*70)

    if stage1_rows is None:
        with open(STAGE1_CSV, newline="", encoding="utf-8") as f:
            stage1_rows = list(csv.DictReader(f))

    extra_seeds = extra_seeds or {}

    # Group Stage 1 rows by creator to get seed URLs per creator
    by_creator = defaultdict(dict)
    for r in stage1_rows:
        name = r["Channel Name"]
        if name not in by_creator:
            by_creator[name] = {
                "channel_url": r["Channel URL"],
                "subscribers": r.get("Subscribers",""),
                "country":     r.get("Country",""),
                "seed_urls":   [],
                "seed_labels": {},
            }
        url = r.get("Destination URL","")
        if url:
            by_creator[name]["seed_urls"].append(url)
            by_creator[name]["seed_labels"][url] = r.get("Link Label","")

    # Inject any manually provided extra seeds
    for name, urls in extra_seeds.items():
        if name in by_creator:
            for u in urls:
                if u not in by_creator[name]["seed_urls"]:
                    by_creator[name]["seed_urls"].append(u)
                    by_creator[name]["seed_labels"][u] = "manual seed"

    all_page_rows = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False, slow_mo=100, executable_path=CHROME_PATH,
            args=["--disable-blink-features=AutomationControlled","--no-sandbox"],
        )
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="en-US", viewport={"width":1280,"height":900},
        )
        pw_page = ctx.new_page()

        # Instagram context is created lazily on first need and reused for the run.
        ig_state = {"ctx": None, "page": None, "status": "unused"}
        ig_meta_rows = []   # per-creator IG discovery results → instagram_meta.csv

        def get_ig():
            """Lazy IG login; reused across creators. Returns ig page or None."""
            if not ENABLE_INSTAGRAM:
                return None
            if ig_state["status"] == "ok":
                return ig_state["page"]
            if ig_state["status"] not in ("unused",):
                return None   # already failed this run — don't hammer login
            igctx, igpage, status = ensure_ig_context(browser)
            ig_state.update(ctx=igctx, page=igpage, status=status)
            return igpage if status == "ok" else None

        for name, info in by_creator.items():
            seeds = info["seed_urls"]
            print(f"\n{'─'*60}")
            print(f"  {name}  ({len(seeds)} seed URL(s))")

            if not seeds:
                print(f"  (no About-page links found — skipping crawl)")
                all_page_rows.append({
                    "Channel Name":   name,
                    "Depth":          0,
                    "Source":         "About page",
                    "Page Type":      "(no links found)",
                    "URL":            info["channel_url"],
                    "Page Title":     "",
                    "Extracted Text": "",
                    "Outbound Links": 0,
                })

            pages = crawl_creator_funnel(name, seeds, pw_page) if seeds else []
            all_page_rows.extend(pages)
            if seeds:
                print(f"  Crawl complete: {len(pages)} page(s) visited")

            # ── Instagram-assisted discovery (gated, secondary) ───────────────
            ig_record = {"Channel Name": name, "Instagram Used": "N",
                         "Profiles Visited": "", "Bio Links Found": "",
                         "Business Accounts Found": "", "Status": "not triggered"}
            need_ig, ig_seed = creator_needs_instagram(seeds, pages)
            if need_ig:
                print(f"  → would be Needs-More-Data; attempting Instagram-assisted discovery")
                ig_page = get_ig()
                if ig_page is None:
                    ig_record.update({"Instagram Used": "Y",
                                      "Status": f"REVIEW_REQUIRED — IG unavailable ({ig_state['status']})"})
                    print(f"  [IG] unavailable ({ig_state['status']}) → REVIEW_REQUIRED")
                else:
                    disc = discover_via_instagram(ig_page, ig_seed, name)
                    ig_record.update({
                        "Instagram Used": "Y",
                        "Profiles Visited": ", ".join("@" + p for p in disc["profiles_visited"]),
                        "Bio Links Found": " | ".join(disc["bio_links"]),
                        "Business Accounts Found": ", ".join("@" + b for b in disc["biz_accounts"]),
                        "Status": disc["status"],
                    })
                    if disc["bio_links"]:
                        print(f"  [IG] {len(disc['bio_links'])} bio link(s) → crawling funnel")
                        extra = crawl_creator_funnel(name, disc["bio_links"], pw_page)
                        for p in extra:
                            p["Source"] = "ig-assisted | " + p.get("Source", "")
                        all_page_rows.extend(extra)
                        print(f"  [IG] funnel crawl added {len(extra)} page(s)")
                    else:
                        print(f"  [IG] no crawlable bio links ({disc['status']})")
            ig_meta_rows.append(ig_record)

            time.sleep(DELAY_BETWEEN_CHANNELS)

        # Close IG context if it was opened
        if ig_state["ctx"] is not None:
            try: ig_state["ctx"].close()
            except Exception: pass
        browser.close()

    fields = ["Channel Name","Depth","Source","Page Type","URL",
              "Page Title","Extracted Text","Outbound Links"]
    with open(STAGE2_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(all_page_rows)

    # Persist per-creator IG discovery metadata for Stage 3
    ig_fields = ["Channel Name","Instagram Used","Profiles Visited",
                 "Bio Links Found","Business Accounts Found","Status"]
    with open(INSTAGRAM_META_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ig_fields)
        w.writeheader(); w.writerows(ig_meta_rows)

    # Persist CAPTCHA-pending pages for a later manual solve + targeted re-run
    captcha_rows = [{"Channel Name": r["Channel Name"], "URL": r["URL"]}
                    for r in all_page_rows if r.get("Page Type") == "CAPTCHA pending"]
    if captcha_rows:
        with open(CAPTCHA_PENDING_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["Channel Name", "URL"])
            w.writeheader(); w.writerows(captcha_rows)

    total_pages   = sum(1 for r in all_page_rows if r["Page Title"])
    total_visited = len(all_page_rows)
    ig_used       = sum(1 for r in ig_meta_rows if r["Instagram Used"] == "Y")
    print(f"\n✓ Stage 2 — {total_visited} pages visited, {total_pages} fetched successfully → {STAGE2_CSV}")
    print(f"  Instagram used for {ig_used} creator(s) → {INSTAGRAM_META_CSV}")
    if captcha_rows:
        print(f"  ⚠ {len(captcha_rows)} CAPTCHA page(s) deferred → {CAPTCHA_PENDING_CSV} "
              f"(solve manually, then re-run those creators)")
    return all_page_rows

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 3 — CREATOR PROFILES
# ══════════════════════════════════════════════════════════════════════════════

def angle_bucket(angle):
    """Collapse a full outreach angle into a coarse classification bucket."""
    a = angle or ""
    if a.startswith("DISQUALIFY"):        return "DISQUALIFIED"
    if a.startswith("SUSPECTED HT"):      return "SUSPECTED HT"
    if a.startswith("ENDPOINT UNCERTAIN"):return "ENDPOINT UNCERTAIN"
    if a.startswith("NEEDS MORE DATA"):   return "NEEDS MORE DATA"
    if a.startswith("QUALIFIED"):         return "QUALIFIED"
    return "REVIEW"


def run_stage3(stage2_rows=None):
    print("\n" + "═"*70)
    print("STAGE 3 — Creator classification")
    print("═"*70 + "\n")

    if stage2_rows is None:
        with open(STAGE2_CSV, newline="", encoding="utf-8") as f:
            stage2_rows = list(csv.DictReader(f))

    # Load Stage 1 for channel metadata (URL, subs, country) since Stage 2
    # rows are crawled pages and may not carry all creator metadata.
    stage1_meta = {}
    email_by_name = {}   # best contact email per creator
    try:
        with open(STAGE1_CSV, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                name = r["Channel Name"]
                if name not in stage1_meta:
                    stage1_meta[name] = {
                        "Channel URL": r["Channel URL"],
                        "Subscribers": r.get("Subscribers",""),
                        "Country":     r.get("Country",""),
                    }
                # Some About-page "links" are actually email addresses
                for e in extract_emails(r.get("Destination URL","")):
                    email_by_name.setdefault(name, e)
    except FileNotFoundError:
        pass

    # Load Instagram-assisted discovery metadata (written by Stage 2), if present
    ig_meta = {}
    try:
        with open(INSTAGRAM_META_CSV, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                ig_meta[r["Channel Name"]] = r
    except FileNotFoundError:
        pass

    # Group Stage 2 rows by creator
    by_creator = defaultdict(list)
    meta       = {}
    for r in stage2_rows:
        name = r["Channel Name"]
        by_creator[name].append(r)
        if name not in meta:
            s1 = stage1_meta.get(name, {})
            meta[name] = {
                "Channel Name": name,
                "Channel URL":  s1.get("Channel URL", r.get("URL","")),
                "Subscribers":  s1.get("Subscribers",""),
                "Country":      s1.get("Country",""),
            }

    # ── Email enrichment ──────────────────────────────────────────────────────
    # 1) YouTube channel descriptions (batched, by existing channel ID — no
    #    re-discovery), 2) crawled page text. Stage-1 bio-link emails already loaded.
    cid_name = [(channel_id_from_url(m["Channel URL"]), n) for n, m in meta.items()]
    cid_name = [(c, n) for c, n in cid_name if c]
    for i in range(0, len(cid_name), 50):
        chunk = cid_name[i:i+50]
        try:
            resp = youtube.channels().list(
                part="snippet", id=",".join(c for c, _ in chunk)).execute()
            desc_by_id = {it["id"]: it["snippet"].get("description", "")
                          for it in resp.get("items", [])}
            for cid, n in chunk:
                if n in email_by_name:
                    continue
                es = extract_emails(desc_by_id.get(cid, ""))
                if es:
                    email_by_name[n] = es[0]
        except Exception as ex:
            print(f"  [email] description lookup failed: {ex}")
    # Page-text fallback for anyone still without an email
    for name, rows in by_creator.items():
        if name in email_by_name:
            continue
        blob = " ".join(r.get("Extracted Text", "") for r in rows)
        es = extract_emails(blob)
        if es:
            email_by_name[name] = es[0]

    out_rows = []
    for name, rows in by_creator.items():
        print(f"  Classifying: {name}")
        classification = classify_creator(name, rows)
        classification["Email"] = email_by_name.get(name, "")

        # ── Instagram-assisted discovery fields ───────────────────────────────
        igm = ig_meta.get(name, {})
        ig_used      = igm.get("Instagram Used", "N")
        ig_status    = igm.get("Status", "")
        ig_pages     = [r for r in rows if "ig-assisted" in (r.get("Source","") or "").lower()]
        ig_assisted  = "Y" if ig_pages else "N"

        prev_class = new_class = ig_evidence = ""
        if ig_assisted == "Y":
            # Recompute what we WOULD have concluded without the IG-discovered pages
            non_ig_rows = [r for r in rows if "ig-assisted" not in (r.get("Source","") or "").lower()]
            prev = classify_creator(name, non_ig_rows) if non_ig_rows else {"Outreach Angle": "NEEDS MORE DATA — no YouTube funnel"}
            prev_class = angle_bucket(prev["Outreach Angle"])
            new_class  = angle_bucket(classification["Outreach Angle"])
            if prev_class != new_class:
                ig_evidence = (f"{classification.get('Highest Offer Type Found','')} "
                               f"({classification.get('Deepest Monetization Layer','')}) "
                               f"via {classification.get('Funnel Path','')[:80]}")

        # REVIEW_REQUIRED override: IG attempted but blocked by a verification wall
        if ig_status.startswith("REVIEW_REQUIRED"):
            classification["Outreach Angle"] = (
                "REVIEW_REQUIRED — Instagram verification wall hit during discovery; "
                "could not retrieve bio funnel. " + ig_status)

        captcha_pending = any(r.get("Page Type") == "CAPTCHA pending" for r in rows)
        classification.update({
            "Captcha Pending":                "Y" if captcha_pending else "N",
            "Instagram Used":                 ig_used,
            "Instagram Profiles Visited":     igm.get("Profiles Visited",""),
            "Instagram Bio Links Found":      igm.get("Bio Links Found",""),
            "Instagram Business Accounts Found": igm.get("Business Accounts Found",""),
            "Instagram Assisted Discovery":   ig_assisted,
            "Previous Classification":        prev_class,
            "New Classification":             new_class,
            "Evidence Found Via Instagram":   ig_evidence,
        })

        row = {**meta[name], **classification}
        out_rows.append(row)
        if ig_used == "Y":
            print(f"    Instagram:     used={ig_used} assisted={ig_assisted} "
                  f"status='{ig_status[:50]}'"
                  + (f"  [{prev_class} → {new_class}]" if ig_evidence else ""))

        # Print a concise summary per creator
        conf      = classification["Data Confidence"]
        mono_conc = classification["Monetization Conclusion"]
        ht        = classification["HT Signals Found"]
        mono      = classification["Existing Monetization"]
        gap       = classification["Monetization Gaps"]
        visited   = classification["Pages Visited"]
        depth     = classification["Max Depth Reached"]
        nav_exp  = classification.get("Nav Explored","?")
        ht_score = classification.get("HT Score", 0)
        ht_level = classification.get("HT Level", "None")
        print(f"    Confidence:    {conf}  ({mono_conc})  [{visited} pages, depth {depth}]  nav={nav_exp}")
        print(f"    Funnel path:   {classification.get('Funnel Path','')[:100]}")
        print(f"    Deepest layer: {classification.get('Deepest Monetization Layer','')}  "
              f"→ {classification.get('Highest Offer Type Found','')} "
              f"(offer conf {classification.get('Highest Offer Confidence','')})")
        print(f"    Endpoint:      conf={classification.get('Endpoint Confidence','')}  "
              f"uncertain={classification.get('Endpoint Uncertain','')}  "
              f"boundary={classification.get('Endpoint Boundary','')}")
        print(f"    HT Score:      {ht_score}  [{ht_level}]")
        print(f"    HT signals:    {ht[:110]}")
        print(f"    Angle:         {classification['Outreach Angle'][:110]}")
        # Evidence: show which pages were visited (NAV-tagged)
        pages_crawled = classification.get("Pages Crawled","")
        if pages_crawled:
            for seg in pages_crawled.split(" | ")[:6]:
                print(f"      {seg}")
        print()

    fields = [
        "Channel Name","Channel URL","Subscribers","Country","Email",
        "Data Confidence","Data Sufficiency Notes","Nav Explored",
        "Pages Visited","Max Depth Reached","Pages Fetched OK",
        "Monetization Conclusion",
        "Deepest Monetization Layer","Funnel Path","Highest Offer Type Found",
        "Highest Offer Confidence","Endpoint Confidence","Endpoint Uncertain",
        "Endpoint Boundary","Lead Magnet Present (Y/N)","Opt-in Form Crossed",
        "HT Score","HT Level",
        "Coaching Present","Mentorship Present","Community Present",
        "Course Present","Newsletter Present","Lead Magnet Present",
        "Book A Call Present","Application Funnel Present",
        "HT Signals Found","Existing Monetization","Funnel Maturity",
        "Monetization Gaps","Outreach Angle","Captcha Pending",
        "Instagram Used","Instagram Profiles Visited","Instagram Bio Links Found",
        "Instagram Business Accounts Found","Instagram Assisted Discovery",
        "Previous Classification","New Classification","Evidence Found Via Instagram",
        "Pages Crawled",
    ]
    with open(STAGE3_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(out_rows)

    disqualified   = sum(1 for r in out_rows if r["Outreach Angle"].startswith("DISQUALIFY"))
    suspected_ht   = sum(1 for r in out_rows if r["Outreach Angle"].startswith("SUSPECTED HT"))
    ep_uncertain   = sum(1 for r in out_rows if r["Outreach Angle"].startswith("ENDPOINT UNCERTAIN"))
    needs_data     = sum(1 for r in out_rows if r["Outreach Angle"].startswith("NEEDS MORE DATA"))
    qualified      = len(out_rows) - disqualified - suspected_ht - ep_uncertain - needs_data
    high_conf      = sum(1 for r in out_rows if r["Data Confidence"] == "High")
    med_conf       = sum(1 for r in out_rows if r["Data Confidence"] == "Medium")
    low_conf       = sum(1 for r in out_rows if r["Data Confidence"] == "Low")
    ht_high        = sum(1 for r in out_rows if r.get("HT Level") == "High")
    ht_med         = sum(1 for r in out_rows if r.get("HT Level") == "Medium")
    print(f"✓ Stage 3 — {qualified} qualified leads, {disqualified} disqualified, "
          f"{suspected_ht} suspected HT, {ep_uncertain} endpoint-uncertain, "
          f"{needs_data} need more data → {STAGE3_CSV}")
    print(f"  Confidence breakdown: High={high_conf}  Medium={med_conf}  Low={low_conf}")
    print(f"  HT score breakdown:   High={ht_high}  Medium={ht_med}")
    return out_rows

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 4 — ICP SCORING
# ══════════════════════════════════════════════════════════════════════════════
#
# Scores the QUALIFIED leads from Stage 3 (0–100) on how good a target they are
# for a high-ticket-backend offer. The ICP: a personal brand with proven demand
# (they already sell a low/mid-ticket product) but NO high-ticket monetization —
# i.e. money visibly left on the table. Score rewards audience, proven buyers,
# the size of the backend gap, and an existing email asset; then discounts for
# weak data / endpoint certainty so a thinly-verified lead never scores like a
# fully-verified one.
#
# Only QUALIFIED leads are scored. Disqualified / suspected-HT / endpoint-uncertain
# / needs-data rows are passed through with a status and no score.

STAGE4_CSV = "stage4_scored_v1.csv"

# Confidence → multiplier (applied to the raw score)
CONF_FACTOR = {"High": 1.0, "Medium": 0.82, "Low": 0.6, "": 0.7}

def _subs_points(subs):
    """Audience / attention — up to 30 pts."""
    try:
        n = int(subs)
    except (ValueError, TypeError):
        return 12, "unknown audience"
    if   n >= 1_000_000: return 30, f"{n:,} subs (massive reach)"
    elif n >=   500_000: return 27, f"{n:,} subs (very large)"
    elif n >=   200_000: return 23, f"{n:,} subs (large)"
    elif n >=   100_000: return 19, f"{n:,} subs (strong)"
    elif n >=    50_000: return 15, f"{n:,} subs (solid)"
    elif n >=    10_000: return 10, f"{n:,} subs (growing)"
    else:                return 6,  f"{n:,} subs (small)"


def score_lead(row):
    """
    Score one Stage 3 row. Returns dict with ICP Score, Lead Tier, and the
    explanation fields. Non-qualified rows return status-only (no score).
    """
    angle = row.get("Outreach Angle", "")
    # Pass-through buckets — not scored
    if angle.startswith("DISQUALIFY"):
        status = "DISQUALIFIED — HT backend present"
    elif angle.startswith("SUSPECTED HT"):
        status = "NOT SCORED — suspected HT, manual review"
    elif angle.startswith("ENDPOINT UNCERTAIN"):
        status = "NOT SCORED — endpoint uncertain, manual review"
    elif angle.startswith("NEEDS MORE DATA"):
        status = "NOT SCORED — insufficient data"
    elif angle.startswith("REVIEW_REQUIRED"):
        status = "NOT SCORED — REVIEW_REQUIRED (Instagram verification wall)"
    else:
        status = "SCORED"

    if status != "SCORED":
        return {
            "ICP Score": "", "Lead Tier": "", "Scoring Status": status,
            "Why Qualified": "", "Existing Offers": "", "Communities Found": "",
            "Funnel Weaknesses": "", "Recommended Outreach Angle": angle,
        }

    Y = lambda k: row.get(k, "N") == "Y"
    offer_type   = row.get("Highest Offer Type Found", "None Found")
    deepest      = row.get("Deepest Monetization Layer", "")
    data_conf    = row.get("Data Confidence", "")
    ep_conf      = row.get("Endpoint Confidence", "")
    funnel_path  = row.get("Funnel Path", "")

    # Reconcile legacy Y/N booleans with the (more thorough) funnel-depth analyzer.
    # The funnel path / deepest layer can reveal offers the keyword matrix missed.
    fp_blob       = (funnel_path + " " + deepest).lower()
    has_community = Y("Community Present") or "community" in fp_blob
    has_course    = (Y("Course Present") or "course" in fp_blob
                     or "digital product" in fp_blob)
    has_membership= "membership" in fp_blob or "subscription" in fp_blob
    has_email     = (Y("Newsletter Present") or Y("Lead Magnet Present")
                     or Y("Lead Magnet Present (Y/N)"))
    has_newsletter= Y("Newsletter Present")

    reasons      = []
    score        = 0

    # 1. Audience / attention (0–30)
    pts, why = _subs_points(row.get("Subscribers", ""))
    score += pts
    reasons.append(why)

    # 2. Proven demand — do they already sell a paid product? (0–30)
    if offer_type == "Mid Ticket":
        score += 30; reasons.append(f"sells a mid-ticket product ({deepest}) — proven buyers")
    elif offer_type == "Low Ticket":
        score += 24; reasons.append(f"sells a low-ticket product ({deepest}) — proven buyers")
    elif offer_type == "Lead Magnet Only":
        score += 10; reasons.append("lead magnet only — demand implied but no confirmed paid sale")
    else:
        score += 4;  reasons.append("no confirmed paid offer")

    # 3. Backend gap — how much is left on the table? (0–25)
    has_paid = offer_type in ("Low Ticket", "Mid Ticket")
    if has_paid and has_community:
        score += 25; reasons.append("paid product + engaged community but NO high-ticket backend — large gap")
    elif has_paid:
        score += 19; reasons.append("paid product but no high-ticket backend above it")
    elif has_email:
        score += 10; reasons.append("capturing leads with no paid backend")
    else:
        score += 4

    # 4. Email / nurture asset (0–15)
    if has_newsletter:
        score += 15; reasons.append("has an email list / newsletter to nurture")
    elif has_email:
        score += 10; reasons.append("has a lead magnet capturing emails")
    else:
        score += 3

    # Confidence discount — weak data or unverifiable endpoint shouldn't score full
    factor = min(CONF_FACTOR.get(data_conf, 0.7), CONF_FACTOR.get(ep_conf, 0.7))
    final  = round(min(score, 100) * factor)

    # Lead tier
    if   final >= 75: tier = "A — Hot"
    elif final >= 60: tier = "B — Warm"
    elif final >= 45: tier = "C — Cool"
    else:             tier = "D — Marginal"

    # Existing offers / communities / weaknesses — funnel-aware
    offers = []
    if has_course:      offers.append("Course/Digital Product")
    if has_membership:  offers.append("Membership/Subscription")
    if has_community:   offers.append("Community")
    if has_newsletter:  offers.append("Newsletter")
    if Y("Lead Magnet Present") or Y("Lead Magnet Present (Y/N)"): offers.append("Lead Magnet")
    # Ensure the deepest paid layer is represented even if unmatched above
    if has_paid and not (has_course or has_membership or has_community):
        offers.append(deepest)
    communities = ("Yes — " + deepest) if has_community else "None detected"

    weaknesses = []
    weaknesses.append("No high-ticket backend (the core opportunity)")
    if has_paid and not has_community:
        weaknesses.append("No community to retain buyers")
    if not has_newsletter:
        weaknesses.append("No ongoing newsletter nurture beyond lead capture"
                          if has_email else "No email capture at all")
    if ep_conf != "High":
        weaknesses.append(f"Endpoint only {ep_conf}-confidence — verify funnel manually")
    if data_conf != "High":
        weaknesses.append(f"Data {data_conf}-confidence — partial crawl coverage")

    return {
        "ICP Score":                  final,
        "Lead Tier":                  tier,
        "Scoring Status":             status,
        "Why Qualified":              "; ".join(reasons),
        "Existing Offers":            ", ".join(offers) if offers else "None confirmed",
        "Communities Found":          communities,
        "Funnel Weaknesses":          " | ".join(weaknesses) if weaknesses else "None — clean profile",
        "Recommended Outreach Angle": angle,
    }


def run_stage4(stage3_rows=None):
    print("\n" + "═"*70)
    print("STAGE 4 — ICP scoring")
    print("═"*70 + "\n")

    if stage3_rows is None:
        with open(STAGE3_CSV, newline="", encoding="utf-8") as f:
            stage3_rows = list(csv.DictReader(f))

    scored = []
    for row in stage3_rows:
        s = score_lead(row)
        merged = {
            "Channel Name":  row.get("Channel Name",""),
            "Channel URL":   row.get("Channel URL",""),
            "Subscribers":   row.get("Subscribers",""),
            "Country":       row.get("Country",""),
            "Funnel Path":   row.get("Funnel Path",""),
            "Highest Offer Type Found": row.get("Highest Offer Type Found",""),
            "Data Confidence":    row.get("Data Confidence",""),
            "Endpoint Confidence":row.get("Endpoint Confidence",""),
            **s,
        }
        scored.append(merged)

    # Rank: scored leads by score desc, then everyone else
    scored_leads = [r for r in scored if r["Scoring Status"] == "SCORED"]
    others       = [r for r in scored if r["Scoring Status"] != "SCORED"]
    scored_leads.sort(key=lambda r: r["ICP Score"], reverse=True)
    ranked = scored_leads + others

    print(f"  {'#':<3}{'Lead':<30}{'Score':<7}{'Tier':<14}{'Offer':<12}{'Status'}")
    print("  " + "─"*88)
    for i, r in enumerate(ranked, 1):
        if r["Scoring Status"] == "SCORED":
            print(f"  {i:<3}{r['Channel Name'][:28]:<30}{r['ICP Score']:<7}"
                  f"{r['Lead Tier']:<14}{r['Highest Offer Type Found']:<12}SCORED")
        else:
            print(f"  {'-':<3}{r['Channel Name'][:28]:<30}{'—':<7}{'—':<14}"
                  f"{r['Highest Offer Type Found'][:10]:<12}{r['Scoring Status']}")

    print()
    for r in scored_leads:
        print(f"  ▸ {r['Channel Name']}  —  {r['ICP Score']}/100  ({r['Lead Tier']})")
        print(f"      Why:        {r['Why Qualified']}")
        print(f"      Offers:     {r['Existing Offers']}")
        print(f"      Weaknesses: {r['Funnel Weaknesses']}")
        print(f"      Angle:      {r['Recommended Outreach Angle'][:110]}")
        print()

    fields = [
        "Channel Name","Channel URL","Subscribers","Country",
        "ICP Score","Lead Tier","Scoring Status",
        "Highest Offer Type Found","Funnel Path",
        "Why Qualified","Existing Offers","Communities Found",
        "Funnel Weaknesses","Recommended Outreach Angle",
        "Data Confidence","Endpoint Confidence",
    ]
    with open(STAGE4_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(ranked)

    print(f"✓ Stage 4 — {len(scored_leads)} leads scored "
          f"({len(others)} passed through unscored) → {STAGE4_CSV}")
    return ranked

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 5 — TWO-SHEET ROUTING (Approved / Manual Review)
# ══════════════════════════════════════════════════════════════════════════════
#
# Conservative router. Every creator lands in exactly one of two sheets; there is
# NO rejected sheet. Bias is toward MANUAL_REVIEW — we would rather hand-check 20
# extra creators than send outreach to someone already running a mature HT backend.

APPROVED_CSV      = "APPROVED_FOR_OUTREACH.csv"
MANUAL_REVIEW_CSV = "MANUAL_REVIEW.csv"

_RATING_ORDER = ["D", "C", "B", "A", "S"]   # ascending

def _rating_cap(letter, ceiling):
    """Lower `letter` to at most `ceiling` (never raises it)."""
    return _RATING_ORDER[min(_RATING_ORDER.index(letter), _RATING_ORDER.index(ceiling))]

def _subs_int(v):
    try:    return int(v)
    except (TypeError, ValueError): return 0

def _is_approved(row):
    """Strict gate. ALL conditions must hold, incl. an available email."""
    # HT Level == "None" + the QUALIFIED bucket already encode the tier-based
    # "no mature HT backend" verdict (price + sales structure). We deliberately do
    # NOT re-gate on the loose legacy Coaching/Application booleans — a priced
    # low-ticket "coaching" offer is a valid prospect, not a disqualifier.
    return (
        angle_bucket(row.get("Outreach Angle","")) == "QUALIFIED"
        and row.get("Data Confidence")        == "High"
        and row.get("Endpoint Confidence")    == "High"
        and row.get("Endpoint Uncertain","N") == "N"
        and row.get("HT Level","None")        == "None"
        and row.get("Captcha Pending","N")    == "N"   # unresolved CAPTCHA → can't fully verify
        and row.get("Highest Offer Type Found","") in ("Low Ticket", "Mid Ticket")
        and bool((row.get("Email","") or "").strip())
    )

def _attractiveness(row):
    """Outreach attractiveness score (independent of crawl confidence)."""
    subs = _subs_int(row.get("Subscribers"))
    if   subs >= 1_000_000: s = 40
    elif subs >=   500_000: s = 34
    elif subs >=   200_000: s = 27
    elif subs >=   100_000: s = 21
    elif subs >=    50_000: s = 15
    elif subs >=    10_000: s = 9
    else:                   s = 4
    ot = row.get("Highest Offer Type Found","")
    b = {"Mid Ticket":28, "Low Ticket":22, "Lead Magnet Only":10}.get(ot, 0)
    g = {"None":24, "Low":14, "Medium":4, "High":0}.get(row.get("HT Level","None"), 0)
    return s + b + g

def _rating(row):
    """S–D rating reflecting outreach attractiveness, capped by verification state."""
    attr = _attractiveness(row)
    if   attr >= 72: letter = "S"
    elif attr >= 56: letter = "A"
    elif attr >= 40: letter = "B"
    elif attr >= 24: letter = "C"
    else:            letter = "D"

    ht   = row.get("HT Level","None")
    dc   = row.get("Data Confidence","")
    ec   = row.get("Endpoint Confidence","")
    bkt  = angle_bucket(row.get("Outreach Angle",""))

    # HT presence makes a lead progressively less attractive for outreach
    if ht == "High" or bkt == "DISQUALIFIED":
        return "D"                          # confirmed HT backend — not an outreach target
    if ht == "Medium" or bkt == "SUSPECTED HT":
        letter = _rating_cap(letter, "C")
    elif ht == "Low":
        letter = _rating_cap(letter, "A")   # weak/ambiguous HT — verify before outreach

    # Verification state caps attractiveness
    if bkt == "NEEDS MORE DATA" or dc == "Low":
        letter = _rating_cap(letter, "C")
    if (dc == "Medium" or ec in ("Low","Medium")
            or row.get("Endpoint Uncertain","N") == "Y"):
        letter = _rating_cap(letter, "B")
    return letter

def _approved_note(row):
    has_comm = (row.get("Community Present")=="Y"
                or "community" in (row.get("Funnel Path","")+row.get("Deepest Monetization Layer","")).lower())
    has_lm   = row.get("Lead Magnet Present (Y/N)")=="Y"
    ot       = row.get("Highest Offer Type Found","")
    big_aud  = _subs_int(row.get("Subscribers")) >= 500_000
    if has_comm:
        return "Community + course, no coaching detected — proven buyers, no ascension model"
    if has_lm:
        return f"Lead magnet funnels into {ot.lower()} offer, no HT backend found"
    if big_aud:
        return "Large audience, low-ticket monetization only, no HT backend found"
    return f"{ot} only, no HT backend found — proven buyers, no ascension model"

def _review_note(row):
    reasons = []
    if row.get("Captcha Pending","N") == "Y":
        reasons.append("reCAPTCHA blocked part of funnel — solve manually then re-run")
    bkt = angle_bucket(row.get("Outreach Angle",""))
    if bkt == "DISQUALIFIED":
        reasons.append(f"HT backend detected ({row.get('Deepest Monetization Layer','')}) — exclude from outreach")
    elif bkt == "SUSPECTED HT":
        reasons.append("suspected HT signals, not confirmed")
    elif bkt == "ENDPOINT UNCERTAIN":
        reasons.append(f"endpoint uncertain — {row.get('Endpoint Boundary','')}")
    elif bkt == "NEEDS MORE DATA":
        reasons.append("insufficient crawl data")
    if not (row.get("Email","") or "").strip():
        reasons.append("missing contact email")
    dc = row.get("Data Confidence","")
    if dc in ("Medium","Low"):
        reasons.append(f"{dc.lower()} data confidence")
    ec = row.get("Endpoint Confidence","")
    if ec == "Low":
        reasons.append(f"crawl hit {row.get('Endpoint Boundary','a gate')}")
    elif ec == "Medium":
        reasons.append("partial funnel coverage")
    ht = row.get("HT Level","None")
    if ht == "Low":
        reasons.append("weak/ambiguous HT signal — verify")
    if row.get("Instagram Used")=="Y" and row.get("Instagram Assisted Discovery")=="N":
        reasons.append("Instagram-assisted discovery incomplete")
    if not reasons:
        reasons.append("not confidently approved — verify funnel")
    # Lead with the positive when the creator is otherwise attractive
    ot = row.get("Highest Offer Type Found","")
    if ot in ("Low Ticket","Mid Ticket") and bkt not in ("DISQUALIFIED",):
        reasons.insert(0, f"{ot} offer, no confirmed HT")
    return "; ".join(reasons)


def build_outreach_sheets(stage3_rows=None):
    print("\n" + "═"*70)
    print("STAGE 5 — Outreach routing (Approved / Manual Review)")
    print("═"*70 + "\n")

    if stage3_rows is None:
        with open(STAGE3_CSV, newline="", encoding="utf-8") as f:
            stage3_rows = list(csv.DictReader(f))

    approved, review, removed = [], [], 0
    for row in stage3_rows:
        # Disqualified leads (confirmed HT backend) are dropped entirely — they
        # never enter either sheet. (Suspected/weak HT stays in MANUAL_REVIEW.)
        if angle_bucket(row.get("Outreach Angle","")) == "DISQUALIFIED":
            removed += 1
            continue
        email = (row.get("Email","") or "").strip()
        common = {
            "Channel Name":   row.get("Channel Name",""),
            "Subscribers":    row.get("Subscribers",""),
            "Email":          email,
            "Channel Link":   row.get("Channel URL",""),
            "Outreach Angle": row.get("Outreach Angle",""),
        }
        if _is_approved(row):
            approved.append({**common,
                "Notes": _approved_note(row),
                "_attr": _attractiveness(row),
                "_conf": row.get("Data Confidence",""),
            })
        else:
            review.append({**common,
                "Confidence": row.get("Data Confidence",""),
                "Rating":     _rating(row),
                "Notes":      _review_note(row),
                "_attr": _attractiveness(row),
            })

    # Sort APPROVED by attractiveness, subs, confidence
    conf_rank = {"High":3, "Medium":2, "Low":1, "":0}
    approved.sort(key=lambda r: (r["_attr"], _subs_int(r["Subscribers"]),
                                 conf_rank.get(r["_conf"],0)), reverse=True)
    # Sort MANUAL_REVIEW by rating, subs, confidence
    review.sort(key=lambda r: (_RATING_ORDER.index(r["Rating"]),
                               _subs_int(r["Subscribers"]),
                               conf_rank.get(r["Confidence"],0)), reverse=True)

    def _safe_write_csv(path, fields, data):
        """Write CSV; if the file is open in Excel (locked), fall back to <name>.new.csv."""
        target = path
        try:
            f = open(path, "w", newline="", encoding="utf-8")
        except PermissionError:
            target = path.replace(".csv", ".new.csv")
            print(f"  ⚠ {path} is open (Excel?) — writing to {target} instead. "
                  f"Close the file and re-run to refresh the original.")
            f = open(target, "w", newline="", encoding="utf-8")
        with f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader(); w.writerows(data)
        return target

    ap_fields = ["Channel Name","Subscribers","Email","Channel Link","Outreach Angle","Notes"]
    _safe_write_csv(APPROVED_CSV, ap_fields, approved)
    mr_fields = ["Channel Name","Subscribers","Email","Channel Link",
                 "Confidence","Rating","Outreach Angle","Notes"]
    _safe_write_csv(MANUAL_REVIEW_CSV, mr_fields, review)

    # ── Summary report ────────────────────────────────────────────────────────
    rc = {ltr: sum(1 for r in review if r["Rating"]==ltr) for ltr in _RATING_ORDER}
    print(f"  Creators scanned:        {len(stage3_rows)}")
    print(f"  Disqualified (removed):  {removed}  (confirmed HT backend — dropped from pipeline)")
    print(f"  Approved for outreach:   {len(approved)}  → {APPROVED_CSV}")
    print(f"  Manual review required:  {len(review)}  → {MANUAL_REVIEW_CSV}")
    print(f"    S-rated: {rc['S']}   A-rated: {rc['A']}   B-rated: {rc['B']}   "
          f"C-rated: {rc['C']}   D-rated: {rc['D']}")
    print()
    if approved:
        print("  APPROVED:")
        for r in approved:
            print(f"    ✓ {r['Channel Name'][:30]:<30} {_subs_int(r['Subscribers']):>9,} subs  "
                  f"{r['Email'] or '(no email)'}")
            print(f"        {r['Notes']}")
    print()
    print("  MANUAL REVIEW (top of list):")
    for r in review[:12]:
        print(f"    [{r['Rating']}] {r['Channel Name'][:28]:<28} {_subs_int(r['Subscribers']):>9,}  "
              f"{r['Confidence']:<7} {r['Notes'][:60]}")

    return approved, review

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-stage", type=int, default=1,
                        help="Resume from stage (1=full, 2=skip discovery, 3=skip fetching, "
                             "4=score+route only, 5=route only)")
    args = parser.parse_args()

    t0 = time.time()

    if args.from_stage <= 1:
        stage1_rows = run_stage1()
    elif args.from_stage <= 3:
        print(f"Skipping Stage 1 — loading {STAGE1_CSV}")
        with open(STAGE1_CSV, newline="", encoding="utf-8") as f:
            stage1_rows = list(csv.DictReader(f))

    if args.from_stage <= 2:
        stage2_rows = run_stage2(stage1_rows)
    elif args.from_stage <= 3:
        print(f"Skipping Stage 2 — loading {STAGE2_CSV}")
        with open(STAGE2_CSV, newline="", encoding="utf-8") as f:
            stage2_rows = list(csv.DictReader(f))

    if args.from_stage <= 3:
        stage3_rows = run_stage3(stage2_rows)
    else:
        print(f"Skipping Stages 1-3 — loading {STAGE3_CSV}")
        with open(STAGE3_CSV, newline="", encoding="utf-8") as f:
            stage3_rows = list(csv.DictReader(f))

    if args.from_stage <= 4:
        run_stage4(stage3_rows)                 # ICP scoring (internal artifact)
    approved, review = build_outreach_sheets(stage3_rows)   # final two-sheet output

    elapsed = (time.time()-t0)/60
    print(f"\n{'═'*70}")
    print(f"Pipeline complete in {elapsed:.1f} min")
    print(f"  {STAGE3_CSV} — creator profiles (full detail)")
    print(f"  {APPROVED_CSV} — {len(approved)} ready for outreach")
    print(f"  {MANUAL_REVIEW_CSV} — {len(review)} need a human look")
    print(f"{'═'*70}")
