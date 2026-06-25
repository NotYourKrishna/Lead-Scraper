---
name: no-face-scoring-not-blocking
description: RULE HARDENED 2026-06-22 — faceless channels are DISQUALIFIED regardless of popularity (HT needs a personal brand); accurate face detection is now critical
metadata: 
  node_type: memory
  type: project
  originSessionId: 76206b37-b278-4fea-ba12-29b9b285fe92
---

**Current rule (operator, 2026-06-22 — "please remember this"):** ALL faceless
channels are DISQUALIFIED, regardless of subscriber count / popularity. Reasoning:
a faceless creator can sell low-ticket (PDFs, courses, memberships) but **high-ticket
coaching/mentorship/masterminds rely on personal trust and authority** — "selling LT
is one thing, HT is a completely different game." Since the service builds HT offers,
a faceless creator is a poor fit → DQ.

This **supersedes** the earlier (2026-06-21) position that no-face should be a
lead-quality score penalty / Manual-Review signal rather than a hard gate. The
operator has converged on a harder rule: face = qualify-able, faceless = DQ.

Faceless covers BOTH sub-types — both are DQ:
- Faceless single-person brand (e.g. Yellow Dude — sells books, never shows face) → DQ.
- Faceless compilation / entertainment channel, no person behind it (e.g. Calisthenics
  Reacts, Calisthenics Watch — clips of random athletes) → DQ.
Personal brand that shows a face → qualify-able.

**Detection is now mission-critical** (a false "faceless" = a false DQ, the worst error):
- A faceless PROFILE PICTURE is not enough to call a channel faceless — check video
  THUMBNAILS: a consistent face across many videos = a real person runs it → NOT
  faceless (Calisthenics Worldwide, Calisthenics Warrior were real people the
  string-matcher wrongly flagged).
- The current no-face string-matcher is broken (fires on the word "and", "channel",
  "education") and MUST be replaced before this DQ rule is automated — otherwise it
  false-DQs real creators (Hybrid Calisthenics, SheMoves, etc.).
- Compilation tell: bio text like "if you'd like your video/clip/bio removed, contact
  us" → compilation → DQ.

Relates to [[affiliate-links-not-owned]] and the HT notes in [[pipeline-evolution-report]].
