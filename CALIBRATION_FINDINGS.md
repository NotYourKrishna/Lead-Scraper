# Calibration Findings — Run `2026-06-21_144632` (fitness)

> Manual calibration of the pipeline against the operator's ground-truth judgment.
> 15 highest-learning-value creators were hand-reviewed across Approved / Manual
> Review / Disqualified. This document logs every confirmed false positive and
> false negative and the bugs they exposed. Rules derived here live in
> BUSINESS_RULES.md.

**Definitions**
- **False Positive (FP):** the pipeline wrongly **blocked or buried a good lead**
  (false DQ, or Manual Review of a creator who should be Approved). Lost opportunity.
- **False Negative (FN):** the pipeline wrongly **advanced or over-rated a creator**
  who should have been blocked or downgraded (over-approval, missed faceless-
  compilation, etc.). Quality leak.
- **Fragile match:** right bucket reached for the *wrong reason* — would flip to
  wrong if the masking factor were corrected.

---

## Strict verdict × reason accounting — all 30 reviewed (2026-06-22)

> Operator directive: **"correct verdict + wrong reason" is NOT a success.** If a
> creator is DQ'd for HT when the real reason is inactivity or persona, fixing the HT
> logic later would wrongly move them to APPROVED. These are latent failures and must
> be tracked as such. This accounting supersedes the looser "right bucket" framing used
> in the Session-1 scorecard below.

**Three classes:**

### ✅ Correct verdict + correct reason — 6 / 29 resolved (~21%)
ANATOLY (LT approve), Coach Blue (real 1:1 application DQ), Daniel Hristov (real 1-1
Typeform DQ), Bronson Dant (own discovery-call DQ), Institute for Integrative Nutrition
(real $3.5k HT — genuinely DQ even with perfect logic), Coach Bart (real 1:1 personal
training DQ).

