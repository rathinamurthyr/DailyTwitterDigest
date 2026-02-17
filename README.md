# Daily Twitter/X Digest Tool

Generate a daily categorized digest of high-engagement tweets from people you follow on Twitter/X. No API key required — uses browser cookies for authentication.

Outputs both a **markdown file** and a **visual HTML page** (dark/light theme, category navigation, tweet cards) that auto-opens in your browser.

## Quick Start with Claude Code

This tool is designed to work as a [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill. Once set up, just type `/daily-twitter` in any session to generate your digest.

### 1. Clone and install

```bash
git clone https://github.com/rathinamurthyr/DailyTwitterDigest.git
cd DailyTwitterDigest
pip install certifi
```

### 2. Install the skill

```bash
mkdir -p ~/.claude/skills/daily-twitter/
cp SKILL.md ~/.claude/skills/daily-twitter/SKILL.md
```

### 3. One-time setup

Before your first run, you need two things from your browser:

**Browser cookies** — Go to [x.com](https://x.com) (logged in) > DevTools (F12) > Application > Cookies > `https://x.com`. Copy `auth_token` and `ct0`. The script will prompt you on first run and save them locally.

**Query ID** — On x.com, click the "Following" tab > DevTools > Network tab > filter by `HomeLatest` > refresh the page. Copy the ID from `https://x.com/i/api/graphql/{QUERY_ID}/HomeLatestTimeline` and paste it when prompted.

### 4. Run

From any Claude Code session:

```
/daily-twitter
```

That's it. Claude will run the digest, open the HTML in your browser, and present you a summary of the day's top tweets.

### Using with OpenAI Codex

The tool works with any AI coding agent that supports shell execution. Point it at the script:

```bash
python3 daily_digest.py
```

The generated digest files will be in the `digests/` folder.

## Running Standalone

You can also run the script directly without Claude Code:

```bash
python3 daily_digest.py
```

First run will prompt for cookies and query ID, then save them for future runs.

Output:
- `digests/YYYY-MM-DD_digest.md` — markdown digest
- `digests/YYYY-MM-DD_digest.html` — visual HTML digest (auto-opens in browser)

## Configuration

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

Edit `config.json`:

| Setting | Default | Description |
|---------|---------|-------------|
| `min_likes` | 50 | Minimum likes to include a tweet |
| `max_pages` | 15 | Max timeline pages to fetch |
| `hours` | 24 | Time window in hours |

### Following list

Run `./fetch_following.sh` to save your following list to `twitter_following.txt` (used for reference, not required for digest generation).

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

**Note:** Twitter may rotate GraphQL query IDs periodically. If the tool stops working, re-capture the query ID from your browser.

## License

MIT
