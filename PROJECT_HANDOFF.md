# PROJECT HANDOFF — Lead Scraper (high-ticket creator outreach)

> Master context for resuming this project in a fresh Claude Code session (e.g. on a
> new machine). Claude Code chat history is stored **locally** per machine and is NOT
> synced to your Claude account — a new laptop will not have the old transcripts. This
> document + the committed files reconstruct the full state. Read this first, then read
> `BUSINESS_RULES.md`, `CALIBRATION_FINDINGS.md`, `FAILURE_MODE_FREQUENCY.md`, and
> `REGRESSION_SET.csv`.

---

## 0. HOW TO RESUME ON A NEW MACHINE

1. `git clone` the repo (GitHub: `NotYourKrishna/Lead-Scraper`). This brings `pipeline.py`
   and all committed docs.
2. Restore Claude memory: copy the files from `claude_memory_backup/` in the repo into
   your new machine's Claude memory dir
   (`~/.claude/projects/<munged-project-path>/memory/`). These hold durable rules the
   agent recalls each session.
3. `runs/` (raw scraped data incl. creator emails) is **gitignored** and stays on the old
   laptop — copy the folder manually only if you need the raw batch outputs. The pending
   review work is captured PII-free in `BATCH3_REVIEW_QUEUE.md`.
4. Recreate `.env` with `YOUTUBE_API_KEY` (and IG creds if using IG-assisted discovery).
5. `pip install` deps (playwright, google-api-python-client, beautifulsoup4, psutil,
   python-dotenv); `playwright install chromium`.
6. Start the new chat by pasting: *"Read PROJECT_HANDOFF.md, BUSINESS_RULES.md,
   CALIBRATION_FINDINGS.md, FAILURE_MODE_FREQUENCY.md, REGRESSION_SET.csv, and
   BATCH3_REVIEW_QUEUE.md, then continue from §9 Current State."*

---

## 1. WHAT THIS PROJECT IS
A pipeline that discovers YouTube fitness (and later other-niche) creators, crawls their
funnels, and classifies them as outreach leads. **Goal:** find creators with a monetized
audience but NO high-ticket (HT) backend — they're the ones we can build/run an HT offer
for. The crawler is a **sensor**; the real asset is **`REGRESSION_SET.csv`** — a growing
set of human-labeled verdicts (the "judgment layer"). Operating principle (operator):
*a dumb crawler + thousands of labels beats a perfect crawler + thirty.*

## 2. PIPELINE ARCHITECTURE (`pipeline.py`)
- **Stage 1 — Discovery:** YouTube search across niche queries → filter (sub band, geo,
  activity) → for each survivor, Playwright-extract About-page links + video-description
  signals → `stage1.csv`. Cross-run dedup via `outputs/<niche>/seen_channels.json`.
- **Stage 2 — Funnel crawl:** per-creator browser crawls each seed funnel → `stage2.csv`.
- **Stage 3 — Classify:** funnel depth, HT detection, ownership, confidence → `stage3.csv`.
- **Stage 4 — ICP score** (internal).
- **Stage 5 — Route:** 5 buckets — `APPROVED_WITH/ WITHOUT_CONTACT`,
  `MANUAL_REVIEW_WITH/WITHOUT_CONTACT`, `DISQUALIFIED`.
- CLI: `py pipeline.py --niche fitness` (full); `--from-stage N` resume; `--to-stage 1`
  discovery only; `--run-dir <folder>` to target a run.

## 3. BUSINESS RULES — see `BUSINESS_RULES.md` (canonical, ~50 rules)
Each rule tagged: **[M]** mechanical bug · **[H]** heuristic · **[D]** design decision,
AND transferability **U** universal / **F** fitness-specific / **?** unknown. Highlights:
- **Qualification ≠ contactability** (separate dimensions; missing contact never DQs).
- **Faceless = DISQUALIFY** (hardened) — regardless of popularity; HT needs a personal
  brand. Detection must use thumbnails (a faceless PFP ≠ faceless channel).
- **Affiliate links** (`?ref=`/`?aff=`/`?affcode=`) = NOT owned — exclude from offers & email.
- **Activity is the #1 HT gate** — measure by recent **long-form** YT (Shorts don't count);
  if YT-stale, fall back to IG/TikTok recency (<1mo, ≤1wk between posts).
