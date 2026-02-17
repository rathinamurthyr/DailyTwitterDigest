---
name: daily-twitter
description: Generate a daily Twitter/X digest with high-engagement tweets from accounts you follow, categorized by topic
---

# Daily Twitter Digest

Run the daily Twitter digest generator to fetch and categorize high-engagement tweets.

## Steps

1. Find the project directory by looking for `daily_digest.py`:
   ```bash
   find ~/Documents -name "daily_digest.py" -path "*/DailyTwitterDigest/*" 2>/dev/null | head -1
   ```

2. Run the digest script from that directory:
   ```bash
   python3 daily_digest.py
   ```

3. After the script completes, read the generated digest file from the `digests/` folder and present the tweets to the user organized by category.

4. If the script fails due to missing query ID, guide the user:
   - Open x.com, click the "Following" tab
   - Open DevTools (F12) > Network tab
   - Filter by "HomeLatest"
   - Refresh the page
   - Copy the query ID from the URL: `https://x.com/i/api/graphql/XXXXX/HomeLatestTimeline`
   - Add it to `config.json`

5. If tokens are expired, guide the user to delete the `.tokens` file and re-run the script to enter fresh cookies.
