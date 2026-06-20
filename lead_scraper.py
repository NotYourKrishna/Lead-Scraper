"""
YouTube Lead Scraper for HT Offer Outreach — Stage 1 + light Stage 2
Finds UNDER-monetized creators (attention + trust + demand, but weak HT backend).

Filters:
  - English-language channels only
  - High-income / strong-buying-power markets only (currency, language, country signals)
  - Personal brands (individual people), not companies/platforms
  - EXCLUDES creators already running a mature high-ticket offer
    (mentorship / coaching / work with me / book a call / mastermind / apply)

Then fetches PUBLIC bio-link landing pages (Linktree, Beacons, Stan, website) to
read what offers exist, scores each lead per the qualification doc, and explains why.

NOTE: emails are only taken from text the creator voluntarily publishes (description /
public bio pages). This script does NOT bypass YouTube's "verify you're human" email gate.
"""

import re
import csv
import sys
import time
from datetime import datetime, timedelta, timezone

import requests
from bs4 import BeautifulSoup
from googleapiclient.discovery import build

# Windows console defaults to cp1252 and crashes on ₹ / ₱ etc. Force UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

API_KEY = "AIzaSyBNf47mCW-jkbQ3_GhFpEuoYPQKHDnNKaI"
youtube = build("youtube", "v3", developerKey=API_KEY)

# ---- Config ----
NICHE_QUERY = "dropshipping business"
MIN_SUBS = 500
MAX_DAYS_INACTIVE = 90
MAX_RESULTS = 50
FETCH_BIO_PAGES = True       # fetch public bio-link landing pages to inspect offers
MAX_LINKS_TO_FETCH = 5       # per channel, to keep it quick
FETCH_TIMEOUT = 8            # seconds per page

EMAIL_REGEX = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
URL_REGEX = r"https?://[^\s\)\]>\"']+"

WEALTH_KEYWORDS = [
    "k/mo", "k a month", "per month", "/month", "side hustle",
    "income", "case study", "made $", "earning", "revenue",
    "6 figures", "7 figures", "passive income", "full time income"
]

# ---- Geography / buying-power signals (skip these markets) ----
HIGH_INCOME_COUNTRIES = {
    "US", "CA", "GB", "AU", "NZ", "IE", "DE", "FR", "NL", "SE", "NO",
    "DK", "FI", "CH", "AT", "BE", "LU", "SG", "AE", "JP", "KR", "IL",
    "IT", "ES", "HK", "TW", "QA",
}
# Currency SYMBOLS are precise — safe to scan even in noisy fetched HTML.
CURRENCY_SYMBOLS = ["₹", "₨", "₦", "₱"]
# Currency/region WORDS — scanned in the channel description only (too noisy in HTML).
# NOTE: "rs." was removed — it false-matches hrs./yrs./errors./minified JS.
CURRENCY_WORDS = [
    " rupee", "rupees", " inr ", " inr.", "naira", " pkr ", " bdt ",
    " taka", " lkr", "magkano", " peso", " pesos",
]
# regional-language words that indicate a non-target audience (description only)
LANGUAGE_RED_FLAGS = [
    "pinoy", "tagalog", "malayalam", "malayali", "telugu", " hindi", " tamil",
    " urdu", "bangla", "kannada", "marathi", " sinhala", "mag-",
]

# ---- Platforms/tools that are NOT personal brands ----
PLATFORM_TITLE_PATTERNS = [
    r"\b(aliexpress|cjdropshipping|alidropship|dsers|zendrop|doba|spocket|oberlo|shopify|autods|salehoo|appscenic)\b",
    r"\b(llc|ltd|inc|corp)\b",
]

# ---- Mature high-ticket / "already selling a service" signals -> EXCLUDE ----
HT_RED_FLAG_KEYWORDS = [
    "mentorship", "mentoring", "1-on-1", "1 on 1", "1:1", "work with me",
    "work with us", "coaching", "coach with", "apply now", "apply to work",
    "apply here", "book a call", "schedule a call", "book a free call",
    "consulting", "consultation", "mastermind", "done-for-you", "done for you",
    "high ticket", "high-ticket",
]
# bio-link domains that strongly imply a direct HT sales/booking funnel
HT_LINK_DOMAINS = ["calendly.com", "cal.com", "tidycal.com", "acuityscheduling.com"]

