#!/usr/bin/env python3
"""
Daily Twitter Digest Generator
Fetches tweets from your home timeline (Following tab), filters by engagement,
and generates a categorized markdown digest.
"""

import json
import sys
import os
import time
import urllib.parse
import urllib.request
import ssl
import certifi
import webbrowser
import html as html_mod
from datetime import datetime, timedelta, timezone
from getpass import getpass
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config.json"
TOKENS_FILE = SCRIPT_DIR / ".tokens"
CATEGORIES_FILE = SCRIPT_DIR / "categories.json"
FOLLOWING_FILE = SCRIPT_DIR / "twitter_following.txt"
DIGESTS_DIR = SCRIPT_DIR / "digests"

BEARER = "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"

# Twitter's datetime format
TW_TIME_FMT = "%a %b %d %H:%M:%S %z %Y"


def load_config():
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}


def save_config(config):
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def load_categories():
    if CATEGORIES_FILE.exists():
        return json.loads(CATEGORIES_FILE.read_text())
    return {}


def build_handle_to_category_map(categories):
    """Build reverse map: handle -> category"""
    mapping = {}
    for category, handles in categories.items():
        for handle in handles:
            mapping[handle.lower()] = category
    return mapping


def get_tokens():
    """Get auth tokens - from saved file or user input"""
    if TOKENS_FILE.exists():
        tokens = json.loads(TOKENS_FILE.read_text())
        print(f"Using saved tokens from .tokens")
        return tokens["auth_token"], tokens["ct0"]

    print("No saved tokens found. Enter your Twitter/X cookies:")
    print("(Get them from browser DevTools > Application > Cookies > x.com)")
    print()
    auth_token = getpass("auth_token: ")
    ct0 = getpass("ct0: ")

    save = input("\nSave tokens for future runs? (y/n): ").strip().lower()
    if save == "y":
        TOKENS_FILE.write_text(json.dumps({"auth_token": auth_token, "ct0": ct0}))
        os.chmod(TOKENS_FILE, 0o600)  # Owner read/write only
        print(f"Tokens saved to .tokens (chmod 600)")

    return auth_token, ct0


def fetch_twitter(url, auth_token, ct0):
    """Make authenticated request to Twitter API"""
    ctx = ssl.create_default_context(cafile=certifi.where())

    req = urllib.request.Request(url)
    req.add_header("accept", "*/*")
    req.add_header("authorization", f"Bearer {BEARER}")
    req.add_header("cookie", f"auth_token={auth_token}; ct0={ct0}")
    req.add_header("x-csrf-token", ct0)
    req.add_header("x-twitter-active-user", "yes")
    req.add_header("x-twitter-auth-type", "OAuth2Session")
    req.add_header("x-twitter-client-language", "en")
    req.add_header("content-type", "application/json")
    req.add_header("user-agent", UA)

    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"  HTTP {e.code}: {body[:200]}")
        return None
    except Exception as e:
        print(f"  Error: {e}")
        return None


def get_timeline_query_id(config):
    """Get or prompt for the HomeLatestTimeline query ID"""
    qid = config.get("timeline_query_id")
    if qid:
        return qid

    print("=" * 60)
    print("FIRST-TIME SETUP: Need HomeLatestTimeline query ID")
    print("=" * 60)
    print()
    print("Steps to get it:")
    print("1. Open x.com in your browser (logged in)")
    print("2. Click the 'Following' tab on the home page")
    print("3. Open DevTools (F12) > Network tab")
    print("4. Filter by 'HomeLatest'")
    print("5. Refresh the page (Cmd+R)")
    print("6. Click the request like 'HomeLatestTimeline?variables=...'")
    print("7. Copy the query ID from the URL:")
    print("   https://x.com/i/api/graphql/XXXXX/HomeLatestTimeline")
    print("   The XXXXX part is the query ID")
    print()
    qid = input("Paste the query ID here: ").strip()

    if qid:
        config["timeline_query_id"] = qid
        save_config(config)
        print(f"Saved query ID: {qid}")

    return qid


