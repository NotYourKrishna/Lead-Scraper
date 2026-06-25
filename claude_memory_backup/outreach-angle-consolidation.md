---
name: outreach-angle-consolidation
description: "For creators with many scattered offers, the outreach angle should pitch consolidating them under one high-ticket service"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 76206b37-b278-4fea-ba12-29b9b285fe92
---

When a qualified creator has **fragmented offers** — multiple courses, ebooks, free
resources, guides, book-a-call links, and/or several MT–HT prices sitting out in
the open — the outreach angle should be: **"Consolidate these scattered resources
under a single roof — a high-ticket service I would build & run for you."**

**Why:** A big price (anything above ~$1k) sitting in the open with no qualification
step, no application, no sales conversation is *scary to the buyer* and leaks
conversions. A creator juggling many disconnected offerings has no coherent
ascension path. Both are concrete, creator-specific funnel weaknesses that make a
strong, non-generic pitch. This is the flip side of the [[ht-qualification-forms]]
logic: HT offers *hide* price behind qualification; a fragmented creator exposing
many prices openly is precisely who needs that structure built for them.

**How to apply:** Implemented in `classify_creator` — triggers when a QUALIFIED
creator has ≥3 distinct monetization asset types OR ≥2 distinct visible price
points (`Offer Fragmentation = Y`), producing a "QUALIFIED (consolidation play)"
angle. The qualification logic is price-structure-based, not price-magnitude-based:
a visible €1700 self-serve offer is still Mid Ticket (qualified), because it lacks
the application/call *structure* that defines a mature HT backend.
