# Failure-Mode Frequency Tracker

> Running occurrence counts per failure mode across calibration sessions. The goal
> is to learn the **error distribution** before fixing anything, and eventually to
> prioritize fixes by **frequency × impact** rather than recency of discovery.
>
> **Counting rule:** a failure mode is counted **once per creator where it
> manifests**, regardless of whether it changed the final verdict. (A correct
> verdict reached via a flawed mechanism still counts — e.g. Prosper's $76k price
> hallucination counts even though the DQ was right.)
>
> Severity/impact is NOT scored yet — that comes later when we move to
> frequency × impact prioritization.

---

## Cumulative tally (all sessions)

| Failure mode | Total | S1 | S2 | Class |
|---|---|---|---|---|
| Faceless / compilation classification | **9** | 2 | 4 S2 / +2 S3 / +1 S4 | [D] hard-DQ |
| HT over-fire (false / misread HT signal) | **8** | 2 | 3 S2 / +3 S3 | [H] |
| Geo / language filter miss | **6** | 0 | 2 S2 / +1 S3 / +3 S4 (Ayyappa, Elvie, Aman; GianzCoach already in S2) | [M] |
| Persona miss (non-creator entity) | **7** | 1 | 4 S2 / +2 S3 | [H] |
| Shorts-as-activity / staleness | **5** | 2 | +1 S2 / +1 S3 / +1 S4 | [M] |
| Affiliate attribution leak | 4 | 3 | 1 | [M] |
| **Niche / relevance mismatch (off-niche surfaced)** | **2 NEW** | 0 | +2 S4 | [D] |
| Engagement / view-count ignored | **2** | 0 | 1 S2 / +1 S4 | [H] |
| **Description-text link not extracted (offer/HT missed)** | **1 NEW** | 0 | +1 S4 | [M] |
| Missed email (incl. obfuscated / split) | 2 | 1 | 1 | [M] |
| Contactability miss | 2 | 1 | 1 | [M] |
| Platform contamination (1 harmful, 1 benign) | 2 | 1 | 1 | [M]/[H] |
| Over-caution (endpoint / CAPTCHA, benign) | 2 | 1 | 1 | [H] |
| Ownership confidence mismatch | 1 | 1 | 0 | [H] |
| Seed coverage failure (+1 pending: GianzCoach) | 1 | 1 | 0 | [M] |
| Link / hostname misclassification | 1 | 1 | 0 | [M] |
| Price hallucination (invented number) | 1 | 1 | 0 | [M] |
| Wrong-price-selected (real number, wrong tier) | 1 | 0 | 1 | [M] |
| Engagement / view-count ignored | 1 | 0 | 1 | [H] |
| Content-quality / no narrative | 1 | 0 | 1 | [H] |
| **Total occurrences** | **~40** | 18 | ~22 | across 26 creators reviewed |

**Distribution is sharpening:** the top three — **faceless/compilation (6), HT
over-fire (5), persona miss (5)** — now dominate and pulled clearly ahead of the
mechanical leaks. Two are heuristic-class (judgment), one straddles design. The
mechanical bugs (affiliate, missed email, staleness, hostname) are real but
lower-frequency than the qualification-judgment errors.

(Class tags reference BUSINESS_RULES.md: [M] mechanical bug · [H] heuristic · [D] design decision.)

---

## Session 1 — run `2026-06-21_144632` (fitness), 15 creators reviewed

Clean (no failure mode): **ANATOLY, Coach Blue, Daniel Hristov, Hany Rambod** (4/15).