def get_features():
    """Current Twitter features string"""
    features = {
        "rweb_video_screen_enabled": False,
        "profile_label_improvements_pcf_label_in_post_enabled": True,
        "responsive_web_profile_redirect_enabled": False,
        "rweb_tipjar_consumption_enabled": False,
        "verified_phone_label_enabled": True,
        "creator_subscriptions_tweet_preview_api_enabled": True,
        "responsive_web_graphql_timeline_navigation_enabled": True,
        "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
        "premium_content_api_read_enabled": False,
        "communities_web_enable_tweet_community_results_fetch": True,
        "c9s_tweet_anatomy_moderator_badge_enabled": True,
        "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
        "responsive_web_grok_analyze_post_followups_enabled": True,
        "responsive_web_jetfuel_frame": True,
        "responsive_web_grok_share_attachment_enabled": True,
        "responsive_web_grok_annotations_enabled": True,
        "articles_preview_enabled": True,
        "responsive_web_edit_tweet_api_enabled": True,
        "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
        "view_counts_everywhere_api_enabled": True,
        "longform_notetweets_consumption_enabled": True,
        "responsive_web_twitter_article_tweet_consumption_enabled": True,
        "tweet_awards_web_tipping_enabled": False,
        "responsive_web_grok_show_grok_translated_post": False,
        "responsive_web_grok_analysis_button_from_backend": True,
        "post_ctas_fetch_enabled": True,
        "freedom_of_speech_not_reach_fetch_enabled": True,
        "standardized_nudges_misinfo": True,
        "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
        "longform_notetweets_rich_text_read_enabled": True,
        "longform_notetweets_inline_media_enabled": True,
        "responsive_web_grok_image_annotation_enabled": True,
        "responsive_web_grok_imagine_annotation_enabled": True,
        "responsive_web_grok_community_note_auto_translation_is_enabled": False,
        "responsive_web_enhance_cards_enabled": False,
    }
    return urllib.parse.quote(json.dumps(features))


def extract_tweets_from_timeline(data):
    """Recursively extract tweet objects from timeline response"""
    tweets = []

    def walk(obj):
        if isinstance(obj, dict):
            # Check if this is a tweet result
            if obj.get("__typename") == "Tweet" or (
                "legacy" in obj and "full_text" in obj.get("legacy", {})
            ):
                tweets.append(obj)
                return
            # Check for tweet in tweet_results
            if "tweet_results" in obj:
                result = obj["tweet_results"].get("result", {})
                if result:
                    # Handle tweets wrapped in TimelineTimelineItem
                    if result.get("__typename") == "TweetWithVisibilityResults":
                        inner = result.get("tweet", {})
                        if inner:
                            tweets.append(inner)
                    elif "legacy" in result:
                        tweets.append(result)
                return
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(data)
    return tweets


def extract_cursors(data):
    """Extract bottom cursor for pagination"""
    cursors = []

    def walk(obj):
        if isinstance(obj, dict):
            if obj.get("cursorType") == "Bottom" and "value" in obj:
                cursors.append(obj["value"])
                return
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(data)
    return cursors[0] if cursors else None