### ⚠️ Correct verdict + WRONG reason — 6 / 29 (~21%)  ← LATENT FAILURES (time bombs)
| Creator | Pipeline reason | Real reason | If logic fixed → |
|---|---|---|---|
| Hany Rambod | ambiguous tier-depth label | budget-range HT form | stays DQ (ok) but for wrong mechanism |
| Girls Gone Strong | HT (coaching/1-on-1) | **inactivity**; offer is MT | **wrongly APPROVED** |
| Prosper Nutrition | HT + $76k hallucination | **inactivity**; offer is $999 MT | **wrongly APPROVED** |
| Virtual Victor AI | Calendly booking (doesn't exist) | software persona | wrongly re-routed |
| Calisthenics Victoria | HT application funnel | sports-org persona | wrongly re-routed |
| Real BB Podcast News | "apply now" (doesn't exist) | media persona | wrongly re-routed |

These 6 are the strongest argument that **staleness gating and persona filtering are
load-bearing**, not optional — they're currently masked by HT over-fire. Fix HT without
them and 4–6 creators flip to wrong verdicts.

### ❌ Wrong verdict — 17 / 29 (~59%)
- **Should be APPROVED, held in MR (missed opportunity, recoverable) — 8:** Will Tennyson,
  CHRIS HERIA, ATHLEAN-X, STRIQfit, Hybrid Calisthenics, Calisthenics Worldwide, SheMoves,
  Christ Glorified.
- **Should be DQ, sitting in MR/Approved (quality leak) — 7:** Calisthenics Reacts,
  Yellow Dude, Coach Marilin, Calisthenics Watch, RxMuscle, Kharoliya, Unbreakable.
- **Should be APPROVED, but DQ'd (worst — false DQ) — 2:** Fun With Calisthenics, Stephanie Long.

### ⏳ Pending — 1
GianzCoach (IG linktree uncrawled).

**Honest top line:** true success (right verdict *and* reason) is **~21%**, not the
~53% "right bucket" figure. Another ~21% are latent failures. The pipeline's apparent
accuracy was inflated by HT over-fire coincidentally landing inactive/persona creators
in DQ for the wrong reason.

### Session 3 update (6 more reviewed → 36 total, 35 resolved)
- **✅ Correct + correct (+1 → 7):** Rahul Modi (real HT Typeform application + Indian
  audience — both reasons right).
- **⚠️ Correct + wrong reason (+3 → 9 latent failures):** Think BIG (DQ'd on a false
  "apply to"; real reason = livestream/media persona), Women's Fitness Academy (DQ'd on
  ambiguous HT; **real reasons = inactivity** (last long-form ~1yr ago, no HT, only a
  $5/wk LT) **+ brand persona** (an actual brand, not a personal brand) — my persona
  guess was a valid co-reason), Precision Nutrition (DQ'd on "qualification form/high-ticket"; **no HT** —
  $59/mo or $599 one-time MT; real reason = company persona).
- **❌ Wrong verdict (+2 → 19):** Calisthenics with Lavender (faceless → should be DQ
  under the hardened R5.1, pipeline put her in MR), Calisthenics Warrior (real person,
  no-face FP → should APPROVE, held in MR).

**Updated top line (35 resolved):** correct+correct **7 (~20%)**, correct+wrong-reason
**9 (~26%)**, wrong verdict **19 (~54%)**. The latent-failure rate is *rising*, and the
pattern is now unmistakable: **HT over-fire masks the real disqualifier (persona or
inactivity).** All 3 new latent failures are this exact shape. Staleness gating + persona
filtering are confirmed load-bearing — HT logic cannot be touched until they exist.

---

## Scorecard (15 creators)

| # | Creator | Subs | Pipeline verdict | Ground truth | Result |
|---|---|---|---|---|---|
| 1 | Will Tennyson | 5.01M | MR Without Contact (Ownership Low) | **APPROVE (SSS)** | ❌ FP |
| 2 | Calisthenics Reacts | 899K | MR With Contact (no-face) | **DQ (faceless compilation)** | ❌ FN |
| 3 | Hany Rambod | 1.16M | DISQUALIFIED | DQ (real HT budget form) | ✅ correct |
| 4 | Fun With Calisthenics | 45.4K | DISQUALIFIED | **APPROVE** | ❌ FP |
| 5 | ANATOLY | 9.57M | APPROVED | APPROVE (LT only) | ✅ correct |
| 6 | Coach Blue | 190K | DISQUALIFIED | DQ (real 1:1 application) | ✅ correct |
| 7 | Yellow Dude | 1.61M | APPROVED | **weak/low (faceless brand)** | ❌ FN |
| 8 | CHRIS HERIA | 5.39M | MR With Contact (endpoint) | **APPROVE (LT/MT app)** | ❌ FP |
| 9 | ATHLEAN-X™ | 14.3M | MR With Contact (no links) | **APPROVE** | ❌ FP |
| 10 | Daniel Hristov | 29.5K | DISQUALIFIED | DQ (real 1-1 Typeform) | ✅ correct |
| 11 | Bronson Dant | 11.6K | DISQUALIFIED | DQ (own discovery call) | ✅ correct |
| 12 | Institute for Integrative Nutrition | 46.3K | DISQUALIFIED | DQ (institution) | ✅ correct |
| 13 | Girls Gone Strong | 43.4K | DISQUALIFIED (HT) | DQ (cadence; offer is MT) | ⚠️ fragile |
| 14 | STRIQfit | 288K | MR With Contact (partial) | **APPROVE** | ❌ FP |
| 15 | Prosper Nutrition | 1.31K | DISQUALIFIED (HT $76k) | DQ (cadence; offer is $999 MT) | ⚠️ fragile |

**Tally:** 6 solid-correct · 2 fragile-correct · 5 false positives · 2 false negatives.
Right *bucket* on 8/15, but only **6/15 for the right reason.**

---

## Confirmed FALSE POSITIVES (good leads wrongly blocked) — 5

### FP-1 · Will Tennyson — 5.01M — buried in MR Without Contact, should be APPROVED (SSS)
- **Pipeline reason:** Ownership Low + no contact path.
- **Truth:** Both bio emails (`contact@willtennyson.ca`, `willt@night.co`) are his and
  sit in plain About-page text. His linktree is his whole funnel: a cookbook (his, LT)
  + MacroFactor/Gymshark affiliate referrals + YT + a broken store link. Minimal owned
  offers + 5M audience + no HT = top lead.
- **Bugs:** (a) bio-text emails not extracted [R11.3]; (b) affiliate links counted
  against ownership [R4]; (c) ownership too conservative on aggregator-hosted offers [R3.3].

### FP-2 · Fun With Calisthenics — 45.4K — false DISQUALIFY
- **Pipeline reason:** "application funnel: apply to".
- **Truth:** No HT, no coaching. Only affiliate links + some dip bars. Good lead.
- **Bug:** the "apply to" came from **Linktree's own** partner-recruitment page, crawled
  as platform contamination [R10.2].

### FP-3 · CHRIS HERIA — 5.39M — over-cautious MR, should be APPROVE
- **Pipeline reason:** ENDPOINT UNCERTAIN (heriapro login wall).
- **Truth:** Behind the wall is a $11.99/mo · $119.99/yr subscription app (LT/MT). No HT.
- **Bug:** endpoint-uncertainty treated a login-gated app subscription as possible HT.

### FP-4 · ATHLEAN-X™ — 14.3M — false "no crawlable links" MR
- **Pipeline reason:** NEEDS MORE DATA — no crawlable links.
- **Truth:** Sells many LT/MT programs; `athleanx.com` IS on his About page.
- **Bug:** `athleanx.com` mis-tagged Page Type **"Twitter/X"** because it ends in the
  substring `x.com`; his real site was discarded as social [R10.4].

### FP-5 · STRIQfit — 288K — false MR (incomplete crawl), should be APPROVE
- **Pipeline reason:** Medium data, only 2 pages crawled.
- **Truth:** No HT; sells LT/MT calisthenics programs. Stage 1 extracted 6
  `striqfit.myshopify.com` program seeds + the app link; Stage 2 crawled only the app
  link (IG skipped). The store that qualifies him was never visited.
- **Bug:** seed-coverage gap — not all extracted seeds are crawled [R10.3].

---

## Confirmed FALSE NEGATIVES (wrongly advanced / over-rated) — 2

### FN-1 · Yellow Dude — 1.61M — APPROVED, should be downgraded (weak HT prospect)
- **Pipeline reason:** QUALIFIED, Ownership High, LT/MT books.
- **Truth:** Faceless single-person brand. Sells books (LT) but **cannot sell HT** —
  buyers don't trust a faceless brand with premium coaching. Still a lead, but a weak
  one; should not be top-of-Approved.
- **Bug:** no-face not applied as a quality discount [R5.1, R5.2].

### FN-2 · Calisthenics Reacts — 899K — held in MR, would false-approve if no-face "fixed"; should be DQ
- **Pipeline reason:** held by the (broken) no-face matcher.
- **Truth:** A **faceless compilation/entertainment channel** — clips of random athletes,
  no individual behind it. Not a personal brand at all → DISQUALIFY. Its only "offers"
  were GORNATION affiliate products (`?ref=calisthenicsreacts`) + a ~$15 guide.
- **Bug:** naively fixing no-face would APPROVE it on contaminated affiliate data. The
  compilation case needs an explicit DQ [R5.2.3]; affiliate data needs exclusion [R4].

---

## Fragile correct (right bucket, wrong reason) — 2

### FR-1 · Girls Gone Strong — 43.4K
- DQ'd for "ambiguous HT coaching/1-on-1." Actual offer is **MT** ($299/mo or $199/mo).
  Correctly DQ'd only because the channel is **~10 months inactive (long-form)**.
- **Upload trace (2026-06-22):** recorded "Last Upload" = 2026-04-06 — but that item is a
  **16s Short** ("Wall Ankle Mobilizations"). ALL of the last 15 uploads are Shorts
  (≤62s exercise demos); **no long-form in the window.** Pipeline saw "active"; truth is
  long-form-dead.
- Risk: fixing HT-over-fire (R6.4) without a staleness gate (R8.2/R8.4) → wrong approval.

### FR-2 · Prosper Nutrition — 1.31K
- DQ'd on structural HT + a hallucinated **$76,000** "price". Actual offer is **$999 MT**.
  Correctly DQ'd only because it is **~9.7 months inactive (long-form)**.
- **Upload trace (2026-06-22):** recorded "Last Upload" = 2026-03-23, a **60s Short**.
  Most recent **long-form = 2025-09-01** (641s) — ~9.7mo ago, matching the operator's
  "9 months". Shorts continued (Mar/Jan/Oct) masking the inactivity.
- Bugs: $76k price hallucination; HT over-fire on a $999 MT page; Shorts counted as
  activity. Saved from wrong approval by cadence reality the pipeline never measured.

---

## Bugs surfaced (consolidated, with evidence)

| Bug | Evidence | Rule |
|---|---|---|
| Affiliate links credited as owned offers / contact | Cal Reacts (`?ref=`), Bronson (`?aff=`) | R4 |
| Bio-text emails not extracted | Will Tennyson (2 emails in About text) | R11.3 |
| Social-domain matched by substring (`x.com`) | ATHLEAN-X (`athleanx.com` → "Twitter/X") | R10.4 |
| Not all extracted seeds crawled | STRIQfit (6 Shopify seeds dropped) | R10.3 |
| Shorts counted as "active creator"; no long-form staleness gate | GGS (last 15 all Shorts), Prosper (last long-form 2025-09-01) — trace 2026-06-22 | R8.2 / R8.4 |
| HT over-fires on visible MT prices | Girls Gone Strong ($299/mo), Prosper ($999) | R6.4 |
| Price hallucination | Prosper ($76,000 invented) | R7.2 |
| Faceless not used as quality signal / DQ | Yellow Dude (over-approved), Cal Reacts (should DQ) | R5 |
| Ownership confidence inconsistent | Yellow Dude High vs Will Tennyson Low (same linktree basis) | R3.2 |
| Platform marketing pages crawled as creator funnel | Fun With Calisthenics (Linktree partner page) | R10.2 |
| No persona filter (institutions enter funnel) | IIN, Precision Nutrition, Calisthenics Victoria | R9.1 |

---

## Key conceptual correction (operator + assistant)

**A creator's own form hosted on a platform is a REAL signal; the platform's own
marketing pages are contamination.** Daniel Hristov's and Coach Blue's 1:1 coaching
applications (built on Typeform) are correct HT DQs. Fun With Calisthenics' "apply to"
came from Linktree's *own* partner page — contamination. The platform-contamination fix
must **distinguish the creator's hosted form from the platform's boilerplate**, not
blanket-block platform domains. (Assistant predictions were wrong on Hany and Daniel for
exactly this reason — both were real HT, not contamination.)

## Prediction accuracy (assistant)
12/15 directionally correct. Wrong on **Hany Rambod** and **Daniel Hristov** (assumed
platform contamination = false DQ; both had real HT forms) and over-analyzed **Yellow
Dude** (predicted ownership inconsistency; real lesson was faceless-can't-sell-HT).

## Mechanical bug register — fix-ready, NOT to implement yet (tracking only)

> These are objectively-wrong behaviors; one example proves each. They need no further
> calibration before fixing — but per operator: **no implementation yet**, keep tracking.

**Risk asymmetry (operator, 2026-06-22):** a broken **HT** detector creates *noise*; a
broken **faceless** detector *buries real creators entirely*. Now that faceless is a hard
DQ (R5.1), the faceless matcher is the most dangerous bug in the system. → **Priority #1.**

| # | Mechanical bug | Rule | Evidence |
|---|---|---|---|
| **1** | **Faceless matcher fires on "and"/"channel"/"education"** | R5.3 | Hybrid, SheMoves, Cal Worldwide, Cal Warrior — real people it flags; under hard-DQ each = a false DQ |
| 2 | Hostname matched by substring (`athleanx.com`→Twitter) | R10.4 | ATHLEAN-X (14.3M lost) |
| 3 | Affiliate `ref=`/`aff=`/`affcode=` credited as owned (offer + email) | R4 | Cal Reacts, Bronson, Cal Worldwide, Will |
| 4 | Seed coverage — extracted seeds not all crawled | R10.3 | STRIQfit (6 Shopify seeds dropped) |
| 5 | Bio-text + obfuscated email not extracted / contact page not captured | R11.3, R13.4 | Will Tennyson, Cal Worldwide |
| 6 | Shorts counted as activity; no long-form / cross-platform measure | R8.4, R8.5 | ~9/44 mis-assessed; GGS, Prosper, WFA |

**NOT mechanical — these need the safety-net ordering, do NOT fix in isolation:**
persona filter (R9.1), activity gate (R8.5), HT-vs-MT price awareness, sold-vs-discovery
call (R13.1), platform-contamination distinction (R10.2). Several DQ verdicts are
currently *correct only by accident* of HT over-fire (9 latent failures) — fixing HT
before persona + activity exist would flip 4–6 creators to wrongly-approved.

## Regression dataset
Labeled verdicts + reasons now tracked in `REGRESSION_SET.csv` (growing): 36 fitness
(calibrated) + 6 dropshipping (reconstructed from transcript — flagged `VERIFY`). Add all
future manually-reviewed creators, any niche. This is the product's ground truth.