- **Sold/paid call = product (qualify); free discovery call = HT funnel (DQ).**
- **Persona filter:** institutions/companies/media/podcasts/software/sports-bodies ≠ creators → DQ.
- **HT tiering by structure, not label;** a visible sub-$2k price downgrades an HT guess to MT.
- Niche-relevance, engagement/view-count, content-narrative, obfuscated-email parsing,
  exact-hostname matching, description-text link/email extraction — all in the doc.

## 4. REGRESSION DATASET — `REGRESSION_SET.csv` (the primary asset)
~50 labeled creators: 44 fitness (calibrated) + 6 dropshipping (reconstructed, marked
`VERIFY`). Columns: creator, niche, subs, pipeline_verdict, true_verdict, verdict_class
(CC=correct+correct / CW=correct-verdict-wrong-reason / W=wrong), true_reasons, key_rules,
session, source, channel_url. **Append every newly reviewed creator.** Operator's logging
format going forward: `Creator / Pipeline verdict / My verdict / Reason / Rule(s)`.
Strict accounting rule: **"correct verdict + wrong reason" is NOT a success** — it's a
latent failure (fixing the masking logic would flip it to wrong).

## 5. FAILURE MODES — `FAILURE_MODE_FREQUENCY.md`
Per-mode occurrence counts across 4 review sessions. Top three (dominant): **faceless/
compilation classification, HT over-fire, persona miss.** Goal: prioritize fixes by
frequency × impact, not recency. Mechanical fix-ready bugs (do NOT implement piecemeal —
the latent-failure trap below): faceless matcher (#1 — broken, fires on the word "and"),
`x.com` substring hostname bug, affiliate attribution, seed coverage, bio/description-text
email & link extraction, Shorts-as-activity.

## 6. PIPELINE BUGS FOUND + FIXES
- **Contactability conflated with qualification** (line ~4661): `if is_ht_disqualified or
  not contactable` buried qualified-but-unreachable creators in DISQUALIFIED. **Fixed** →
  DISQUALIFIED is now business-model-only; contact split keyed on `contactable`. (Committed
  `8252f22`.)
- **No-face matcher broken** — fires on "and"/"channel"/"education" → false faceless flags
  on real people (62/80 of batch-3 discovery). Now a *hard DQ*, so this is mechanical bug #1
  (a false faceless = a false DQ). NOT yet fixed.
- **HT over-fire** — "Ambiguous, No Price/Structure → HT" DQs even when structural HT score
  is None/Medium; masks the real disqualifier (persona/inactivity). The big open accuracy issue.
- Affiliate-as-owned, `athleanx.com`→Twitter hostname bug, seed-coverage (extracted seeds
  not crawled), bio/description-text emails+links missed, price hallucination/wrong-tier,
  persona/niche-relevance/engagement signals — all documented with creator evidence in
  `CALIBRATION_FINDINGS.md`. **Per operator: NOT implemented yet — still in calibration.**

## 7. THE CRAWLER CRASH SAGA + FIXES (batch 3, a multi-hour debug)
Long runs kept dying as clean freezes (no traceback, process gone), ~16–41 min in.
- **WRONG hypothesis #1: machine sleep.** Refuted — operator was actively using the laptop, lid open.
- **WRONG hypothesis #2: Playwright Chrome orphans / Python OOM.** Refuted — Python RAM was
  flat ~70 MB; the 37 chrome.exe were the operator's *own* browser (no automation flag).
- **Leading hypothesis (evidence, not proof): memory pressure.** Memory sampler showed
  Chrome peaking 7.2 GB and system free dipping to **0.5 GB** during heavy *store* creators
  (Fourthwall/Shopify). The visible browser + operator's Chrome usage collided → silent OOM.
- **Fixes applied (in `pipeline.py`):**
  1. **Stage 1 incremental write + context recycle every 20** (was: write only at the very
     end → any death lost everything). Now `stage1.csv` flushes per creator.
  2. **Stage 2 checkpoint per creator + resume** — `stage2.csv` flushes after each creator;
     on rerun it loads the partial and skips done creators. **This is the most valuable fix:
     it converts a catastrophic failure into a one-creator interruption, cause-agnostic.**
  3. **Headless crawl + `--renderer-process-limit`/`--disable-gpu`** — drops Chrome's memory
     footprint (the leading-hypothesis fix; bought breathing room but margin was thin, 0.5 GB).
  4. **Guaranteed per-creator browser cleanup (try/finally).**
  5. Sleep inhibitor (`SetThreadExecutionState`) — added during the wrong-sleep-theory phase;
     harmless, low value.
- **Result:** batch 3 completed clean — 76 attempted / 73 classified, 0 crashes, 86.8 min
  crawl, peak Chrome 7.2 GB, min free 0.5 GB, 6 abnormal-time creators (store-heavy; Madeleine
  Storace 544s). **Per operator: one clean run is evidence, not proof — treat headless-memory
  as the leading hypothesis until a second clean run.**

## 8. AGENT / PROCESS MISTAKES (so the next session avoids them)
- **Scored myself generously** — counted "right bucket, wrong reason" as success until the
  operator forced the strict 3-way accounting. True success was ~20%, not ~53%.
- **Inferred from priors instead of verifying** — wrong on Hany/Daniel (assumed
  contamination = false DQ; both real HT), Lavender (assumed name→face), Precision (assumed
  big company→HT). Lesson: verify the visible offer/face, don't pattern-match.
- **Chased a satisfying explanation over evidence** — pushed "sleep" twice in the crash
  debug without data. Operator's rule now: **post-mortem from collected evidence only, no
  speculation until the data is checked.**
- **Latent-failure trap:** the pipeline's apparent accuracy is propped up by HT over-fire
  coincidentally landing persona/inactive creators in DQ. Fixing HT *in isolation* would
  flip ~4–6 creators to wrongly-approved. **Persona filtering + activity gating must land
  before any HT-logic change.**

## 9. CURRENT STATE (resume here)
- **Mode:** calibration. NO new scrape, NO implementing the mechanical fixes yet — grow the
  labeled dataset first.
- **Batch 3 complete:** 73 classified creators (2 approved, 34 MR, 37 DQ) in run
  `runs/fitness/2026-06-24_112519/`.
- **PENDING TASK:** the operator is reviewing all 73 (see `BATCH3_REVIEW_QUEUE.md` — every
  creator with channel link, pipeline verdict, and the agent's prediction). As the operator
  gives verdicts, append each to `REGRESSION_SET.csv` in the format
  `Creator / Pipeline verdict / My verdict / Reason / Rule(s)`.
- **Top thing to learn from batch 3:** whether the **"Ambiguous, No Price/Structure → HT"**
  DQ path is a systemic over-fire (≈15 creators DQ'd this way; many HT:None/Medium). The
  HT:None ones (Taliyah Joelle 481K, Kirra Mitlo, Jenn Clayton, Kelsey Poulter, ACE Method,
  Graham Hicks) are the strongest false-DQ candidates. Second test: do "Private 1:1" DQs hold
  (is 1:1 always HT?).

## 10. NEXT STEPS
1. Finish labeling batch 3 → append to `REGRESSION_SET.csv`.
2. Re-score the failure-mode distribution with the new labels.
3. Decide whether the dataset is large enough to start implementing the mechanical fixes
   (faceless matcher first) — with persona + activity gates BEFORE any HT change.
4. Only then consider another scrape (fitness queries are largely exhausted; needs new
   sub-niche queries, or pivot niche to validate the U/F/? rule tags).

## 11. FILE INVENTORY
- `pipeline.py` — the whole pipeline (all batch-3 + crash fixes included).
- `BUSINESS_RULES.md`, `CALIBRATION_FINDINGS.md`, `FAILURE_MODE_FREQUENCY.md` — calibration docs.
- `REGRESSION_SET.csv` — the labeled dataset (the asset).
- `BATCH3_REVIEW_QUEUE.md` — the 73 pending reviews (PII-free).
- `PIPELINE_EVOLUTION_REPORT.md` — long-form project post-mortem (older).
- `claude_memory_backup/` — copy of the agent's durable memory files.
- `runs/` — raw run outputs (gitignored; contains scraped emails; lives on the old laptop only).