def parse_tweet(tweet_obj):
    """Parse a tweet object into a clean dict"""
    try:
        legacy = tweet_obj.get("legacy", {})
        core = tweet_obj.get("core", {})
        user_results = core.get("user_results", {}).get("result", {})

        # Get user info - try core first, then legacy
        user_core = user_results.get("core", {})
        user_legacy = user_results.get("legacy", {})

        screen_name = user_core.get("screen_name", "") or user_legacy.get(
            "screen_name", ""
        )
        display_name = user_core.get("name", "") or user_legacy.get("name", "")

        # Tweet content
        full_text = legacy.get("full_text", "")
        tweet_id = legacy.get("id_str", "") or tweet_obj.get("rest_id", "")

        # Engagement
        favorite_count = legacy.get("favorite_count", 0)
        retweet_count = legacy.get("retweet_count", 0)
        reply_count = legacy.get("reply_count", 0)
        bookmark_count = legacy.get("bookmark_count", 0)
        views = tweet_obj.get("views", {}).get("count", "0")

        # Timestamp
        created_at_str = legacy.get("created_at", "")
        created_at = None
        if created_at_str:
            try:
                created_at = datetime.strptime(created_at_str, TW_TIME_FMT)
            except ValueError:
                pass

        # Skip retweets (they start with "RT @")
        is_retweet = full_text.startswith("RT @")

        # Skip replies (unless it's a self-reply / thread)
        in_reply_to = legacy.get("in_reply_to_screen_name", "")
        is_reply = bool(in_reply_to) and in_reply_to.lower() != screen_name.lower()

        # Tweet URL
        url = f"https://x.com/{screen_name}/status/{tweet_id}" if screen_name and tweet_id else ""

        return {
            "screen_name": screen_name,
            "display_name": display_name,
            "text": full_text,
            "tweet_id": tweet_id,
            "url": url,
            "likes": favorite_count,
            "retweets": retweet_count,
            "replies": reply_count,
            "bookmarks": bookmark_count,
            "views": int(views) if views else 0,
            "created_at": created_at,
            "is_retweet": is_retweet,
            "is_reply": is_reply,
        }
    except Exception as e:
        return None


def fetch_home_timeline(auth_token, ct0, query_id, max_pages=15):
    """Fetch the Following tab timeline with pagination"""
    all_tweets = []
    cursor = None
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    features = get_features()

    for page in range(1, max_pages + 1):
        print(f"  Fetching timeline page {page}...")

        variables = {
            "count": 100,
            "includePromotedContent": False,
            "latestControlAvailable": True,
        }
        if cursor:
            variables["cursor"] = cursor

        encoded_vars = urllib.parse.quote(json.dumps(variables))
        url = f"https://x.com/i/api/graphql/{query_id}/HomeLatestTimeline?variables={encoded_vars}&features={features}"

        data = fetch_twitter(url, auth_token, ct0)
        if not data:
            print(f"  Failed to fetch page {page}, stopping.")
            break

        # Check for errors
        if "errors" in data:
            for err in data["errors"]:
                print(f"  API Error: {err.get('message', 'unknown')}")
            break

        # Extract tweets
        raw_tweets = extract_tweets_from_timeline(data)
        page_count = 0
        oldest_on_page = None

        for raw in raw_tweets:
            parsed = parse_tweet(raw)
            if not parsed or not parsed["screen_name"]:
                continue

            if parsed["created_at"]:
                if oldest_on_page is None or parsed["created_at"] < oldest_on_page:
                    oldest_on_page = parsed["created_at"]

            all_tweets.append(parsed)
            page_count += 1

        print(f"    Got {page_count} tweets", end="")
        if oldest_on_page:
            print(f" (oldest: {oldest_on_page.strftime('%Y-%m-%d %H:%M')} UTC)")
        else:
            print()

        # Check if we've gone past 24 hours
        if oldest_on_page and oldest_on_page < cutoff:
            print(f"  Reached 24h cutoff, stopping pagination.")
            break

        # Get next cursor
        next_cursor = extract_cursors(data)
        if not next_cursor:
            print(f"  No more pages.")
            break

        cursor = next_cursor
        time.sleep(1)  # Rate limit respect

    return all_tweets


def filter_tweets(tweets, min_likes=50, hours=24):
    """Filter tweets by engagement and time"""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    filtered = []

    for t in tweets:
        # Skip retweets and replies
        if t["is_retweet"] or t["is_reply"]:
            continue
        # Filter by time
        if t["created_at"] and t["created_at"] < cutoff:
            continue
        # Filter by likes
        if t["likes"] < min_likes:
            continue
        filtered.append(t)

    # Deduplicate by tweet_id
    seen = set()
    unique = []
    for t in filtered:
        if t["tweet_id"] not in seen:
            seen.add(t["tweet_id"])
            unique.append(t)

    return unique


