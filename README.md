# YouTube Lead Scraper — Setup Instructions

## What this does
Searches YouTube for channels in a given niche, filters by subscriber count and recent
activity, pulls plain-text emails and "wealth signal" language from channel descriptions,
and extracts any bio links (Linktree, Calendly, websites). Outputs everything to a CSV.

This is Stage 1 only — bulk filtering. Stage 2 (visiting bio links + facecam check) will
be added once Stage 1 results look good.

## Setup (run these in your terminal, in this folder)

1. Install Python packages:
   ```
   pip install -r requirements.txt
   ```

2. Open `lead_scraper.py` and check the config section near the top:
   ```python
   NICHE_QUERY = "dropshipping business"   # change this to test other niches
   MIN_SUBS = 500
   MAX_DAYS_INACTIVE = 90
   MAX_RESULTS = 25                         # keep this low while testing
   ```

3. **Important: regenerate your API key** before running this for real, since it was
   shared in a chat. Go to Google Cloud Console > Credentials > regenerate the key,
   then paste the new key into the `API_KEY` variable in the script.

4. Run it:
   ```
   python3 lead_scraper.py
   ```

5. Check the output file `leads_dropshipping_test.csv` in this same folder.

## What to check in the results
- Are the channels actually facecam/human-presence channels? (Stage 1 doesn't filter
  this yet — that's next.)
- Are the subscriber counts and upload dates accurate?
- Are the wealth signal keywords catching the right channels, or too many false positives?
- How many emails got captured vs how many show "No plain-text email"?

Bring the CSV back to this conversation (or describe what you see) and we'll tune the
filters and add the Stage 2 bio-link + facecam check next.

## Notes on quota
Each search costs ~100 units, each channel lookup ~1-3 units. Free tier = 10,000 units/day.
At MAX_RESULTS=25 you'll use roughly 100-200 units per run — you can run this many times
a day without hitting limits.
