"""
Instagram extraction diagnostic — reuses the saved session (ig_session.json) and
dumps everything we can see on @jordanwelch's profile, so we can fix tagged-account
+ bio-link extraction without re-running the whole pipeline.
"""
import re, sys, time
sys.stdout.reconfigure(encoding="utf-8")

from playwright.sync_api import sync_playwright
import pipeline as P

HANDLE = sys.argv[1] if len(sys.argv) > 1 else "jordanwelch"

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False, slow_mo=120, executable_path=P.CHROME_PATH,
        args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
    )
    ctx, page, status = P.ensure_ig_context(browser)
    print(f"\n=== IG session status: {status} ===")
    if status != "ok":
        print("Cannot proceed without a logged-in session.")
        browser.close(); sys.exit(1)

    url = f"https://www.instagram.com/{HANDLE}/"
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(5000)

    print(f"\n=== URL after load: {page.url}")

    # 1. header inner_text (what we currently parse)
    for sel in ("header section", "header", "main"):
        try:
            t = page.locator(sel).first.inner_text(timeout=4000)
            print(f"\n--- inner_text('{sel}') [{len(t)} chars] ---\n{t[:900]}")
        except Exception as e:
            print(f"\n--- inner_text('{sel}') FAILED: {e}")

    # 2. all header anchors
    for sel in ("header a[href]", "main a[href]"):
        try:
            hrefs = page.eval_on_selector_all(sel, "els => els.map(e => e.href || e.getAttribute('href'))")
            print(f"\n--- anchors '{sel}' [{len(hrefs)}] ---")
            for h in hrefs[:40]:
                print(f"    {h}")
        except Exception as e:
            print(f"\n--- anchors '{sel}' FAILED: {e}")

    # 3. page HTML regex for embedded profile JSON
    html = page.content()
    for key in ("external_url", "biography", "external_lynx_url", "bio_links"):
        m = re.search(rf'"{key}":\s*"((?:[^"\\]|\\.)*)"', html)
        if m:
            print(f"\n--- JSON '{key}': {m.group(1)[:200]}")

    # 4. @mentions anywhere in header text
    try:
        htext = page.locator("header").first.inner_text(timeout=4000)
        mentions = re.findall(r"@([A-Za-z0-9_.]{2,})", htext)
        print(f"\n--- @mentions in header text: {mentions}")
    except Exception as e:
        print(f"\n--- mentions FAILED: {e}")

    # 5. is there a 'links' button (multi-link sheet)?
    for label in ("link in bio", "links", "🔗"):
        try:
            cnt = page.locator(f"text=/{label}/i").count()
            print(f"--- '{label}' button count: {cnt}")
        except Exception:
            pass

    print("\n=== Now running discover_via_instagram() ===")
    disc = P.discover_via_instagram(page, url, "Diag")
    print(disc)

    browser.close()