def categorize_tweets(tweets, handle_to_category):
    """Group tweets by category"""
    categorized = {}

    for t in tweets:
        handle = t["screen_name"].lower()
        category = handle_to_category.get(handle, "Other")

        if category not in categorized:
            categorized[category] = []
        categorized[category].append(t)

    # Sort tweets within each category by likes (descending)
    for category in categorized:
        categorized[category].sort(key=lambda x: x["likes"], reverse=True)

    return categorized


def generate_digest(categorized_tweets, min_likes, date_str):
    """Generate markdown digest"""
    lines = []
    lines.append(f"# Daily Twitter Digest - {date_str}")
    lines.append(f"")
    lines.append(f"**Filter:** {min_likes}+ likes | Last 24 hours | Excluding retweets & replies")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"")

    total = sum(len(tweets) for tweets in categorized_tweets.values())
    lines.append(f"**Total tweets:** {total}")
    lines.append(f"")

    # Table of contents
    lines.append("## Contents")
    lines.append("")
    category_order = [
        "AI / ML & Research",
        "Tech CEOs & Founders",
        "VC & Investors",
        "India Startup Ecosystem",
        "Product & Growth",
        "Creators & Writers",
        "Design & UX",
        "Crypto & Web3",
        "SaaS & Enterprise",
        "Media & News",
        "Politics & Public Figures",
        "Entertainment & Sports",
        "Other",
    ]

    # Show categories in order, skip empty ones
    active_categories = []
    for cat in category_order:
        if cat in categorized_tweets and categorized_tweets[cat]:
            active_categories.append(cat)
    # Add any categories not in the predefined order
    for cat in categorized_tweets:
        if cat not in active_categories and categorized_tweets[cat]:
            active_categories.append(cat)

    for cat in active_categories:
        count = len(categorized_tweets[cat])
        anchor = cat.lower().replace(" ", "-").replace("/", "").replace("&", "and")
        lines.append(f"- [{cat}](#{anchor}) ({count} tweets)")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Each category section
    for cat in active_categories:
        tweets = categorized_tweets[cat]
        lines.append(f"## {cat}")
        lines.append("")

        for t in tweets:
            # Clean up tweet text for markdown
            text = t["text"].replace("\n", " ").strip()
            # Truncate very long tweets
            if len(text) > 280:
                text = text[:277] + "..."

            lines.append(f"**@{t['screen_name']}** ({t['display_name']})")
            lines.append(f"> {text}")
            lines.append(f"")
            lines.append(
                f"Likes: {t['likes']:,} | "
                f"Retweets: {t['retweets']:,} | "
                f"Views: {t['views']:,} | "
                f"[View Tweet]({t['url']})"
            )
            lines.append("")
            lines.append("---")
            lines.append("")

    return "\n".join(lines)


