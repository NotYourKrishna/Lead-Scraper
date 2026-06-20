"""
Proof-of-concept: Extract external links + labels from YouTube About pages using Playwright.
Tests 3 known channels. Does NOT score or qualify. Just proves link extraction works.
"""

import csv
import time
import sys
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

sys.stdout.reconfigure(encoding="utf-8")

TEST_CHANNELS = [
    {"name": "Jordan Welch",      "url": "https://www.youtube.com/@JordanWelch/about"},
    {"name": "Davie Fogarty",     "url": "https://www.youtube.com/@DavieFogarty/about"},
    {"name": "Baddie In Business","url": "https://www.youtube.com/@BaddieinBusiness/about"},
]

def dismiss_consent(page):
    """Dismiss cookie/consent dialogs if present (EU regions)."""
    try:
        btn = page.locator("button:has-text('Accept all'), button:has-text('Reject all'), button:has-text('Accept & continue')")
        if btn.count() > 0:
            btn.first.click()
            page.wait_for_timeout(1000)
    except Exception:
        pass


def extract_links(page, channel_name, channel_url):
    """
    Navigate to the About page and extract external links + their display labels.
    Returns a list of {"label": ..., "url": ...} dicts.
    """
    print(f"\n{'='*60}")
    print(f"Channel: {channel_name}")
    print(f"URL:     {channel_url}")

    try:
        page.goto(channel_url, wait_until="domcontentloaded", timeout=30000)
        dismiss_consent(page)

        # Wait for the page to settle — YouTube is a heavy SPA
        page.wait_for_timeout(4000)

        # --- Strategy 1: look for the dedicated links container ---
        # YouTube renders About-tab links inside an element with id="links-section"
        # or inside a yt-channel-external-link-view-model component.
        # Try several selectors in order of specificity.

        selectors_to_try = [
            # Current (2024-2025) YouTube DOM: each link is a yt-channel-external-link-view-model
            "yt-channel-external-link-view-model",
            # Older layout: links inside #links-section
            "#links-section a[href]",
            # Generic: any anchor inside the about/links area
            "ytd-channel-external-link-renderer",
            # Last resort: all anchors in the about container
            "#about a[href]",
        ]

        results = []

        for selector in selectors_to_try:
            elements = page.locator(selector)
            count = elements.count()
            print(f"  Selector '{selector}': {count} match(es)")

            if count > 0:
                for i in range(count):
                    el = elements.nth(i)
                    # Try to get the label (display text above/beside the link)
                    label = el.inner_text().strip()
                    # Try to get the href from an anchor inside (or the element itself)
                    link_el = el.locator("a[href]")
                    if link_el.count() > 0:
                        href = link_el.first.get_attribute("href") or ""
                    else:
                        href = el.get_attribute("href") or ""
                    # YouTube wraps external links through a redirect; unwrap it
                    if "youtube.com/redirect" in href:
                        import re
                        match = re.search(r"[?&]q=([^&]+)", href)
                        if match:
                            from urllib.parse import unquote
                            href = unquote(match.group(1))
                    if href and not href.startswith("javascript"):
                        results.append({"label": label, "url": href})
                        print(f"    FOUND: [{label}] -> {href}")

                if results:
                    break  # found with this selector, stop trying

        if not results:
            print("  NO LINKS FOUND with any selector.")
            # Dump a snippet of the page HTML so we can inspect what IS there
            html_snippet = page.content()[:3000]
            print(f"  --- PAGE HTML SNIPPET (first 3000 chars) ---")
            print(html_snippet)

        return results

    except PWTimeout:
        print(f"  TIMEOUT loading {channel_url}")
        return []
    except Exception as e:
        print(f"  ERROR: {e}")
        return []


def run_poc():
    all_rows = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,   # visible browser — helps avoid bot detection for POC
            slow_mo=200,      # 200ms between actions, more human-like
            executable_path=r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ]
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()

        # Warm up: visit YouTube home first so we don't start cold on an About page
        print("Warming up browser on youtube.com ...")
        page.goto("https://www.youtube.com", wait_until="domcontentloaded", timeout=20000)
        dismiss_consent(page)
        page.wait_for_timeout(2000)

        for ch in TEST_CHANNELS:
            links = extract_links(page, ch["name"], ch["url"])
            for link in links:
                all_rows.append({
                    "Channel": ch["name"],
                    "Label": link["label"],
                    "URL": link["url"],
                })
            # Polite delay between channels
            time.sleep(3)

        browser.close()

    # Output
    output = "poc_links_output.csv"
    with open(output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Channel", "Label", "URL"])
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\n{'='*60}")
    print(f"RESULT: {len(all_rows)} links extracted across {len(TEST_CHANNELS)} channels")
    print(f"Saved to {output}")
    print()
    for row in all_rows:
        print(f"  [{row['Channel']}] {row['Label']} -> {row['URL']}")


if __name__ == "__main__":
    run_poc()
