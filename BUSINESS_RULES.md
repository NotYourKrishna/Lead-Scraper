# Business Rules — Lead Qualification Engine

> Canonical rule reference for the pipeline. These are the *business* rules that
> define who qualifies, who is disqualified, and how leads are routed — separate
> from implementation. Every rule notes its **status**:
> ✅ enforced · 🟡 partial / inconsistent · 🔴 agreed but not yet implemented.
>
> Rules tagged **[cal 2026-06-21]** were learned or confirmed during the manual
> calibration of run `runs/fitness/2026-06-21_144632` (see CALIBRATION_FINDINGS.md).
>
> **Evidence class** (orthogonal to implementation status) — per the operator's
> 3-way split:
> - **[M] Mechanical** — objectively-wrong behavior or a definitional fact. One
>   example proves it; no further calibration needed before fixing.
> - **[H] Heuristic** — a lead-quality judgment that needs multiple reviewed
>   examples to generalize safely.
> - **[D] Design decision** — an accepted business stance (no outcome data required),
>   but needs explicit operator agreement to adopt.
>
> **Transferability** (added 2026-06-22 — STOP assuming fitness findings are universal):
> every rule is also tagged **U** universal · **F** fitness-specific · **?** unknown.

---

## 0. Rule transferability map (U / F / ?)

> The key insight from tagging: most **principles** are Universal, but several
> **thresholds/magnitudes** are Fitness-specific or Unknown and will likely shift in
> other niches. Re-validate the ? and F rows on the first non-fitness batch.

| Rule / group | Tag | Note |
|---|---|---|
| Contactability orthogonal to qualification (§2) | **U** | structural |
| Ownership / affiliate `ref=`/`aff=` not owned (§3, §4) | **U** | definitional |
| Faceless → DQ (R5.1–5.2) | **U** | HT relies on personal trust in any niche (operator design decision) |
| No-face matcher / thumbnail-face / compilation tell (R5.3, R13.2, R13.3) | **U** | detection mechanics |
| Tier-over-label; structural HT signals; budget-form = HT (R6.1–6.3) | **U** | structure is niche-agnostic |
| Sold call vs free discovery call (R6.6/R13.1) | **U** | applies to any coaching niche |
| Persona filter: institution/company/media ≠ creator (R9.1) | **U** | any niche has non-creator entities |
| Activity is #1 HT gate (R8.5, principle) | **U** | a dormant audience can't be sold HT anywhere |
| Crawl mechanics: platform-stop, seed coverage, hostname match (§10) | **U** | mechanical |
| Email: own-domain gate, bio-text, obfuscated (§11, R13.4) | **U** | mechanical |
| Engagement / content-narrative as quality signal (R13.6–13.7, principle) | **U** | weak audience = weak HT prospect anywhere |
| English-only / language detection (R13.8) | **U** | operator-wide targeting |
| **"Shorts don't count" on YouTube (R8.4)** | **F** | operator: "for this niche" — YT long-form ≠ community in fitness; re-check elsewhere |
| **Niche ROI prior — fitness pays less for HT (R13.10)** | **F** | explicitly a fitness-vs-business-niche statement |
| **Price tier thresholds: LT<$300 / MT $300–1,999 / HT $2k+ (R7.1)** | **?** | HT price points differ by niche (fitness vs business); boundaries may move |
| **Engagement cutoff (e.g. 127 views = dead) (R13.6 threshold)** | **?** | depends on sub count / niche norms; principle is U, number is ? |
| **IG/TikTok activity cutoffs: <1mo, ≤1wk between posts (R8.5 thresholds)** | **?** | reasonable default; not yet validated across niches |

---

## 1. Target / ICP

- **R1.1** ✅ The ideal lead is a creator with an **engaged, monetized audience but
  no high-ticket (HT) backend** — proven buyers, an open gap we can fill by
  building/running their HT offer.
- **R1.2** ✅ Must be English-speaking; geo/language filtered.
- **R1.3** ✅ Must be an actively-posting **personal brand** (see §5), not a faceless
  media company or compilation channel.
