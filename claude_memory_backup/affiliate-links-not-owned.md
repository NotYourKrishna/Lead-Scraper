---
name: affiliate-links-not-owned
description: URLs containing ?ref= or ?aff= (or similar) are affiliate/referral links — NOT owned by the creator; exclude from offer attribution AND email attribution
metadata: 
  node_type: memory
  type: project
  originSessionId: 76206b37-b278-4fea-ba12-29b9b285fe92
---

Rule (user-taught, 2026-06-21 calibration): a destination URL containing an
affiliate/referral marker — `?ref=`, `&ref=`, `?aff=`, `/?aff=`, `ref=<handle>`,
promo-code params, etc. — points to a product/brand the creator does **not** own.
They earn commission; it is not their offer.

**How to apply:**
- Exclude affiliate-marked pages from OFFER attribution (don't credit their
  prices/tiers to the creator — this is the GORNATION / Calisthenics Reacts bug).
- Exclude affiliate-marked pages from EMAIL attribution (e.g. Bronson Dant's
  `info@inbody.com` reached via `inbody.com/?aff=apextraining` is a third-party
  leak, not his contact).
- Treat as a strong "Partner/Affiliate" ownership signal in [[pipeline-evolution-report]].

Examples: `gornation.com/?ref=calisthenicsreacts` (Cal Reacts), Will Tennyson's
MacroFactor/Gymshark linktree referrals, `inbody.com/?aff=apextraining` (Bronson).
Related: [[no-face-scoring-not-blocking]] (faceless taxonomy).