# ---- Green-flag monetization signals (demand exists, backend may be missing) ----
COMMUNITY_DOMAINS = {
    "skool.com": ("Skool community", 4),
    "whop.com": ("Whop community", 4),
    "circle.so": ("Circle community", 4),
    "discord.gg": ("Discord (free community)", 3),
    "discord.com": ("Discord (free community)", 3),
    "t.me": ("Telegram community", 3),
    "facebook.com/groups": ("Facebook group", 3),
}
COURSE_DOMAINS = {
    "gumroad.com": ("Gumroad product/course", 3),
    "stan.store": ("Stan Store", 3),
    "payhip.com": ("Payhip product", 3),
    "podia.com": ("Podia course", 3),
    "teachable.com": ("Teachable course", 3),
    "thinkific.com": ("Thinkific course", 3),
    "kajabi.com": ("Kajabi product", 3),
}
NEWSLETTER_DOMAINS = {
    "beehiiv.com": ("beehiiv newsletter", 2),
    "substack.com": ("Substack newsletter", 2),
    "convertkit.com": ("ConvertKit list", 2),
    "mailchimp.com": ("Mailchimp list", 2),
}
NEWSLETTER_TEXT_SIGNALS = [
    "newsletter", "free guide", "free ebook", "free e-book", "free training",
    "free download", "lead magnet", "free webinar", "join my email",
    "subscribe to my", "free pdf", "free checklist",
]


def classify_link(url):
    """Return a human-readable label for a URL based on its domain."""
    u = url.lower()
    table = [
        ("linktr.ee", "Linktree"), ("lnktr.ee", "Linktree"), ("beacons.ai", "Beacons"),
        ("stan.store", "Stan Store"), ("calendly.com", "Calendly"), ("cal.com", "Cal.com"),
        ("skool.com", "Skool"), ("whop.com", "Whop"), ("circle.so", "Circle"),
        ("discord", "Discord"), ("t.me", "Telegram"), ("telegram", "Telegram"),
        ("instagram.com", "Instagram"), ("tiktok.com", "TikTok"),
        ("twitter.com", "Twitter/X"), ("x.com", "Twitter/X"),
        ("facebook.com/groups", "Facebook Group"), ("facebook.com", "Facebook"),
        ("whatsapp", "WhatsApp"), ("gumroad.com", "Gumroad"), ("payhip.com", "Payhip"),
        ("patreon.com", "Patreon"), ("ko-fi.com", "Ko-fi"), ("beehiiv.com", "beehiiv"),
        ("substack.com", "Substack"), ("kajabi", "Kajabi"), ("teachable", "Teachable"),
        ("thinkific", "Thinkific"), ("podia.com", "Podia"), ("youtube.com", "YouTube"),
        ("amzn", "Amazon"), ("amazon.", "Amazon"), ("shopify.com", "Shopify"),
    ]
    for needle, label in table:
        if needle in u:
            return f"{label}: {url}"
    return f"Website: {url}"


def is_english_channel(channel_item):
    snippet = channel_item["snippet"]
    default_lang = snippet.get("defaultLanguage", "")
    if default_lang and not default_lang.startswith("en"):
        return False
    description = snippet.get("description", "")
    if description:
        ascii_chars = sum(1 for c in description if ord(c) < 128)
        if len(description) > 20 and ascii_chars / len(description) < 0.7:
            return False
    return True


def passes_geography(country, description):
    """
    Return (ok, reason). Skip low-buying-power markets.
    Runs the full word/symbol/language scan on the DESCRIPTION (clean text) + country code.
    """
    t = description.lower()
    for sym in CURRENCY_SYMBOLS:
        if sym in description:
            return False, f"currency symbol '{sym}'"
    for flag in CURRENCY_WORDS:
        if flag in t:
            return False, f"currency word '{flag.strip()}'"
    for flag in LANGUAGE_RED_FLAGS:
        if flag in t:
            return False, f"language signal '{flag.strip()}'"
    if country and country not in HIGH_INCOME_COUNTRIES:
        return False, f"country '{country}' not a target market"
    return True, ""


def page_has_foreign_currency(page_text):
    """Only scan fetched HTML for precise currency SYMBOLS (words are too noisy here)."""
    for sym in CURRENCY_SYMBOLS:
        if sym in page_text:
            return True, f"currency symbol '{sym}'"
    return False, ""


