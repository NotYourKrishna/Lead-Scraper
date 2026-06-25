---
name: sold-call-vs-discovery-call
description: a SOLD/paid call is a product (good — qualifies); a FREE discovery/strategy call is the HT-funnel signal (disqualifies). Distinguish them.
metadata: 
  node_type: memory
  type: project
  originSessionId: 76206b37-b278-4fea-ba12-29b9b285fe92
---

HT-detection edge case (operator, 2026-06-22, explicitly flagged as previously
un-communicated): not every "call" is a high-ticket signal.

- **Selling a call** (the call itself is a paid product) → GOOD sign. The call is
  the deliverable, not a mechanism to upsell into a high-ticket backend. Such a
  creator is QUALIFIED (the call is typically an LT/MT product).
- **Free discovery / strategy / clarity call** → the classic HT funnel entrance
  (apply → call → pitch). This is the disqualifying signal.

So the current logic that flags any "discovery/strategy call" as HT over-fires on
creators who *sell* a call. Misfire example: Stephanie Long was DQ'd on "discovery
call" but her call is a sold product + she has a confirmed MT → she should be
APPROVED.

**How to apply:** when a call is detected, check whether it is priced/sold (→ product,
qualify) vs free-and-gated-behind-an-application (→ HT, disqualify). Relates to
[[ht-qualification-forms]] (budget-range forms are still definitive HT) and the HT
detection notes in [[pipeline-evolution-report]].