- **R1.4** ✅ Sells low-ticket (LT) or mid-ticket (MT) → proof of buyers. No mature
  HT backend → that's the opportunity.

## 2. Qualification vs Contactability are ORTHOGONAL

- **R2.1** ✅ **Qualification** (business-model fit) and **contactability** (can we
  reach them) are independent dimensions. One never decides the other.
- **R2.2** ✅ **Contactable = a direct email OR a YouTube email button exists.** A
  button requiring a manual CAPTCHA solve still counts — that's an automation
  limit, not an outreach limit. [cal 2026-06-21]
- **R2.3** ✅ A missing contact path **never disqualifies**. A qualified-but-unreachable
  creator routes to `*_WITHOUT_CONTACT`, staying visible. (Fixed: the line-4661 bug
  that buried Will Tennyson in DISQUALIFIED.)
- **R2.4** ✅ Report contact *quality* explicitly: `Email Found` (Y/N) and
  `Contact Method` (Email / YT button only / Email + YT button / None), so an
  immediately-reachable lead is distinguished from one needing manual retrieval.

## 3. Ownership & Attribution

- **R3.1** ✅ Each crawled page is classified: **Creator Asset / Partner Brand /
  Affiliate Offer / Unknown.** Only Creator-Asset offers may be attributed to the
  creator for pricing/tiering.
- **R3.2** 🟡 Ownership confidence must be **consistent across equivalent evidence.**
  Two creators with offers hosted on a linktree must not get High vs Low ownership
  on the same basis (Yellow Dude = High, Will Tennyson = Low — inconsistent). [cal]
- **R3.3** 🔴 **[D]** A small number of owned offers must **not disqualify** an
  otherwise-strong creator. *Reframed 2026-06-21 (operator):* minimal owned offers is
  **not itself a positive** — do not generalize "few offers = top lead" from Will
  Tennyson. Lead strength comes from **audience size + clear personal brand + audience
  trust + contactability + no HT backend**; sparse owned offers is merely
  non-disqualifying, not a virtue. (Will is a top lead *despite* thin owned offers,
  not because of them.)

## 4. Affiliate / Referral Links  [cal 2026-06-21]

- **R4.1** 🔴 A URL containing an affiliate/referral marker — `?ref=`, `&ref=`,
  `?aff=`, `/?aff=`, promo-code params — is **NOT owned by the creator.** They earn
  commission; it is not their offer.
- **R4.2** 🔴 Exclude affiliate-marked pages from **offer attribution** (do not credit
  their prices/tiers to the creator). This is the GORNATION / Calisthenics Reacts
  contamination (`gornation.com/?ref=calisthenicsreacts`).
