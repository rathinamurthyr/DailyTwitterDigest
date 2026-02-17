#!/bin/bash
# Fetch Twitter/X following list
# Uses the GraphQL Following endpoint with correct query ID

SCRIPT_DIR="$(dirname "$0")"
OUTPUT_FILE="${SCRIPT_DIR}/twitter_following.txt"
DEBUG_FILE="${SCRIPT_DIR}/debug_response.json"
USER_ID="16777965"

echo "=== Twitter/X Following Fetcher ==="
echo ""
echo "Paste your cookies from browser DevTools:"
echo ""

# Read tokens with masked input — shows * for each character
read_masked() {
  local prompt="$1"
  local result=""
  printf "%s" "$prompt"
  while IFS= read -r -s -n 1 char; do
    if [[ -z "$char" ]]; then
      break
    elif [[ "$char" == $'\x7f' || "$char" == $'\b' ]]; then
      if [[ -n "$result" ]]; then
        result="${result%?}"
        printf "\b \b"
      fi
    else
      result+="$char"
      printf "*"
    fi
  done
  echo ""
  eval "$2='$result'"
}

read_masked "auth_token: " AUTH_TOKEN
read_masked "ct0: " CT0
echo ""
echo "Fetching following list..."
echo ""

BEARER="AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
QID="M3LO-sJg6BCWdEliN_C2fQ"
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"

FEATURES='%7B%22rweb_video_screen_enabled%22%3Afalse%2C%22profile_label_improvements_pcf_label_in_post_enabled%22%3Atrue%2C%22responsive_web_profile_redirect_enabled%22%3Afalse%2C%22rweb_tipjar_consumption_enabled%22%3Afalse%2C%22verified_phone_label_enabled%22%3Atrue%2C%22creator_subscriptions_tweet_preview_api_enabled%22%3Atrue%2C%22responsive_web_graphql_timeline_navigation_enabled%22%3Atrue%2C%22responsive_web_graphql_skip_user_profile_image_extensions_enabled%22%3Afalse%2C%22premium_content_api_read_enabled%22%3Afalse%2C%22communities_web_enable_tweet_community_results_fetch%22%3Atrue%2C%22c9s_tweet_anatomy_moderator_badge_enabled%22%3Atrue%2C%22responsive_web_grok_analyze_button_fetch_trends_enabled%22%3Afalse%2C%22responsive_web_grok_analyze_post_followups_enabled%22%3Atrue%2C%22responsive_web_jetfuel_frame%22%3Atrue%2C%22responsive_web_grok_share_attachment_enabled%22%3Atrue%2C%22responsive_web_grok_annotations_enabled%22%3Atrue%2C%22articles_preview_enabled%22%3Atrue%2C%22responsive_web_edit_tweet_api_enabled%22%3Atrue%2C%22graphql_is_translatable_rweb_tweet_is_translatable_enabled%22%3Atrue%2C%22view_counts_everywhere_api_enabled%22%3Atrue%2C%22longform_notetweets_consumption_enabled%22%3Atrue%2C%22responsive_web_twitter_article_tweet_consumption_enabled%22%3Atrue%2C%22tweet_awards_web_tipping_enabled%22%3Afalse%2C%22responsive_web_grok_show_grok_translated_post%22%3Afalse%2C%22responsive_web_grok_analysis_button_from_backend%22%3Atrue%2C%22post_ctas_fetch_enabled%22%3Atrue%2C%22freedom_of_speech_not_reach_fetch_enabled%22%3Atrue%2C%22standardized_nudges_misinfo%22%3Atrue%2C%22tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled%22%3Atrue%2C%22longform_notetweets_rich_text_read_enabled%22%3Atrue%2C%22longform_notetweets_inline_media_enabled%22%3Atrue%2C%22responsive_web_grok_image_annotation_enabled%22%3Atrue%2C%22responsive_web_grok_imagine_annotation_enabled%22%3Atrue%2C%22responsive_web_grok_community_note_auto_translation_is_enabled%22%3Afalse%2C%22responsive_web_enhance_cards_enabled%22%3Afalse%7D'

ALL_USERS=""
CURSOR=""
PAGE=1

