---
name: ig-bio-email-gap
description: "Pipeline does not extract emails from Instagram bios, missing some real creator contacts"
metadata: 
  node_type: memory
  type: project
  originSessionId: 76206b37-b278-4fea-ba12-29b9b285fe92
---

The pipeline sources contact emails from: About-page bio links, YouTube channel
description, and creator-own-domain page text (third-party/agency emails are
deliberately rejected — see the email-trust logic in `run_stage3`). It does **not**
extract emails written in an Instagram bio.

**Why it matters:** Some creators put their real booking/management email only in
their IG bio. Example: Jewish Fitness Coach's genuine contact is
`teamyoel@marquis-mgt.com` (IG bio), but his YouTube About page had only social
links, so the pipeline found no trustworthy email and routed him to DISQUALIFIED
(no contact path) rather than guessing a third-party agency address.

**How to apply:** A future contactability enhancement is to have the
Instagram-assisted discovery step also regex emails out of the IG bio text and feed
them in as a trusted source (the IG profile is the creator's own). Relates to
[[ig-ht-behind-tagged-accounts]] which already extends IG scraping for tagged
business accounts.