- **R4.3** 🔴 Exclude affiliate-marked pages from **email attribution**
  (`inbody.com/?aff=apextraining` → `info@inbody.com` is a third-party leak, not the
  creator's contact — Bronson Dant).

## 5. Personal Brand / Face — THREE tiers  [cal 2026-06-21]

- **R5.1** 🔴 **[D] HARDENED 2026-06-22 — faceless = DISQUALIFY (hard gate).** Supersedes
  the earlier "score penalty, not a gate" framing. ALL faceless channels are
  disqualified **regardless of popularity**: a faceless creator can sell LT, but HT
  coaching/mentorship relies on personal trust/authority ("selling LT is one thing, HT
  is a completely different game"). Face = qualify-able; faceless = DQ.
- **R5.2** Both faceless sub-types are DQ (no longer a tiered penalty):
  1. **[D]** Face-forward personal brand → qualify-able (strong HT prospect).
  2. **[D]** Faceless **single-person brand** (Yellow Dude — books, no face) → **DQ**
     (was "weak lead"; now disqualified).
  3. **[D]** Faceless **compilation / entertainment** channel, no person (Calisthenics
     Reacts, Calisthenics Watch) → **DQ**.
  - ⚠️ **Detection is now mission-critical:** under a hard DQ, a false "faceless" =
    a false DQ (worst error). A faceless PFP is insufficient — check thumbnails for a
    consistent face (R13.2). The broken string-matcher (R5.3) MUST be fixed before this
    rule is automated, else it false-DQs real creators (Hybrid, SheMoves, Cal Worldwide,
    Cal Warrior were all real people it flagged).
- **R5.3** 🔴 **[M]** The current no-face *matcher* is broken — it fires on the literal
  word "and" and tokens like "channel"/"education". Objectively wrong; must require real
  faceless evidence, not ordinary description text.

## 6. High-Ticket (HT) Detection

- **R6.1** ✅ **Tier over label.** "coaching"/"mentorship"/"1:1" are not HT by
  themselves. `$97 coaching` is LOW ticket.
- **R6.2** ✅ Structural HT signals (definitive): application/qualification funnel,
  sales/strategy/discovery call, private 1:1 / mentorship / mastermind, $2k+ offer,
  done-for-you.
- **R6.3** ✅ **Budget-range qualification form = definitive HT.** A form asking
  "preferred budget range you can comfortably invest" is a dead HT giveaway (Hany
  Rambod — `fst-7.com` coaching form). [cal]
- **R6.4** 🟡 **A visible sub-$2k price downgrades an HT structural guess to MT/LT.**
  A coaching page showing $299/mo or $999 is **MT, not HT**, even with "1-on-1"
  language. The detector currently over-fires HT on MT pages (Girls Gone Strong
  $299/mo, Prosper $999). [cal]
- **R6.5** ⛔ **CONTRADICTED — do not adopt as written.** Originally: "structural HT
  score should override an ambiguous tier-depth label." Calibration disproved this:
  Hany Rambod had `HT Level = None / Score 0` with an ambiguous→HT tier-depth label,
  and he is a **correct** DQ (real budget-range form). Applying R6.5 would have wrongly
  un-DQ'd him. The real lesson is **R6.3** (detect the budget form and set HT at the
  source), not "trust the score over the label." Pending replacement.

## 7. Offer Tiering

- **R7.1** ✅ LOW < $300 · MID $300–$1,999 · HIGH ≥ $2,000.
- **R7.2** ✅ Routing is driven primarily by **offer TYPE/structure**, not exact
  price. Price is supporting evidence, never the sole gate (Greg Doucette $99,700).
- **R7.3** ✅ Buyer-only categories (Supplement, Physical Product) are monetization
  proof but **not coaching demand**; they never manufacture an HT disqualification.

## 8. Cadence / Activity  [cal 2026-06-21]

- **R8.1** 🟡 Existing: a >90-day gap *between recent uploads* → REVIEW_REQUIRED.
- **R8.2** 🔴 **[H/M]** **Add staleness-from-today.** "Months since last *meaningful*
  upload" is a distinct, first-class signal. A channel dark ~9–10 months → **automatic
  DQ** regardless of offer (Girls Gone Strong, Prosper). Threshold is still a heuristic
  to calibrate.
- **R8.3** 🔴 Consequence: cadence is a real safety net. Without it, fixing HT
  over-firing (R6.4) would start wrongly approving inactive MT creators.
- **R8.4** 🔴 **[M] "Active creator" = recent meaningful LONG-FORM video; Shorts do
  NOT count as activity.** *Confirmed by upload trace 2026-06-22:* the pipeline records
  "Last Upload Date" from the most recent uploads-playlist item *of any type*, so a 16s
  Short marks a dead channel active. Girls Gone Strong's last 15 uploads are ALL Shorts
  (≤62s exercise demos); Prosper's last long-form was 2025-09-01 (~9.7mo ago) despite
  Shorts through 2026-03-23. The data **is** available (`videos.list`
  `contentDetails.duration`); define last-meaningful-upload as the most recent video
  with duration > ~180s (or exclude ≤60s / `#shorts`) and measure staleness from that.
  This is mechanical, not a missing-data problem.
- **R8.5** 🔴 **[D] ACTIVITY IS THE #1 PREREQUISITE FOR HT — check it first.** Before
  evaluating offers, confirm the creator is active; a dormant audience can't be sold HT.
  Measure in order: (1) **YouTube long-form** (R8.4 — Shorts don't count; you can't
  build community off YT Shorts in this niche). (2) **If YT long-form is stale, fall back
  to Instagram / TikTok** (links from bio or video descriptions) — those are short-form-
  native ecosystems where activity DOES count. **IG/TikTok "active" = last post < 1 month
  ago AND ≤ ~1 week between posts.** (3) Active on ANY platform → passes the gate; active
  nowhere → **DQ**. (Supersedes/expands R13.5 with concrete thresholds and gate ordering.)

## 9. Persona — Individual vs Institution  [cal 2026-06-21]

- **R9.1** 🔴 Certification schools / sports governing bodies / companies are **not
  our ICP**, even when they openly sell HT (IIN — $3.5k Health Coach Training; also
  Precision Nutrition, Calisthenics Victoria). They are correct DQs but should be
  filtered **upstream** to save crawl budget and audit noise.
- **R9.2** Openly-displayed HT pricing is normally a great signal — but only for an
  **individual creator**, not an institution.

## 10. Crawl & Navigation

- **R10.1** ✅ Human-mimicking nav priority (Store > Programs > Membership > … >
  Contact); structured product extraction on store/pricing pages.
- **R10.2** 🔴 **Creator's own form ≠ platform's marketing pages.** A creator's
  application/coaching form *hosted on* Typeform/Linktree/Calendly is a REAL signal
  (Daniel Hristov's 1-1 Typeform, Coach Blue's 1:1 application = correct HT DQs).
  The platform's *own* marketing pages (`typeform.com/pricing`,
  `linktr.ee/features/shops`, "apply to become a partner") are **contamination**
  (Fun With Calisthenics false DQ). The fix distinguishes the two — not "stop at
  platform domains". [cal]