def generate_html_digest(categorized_tweets, min_likes, date_str):
    """Generate a self-contained HTML digest with embedded CSS"""
    # Build category order (same as markdown)
    category_order = [
        "AI / ML & Research",
        "Tech CEOs & Founders",
        "VC & Investors",
        "India Startup Ecosystem",
        "Product & Growth",
        "Creators & Writers",
        "Design & UX",
        "Crypto & Web3",
        "SaaS & Enterprise",
        "Media & News",
        "Politics & Public Figures",
        "Entertainment & Sports",
        "Other",
    ]
    active_categories = []
    for cat in category_order:
        if cat in categorized_tweets and categorized_tweets[cat]:
            active_categories.append(cat)
    for cat in categorized_tweets:
        if cat not in active_categories and categorized_tweets[cat]:
            active_categories.append(cat)

    total = sum(len(tweets) for tweets in categorized_tweets.values())

    def esc(text):
        return html_mod.escape(text)

    def fmt_number(n):
        if n >= 1_000_000:
            return f"{n / 1_000_000:.1f}M"
        if n >= 1_000:
            return f"{n / 1_000:.1f}K"
        return str(n)

    def cat_id(cat):
        return cat.lower().replace(" ", "-").replace("/", "").replace("&", "and")

    # Build nav items
    nav_html = ""
    for cat in active_categories:
        count = len(categorized_tweets[cat])
        cid = cat_id(cat)
        nav_html += f'<a href="#{cid}" class="nav-item" data-section="{cid}">{esc(cat)}<span class="nav-count">{count}</span></a>\n'

    # Build tweet cards
    sections_html = ""
    for cat in active_categories:
        cid = cat_id(cat)
        tweets = categorized_tweets[cat]
        cards_html = ""
        for t in tweets:
            text = t["text"].strip()
            # Preserve newlines as <br> in HTML
            text_html = esc(text).replace("\n", "<br>")
            initials = esc(t["display_name"][:2].upper()) if t["display_name"] else "?"
            cards_html += f'''<div class="tweet-card">
  <div class="tweet-header">
    <div class="avatar">{initials}</div>
    <div class="tweet-author">
      <span class="display-name">{esc(t["display_name"])}</span>
      <span class="handle">@{esc(t["screen_name"])}</span>
    </div>
  </div>
  <div class="tweet-text">{text_html}</div>
  <div class="tweet-stats">
    <span class="stat" title="Likes"><svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>{fmt_number(t["likes"])}</span>
    <span class="stat" title="Retweets"><svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M7 7h10v3l4-4-4-4v3H5v6h2V7zm10 10H7v-3l-4 4 4 4v-3h12v-6h-2v4z"/></svg>{fmt_number(t["retweets"])}</span>
    <span class="stat" title="Views"><svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"/></svg>{fmt_number(t["views"])}</span>
    <a href="{esc(t["url"])}" target="_blank" rel="noopener" class="view-link">View Tweet &rarr;</a>
  </div>
</div>
'''
        sections_html += f'''<section id="{cid}" class="category-section">
  <h2 class="category-title">{esc(cat)} <span class="category-count">{len(tweets)}</span></h2>
  {cards_html}
</section>
'''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Daily Digest - {esc(date_str)}</title>
<style>
:root {{
  --bg: #0d1117;
  --bg-secondary: #161b22;
  --bg-card: #1c2128;
  --border: #30363d;
  --text: #e6edf3;
  --text-secondary: #8b949e;
  --accent: #58a6ff;
  --accent-hover: #79c0ff;
  --likes: #f472b6;
  --retweets: #34d399;
  --views: #60a5fa;
  --nav-bg: #161b22;
  --nav-active: #1f6feb33;
  --stat-bg: #ffffff08;
}}
html.light {{
  --bg: #ffffff;
  --bg-secondary: #f6f8fa;
  --bg-card: #ffffff;
  --border: #d0d7de;
  --text: #1f2328;
  --text-secondary: #656d76;
  --accent: #0969da;
  --accent-hover: #0550ae;
  --likes: #db2777;
  --retweets: #059669;
  --views: #2563eb;
  --nav-bg: #f6f8fa;
  --nav-active: #0969da1a;
  --stat-bg: #00000008;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
}}
.layout {{
  display: flex;
  min-height: 100vh;
}}
/* Sidebar */
.sidebar {{
  position: fixed;
  top: 0;
  left: 0;
  width: 280px;
  height: 100vh;
  overflow-y: auto;
  background: var(--nav-bg);
  border-right: 1px solid var(--border);
  padding: 24px 0;
  z-index: 100;
}}
.sidebar-header {{
  padding: 0 20px 20px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 12px;
}}
.sidebar-header h1 {{
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 4px;
}}
.sidebar-header .subtitle {{
  font-size: 13px;
  color: var(--text-secondary);
}}
.nav-item {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 20px;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 14px;
  transition: all 0.15s;
  border-left: 3px solid transparent;
}}
.nav-item:hover {{
  color: var(--text);
  background: var(--nav-active);
}}
.nav-item.active {{
  color: var(--accent);
  background: var(--nav-active);
  border-left-color: var(--accent);
}}
.nav-count {{
  background: var(--stat-bg);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 2px 8px;
  font-size: 12px;
  font-weight: 500;
}}
.theme-toggle {{
  position: absolute;
  bottom: 20px;
  left: 20px;
  right: 20px;
  padding: 10px;
  background: var(--stat-bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 13px;
  text-align: center;
  transition: all 0.15s;
}}
.theme-toggle:hover {{
  color: var(--text);
  border-color: var(--accent);
}}
/* Main content */
.main {{
  margin-left: 280px;
  flex: 1;
  padding: 32px 40px;
  max-width: 900px;
}}
/* Welcome header */
.welcome {{
  margin-bottom: 36px;
  padding-bottom: 24px;
  border-bottom: 1px solid var(--border);
}}
.welcome-greeting {{
  font-size: 14px;
  text-transform: uppercase;
  letter-spacing: 1.5px;
  color: var(--text-secondary);
  margin-bottom: 6px;
}}
.welcome-title {{
  font-size: 30px;
  font-weight: 700;
  line-height: 1.3;
  margin-bottom: 10px;
}}
.welcome-title .highlight {{
  background: linear-gradient(135deg, var(--accent), #a855f7);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}}
.welcome-meta {{
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary);
  font-size: 14px;
  flex-wrap: wrap;
}}
.welcome-meta .dot {{
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--text-secondary);
  opacity: 0.5;
}}
/* Category sections */
.category-section {{
  margin-bottom: 40px;
}}
.category-title {{
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--border);
  display: flex;
  align-items: center;
  gap: 10px;
}}
.category-count {{
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
  background: var(--stat-bg);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 2px 10px;
}}
/* Tweet cards */
.tweet-card {{
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 12px;
  transition: border-color 0.15s;
}}
.tweet-card:hover {{
  border-color: var(--accent);
}}
.tweet-header {{
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}}
.avatar {{
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--accent), #a855f7);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  font-weight: 700;
  color: #fff;
  flex-shrink: 0;
}}
.tweet-author {{
  display: flex;
  flex-direction: column;
}}
.display-name {{
  font-weight: 600;
  font-size: 15px;
}}
.handle {{
  color: var(--text-secondary);
  font-size: 13px;
}}
.tweet-text {{
  font-size: 15px;
  line-height: 1.7;
  margin-bottom: 14px;
  word-wrap: break-word;
}}
.tweet-stats {{
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
}}
.stat {{
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  color: var(--text-secondary);
}}
.stat:nth-child(1) {{ color: var(--likes); }}
.stat:nth-child(2) {{ color: var(--retweets); }}
.stat:nth-child(3) {{ color: var(--views); }}
.stat svg {{ opacity: 0.85; }}
.view-link {{
  margin-left: auto;
  font-size: 13px;
  color: var(--accent);
  text-decoration: none;
  font-weight: 500;
}}
.view-link:hover {{
  color: var(--accent-hover);
  text-decoration: underline;
}}
/* Mobile menu */
.mobile-menu-btn {{
  display: none;
  position: fixed;
  top: 16px;
  left: 16px;
  z-index: 200;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 8px 12px;
  color: var(--text);
  cursor: pointer;
  font-size: 18px;
}}
/* Responsive */
@media (max-width: 768px) {{
  .mobile-menu-btn {{ display: block; }}
  .sidebar {{
    transform: translateX(-100%);
    transition: transform 0.25s;
  }}
  .sidebar.open {{ transform: translateX(0); }}
  .main {{
    margin-left: 0;
    padding: 24px 16px;
    padding-top: 60px;
  }}
  .summary {{ flex-direction: column; }}
  .summary-card {{ min-width: auto; }}
}}
</style>
</head>
<body>
<button class="mobile-menu-btn" onclick="document.querySelector('.sidebar').classList.toggle('open')">&equiv; Menu</button>
<div class="layout">
  <nav class="sidebar">
    <div class="sidebar-header">
      <h1>Daily Digest</h1>
      <div class="subtitle">{esc(date_str)} &middot; {min_likes}+ likes</div>
    </div>
    {nav_html}
    <button class="theme-toggle" onclick="toggleTheme()">Toggle Light/Dark</button>
  </nav>
  <main class="main">
    <div class="welcome">
      <div class="welcome-greeting">Good to see you</div>
      <h1 class="welcome-title">Welcome to your <span class="highlight">Daily X Digest</span></h1>
      <div class="welcome-meta">
        <span>{esc(date_str)}</span>
        <span class="dot"></span>
        <span>{total} tweets</span>
        <span class="dot"></span>
        <span>{len(active_categories)} categories</span>
        <span class="dot"></span>
        <span>{min_likes}+ likes</span>
      </div>
    </div>
    {sections_html}
  </main>
