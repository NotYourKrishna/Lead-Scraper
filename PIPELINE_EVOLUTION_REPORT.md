# Pipeline Evolution Report — Engineering Post-Mortem

> Onboarding document for a new engineer. Covers the project from the initial
> commit (`f8a1891`, 2026-06-20) through the current head (`0dc7cfd`, 2026-06-21).
> Grounded in git history and the validation run `runs/fitness/2026-06-21_144632`.

> **Note on the timeline:** version control understates the real history. The
> first commit (`f8a1891`) was made on **2026-06-20 05:26**, but development began
> **2026-06-19 10:28** — a full ~19 hours earlier. That first commit bundled an
> entire day of staged work (Section 0). The pre-commit history below is
> reconstructed from the session transcript, not from git.

**Pre-commit development (Jun 19 → first commit Jun 20 05:26):** see Section 0.

**Timeline at a glance (13 commits, ~2 days of intensive iteration):**

| # | Commit | Date | Theme |
|---|--------|------|-------|
| 1 | `f8a1891` | 06-20 | Initial commit — bundles all of Section 0 (POC → staged pipeline → IG → 2-sheet output → tier model) |
| 2 | `0829b50` | 06-20 | Email no longer required for approval; hidden-email scraper |
| 3 | `49a851d` | 06-20 | 4-file contactability output; YT email-button detection; secrets to `.env` |
| 4 | `4f16e47` | 06-20 | Niche configs, multi-query discovery, DISQUALIFIED audit trail, funnel report |
| 5 | `80d4114` | 06-20 | Own-domain email tightening; consolidation outreach angle |
| 6 | `a1df8e2` | 06-20 | Instagram bio emails as a trusted source |
| 7 | `7088686` | 06-21 | Price-hallucination fix; cadence/no-face filters; concurrency |
| 8 | `387a5c8` | 06-21 | Latest-video-description emails |
| 9 | `bb68357` | 06-21 | Ownership attribution (Creator Asset vs Partner vs Affiliate) |
| 10 | `dd42239` | 06-21 | Category-based broad-language outreach angles |
| 11 | `be8d2dd` | 06-21 | Human-mimicking navigation + structured product extraction |
| 12 | `7e779ac` | 06-21 | Video-desc signals, 11-category taxonomy, conservative ownership, crawl efficiency |
| 13 | `0dc7cfd` | 06-21 | Serial crawling, versioned runs, crawl audit, price-decoupled routing, MR calibration |

---

## SECTION 0 — PRE-COMMIT DEVELOPMENT (Jun 19, before `f8a1891`)

> Reconstructed from the session transcript (`76206b37-…jsonl`), which begins
> 2026-06-19 10:28. None of this was under version control at the time; it was all
> squashed into the "Initial commit" the next morning. This is the project's true
> origin story and explains *why* the initial architecture (Section 2) looked the
> way it did.

The defining characteristic of this phase: **the user enforced a strict staged
build and refused to let scoring be added before each earlier stage was verified
against real creators.** Nearly every architectural principle that survives today
was set here.

### Phase 0 — Setup (10:28–10:41)
User supplied a YouTube Data API key and an existing lead-scraping tool to set up
and run. Early friction getting Python accessible on the user's Windows machine.

### Phase 1 — First run + filtering rules (10:41–13:03)
First run worked ("great start"). User immediately tightened scope:
**English-speaking channels only**, geo filtering. Manual spot-checks established
the verification-driven working style that defined the whole project:
- Saamir Mithwani — acceptable lead.
- **Shahid Anwar** — already selling a mentorship/high-ticket offer; should never
  have been scraped (early evidence the HT filter was needed).
- An Etsy-dropshipping creator — Filipino, should have been geo-filtered.

### Phase 2 — The link-extraction debate (13:21–13:45)
The pivotal early exchange. The user challenged the core feasibility assumption:

> "Can you explain exactly how you plan to obtain the creator's external links?
> The YouTube API does not expose About-page links."

He demanded a step-by-step explanation (how links are discovered, visited,
extracted; what's implemented; what's blocked) **and an upfront estimate of
whether Playwright could even see the About-page links before any building
began.** Only then did he greenlight a proof-of-concept with explicit
constraints:
- 50–100 channels per run
- 10–20 min runtime acceptable
- **Reliability over speed**
- "Do not implement scoring yet. Prove link extraction works first."

This established the **Playwright-About-page approach** that is still the
foundation of Stage 1, and the **reliability-over-scale** philosophy.

### Phase 3 — Staged pipeline build + validation (13:45–16:19)
User explicitly forbade jumping to ICP scoring and dictated the staging:
- **Stage 1:** API discovery + filtering → Playwright About-page → CSV of
  {Channel Name, Channel URL, Link Label, Destination URL}. Verify before moving on.
- **Stage 2:** crawl the links. Results "extremely encouraging" — the scraper
  re-found known creators, proving the concept.
- **Stage 3:** classification. User caught the first major conceptual bug:

  > "'No monetization detected' is treated as if it means 'No monetization
  > exists.' Those are different conclusions."

  This forced the **confidence-level model** (Monetization Confirmed vs
  Insufficient Data vs None) that still underpins Stage 3.

### Phase 4 — Multi-layer funnel traversal (16:19, the "one layer deep" fix)
User identified that the crawler only inspected one layer:

