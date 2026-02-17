# Daily Twitter/X Digest Tool

Generate a daily categorized digest of high-engagement tweets from people you follow on Twitter/X. No API key required — uses browser cookies for authentication.

## Features

- Fetches your "Following" timeline (chronological feed)
- Filters by engagement threshold (default: 50+ likes)
- Filters to last 24 hours, excludes retweets and replies
- Categorizes tweets into sections (AI/ML, VCs, Founders, Creators, etc.)
- Generates a clean markdown digest with tweet text and links
- Saves tokens locally so you only enter them once

## Setup

### 1. Install

```bash
git clone https://github.com/YOUR_USERNAME/DailyTwitterSummaryTool.git
cd DailyTwitterSummaryTool
```

Python 3.9+ required. Install the only dependency:

```bash
pip install certifi
```

### 2. Fetch your following list

```bash
./fetch_following.sh
```

This prompts for your browser cookies and saves your following list to `twitter_following.txt`.

### 3. Get your browser cookies

1. Go to [x.com](https://x.com) (logged in)
2. Open DevTools (F12) > **Application** tab > **Cookies** > `https://x.com`
3. Copy the values for `auth_token` and `ct0`

### 4. Get the HomeLatestTimeline query ID

1. On x.com, click the **"Following"** tab
2. Open DevTools (F12) > **Network** tab
3. Type `HomeLatest` in the filter box
4. Refresh the page (Cmd+R)
5. Find the request to `HomeLatestTimeline?variables=...`
6. Copy the query ID from the URL: `https://x.com/i/api/graphql/{QUERY_ID}/HomeLatestTimeline`

### 5. Configure

```bash
cp config.example.json config.json
```

Edit `config.json` and paste your query ID:

```json
{
  "min_likes": 50,
  "max_pages": 15,
  "hours": 24,
  "timeline_query_id": "YOUR_QUERY_ID_HERE"
}
```

### 6. Run

```bash
python3 daily_digest.py
```

First run will prompt for your cookies and optionally save them to `.tokens`.

Output is saved to `digests/YYYY-MM-DD_digest.md`.

## Customization

### Categories

Edit `categories.json` to map Twitter handles to your own categories:

```json
{
  "AI / ML & Research": ["karpathy", "AndrewYNg", "sama"],
  "My Custom Category": ["handle1", "handle2"]
}
```

Accounts not in any category appear under "Other".

### Settings

In `config.json`:

| Setting | Default | Description |
|---------|---------|-------------|
| `min_likes` | 50 | Minimum likes to include a tweet |
| `max_pages` | 15 | Max timeline pages to fetch (more = slower but covers more time) |
| `hours` | 24 | Time window in hours |

## Claude Code Integration

If you use [Claude Code](https://claude.ai/code), copy the skill file:

```bash
mkdir -p ~/.claude/skills/daily-twitter/
cp SKILL.md ~/.claude/skills/daily-twitter/SKILL.md
```

Then run `/daily-twitter` from any Claude Code session.

## File Structure

```
DailyTwitterSummaryTool/
├── daily_digest.py          # Main digest generator
├── fetch_following.sh       # Fetches your following list
├── categories.json          # Handle-to-category mapping
├── config.example.json      # Config template
├── config.json              # Your config (gitignored)
├── .tokens                  # Your auth cookies (gitignored)
├── twitter_following.txt    # Your following list (gitignored)
├── SKILL.md                 # Claude Code skill definition
└── digests/                 # Generated digests (gitignored)
```

## Security

- `.tokens` is chmod 600 (owner read/write only) and gitignored
- Cookies are never logged or transmitted
- Query IDs are not sensitive (they're public in Twitter's JS bundle)
- To invalidate tokens: log out of x.com and log back in

## How it works

This tool uses Twitter/X's internal GraphQL API (the same one your browser uses) with your session cookies. No official API key or paid tier needed.

**Note:** Twitter may rotate GraphQL query IDs periodically. If the tool stops working, re-capture the query ID from your browser (Step 4).

## License

MIT