def is_personal_brand(title, description):
    """Hard-block obvious platforms/companies; pass individual people."""
    title_lower = title.lower()
    desc_lower = description.lower()
    for pattern in PLATFORM_TITLE_PATTERNS:
        if re.search(pattern, title_lower):
            return False
    if re.search(r"^(dropshipping business|dropship store|ecom store|ecommerce store|dropship platform)$", title_lower):
        return False
    corporate_we = ["we give ", "we help ", "we offer ", "we provide ", "we teach ",
                    "we are a ", "we are an ", "our mission is", "our team ", "our company"]
    corp = sum(1 for p in corporate_we if p in desc_lower)
    first_person = len(re.findall(r"\b(i |i'm |i've |i'll |i'd )\b", desc_lower))
    if corp >= 2:
        return False
    if corp >= 1 and first_person == 0 and len(description) > 100:
        return False
    return True


def detect_ht_offer(text, links):
    """Return the first mature-HT signal found, or None. Checks text + link URLs."""
    t = text.lower()
    for kw in HT_RED_FLAG_KEYWORDS:
        if kw in t:
            return f"keyword '{kw}'"
    for url in links:
        ul = url.lower()
        for kw in HT_RED_FLAG_KEYWORDS:
            if kw.replace(" ", "") in ul.replace("-", "").replace("_", ""):
                return f"link keyword '{kw}'"
        for dom in HT_LINK_DOMAINS:
            if dom in ul:
                return f"booking link ({dom})"
    return None


def score_lead(combined_text, links):
    """Score green-flag monetization signals. Returns (score, reasons[])."""
    score = 0
    reasons = []
    t = combined_text.lower()
    link_blob = " ".join(links).lower()

    def has_domain(domain):
        return domain in link_blob

    for dom, (label, pts) in COMMUNITY_DOMAINS.items():
        if has_domain(dom):
            score += pts
            reasons.append(f"+{pts} {label}")
            break
    for dom, (label, pts) in COURSE_DOMAINS.items():
        if has_domain(dom):
            score += pts
            reasons.append(f"+{pts} {label}")
            break
    newsletter_found = False
    for dom, (label, pts) in NEWSLETTER_DOMAINS.items():
        if has_domain(dom):
            score += pts
            reasons.append(f"+{pts} {label}")
            newsletter_found = True
            break
    if not newsletter_found:
        for sig in NEWSLETTER_TEXT_SIGNALS:
            if sig in t:
                score += 2
                reasons.append(f"+2 lead magnet/newsletter ('{sig}')")
                break
    return score, reasons


