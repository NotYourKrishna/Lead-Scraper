---
name: active-creator-last-longform
description: ACTIVITY is the
metadata: 
  node_type: memory
  type: project
  originSessionId: 76206b37-b278-4fea-ba12-29b9b285fe92
---

**Activity is the absolute FIRST priority for selling HT** (operator, 2026-06-22).
Before evaluating offers/funnel, a creator must be ACTIVE — a dormant audience
cannot be sold a high-ticket offer. Inactive everywhere → DQ.

**How to measure activity (in order):**
1. **YouTube — LONG-FORM only.** Recent meaningful long-form video = active. **Shorts
   do NOT count** on YouTube. Why: in this niche you can't build community off YT
   Shorts — YouTube is primarily a long-form platform, so YT activity must be measured
   by long-form. (The pipeline's `get_upload_cadence` currently counts the most recent
   upload of ANY type, so a recent Short wrongly marks a dead channel active — bug.)
2. **If YT long-form is stale, check Instagram / TikTok** (when their links appear in
   the YT bio or video descriptions). IG and TikTok are different ecosystems —
   short-form IS the native content there, so activity counts. **Active on IG/TikTok =
   last post < 1 month ago AND ≤ ~1 week between posts.** If they meet that, classify
   the creator as ACTIVE even if YouTube long-form is stale (some creators are just
   more active off-YT).
3. Active on ANY of the above → passes the activity gate. Active nowhere → DQ.

**Evidence:** Girls Gone Strong (YT last 15 uploads all Shorts; long-form ~10mo dark),
Prosper (last long-form 2025-09-01), Women's Fitness Academy (last long-form ~1yr; DQ
for inactivity AND brand-persona). Implementation: define last-meaningful-YT-upload =
most recent video with `contentDetails.duration` > ~180s; add IG/TikTok recency checks
from bio/description links. Relates to [[pipeline-evolution-report]].