- **R10.3** 🔴 **Crawl all of a creator's extracted seed URLs.** STRIQfit had 6
  Shopify program seeds extracted in Stage 1 but only the app link was crawled —
  the store that would have qualified him was dropped. [cal]
- **R10.4** 🔴 **Match social domains on exact hostname, not substring.**
  `athleanx.com` was tagged "Twitter/X" because it ends in `x.com`, discarding a
  14.3M creator's real website → false "no crawlable links". [cal]

## 11. Email / Contact Discovery

- **R11.1** ✅ Trust chain: About-page bio link → YouTube channel description →
  latest video description → Instagram bio → own-domain page text.
- **R11.2** ✅ Own-domain gate: accept an email only if its domain matches a creator
  own-domain or appears on a creator-owned page (reject third-party/agency).
- **R11.3** 🔴 **Extract emails from the About-page description TEXT**, not only from
  links and video descriptions. Will Tennyson's two emails (`contact@willtennyson.ca`,
  `willt@night.co`) were in plain bio text and were missed. [cal]
- **R11.4** 🔴 Apply R4.3 — never source a contact email from an affiliate-linked
  third-party domain.

## 12. Routing Buckets (exactly 5)

- **R12.1** ✅ `APPROVED_WITH_CONTACT` — qualified + reachable.
- **R12.2** ✅ `APPROVED_WITHOUT_CONTACT` — qualified + no contact path found (still a
  lead; go find a contact).
- **R12.3** ✅ `MANUAL_REVIEW_WITH_CONTACT` — needs review + reachable.
- **R12.4** ✅ `MANUAL_REVIEW_WITHOUT_CONTACT` — needs review + no contact path.
- **R12.5** ✅ `DISQUALIFIED` — **business-model disqualification ONLY** (confirmed HT
  backend, faceless compilation per R5.2.3, institution per R9.1, dead channel per
  R8.2). Never a data-collection limitation.
- **R12.6** ✅ Conservative default: when genuinely uncertain, route to Manual Review,
  never silently drop.

---

## 13. Session-2 calibration additions (2026-06-22)
> New rules from the second 15-creator review. Logical home noted in brackets.

- **R13.1 [H] Sold/paid call ≠ HT funnel.** If a creator *sells* a call (the call is
  the paid product), that is a GOOD sign — it's a product, not an upsell mechanism. A
  **free** discovery/strategy call is the HT signal. The pipeline must distinguish
  *paid call* (qualifies, LT/MT) from *free discovery call* (HT). Misfire: Stephanie
  Long DQ'd on "discovery call" but her call is a sold product → should be APPROVED.
  [refines §6 HT]