def fetch_page_text(url):
    """Fetch a PUBLIC page and return its visible text lowercased, or '' on failure."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; lead-research/1.0)"}
        resp = requests.get(url, headers=headers, timeout=FETCH_TIMEOUT, allow_redirects=True)
        if resp.status_code != 200 or "text/html" not in resp.headers.get("Content-Type", ""):
            return ""
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        return soup.get_text(separator=" ", strip=True)
    except Exception:
        return ""


# ---- YouTube API helpers ----
def search_channels(query, max_results=50):
    channels = []
    resp = youtube.search().list(
        part="snippet", q=query, type="channel",
        maxResults=min(max_results, 50), relevanceLanguage="en"
    ).execute()
    for item in resp.get("items", []):
        channels.append(item["snippet"]["channelId"])
    return channels


def get_channel_details(channel_id):
    resp = youtube.channels().list(
        part="snippet,statistics,contentDetails,brandingSettings", id=channel_id
    ).execute()
    if not resp.get("items"):
        return None
    item = resp["items"][0]
    return {
        "title": item["snippet"]["title"],
        "description": item["snippet"]["description"],
        "country": item["snippet"].get("country", ""),
        "subscriber_count": int(item["statistics"].get("subscriberCount", 0)),
        "uploads_playlist": item["contentDetails"]["relatedPlaylists"]["uploads"],
        "thumbnail": item["snippet"]["thumbnails"]["high"]["url"],
        "channel_url": f"https://www.youtube.com/channel/{channel_id}",
        "_raw_item": item,
    }


def get_latest_upload_date(uploads_playlist_id):
    resp = youtube.playlistItems().list(
        part="contentDetails", playlistId=uploads_playlist_id, maxResults=1
    ).execute()
    if not resp.get("items"):
        return None
    published_at = resp["items"][0]["contentDetails"]["videoPublishedAt"]
    return datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def extract_email(text):
    matches = re.findall(EMAIL_REGEX, text)
    valid = [m for m in matches if not re.search(r"\.(png|jpg|jpeg|gif|webp|svg|mp4|mov)$", m, re.I)]
    return valid[0] if valid else None


def extract_raw_links(text):
    raw = re.findall(URL_REGEX, text)
    return [re.sub(r"[.,;:!?]+$", "", u) for u in raw]


def process_niche(query, min_subs, max_days_inactive, max_results):
    print(f"Searching niche: {query}")
    channel_ids = search_channels(query, max_results)
    print(f"Found {len(channel_ids)} candidate channels\n")

    results = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_days_inactive)
    counts = {"english": 0, "geo": 0, "subs": 0, "inactive": 0, "company": 0, "ht": 0}

    for cid in channel_ids:
        try:
            d = get_channel_details(cid)
            if not d:
                continue
            title = d["title"]

            if not is_english_channel(d["_raw_item"]):
                counts["english"] += 1
                print(f"  skip [non-English]   {title}")
                continue

            geo_ok, geo_reason = passes_geography(d["country"], d["description"])
            if not geo_ok:
                counts["geo"] += 1
                print(f"  skip [geography]     {title}  ({geo_reason})")
                continue

            if d["subscriber_count"] < min_subs:
                counts["subs"] += 1
                continue

            latest = get_latest_upload_date(d["uploads_playlist"])
            if latest is None or latest < cutoff:
                counts["inactive"] += 1
                continue

            if not is_personal_brand(title, d["description"]):
                counts["company"] += 1
                print(f"  skip [company]       {title}")
                continue

            raw_links = extract_raw_links(d["description"])

            # Fetch public bio-link pages to inspect offers (Stage 2-lite)
            page_text = ""
            if FETCH_BIO_PAGES and raw_links:
                for url in raw_links[:MAX_LINKS_TO_FETCH]:
                    page_text += " " + fetch_page_text(url)
                    time.sleep(0.3)

            combined = d["description"] + " " + page_text

            # Re-check geography against fetched page text — symbols only (precise)
            page_foreign, page_reason = page_has_foreign_currency(page_text)
            if page_foreign:
                counts["geo"] += 1
                print(f"  skip [geography*]    {title}  ({page_reason}, from bio page)")
                continue

            # Exclude mature / already-selling HT creators
            ht_signal = detect_ht_offer(combined, raw_links)
            if ht_signal:
                counts["ht"] += 1
                print(f"  skip [sells HT]      {title}  ({ht_signal})")
                continue

            score, reasons = score_lead(combined, raw_links)
            # No HT offer but trust+demand exists = top priority per doc
            score += 5
            reasons.insert(0, "+5 no high-ticket offer detected (monetization gap)")

            email = extract_email(combined)
            labeled = [classify_link(u) for u in raw_links]

            why = "; ".join(reasons)
            notes = []
            if not email:
                notes.append("No plain-text email - check 'About' tab manually")
            wealth = [kw for kw in WEALTH_KEYWORDS if kw in combined.lower()]
            if wealth:
                notes.append(f"Wealth signals: {', '.join(wealth[:4])}")

            results.append({
                "Name": title,
                "Subscribers": d["subscriber_count"],
                "Country": d["country"] or "unknown",
                "Email": email or "",
                "ChannelLink": d["channel_url"],
                "BioLinks": " | ".join(labeled),
                "Score": score,
                "WhyQualified": why,
                "Notes": "; ".join(notes),
            })
            print(f"  ADDED [{score:>2}]         {title} ({d['subscriber_count']:,} subs)")
            time.sleep(0.2)

        except Exception as e:
            print(f"  error {cid}: {e}")
            continue

    print(f"\n--- Filter summary ---")
    print(f"  non-English:   {counts['english']}")
    print(f"  geography:     {counts['geo']}")
    print(f"  low subs:      {counts['subs']}")
    print(f"  inactive:      {counts['inactive']}")
    print(f"  company:       {counts['company']}")
    print(f"  sells HT:      {counts['ht']}")
    print(f"  QUALIFIED:     {len(results)}")
    # sort best-first
    results.sort(key=lambda r: r["Score"], reverse=True)
    return results


if __name__ == "__main__":
    leads = process_niche(NICHE_QUERY, MIN_SUBS, MAX_DAYS_INACTIVE, MAX_RESULTS)

    output_file = "leads_dropshipping_v4.csv"
    fields = ["Name", "Subscribers", "Country", "Email", "ChannelLink",
              "BioLinks", "Score", "WhyQualified", "Notes"]
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(leads)

    print(f"\nDone. {len(leads)} qualified leads saved to {output_file}")