| Failure mode | Count | Creators (evidence) |
|---|---|---|
| Affiliate attribution leak | 3 | Will Tennyson (MacroFactor/Gymshark referrals), Calisthenics Reacts (`gornation?ref=`), Bronson Dant (`inbody?aff=` email) |
| Faceless classification issue | 2 | Calisthenics Reacts (compilation undetected → should DQ), Yellow Dude (faceless brand over-approved) |
| Shorts counted as activity | 2 | Girls Gone Strong (last 15 uploads all Shorts), Prosper Nutrition (last long-form 2025-09-01) |
| HT over-fire | 2 | Girls Gone Strong ($299/mo MT read as HT), Prosper ($999 MT read as HT) |
| Ownership confidence mismatch | 1 | Will Tennyson (Low when offers are his) |
| Missed bio email | 1 | Will Tennyson (2 emails in About-page text) |
| Contactability miss | 1 | Will Tennyson (wrongly WITHOUT_CONTACT) |
| Platform contamination | 1 | Fun With Calisthenics (Linktree's own "apply to" page → false DQ) |
| Seed coverage failure | 1 | STRIQfit (6 Shopify seeds extracted, never crawled) |
| Link / hostname misclassification | 1 | ATHLEAN-X (`athleanx.com` tagged "Twitter/X") |
| Persona miss (institution) | 1 | Institute for Integrative Nutrition (cert school entered funnel) |
| Price hallucination | 1 | Prosper Nutrition ($76,000 invented) |
| Endpoint over-caution | 1 | CHRIS HERIA (login-wall app read as possible HT) |

**Co-occurrence note:** Will Tennyson alone accounts for 4 modes that are causally
linked — missed bio email → contactability miss; affiliate links → ownership mismatch.
A single root fix (affiliate exclusion + bio-text email extraction) clears all four for
him. Frequency counts should be read alongside these linkages, not as 18 independent bugs.

**New failure classes discovered this session** (beyond the initial 9-mode list):
Link/hostname misclassification, Persona miss (institution), Price hallucination,
Endpoint over-caution.

---

## Observations (not yet acted on)
- The most *frequent* mode so far is **affiliate attribution leak (3)** — and it's
  mechanical, so frequency and fixability align.
- Several modes are tied at 2 (faceless, Shorts-as-activity, HT over-fire) — too early
  to rank; need more sessions.
- 4/15 creators were fully clean — the pipeline is not uniformly broken; errors cluster.

## Session 2 — same run `2026-06-21_144632`, 15 more creators reviewed

Clean / pipeline-correct verdict: **Coach Bart** (DQ, real 1:1), **Virtual Victor**
(DQ, persona), **RxMuscle** (DQ persona — was MR), **Calisthenics Victoria** (DQ),
**Real BB Podcast** (DQ). Note several "correct verdict, wrong reason" below.

| Failure mode | Count | Creators (evidence) |
|---|---|---|
| Faceless / compilation classification | 4 | Hybrid Calisthenics (real face, no-face FP), Calisthenics Watch (compilation not DQ'd), Calisthenics Worldwide (faceless PFP but consistent thumbnail face = real person), SheMoves (real face, no-face FP) |
| Persona miss (non-creator entity) | 4 | RxMuscle (news outlet), Calisthenics Victoria (sports body), Real BB Podcast (media), Virtual Victor (AI software product) |
| HT over-fire (false / misread HT) | 3 | Stephanie Long (a **sold/paid call** misread as HT funnel), Virtual Victor (Calendly signal the operator couldn't find), Real BB Podcast ("apply now" the operator couldn't find) |
| Geo / language filter miss | 2 | Kharoliya (Hindi), GianzCoach (Italian — country=IT) |
| Affiliate attribution leak | 1 | Calisthenics Worldwide (`calimove?affcode=` → $497 supplement) |
| Missed email (obfuscated) | 1 | Calisthenics Worldwide (`info [at] … [dot] com`) |
| Contactability miss | 1 | Calisthenics Worldwide (had email, routed WITHOUT_CONTACT) |
| Shorts-as-activity / staleness | 1 | Kharoliya (last real long-form > 1 year ago) |
| Wrong-price-selected (tier error) | 1 | SheMoves ($310 picked; real offer is $33/mo → LT not MT) |
| Engagement / view-count ignored | 1 | Coach Marilin (127 views on recent video = dead audience) |
| Content-quality / no narrative | 1 | Unbreakable (just records workouts, no story/brand) |
| Platform contamination (benign) | 1 | Coach Bart (13/15 pages Calendly's own site; verdict still correct) |
| Over-caution (CAPTCHA, benign) | 1 | Christ Glorified (CAPTCHA hid nothing; qualified LT) |

**Pending:** GianzCoach — IG bio linktree (with his coaching offer, in Italian) was
NOT crawled; IG discovery went to threads.com + tagged brand accounts instead.
Confirmed **seed/IG coverage gap**; verdict deferred until the linktree is crawled.

**New failure classes this session:** Geo/language filter miss, Wrong-price-selected,
Engagement/view-count ignored, Content-quality/no-narrative. **Bug that did NOT recur:**
the ATHLEAN-X `x.com` hostname bug — Unbreakable genuinely has no links (bounds that bug).

## Whole-run automated scan (2026-06-22) — prevalence beyond hand-review

> Read-only scans over the existing run data (no scraping, no pipeline change) to
> estimate how widespread the top modes are across **all 44 creators**, not just the
> 30 hand-reviewed. These are **automated-heuristic estimates**, kept separate from
> the hand-confirmed counts above.

- **Staleness / Shorts-as-activity — far more common than hand-review showed.**
  At a >180s "long-form" threshold, **9/44 are long-form-stale** (>180 days since last
  long-form, or none in last 30 uploads). 8 have **no long-form at all** in their recent
  uploads (Shorts-only): Coach Bart, Hany Rambod, Ayyappa, Women's Fitness Academy,
  Coach Elvie, Girls Gone Strong, Michelle Fitness, WOMENS FAT LOSS — plus Prosper
  (294 days). **Caveat:** the >180s threshold is uncalibrated; some may be 60–180s
  "long-form." But directionally this mode affects ~20% of the batch, not 2 creators.
  Worth a manual spot-check on Hany Rambod (big name, surprising if Shorts-only).
- **Affiliate leak — bounded.** Exactly **3 creators** run-wide carry an affiliate
  marker, all already known: Bronson Dant (`inbody?aff=`), Calisthenics Reaction
  (`gornation?ref=`), Calisthenics Worldwide (`calimove?affcode=`). The 3 markers
  (`ref=`/`aff=`/`affcode=`) cover every case here. No hidden ones.
- **Persona signals — ~16% by name.** 7 name-pattern persona/compilation hits: IIN,
  Precision Nutrition, Real BB Podcast, Virtual Victor (AI), Women's Fitness Academy,
  Calisthenics Reaction, Calisthenics Watch. **1 false positive: Calisthenics Worldwide**
  (brandy name, but a real person) — so a name pre-filter is a useful first pass but
  must NOT auto-DQ; it needs the thumbnail-face rescue (R13.2).
- **Obfuscated email — deeper than parsing.** Calisthenics Worldwide's split email
  isn't even in our stored `stage2` text → the **contact-page text wasn't captured**
  (not just unparsed). Capture gap precedes the parse gap (R13.4).

## Session 4 — the "low-value stragglers" (9 reviewed, incl. resolving GianzCoach)

> Lesson of the session: **my P(new) estimates were badly miscalibrated.** I rated
> these the *lowest* learning value (~15–35%) — they produced **3 new findings**, more
> than I forecast for the whole batch. "No crawlable data in the pipeline" ≠ "nothing to
> learn", because the pipeline's *blindness* is itself the lesson. All 9 → DQ.

| Failure mode | Count | Creators (evidence) |
|---|---|---|
| Geo / language filter miss | 3 | Ayyappa (Indian), Coach Elvie (audience COMMENTS non-English), Aman (Indian-language thumbnail + name) |
| **Niche / relevance mismatch (NEW)** | 2 | Ayyappa (not bodybuilding), Senior Nutrition Coach (elderly nutrition, not fitness) |
| Faceless / compilation | 1 | No Limits Calisthenics (105K compilation) |
| Engagement / view-count | 1 | Jimmy Leiva (low views + broken IG) |
| Shorts-as-activity / staleness | 1 | WOMENS FAT LOSS COACH (no long-form at all) |
| **Description-text link not extracted (NEW [M])** | 1 | Michelle Fitness Coach (real HT in a description-text link; pipeline reads only the structured links section) |
| Geo (resolved pending) | — | GianzCoach → DQ Italian; IG linktree DID hold the coaching offer (seed-coverage gap confirmed real, but moot vs geo) |

**New failure classes this session:** Niche/relevance mismatch, Description-text link
not extracted. **New detection signals for geo/language:** audience-comment language,
thumbnail-text language, name heuristic — all things the pipeline currently cannot see.

**Meta-finding — what the pipeline is BLIND to:** audience language (comments), content
relevance to niche, thumbnail content, and offers linked in description *text*. These are
decisive signals invisible to a "crawl the funnel + read structured links" sensor. This is
concrete backing for the dataset-is-the-product thesis: the sensor can't see what the
human can, so the labels carry the knowledge.

## Template — Session N (run `____`)
| Failure mode | Count | Creators (evidence) |
|---|---|---|
| … | | |