- **R13.2 [H] Faceless = PFP-only is insufficient evidence.** No face in the profile
  picture but a **consistent face across video thumbnails** = one identifiable person
  runs the channel = real personal brand (Calisthenics Worldwide). Detection must look
  at thumbnails/video, not just PFP/bio. [refines §5]
- **R13.3 [M] Compilation-channel tell:** bio language like *"if you'd like your
  video/clip/bio removed, contact us"* signals a reaction/compilation channel →
  DISQUALIFY (operator: "remove all compilation channels"). Calisthenics Watch.
  [refines §5 R5.2.3]
- **R13.4 [M] Parse obfuscated / split emails.** `info [at] domain [dot] com` →
  `info@domain.com` (replace `[at]`→`@`, `[dot]`→`.`; handle spaced variants). Creators
  split emails to dodge scrapers. Calisthenics Worldwide's email was missed this way.
  [refines §11]
- **R13.5 [H] Cross-platform reach & activity count.** When a creator links IG / TikTok,
  note follower size **and** posting activity there too — some are inactive on YouTube
  but active/larger on IG. A YT-quiet creator may still be a strong lead. [refines §8]
- **R13.6 [H] Engagement / view-count is a quality signal.** Very low recent-video views
  (e.g. 127) indicate a dead/unengaged audience → weak HT prospect even with a decent
  subscriber count. Coach Marilin. [new — Audience Quality]
- **R13.7 [H] Content-quality / narrative signal.** A creator with no story or
  personal-brand narrative — just raw workout recordings, nothing distinctive — is a
  weak HT prospect even if a face is present. Unbreakable Women's Fitness. (Hard to
  operationalize; flag for human review.) [new — Audience Quality]
- **R13.8 [M] Language-detection at discovery.** Non-English-*content* creators slip
  past the country filter when channel metadata says US/unknown. Italian (GianzCoach,
  country=IT) and Hindi (Kharoliya) creators reached crawl. Need content-language
  detection, not just `country`. [refines discovery filters]
- **R13.9 [M] Price selection when multiple prices exist.** Don't default to the
  highest figure — pick the creator's actual recurring/headline offer. SheMoves was
  mis-tiered MT on a $310 figure when the real offer is $33/mo (LT). [refines §7]
- **R13.10 [D] Niche ROI context.** Fitness audiences are less likely to pay HT prices
  (no direct cash ROI) than business/make-money niches. Treat as a niche-level prior on
  HT-prospect quality, not a per-creator gate. [refines §1 ICP]

## 14. Session-4 additions (2026-06-23) — what the sensor is blind to
> The "low-value" stragglers surfaced these. Theme: decisive signals the pipeline
> currently cannot see.

- **R14.1 [U][D] Niche / relevance gate.** A channel surfaced by discovery must actually
  be IN the target niche — discovery returns false-niche matches. Off-niche → DQ.
  Evidence: Ayyappa (general Indian content, not bodybuilding), Senior Nutrition Coach
  (nutrition for the elderly, not fitness). [new failure mode]
- **R14.2 [U][M] Extract links embedded in the DESCRIPTION TEXT, not only the structured
  links section.** Michelle Fitness Coach's real HT offer was a link in her description
  text → the pipeline missed it entirely (parallel to bio-text emails, R11.3). A
  description-text-only HT is a silent false-negative. [new mechanical bug]
- **R14.3 [U][M/H] Language detection needs signals beyond `country` metadata:**
  (a) **audience-comment language** — Coach Elvie looked like a good lead but her comments
  are non-English → DQ; (b) **thumbnail-text language** — Aman's recent thumbnail had
  Indian-language text; (c) **name heuristic** — "Aman" reads as an Indian name. Combine
  these with country. [extends R13.8]
- **R14.4 [U] Compilation detection is content-based, not funnel-based.** No Limits
  Calisthenics had 0 crawlable funnel pages yet is a clear compilation → DQ. The signal
  comes from the channel's videos/thumbnails, not its (absent) funnel. [reinforces R5.2.3]