</div>
<script>
// Theme toggle
function toggleTheme() {{
  document.documentElement.classList.toggle("light");
  localStorage.setItem("theme", document.documentElement.classList.contains("light") ? "light" : "dark");
}}
(function() {{
  if (localStorage.getItem("theme") === "light") document.documentElement.classList.add("light");
}})();

// Active nav highlight on scroll
const sections = document.querySelectorAll(".category-section");
const navItems = document.querySelectorAll(".nav-item");
const observer = new IntersectionObserver(entries => {{
  entries.forEach(entry => {{
    if (entry.isIntersecting) {{
      navItems.forEach(n => n.classList.remove("active"));
      const active = document.querySelector('.nav-item[data-section="' + entry.target.id + '"]');
      if (active) active.classList.add("active");
    }}
  }});
}}, {{ rootMargin: "-20% 0px -70% 0px" }});
sections.forEach(s => observer.observe(s));

// Close mobile nav on link click
navItems.forEach(n => n.addEventListener("click", () => {{
  document.querySelector(".sidebar").classList.remove("open");
}}));
</script>
</body>
</html>'''


def main():
    print("=" * 50)
    print("  DAILY TWITTER DIGEST GENERATOR")
    print("=" * 50)
    print()

    # Load config
    config = load_config()
    min_likes = config.get("min_likes", 50)
    max_pages = config.get("max_pages", 15)

    # Get tokens
    auth_token, ct0 = get_tokens()
    print()

    # Get query ID
    query_id = get_timeline_query_id(config)
    if not query_id:
        print("ERROR: No query ID provided. Cannot proceed.")
        sys.exit(1)
    print()

    # Load categories
    categories = load_categories()
    handle_to_category = build_handle_to_category_map(categories)
    print(f"Loaded {len(handle_to_category)} categorized accounts across {len(categories)} categories")
    print()

    # Fetch timeline
    print(f"Fetching home timeline (Following tab)...")
    all_tweets = fetch_home_timeline(auth_token, ct0, query_id, max_pages)
    print(f"\nTotal raw tweets fetched: {len(all_tweets)}")

    # Filter tweets
    print(f"Filtering: {min_likes}+ likes, last 24h, no retweets/replies...")
    filtered = filter_tweets(all_tweets, min_likes=min_likes, hours=24)
    print(f"Tweets after filtering: {len(filtered)}")

    if not filtered:
        print("\nNo tweets matched the criteria. Try lowering the threshold or fetching more pages.")
        print("You can edit config.json to change 'min_likes' or 'max_pages'.")
        sys.exit(0)

    # Categorize
    categorized = categorize_tweets(filtered, handle_to_category)
    print(f"\nCategories with tweets:")
    for cat, tweets in sorted(categorized.items(), key=lambda x: -len(x[1])):
        print(f"  {cat}: {len(tweets)} tweets")

    # Generate digest
    date_str = datetime.now().strftime("%Y-%m-%d")
    digest = generate_digest(categorized, min_likes, date_str)
    html_digest = generate_html_digest(categorized, min_likes, date_str)

    # Save
    DIGESTS_DIR.mkdir(exist_ok=True)
    md_file = DIGESTS_DIR / f"{date_str}_digest.md"
    html_file = DIGESTS_DIR / f"{date_str}_digest.html"
    md_file.write_text(digest)
    html_file.write_text(html_digest)

    # Open HTML in browser
    webbrowser.open(html_file.as_uri())

    print(f"\n{'=' * 50}")
    print(f"  DIGEST SAVED:")
    print(f"    Markdown: {md_file}")
    print(f"    HTML:     {html_file}")
    print(f"  Total tweets: {len(filtered)}")
    print(f"  Categories: {len(categorized)}")
    print(f"  Opened in browser!")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
