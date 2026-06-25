---
name: ig-ht-behind-tagged-accounts
description: "Some creators hide their high-ticket offer behind an Instagram-bio-tagged business account, not their own bio link"
metadata: 
  node_type: memory
  type: project
  originSessionId: 76206b37-b278-4fea-ba12-29b9b285fe92
---

For some target creators, the high-ticket (HT) offer is NOT on their own Instagram profile's bio link — it lives inside one of the **business accounts tagged (@mentioned) in their IG bio**. Confirmed example: **Jordan Welch** — his personal bio link leads nowhere disqualifying, but a tagged account's funnel contains the HT offer.

**Why it matters:** Instagram-assisted discovery must follow tagged business accounts and crawl *their* bio links, not just the creator's primary bio link. Stopping at the personal profile produces a false negative (creator looks like a clean lead when an HT backend actually exists).

**How it works (fixed):** In `ig_extract_profile` (pipeline.py), tagged accounts are parsed from **bio text only** — the embedded JSON `"biography"` field (decoded via `json.loads`, so `@handle` → `@handle`), falling back to `header` inner_text. Do NOT scrape profile anchors for mentions: `main a[href]` is polluted with the "Accounts you might like" suggestion rail, which are not bio tags. Two gotchas learned from live IG DOM: (1) `header section` returns 0 chars — use full `header`; (2) the real external bio link comes from `header a[href]` unwrapped from `l.instagram.com/?u=`.

**Confirmed working:** Jordan Welch's bio tags `@aicomacademy @1800bankroll @2up`; visiting `@aicomacademy` yields bio link `https://www.aicom.co/apply` (an application funnel = HT) → Jordan correctly flips NEEDS MORE DATA → DISQUALIFIED. `MAX_IG_PROFILES_PER_CREATOR=3` (creator + 2 tagged). Diagnostic tool: `ig_diag.py <handle>`. Relates to [[instagram-assisted-discovery]].