> "YouTube → About Page → External Link → Inspect → Stop. This misses many
> funnels because monetization is often hidden behind additional layers."

He cited **Jordan Welch** (YouTube → Instagram → tagged business account → link in
bio → VSL) and **Baddie In Business** as multi-hop examples. This is the origin of
deep funnel traversal and, later, navigation prioritization.

**The Zain Shah validation** (the canonical early test case): the crawler
classified him "High confidence / No monetization found," but he actually sold a
**£200 course hidden behind a nav button labeled "Online Business."** This proved
the crawler discovered links correctly but didn't explore *website navigation*
deeply enough — the direct ancestor of the nav-priority system (commit 11, months
of conceptual distance compressed into a day).

### Phase 5 — Funnel-depth philosophy + HT focus (16:19–17:20)
User crystallized the qualification thesis:

> "I do not care whether a creator has a lead magnet. I care what the lead magnet
> ultimately leads to. A lead magnet is not a monetization endpoint — it is the
> first step in a funnel. Identify the **deepest monetization layer**."

He provided opt-in identity for traversing forms (`topticketclosers@gmail.com`,
name "Gary") and authorized reCAPTCHA solving. Concern shifted from surface HT
signals to **missing deep HT backends** — the false-negative risk that still
drives the endpoint-uncertainty logic.

### Phase 6 — Instagram-assisted discovery (17:20–18:27)
User specified IG-assisted discovery with strict guardrails:
- IG is **not** a primary source — only used when a creator survives filtering,
  has no HT backend found yet, and would otherwise be "Needs More Data."
- Throwaway IG account via Playwright; serial (shared session).
- **Jordan Welch:** HT offer lives behind an account *tagged in his IG bio*, not
  his own bio link — tagged-account extraction must work.
- **`@aicomacademy`:** the tagged account whose own bio holds the HT page.

(These two cases are now permanent entries in project memory.)