while true; do
  echo "  Page ${PAGE}..."

  # Build variables
  if [ -z "$CURSOR" ]; then
    VARS=$(python3 -c "
import urllib.parse, json
v = {'userId': '${USER_ID}', 'count': 100, 'includePromotedContent': False, 'withGrokTranslatedBio': False}
print(urllib.parse.quote(json.dumps(v)))
")
  else
    VARS=$(python3 -c "
import urllib.parse, json
v = {'userId': '${USER_ID}', 'count': 100, 'cursor': '${CURSOR}', 'includePromotedContent': False, 'withGrokTranslatedBio': False}
print(urllib.parse.quote(json.dumps(v)))
")
  fi

  RESPONSE=$(curl -s "https://x.com/i/api/graphql/${QID}/Following?variables=${VARS}&features=${FEATURES}" \
    -H 'accept: */*' \
    -H "authorization: Bearer ${BEARER}" \
    -H 'content-type: application/json' \
    -H "cookie: auth_token=${AUTH_TOKEN}; ct0=${CT0}" \
    -H "referer: https://x.com/following" \
    -H "user-agent: ${UA}" \
    -H "x-csrf-token: ${CT0}" \
    -H 'x-twitter-active-user: yes' \
    -H 'x-twitter-auth-type: OAuth2Session' \
    -H 'x-twitter-client-language: en')

  # Save first page for debugging
  if [ "$PAGE" -eq 1 ]; then
    echo "$RESPONSE" | python3 -m json.tool > "$DEBUG_FILE" 2>/dev/null || echo "$RESPONSE" > "$DEBUG_FILE"
  fi

  # Parse response
  PAGE_DATA=$(echo "$RESPONSE" | python3 -c "
import sys, json

def find_users_and_cursor(data, users, cursors):
    if isinstance(data, dict):
        # User object: screen_name is now in 'core', followers in 'legacy'
        core = data.get('core', {})
        legacy = data.get('legacy', {})
        if 'screen_name' in core:
            sn = core.get('screen_name', '')
            name = core.get('name', '')
            followers = legacy.get('followers_count', 0)
            if sn:
                users.append(f'@{sn}|{name}|{followers}')
            return
        # Fallback: old structure where screen_name is in legacy
        if 'screen_name' in legacy:
            sn = legacy.get('screen_name', '')
            name = legacy.get('name', '')
            followers = legacy.get('followers_count', 0)
            if sn:
                users.append(f'@{sn}|{name}|{followers}')
            return
        if data.get('cursorType') == 'Bottom' and 'value' in data:
            cursors.append(data['value'])
            return
        for v in data.values():
            find_users_and_cursor(v, users, cursors)
    elif isinstance(data, list):
        for item in data:
            find_users_and_cursor(item, users, cursors)

try:
    data = json.load(sys.stdin)

    if 'errors' in data:
        for e in data['errors']:
            print(f'ERROR:{e.get(\"message\", \"unknown\")}')
        sys.exit(0)

    users = []
    cursors = []
    find_users_and_cursor(data, users, cursors)

    seen = set()
    for u in users:
        handle = u.split('|')[0]
        if handle not in seen:
            seen.add(handle)
            print(u)

    if cursors:
        print(f'CURSOR:{cursors[0]}')

    if not users:
        print('NO_USERS_FOUND')
except Exception as e:
    print(f'PARSE_ERROR:{e}')
")

  # Check for errors
  ERROR_LINE=$(echo "$PAGE_DATA" | grep "^ERROR:\|^PARSE_ERROR:")
  if [ -n "$ERROR_LINE" ]; then
    echo "  $ERROR_LINE"
    echo "  Debug saved to: ${DEBUG_FILE}"
    break
  fi

  NEW_USERS=$(echo "$PAGE_DATA" | grep "^@")
  NEXT_CURSOR=$(echo "$PAGE_DATA" | grep "^CURSOR:" | sed 's/^CURSOR://')

  NEW_COUNT=$(echo "$NEW_USERS" | grep -c "^@" 2>/dev/null || echo "0")
  echo "    Found ${NEW_COUNT} users on this page"

  if [ -n "$NEW_USERS" ]; then
    if [ -z "$ALL_USERS" ]; then
      ALL_USERS="$NEW_USERS"
    else
      ALL_USERS="${ALL_USERS}
${NEW_USERS}"
    fi
  fi

  if [ -z "$NEXT_CURSOR" ] || [ -z "$NEW_USERS" ]; then
    break
  fi

  CURSOR="$NEXT_CURSOR"
  PAGE=$((PAGE + 1))
  sleep 1
done

# Clear sensitive variables
unset AUTH_TOKEN CT0

# Save results
if [ -n "$ALL_USERS" ]; then
  TOTAL=$(echo "$ALL_USERS" | grep -c "^@")
  echo "handle|display_name|followers" > "$OUTPUT_FILE"
  echo "$ALL_USERS" >> "$OUTPUT_FILE"
  echo ""
  echo "=== Done! Found ${TOTAL} accounts ==="
  echo "Saved to: ${OUTPUT_FILE}"
else
  echo ""
  echo "=== Found 0 accounts ==="
  echo "Debug response saved to: ${DEBUG_FILE}"
  echo "Share debug_response.json here so we can diagnose."
fi

echo ""
echo "REMINDER: Log out of x.com and log back in to invalidate your token!"
