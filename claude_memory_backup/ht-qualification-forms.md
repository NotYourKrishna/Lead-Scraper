---
name: ht-qualification-forms
description: High-ticket offers hide behind multi-step qualification forms (Typeform) that screen for revenue + investment capital
metadata: 
  node_type: memory
  type: project
  originSessionId: 76206b37-b278-4fea-ba12-29b9b285fe92
---

A major HT backend pattern: the offer is gated behind a **multi-step qualification form** (often Typeform) reached by clicking a CTA button inside a bio link's landing page. Confirmed example: **Saamir Mithwani** — bio → "Join Brandify" → "Scale Your Brand Today" button → a Typeform that, once filled, redirects to a **Calendly** booking link for a high-ticket mentorship. The crawler originally never filled the form, so it missed the HT offer and misread a stray "$50" as a membership (there was no $50 offer).

**The tell:** forms asking *"what is your current monthly revenue?"* AND *"how much cash do you have set aside to invest in yourself / the business?"* with options in the **thousands ($2k–$10k)**. Those questions exist only to qualify a buyer for a high-ticket program — they never appear on a low/mid-ticket checkout. Detecting that language alone = HT (see `HT_QUALIFIER_INVEST` / `HT_QUALIFIER_REVENUE` in pipeline.py).

**How to apply:** once a button inside a bio link is clicked and form elements appear, FILL the form to reach the end and see what's on the other side (a Calendly/booking link ⇒ HT). Use real LEAD_IDENTITY for email/name/phone; fill text fields with harmless filler; for revenue/budget questions pick the **highest** option so the form routes you to the booking page (the "qualified" path) rather than a rejection. Implemented in `fill_and_advance_form()`. Relates to [[ig-ht-behind-tagged-accounts]].
