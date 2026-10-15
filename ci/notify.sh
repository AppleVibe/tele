#!/usr/bin/env bash
# notify.sh <text on success or start> [text on failure]
# sends a private telegram message about a ci run when the notification secrets are set
[ -n "$NOTIFY_TOKEN" ] && [ -n "$NOTIFY_CHAT" ] || exit 0
case "${STATUS:-}" in
  success) text="✅ $1" ;;
  failure) text="❌ ${2:-$1}" ;;
  cancelled) text="⏹ ${2:-$1} (cancelled)" ;;
  *) text="$1" ;;
esac
url="$GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID"
# the text goes through stdin: on windows runners curl's arguments pass the
# ansi code page, which turns emoji into "?"
printf '%s\n%s' "$text" "$url" | curl -sS -m 30 -o /dev/null "https://api.telegram.org/bot$NOTIFY_TOKEN/sendMessage" \
  --data-urlencode "chat_id=$NOTIFY_CHAT" \
  --data-urlencode "text@-" \
  --data-urlencode 'link_preview_options={"is_disabled":true}' || true