### Phase 7 — Two-sheet output + tier model → first commit (18:27 → Jun 20 05:26)
- **Output redesign:** user mandated a **two-sheet workflow** — `APPROVED_FOR_OUTREACH`
  and `MANUAL_REVIEW`, explicitly **no rejected sheet**, default to MANUAL_REVIEW
  when uncertain. Minimizing false positives was the stated goal. (This is the
  direct ancestor of today's 5-bucket router.)
- **Coaching/mentorship false-positive fix:** user identified the single most
  important classification flaw:

  > "Current logic overweights words like coaching / mentorship and disqualifies
  > strong prospects. $47/$97/$197 coaching should NOT auto-disqualify. Classify
  > offer **TIER**, not offer **LABEL**."

  He defined LOW (<$300) / MID / HIGH ($2k+) tiers and confirmed mentorship should
  price-tier the same way (**Austin Rabin**'s $97 mentorship = ideal LT prospect,
  not HT). This is the genesis of the entire tier model in Section 4.
- Then: *"please commit all this to my github"* → repo + token provided → `f8a1891`.

### What Section 0 established that still holds
| Principle | Set on | Still in pipeline |
|-----------|--------|-------------------|
| Playwright About-page link extraction | Phase 2 | Stage 1 |
| Reliability over scale | Phase 2 | Serial crawl, deferral-not-blocking |
| Strict staged build, verify each stage | Phase 3 | 5-stage architecture |
| "No data" ≠ "no monetization" | Phase 3 | Confidence model |
| Deepest-monetization-layer | Phase 5 | `analyze_funnel_depth` |
| Multi-layer / nav traversal | Phase 4 | Nav priority (commit 11) |
| IG only as fallback, tagged accounts | Phase 6 | IG-assisted discovery |
| Default to Manual Review when uncertain | Phase 7 | Conservative router |
| Tier over label | Phase 7 | `assess_ht_level` |

---

## SECTION 1 — ORIGINAL GOAL

### What the pipeline was designed to do
Find YouTube creators who have **an engaged, monetized audience but no
high-ticket (HT) offer**, and route them to outreach. The business thesis: these
creators have already proven people will pay them (they sell courses, programs,
communities, merch), but they're leaving money on the table by not having a
premium coaching/service backend. The operator's pitch is to **build and run
that high-ticket backend for them**.

### Target ICP
- English-speaking creator (geo/language filtered)
- Above a minimum subscriber threshold, actively posting
- A **personal brand** (a human the audience follows), not a faceless media company
- Sells **low-ticket (LT) or mid-ticket (MT)** offers — proof of buyers
- Has **no mature HT backend** — that's the gap to fill
- Reachable (email or YouTube email button)

### Qualification logic (the core decision)
For each creator, determine the **deepest monetization layer** in their funnel:
- **HT backend present** (application funnel, strategy call, $2k+ offer, 1:1
  mentorship, mastermind) → **DISQUALIFY** (they already solved the problem)
- **LT/MT only, no HT** → **QUALIFY** (the ideal target — proven buyers, open gap)
- **Nothing found / ambiguous / blocked** → **MANUAL REVIEW**

### Outreach workflow
Qualified creators get an **outreach angle** auto-generated from their funnel
(e.g. "you sell a $40 course but have no HT backend — let's build your ascension
offer"). Creators with fragmented offers get a **consolidation angle**.

### Intended end-to-end flow
```
YouTube Discovery → Initial Filtering → Funnel Crawl → HT Detection
→ Contact Discovery → Qualification → Outreach Routing
```

---

## SECTION 2 — ORIGINAL ARCHITECTURE (commit `f8a1891`)

A single `pipeline.py` (~3,300 lines) with a 5-stage flow. Supporting one-off
scripts (`lead_scraper.py`, `poc_links.py`, `ig_diag.py`) were proof-of-concept
and are now legacy.

| Stage | Function | What it did originally |
|-------|----------|------------------------|
| 1 | Discovery | YouTube Data API search for one query; pull channel details + About-page bio links via Playwright |
| 2 | Funnel crawl | Playwright walks each bio link, follows outbound links a couple levels deep, dumps raw page text |
| 3 | Classify | Keyword + price scan over the combined text blob → monetization tier; build outreach angle |
| 4 | Score | ICP fit score (subscribers + offer type + gap) |
| 5 | Route | Two CSVs: `APPROVED_FOR_OUTREACH.csv`, `MANUAL_REVIEW.csv` |

Also present from day one: Instagram-assisted discovery, multi-step Typeform
qualification-form traversal, and non-blocking CAPTCHA deferral.

### Assumptions baked in (most were later proven wrong)
1. **A raw text blob per creator is enough** to classify the funnel. *(Wrong — see Sections 4 & 5.)*
2. **Any dollar figure on a page is an offer price.** *(Wrong — revenue/testimonial numbers hallucinated prices.)*
3. **Any page the funnel links to belongs to the creator.** *(Wrong — partner brands, affiliates, and platform pages.)*
4. **Email is mandatory to act on a lead.** *(Wrong — relaxed in commit 2; a YT email button is enough.)*
5. **The word "coaching" implies high-ticket.** *(Wrong — "$97 coaching" is low-ticket.)*
6. **Random link-following finds the offer.** *(Wrong — needed human-mimicking nav priority.)*

---

## SECTION 3 — EVERY MAJOR PROBLEM DISCOVERED

> Format: Problem · Symptoms · Root cause · Example creators · Impact · Fix · Status

### 3.1 "Coaching" word false positives
- **Symptoms:** Creators selling a $97 coaching call flagged as HT and disqualified.
- **Root cause:** Label-based HT detection — the literal word "coaching" mapped to HT.
- **Examples:** Numerous low-ticket coaches across early fitness runs.
- **Impact:** Systematic false-positive disqualification of the exact ICP.
- **Fix:** Tier model (`assess_ht_level`) — "coaching" with a sub-$2k price prices out as LT; coaching with no price/structure → Medium (suspected → manual review), never auto-DQ.
- **Status:** ✅ Fixed (commit 7 onward).

### 3.2 Price hallucination
- **Symptoms:** Prices invented from unrelated numbers (e.g. Greg Doucette DQ'd on "$99,700").
- **Root cause:** Regex grabbed any `$N`; supplement bundles, milligrams, follower counts all became "offer prices."
- **Examples:** Greg Doucette ($99,700 supplement misfire), early dropshipping creators.
- **Impact:** Both false DQs (huge fake HT prices) and false approvals (wrong tier).
- **Fix:** `extract_prices()` requires offer-adjacent keywords within ±80 chars and rejects revenue/testimonial context (commit 7). Routing later **decoupled from exact price** entirely (commit 13).
- **Status:** ✅ Largely fixed; price is now a supporting signal, not a gate.

### 3.3 Revenue mistaken for offer prices
- **Symptoms:** "$30k/month" testimonial counted as the offer price → mis-tiered to HT.
- **Root cause:** No distinction between *what they charge* and *what they/students earn*.
- **Impact:** Inflated tier; false DQs.
- **Fix:** `REVENUE_CONTEXT` exclusion window in `ht_offer_prices()` / `extract_prices()`.
- **Status:** ✅ Fixed.

### 3.4 HT vs LT classification by label
- **Symptoms:** Tier driven by keywords, not structure.
- **Root cause:** No model of sales *structure* (application/qualification/booking).
- **Fix:** Tier framework with `HT_STRUCTURAL_SIGNALS`, `HT_PLATFORM_SIGNALS`, `SOFT_HT_SIGNALS` and price thresholds (`HT_PRICE_THRESHOLD=2000`, `MID_PRICE_THRESHOLD=300`).
- **Status:** ✅ Fixed structurally; residual ambiguity remains (see 3.18).

### 3.5 Instagram discovery problems
- **Symptoms:** Many creators only expose links via IG bio, not the YT About page; verification walls.
- **Root cause:** Bio funnels live off-platform; IG requires login/session and hits MFA/verification walls.
- **Fix:** IG-assisted discovery (serial, shared session), `REVIEW_REQUIRED` override when a wall is hit, tagged-account extraction.
- **Status:** ⚠️ Partial — works when bio links resolve, still frequently returns "no crawlable bio links." MFA bypass is explicitly out of scope.

### 3.6 Third-party / agency email misattribution
- **Symptoms:** A creator assigned an email belonging to a sponsor or management agency (e.g. `CONTACT@MARQUIS.FR` off an IG-linked brand).
- **Root cause:** Page-text email fallback accepted any email on any linked page.
- **Examples:** Jewish Fitness Coach (dropped MARQUIS.FR → correctly routed to DISQUALIFIED no-contact).
- **Impact:** Outreach would go to the wrong inbox.
- **Fix:** Own-domain restriction (commit 5) — email accepted only if its domain matches a creator own-domain or appears on a creator-owned page. `Email Source` provenance field added.
- **Status:** ✅ Fixed for page-text; **regression observed** in latest audit (Bronson Dant → `info@inbody.com`; see 3.20).

### 3.7 YouTube email-button challenge
- **Symptoms:** Real creator emails sit behind YouTube's "View email address" reCAPTCHA.
- **Root cause:** YouTube gates emails behind a CAPTCHA to prevent scraping.
- **Fix attempts:** Commit 2 added an undetected-chromedriver auto-clicker; **removed in commit 3** (against policy / brittle). Replaced with `check_yt_email_button()` which only detects *presence* ("Sign in to see email address") without revealing it.
- **Status:** ✅ Resolved by design — presence of the button = "contactable, retrieve manually." We never auto-bypass the CAPTCHA.

### 3.8 CAPTCHA bottlenecks (funnel pages)
- **Symptoms:** Store/checkout pages throw reCAPTCHA mid-crawl, stalling the run.
- **Root cause:** Bot-detection on Shopify/Squarespace/etc.
- **Fix:** Non-blocking deferral — flag the page, record to `captcha_pending.csv`, continue. Affected creators route to Manual Review with a "solve manually then re-run" note.
- **Status:** ✅ Handled gracefully; 12 pages deferred in the latest run.

### 3.9 Concurrency / creator isolation concern
- **Symptoms:** In a 3-worker run, one creator's pages printed under another's block (Jeremy Ethier under Charles Glass).
- **Root cause:** Interleaved **stdout** from `ThreadPoolExecutor` workers — cosmetic. Each worker owns its own Playwright context; `pages_by_creator`/`all_page_rows` are written only in the main thread after `fut.result()`.
- **Impact:** Looked like data mixing; on inspection it was log interleaving.
- **Fix:** `MAX_CONCURRENT_CREATORS=1` (serial) in commit 13 — correctness-first while we add a per-page audit trail to *prove* isolation.
- **Status:** ✅ De-risked; can return to 2 now that `crawl_audit.csv` exists to verify (see Section 10).

### 3.10 Output overwrite problem
- **Symptoms:** Re-running a niche overwrote prior outputs; before/after comparison impossible. `seen_channels.json` also caused the "same batch" re-run to surface 50 *new* creators instead.
- **Root cause:** Fixed output paths under `outputs/{niche}/`; no run versioning.
- **Impact:** Lost the ability to compare runs — the exact thing needed to validate changes.
- **Fix:** Versioned run folders `runs/{niche}/YYYY-MM-DD_HHMMSS/` (commit 13). `seen_channels.json` deliberately stays in `outputs/{niche}/` as cross-run dedup state.
- **Status:** ✅ Fixed.

### 3.11 Ownership attribution
- **Symptoms:** Prices/offers from partner/affiliate pages credited to the creator.
- **Root cause:** No model of who owns a page.
- **Examples:** Coach Kolton (linktree → biohackr.lol, Redacted Esthetics, OnWellness — all partner pages; previously QUALIFIED with hallucinated prices).
- **Fix:** `classify_page_ownership()` → Creator Asset / Partner Brand / Affiliate Offer / Unknown (commit 9). Partner/affiliate pages contribute **category** signal but have **price stripped** (commit 10). `Ownership Confidence` field added; Low confidence → Manual Review (commit 12).
- **Status:** ✅ Core model fixed; attribution still imperfect on affiliate-seed crawls (see 3.14).

### 3.12 Linktree contamination
- **Symptoms:** Creators DQ'd on HT signals found on **Linktree's own marketing site**, not their funnel.
- **Root cause:** Crawler followed Linktree's internal nav (`/features/shops`, `/marketplace`, `/pricing`) which contains "apply to (become a partner)", "high-ticket", "community."
- **Examples (latest run):** Fun With Calisthenics (false DQ on `apply to` from Linktree partner page); Coach Marilin; Daniel Hristov.
- **Impact:** False-positive disqualifications; wasted crawl budget.
- **Fix:** ❌ Not yet implemented.
- **Status:** 🔴 Open — high priority (Section 10).

### 3.13 Typeform contamination
- **Symptoms:** Creator DQ'd / mis-tiered on Typeform platform copy.
- **Root cause:** Following a creator's Typeform link into Typeform's own site (`/explore`, `/pricing`, `/enterprise`, "high-ticket" tier names).
- **Examples:** Coach Blue (seed *is* a Typeform application — the DQ is arguably correct, but 13 of 15 pages were Typeform's site); Daniel Hristov.
- **Fix:** ❌ Not yet implemented (same fix as 3.12).
- **Status:** 🔴 Open.

### 3.14 Affiliate-link contamination (GORNATION pattern)
- **Symptoms:** Entire crawl budget spent inside a 3rd-party store; creator's own funnel never reached; the creator's "offers" and prices are actually the partner's catalog.
- **Root cause:** When an **affiliate link is the first seed** (`?ref=…`), `monetization_found` trips inside the partner store and the creator's own domain is skipped.
- **Examples (latest run):** Calisthenics Reaction — seed `gornation.com/?ref=calisthenicsreacts`; all 15 pages were GORNATION; classified "Mid Ticket" off GORNATION's product prices.
- **Impact:** Wrong tier, wrong angle, wrong prices — one of the most damaging data errors in the batch.
- **Fix:** ❌ Not implemented. Need to deprioritize affiliate seeds and prefer the creator's own domain.
- **Status:** 🔴 Open — high priority.

### 3.15 No-face detector failures
- **Symptoms:** Verified personal brands flagged "no personal brand detected" and held in Manual Review.
- **Root cause (two layers):**
  1. *Matching bug* — the detection pattern matches the literal word **"and"** (`" and "`) in a channel description, i.e. nearly every description. Standalone tokens `channel`, `education`, `media` also over-fire.
  2. *Design flaw* — even with perfect matching, treating "no face" as a hard **Manual-Review gate** is wrong. A confirmed faceless brand should *lower lead quality*, not block qualification.
- **Examples (latest run):** Hybrid Calisthenics (Hampton Liu), SheMoves (Marina Zinchuk), Calisthenics with Lavender — all real humans, all stuck.
- **Impact:** **12 of 14 Manual Review creators** in the latest run were blocked solely by this. Single biggest yield bottleneck.
- **Decision (2026-06-21):** keep the no-face *concept* but redesign it as a **scoring signal**, not a gate:
  - Clearly personal brand → **positive** signal (raises score).
  - Clearly faceless brand → **negative** signal / lower score (NOT auto-block).
  - Uncertain → Manual Review.
  *Rationale:* for this HT service, faceless creators are weaker HT prospects — HT
  coaching/mentorship/masterminds rely on personal trust and authority, whereas
  faceless creators can still sell LT PDFs/courses/memberships. So face presence
  should weight **ICP score (Stage 4)**, not the Stage 3 REVIEW_REQUIRED override.
- **Fix:** ❌ Not yet implemented (design agreed; see Section 12).
- **Status:** 🔴 Open — **highest priority** (Section 10).

### 3.16 Missing video-description signals
- **Symptoms:** Real monetization links (Calendly/Skool/coaching) only in recent video descriptions were missed.
- **Fix:** `get_video_description_signals()` fetches the 3 newest descriptions in one API call, extracts emails + monetization URLs, feeds them as `video_description` seed rows into Stage 2 (commit 12).
- **Status:** ✅ Fixed.

### 3.17 Missing latest-video emails
- **Symptoms:** Booking/contact emails placed in a recent video description but not the channel bio were missed.
- **Examples:** Coach Kolton.
- **Fix:** Latest-video-description email tier inserted into the trust chain (commit 8).
- **Status:** ✅ Fixed.

### 3.18 Contact-path disqualification bug
- **Symptoms:** Fully **qualified** creators (no HT, proven buyers) dumped into `DISQUALIFIED.csv` purely because no email/button was found.
- **Examples (latest run):** Will Tennyson (5.01M subs, ICP 89/100, zero HT signals) sits in DISQUALIFIED next to creators running real application funnels; ATHLEAN-X™ (14.3M).
- **Root cause:** Router collapses "HT-disqualified" and "no contact path" into one bucket.
- **Impact:** Best leads in the batch are buried in the reject pile.
- **Fix:** ❌ Not yet implemented. Qualified-but-uncontactable should go to **Manual Review Without Email**, not Disqualified.
- **Status:** 🔴 Open — high priority.

### 3.19 Store-page detection / navigation-priority failures
- **Symptoms:** Crawler stopped at an About/blog page and missed the store; "study-guide PDF" mis-read as a coaching offer.
- **Root cause:** Random link-following; raw-blob keyword matching.
- **Fix:** Navigation priority tiers (Store=1 … Contact=9), `classify_page_content_type()`, `extract_structured_products()` (commit 11); informational-path skipping once monetization found (commit 12).
- **Status:** ✅ Largely fixed (the big step-change in crawl quality).

### 3.20 Ambiguous-HT routing contradiction
- **Symptoms:** `HT Score = 0 / HT Level = None` but the creator is DISQUALIFIED because the funnel-depth model returned an "Ambiguous, No Price/Structure" deepest layer that auto-maps to HT.
- **Examples (latest run):** Hany Rambod (1.16M, runs a supplement brand — not a coaching funnel; false DQ).
- **Root cause:** Two HT judgments (`assess_ht_level` score vs tier-depth label) can disagree; tier-depth wins in routing.
- **Fix:** ❌ Not implemented. Structural score should override an ambiguous tier-depth label.
- **Status:** 🔴 Open — medium priority.

### 3.21 Wrong-persona discovery (institutions / orgs)
- **Symptoms:** Certification schools and sports governing bodies surface for "nutrition coach" / "calisthenics coach" and DQ on legitimate (but irrelevant) HT signals.
- **Examples (latest run):** Institute for Integrative Nutrition, Precision Nutrition, Calisthenics Victoria (Australian state sports org).
- **Impact:** Wasted crawl budget; noise in DQ audit.
- **Fix:** ❌ Not implemented. Need a persona filter (creator vs institution).
- **Status:** 🟡 Open — medium priority.

### 3.22 Cross-creator email bleed (suspected)
- **Symptoms:** `calisthenicsreaction65@gmail.com` (sourced "Instagram bio") attributed to **Calisthenics Watch**, a different creator.
- **Root cause:** Suspected mis-attribution in the serial IG phase (not concurrency — IG runs serially).
- **Impact:** Wrong contact on a lead.
- **Fix:** ❌ Not investigated yet.
- **Status:** 🟡 Open — needs reproduction via `crawl_audit.csv`.

---

## SECTION 4 — EVOLUTION OF HT DETECTION

**V1 — Word-based (initial).** Keyword → tier. "coaching"/"mentorship"/"1:1" =
HT. *Problems:* false-positive DQs on $97 coaches (3.1); no notion of structure
or price.

**V2 — Price-based (commit 7).** Add `$2,000+ = HT`, `$300–1,999 = MT`, `<$300
= LT`, with offer-adjacent keyword gating and revenue exclusion. *Problems:*
price hallucination (3.2), revenue-as-price (3.3), supplement bundles tripping
HT (Greg Doucette $99,700).

**V3 — Tier framework (`assess_ht_level`, commits 7→12).** Structure first:
`HT_STRUCTURAL_SIGNALS` (application funnel, strategy/discovery call, 1:1
mentorship, mastermind, done-for-you), `HT_PLATFORM_SIGNALS`, `SOFT_HT_SIGNALS`
(ambiguous → Medium → manual review), plus qualification-form revenue+invest
screening. Returns High/Medium/None. *Problems:* tier-depth vs score
disagreement (3.20); still allowed price to gate routing.

**Current (commit 13).** `_detect_page_tier` runs in strict order:
1. **Structural HT signals fire first** (always definitive).
2. **Structured products** resolve the page — buyer-only categories (Supplement,
   Physical Product) return immediately, *bypassing any price-based HT check*.
3. **Price-based HT** only in the raw-text fallback, after buyer-only pages are excluded.

*Strengths:* a supplement bundle can no longer manufacture an HT disqualification
(Greg Doucette class fixed); structure dominates price. *Weaknesses:* the
ambiguous-tier-depth contradiction (3.20) still routes some non-coaching brands
(Hany Rambod) to DQ; platform/affiliate contamination still feeds bad signal in.

---

## SECTION 5 — EVOLUTION OF FUNNEL ANALYSIS

1. **Raw page scanning (initial).** Dump text, keyword-match a blob. Couldn't
   tell a store from a blog; missed offers behind nav.
2. **Navigation prioritization (commit 11).** `_nav_link_priority()` scores
   links by the creator's own label (Store=1 … Contact=9) and crawls
   highest-value pages first — mimics how a human looks for the offer. Link
   **text** captured alongside href so "Store" outranks "/page-3".
3. **Page content-type classification (commit 11).** `classify_page_content_type()`
   tags each page store/pricing/programs/membership/community/coaching/contact/
   checkout/linktree/homepage.
4. **Structured product extraction (commit 11).** `extract_structured_products()`
   pulls individual {title, price, category} tuples from store/pricing pages —
   kills "study-guide PDF → coaching offer" errors. Trusted for price even at Low
   ownership *if* structured products were extracted.
5. **Ownership classification (commit 9).** Creator Asset vs Partner Brand vs
   Affiliate vs Unknown; partner/affiliate price stripped, category retained.
6. **Crawl efficiency (commit 12).** `monetization_found` flag → skip
   informational paths (about/blog/faq/privacy/terms) once an offer is found.
7. **Crawl audit trail (commit 13).** `crawl_audit.csv` — one row per page
   visited with Content Type, Ownership, Offer Categories, Funnel Tier. Exists to
   *prove* per-creator isolation and to debug contamination (3.12–3.14).

Each step was forced by a specific failure: random crawling missed stores →
nav priority; blobs mis-tiered → structured extraction; partner prices credited
to creators → ownership; budget burned on docs → info-skip; isolation doubts →
audit trail.

---

## SECTION 6 — EVOLUTION OF EMAIL DISCOVERY

**Original.** Website + channel-description extraction; email **required** to approve.

**Layered trust chain (commits 2,3,5,6,8) — current order:**
1. **About-page bio link** — strongest; creator's own declared link.
2. **YouTube channel description** — creator's own voice.
3. **Latest video description** (commit 8) — booking emails often live here.
4. **Instagram bio** (commit 6) — creator's voice; genuine booking/mgmt contacts.
5. **Own-domain page text** (commit 5) — accepted only if domain matches a
   creator own-domain (third-party emails dropped).

**YouTube email button (commits 2→3).** Auto-CAPTCHA-click was tried and
**deliberately removed**; replaced with presence-only detection. A button =
"contactable, retrieve manually." Email is **not required** to approve.

**Contactability framework.** `contactable = has_email OR yt_email_button`.
Approved/Manual-Review split further into with-email / without-email.

*Strengths:* provenance tracked (`Email Source`); own-domain rule prevents most
misattribution. *Weaknesses:* own-domain rule has a regression (Bronson Dant →
`info@inbody.com`, 3.6/3.20); suspected IG cross-creator bleed (3.22); many
small creators expose no crawlable links at all → no email.

---

## SECTION 7 — OUTPUT SYSTEM EVOLUTION

- **Initial:** 2 files — `APPROVED_FOR_OUTREACH.csv`, `MANUAL_REVIEW.csv`.
- **4-file contactability (commit 3):** APPROVED_WITH_EMAIL / APPROVED_WITHOUT_EMAIL
  / MANUAL_REVIEW_WITH_EMAIL / MANUAL_REVIEW_WITHOUT_EMAIL. *Why:* "no email" ≠
  "not a lead" — a YT button still lets you act.
- **DISQUALIFIED.csv (commit 4):** 5th bucket; every dropped creator gets an
  audit row (HT Score/Level, reason, evidence, deepest layer). *Why:* nothing
  silently discarded — the file is the qualification engine's audit trail. *Caveat:*
  currently over-loaded (3.18).
- **End-of-run funnel report (commit 4):** discovery counts, per-bucket routing,
  approval/DQ/review rates, timing. *Why:* see whether logic is too strict/loose.
- **Crawl audit CSV (commit 13):** per-page trace. *Why:* prove isolation, debug contamination.
- **Versioned run folders (commit 13):** `runs/{niche}/<timestamp>/`. *Why:* never
  overwrite; enable before/after comparison (3.10).
- **MR calibration report (commit 13):** Manual-Review counts by root cause
  (no-face/cadence/CAPTCHA/suspected-HT/low-data/low-ownership). *Why:* see what's
  actually bottlenecking yield — immediately exposed the no-face problem (12/14).

---

## SECTION 8 — CURRENT ARCHITECTURE

```
┌─ setup_niche(niche[, run_dir]) ───────────────────────────────────────────┐
│  outputs/{niche}/seen_channels.json   (cross-run dedup state)              │
│  runs/{niche}/YYYY-MM-DD_HHMMSS/       (this run's versioned outputs)       │
└────────────────────────────────────────────────────────────────────────────┘

STAGE 1 — DISCOVERY                                          → stage1.csv
  • Iterate niche query variations (NICHE_CONFIGS)
  • YouTube Data API search → channel IDs
  • Dedup vs this run + seen_channels.json
  • Filter: language / geo / subs / inactive / company
  • Playwright: About-page bio links  (Source = about_page)
  • get_upload_cadence(): last upload, max gap, top-3 video IDs
  • get_video_description_signals(): emails + monetization URLs
        from 3 newest video descriptions  (Source = video_description)
  • check_yt_email_button(): presence only (no CAPTCHA bypass)
  • detect_no_face_signal()   ⚠ over-fires (3.15)
        │
        ▼
STAGE 2 — FUNNEL CRAWL  (serial; MAX_CONCURRENT_CREATORS=1)  → stage2.csv
  • Per creator: own Playwright browser/context
  • Nav-priority sort (Store=1 … Contact=9), crawl best pages first
  • classify_page_content_type() per page
  • extract_structured_products() on store/pricing pages
  • classify_page_ownership(): Creator Asset / Partner / Affiliate / Unknown
  • monetization_found → skip informational paths
  • CAPTCHA → defer to captcha_pending.csv, continue
  • Instagram-assisted discovery (serial, shared session)
        │
        ▼
STAGE 3 — CLASSIFY                                  → stage3.csv + crawl_audit.csv
  • Group pages by creator
  • Email enrichment trust chain (5 tiers, own-domain gated)
  • analyze_funnel_depth(): deepest monetization layer (ownership-filtered)
  • assess_ht_level() + _detect_page_tier(): structure-first, price-decoupled
  • Overrides → REVIEW_REQUIRED: slow cadence (>90d), no-face, endpoint-uncertain
  • Outreach angle (category-based; broad language unless ownership High)
  • Writes per-page crawl_audit.csv
        │
        ▼
STAGE 4 — SCORE                                             → stage4.csv
  • ICP fit (subs + offer type + HT gap); only QUALIFIED scored
        │
        ▼
STAGE 5 — ROUTE                          → 5 CSVs + MR calibration report
  • DISQUALIFIED  = HT backend OR no contact path     ⚠ over-loaded (3.18)
  • _is_approved(): QUALIFIED + High data + High endpoint + no HT
        + no CAPTCHA + LT/MT + Ownership≠Low
  • APPROVED / MANUAL_REVIEW × {with_email, without_email}
  • MR calibration breakdown by root cause
```

Resume support: `--from-stage N` auto-detects the latest run folder;
`--run-dir <path>` targets a specific one.

---

## SECTION 9 — CURRENT PERFORMANCE (run `2026-06-21_144632`)

| Metric | Value |
|--------|-------|
| Creators processed | 44 |
| Approved | 2 (1 with email, 1 without) |
| Manual Review | 14 (4 with email, 10 without) |
| Disqualified | 27 (17 HT backend, 10 no-contact) |
| Approval rate | 4.5% |
| Disqualification rate | 61.4% |
| Manual review rate | 31.8% |
| Total runtime | 98.4 min (serial) |
| Stage 2 crawl | 4,446 s (~75 min) — the bottleneck |
| Avg crawl/creator | 101 s |
| Leads/hour | 9.8 |

**Biggest false positives:** (1) Linktree/Typeform platform-page contamination
→ false HT DQs; (2) no-face over-firing holds verified humans in MR; (3)
qualified-but-uncontactable dumped into DISQUALIFIED.

**Biggest false negatives:** (1) creators with no About-page links get zero crawl
data (ATHLEAN-X™ 14.3M, Will Tennyson 5.01M) — no domain inference; (2)
affiliate seed (GORNATION) consumes the whole crawl budget; (3) no-face blocks
~6 otherwise-approvable creators.

**Biggest bottlenecks:** Stage 2 crawl wall-time (75 min serial); no-face signal
(12/14 MR); discovery surfacing wrong personas (institutions/orgs).

---

## SECTION 10 — REMAINING KNOWN ISSUES (ranked)

| # | Issue | Sev | Est. impact | Suggested fix |
|---|-------|-----|-------------|---------------|
| 1 | No-face: broken matcher + used as a hard gate | 🔴 Critical | ~6 extra approvals/batch; 12/14 MR blocked | (a) Fix matcher (proper-noun adjacency; drop standalone channel/education/media). (b) Redesign as ICP score weight: personal=+, faceless=−, uncertain=MR. Not a qualification gate. |
| 2 | Qualified-but-uncontactable → DISQUALIFIED | 🔴 High | Best leads buried (Will Tennyson 89/100) | Route ICP>0 + no-contact to MR-Without-Email |
| 3 | Affiliate-seed budget burn (GORNATION) | 🔴 High | Wrong tier/angle/prices on affected creators | Deprioritize `?ref=/?aff=` seeds; crawl own-domain first |
| 4 | Linktree/Typeform/Calendly platform contamination | 🔴 High | False HT DQs (Fun With Calisthenics) | At depth≥1 on known platforms, only follow links exiting to creator domain |
| 5 | Ambiguous-tier-depth vs score contradiction | 🟠 Med | False DQs (Hany Rambod) | Structural score overrides ambiguous tier-depth label |
| 6 | No domain inference for linkless creators | 🟠 Med | Misses mega-creators (ATHLEAN-X™) | Try `{name}.com`; parse YT about-tab structured data |
| 7 | Wrong-persona discovery (institutions/orgs) | 🟡 Med | Wasted budget; DQ noise | Creator-vs-institution persona filter |
| 8 | Own-domain email regression (info@inbody.com) | 🟡 Med | Occasional wrong contact | Re-check own-domain derivation when partner store is in bio |
| 9 | Suspected IG cross-creator email bleed | 🟡 Med | Rare wrong contact | Reproduce via crawl_audit.csv; scope IG email to active creator |
| 10 | Serial crawl wall-time | 🟡 Low | ~2× runtime | Return to `MAX_CONCURRENT_CREATORS=2` once audit verifies isolation |

---

## SECTION 11 — LESSONS LEARNED

**Harder than expected:**
- **Attribution, not classification.** Deciding *whose* offer a page represents
  (creator vs partner vs affiliate vs platform) turned out to be the dominant
  source of error — far more than tiering the offer once attribution is right.
- **The crawler is the product.** Most "classification bugs" were really
  navigation bugs — the crawler looked at the wrong page (platform site, partner
  store, blog) and classified it faithfully.
- **Heuristic signals over-fire silently.** The no-face `" and "` bug sat
  undiagnosed until the calibration report quantified it (12/14).

**Wrong assumptions:** raw-blob is enough; any `$N` is an offer; any linked page
is the creator's; "coaching" = HT; email is mandatory.

**Correct decisions:** staged pipeline with per-stage CSVs (resumable, debuggable);
never silently discarding a creator (5-bucket audit); making email optional;
structure-first HT model; the crawl audit trail and versioned runs (turned
debugging from guesswork into evidence).

**If rebuilding from scratch:**
- Make **ownership/attribution a first-class gate before tiering**, not a later patch.
- Maintain an explicit **domain boundary** per creator; never follow links off it
  into platform/partner sites without demotion.
- Treat **discovery persona** (individual creator vs org) as a filter, not an afterthought.
- Build the **audit trail and versioned outputs on day one** — every later debugging
  session needed them.
- Unit-test heuristic signals against a labeled fixture set so over-firing (no-face)
  is caught immediately.

---

## SECTION 12 — ROADMAP

### Immediate (highest priority — do before the next validation run)
1. **Redesign the no-face signal** (Issue 1). Single highest-leverage change; unblocks ~6 approvals/batch.
   Two parts: (a) fix the matcher so it stops firing on ordinary words; (b) move the
   signal from the Stage 3 REVIEW_REQUIRED override into **Stage 4 ICP scoring** as a
   weight — personal brand raises score, confirmed faceless lowers it, only *uncertain*
   face-presence routes to Manual Review. Faceless no longer blocks qualification.
2. **Reclassify qualified-but-uncontactable** to Manual Review Without Email (Issue 2). Stops burying the best leads.
3. **Affiliate-seed demotion** (Issue 3) and **platform-page navigation stop** (Issue 4). These two fix the worst data-quality errors (GORNATION, Linktree/Typeform).

*Why now:* all four are false-positive/negative sources that directly corrupt the
output buckets; none require architectural change.

### Medium-term
4. **Score-overrides-ambiguous-tier-depth** (Issue 5) — resolve the routing contradiction.
5. **Domain inference** for linkless creators (Issue 6) — recover mega-creators.
6. **Persona filter** (Issue 7) — keep institutions out of the funnel.
7. **Own-domain email regression + IG bleed** (Issues 8,9) — tighten contact correctness.
8. **Return concurrency to 2** (Issue 10) once `crawl_audit.csv` confirms isolation.

*Why medium:* each improves precision/yield but the pipeline is usable without them.

### Long-term (scaling)
- **Labeled fixture suite + regression tests** for every heuristic signal.
- **Multi-niche batch orchestration** with per-niche dashboards over `runs/`.
- **Incremental re-crawl** of CAPTCHA-deferred / endpoint-uncertain creators.
- **Confidence-weighted scoring** instead of hard gates, so borderline creators
  are ranked rather than bucketed.
- **Throughput**: distribute Stage 2 crawl (the 75-min bottleneck) across workers/machines.

*Why long:* these are investments that pay off across many niches and runs, not
single-run fixes.
