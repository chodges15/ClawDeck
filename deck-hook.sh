#!/bin/bash
# deck-hook.sh — ClawDeck hook that reports Claude Code session state.
#
# Called by Claude Code hooks with a single argument: the state.
#   idle        — Claude is waiting for user input
#   pending     — Claude is about to use a tool (PreToolUse)
#   working     — Claude's tool finished running (PostToolUse)
#   permission  — Claude needs permission approval (Notification)
#
# Writes a status file to /tmp/deck-status/ keyed by TTY name so the
# Stream Deck controller can map it to a grid slot.

STATE="${1:-unknown}"
STATUS_DIR="/tmp/deck-status"

# The hook process inherits the terminal's TTY.
# Read it directly — this is instant (no ps/grep).
SHELL_TTY=$(tty 2>/dev/null)
if [ -z "$SHELL_TTY" ] || [ "$SHELL_TTY" = "not a tty" ]; then
    # Fallback: read from the parent process chain
    SHELL_PID=$(ps -o ppid= -p $PPID 2>/dev/null | tr -d ' ')
    [ -z "$SHELL_PID" ] && exit 0
    SHELL_TTY=$(ps -o tty= -p "$SHELL_PID" 2>/dev/null | tr -d ' ')
    [ -z "$SHELL_TTY" ] || [ "$SHELL_TTY" = "??" ] && exit 0
    SHELL_TTY="/dev/$SHELL_TTY"
fi

# Normalize: "/dev/ttys003" → "ttys003"
TTY_NAME="${SHELL_TTY#/dev/}"

[ -z "$TTY_NAME" ] && exit 0

HOOK_INPUT=$(cat 2>/dev/null || true)
[ -z "$HOOK_INPUT" ] && HOOK_INPUT="null"

TOOL_INFO="null"
if [ "$STATE" = "pending" ]; then
    TOOL_INFO="$HOOK_INPUT"
fi

# Ensure status directory exists
mkdir -p "$STATUS_DIR" 2>/dev/null

# Write status file (atomic via temp + mv)
TMPFILE=$(mktemp "$STATUS_DIR/.tmp.XXXXXX")
printf '{"state":"%s","tty":"%s","ts":%s,"hook_input":%s,"tool_input":%s}' \
    "$STATE" "$TTY_NAME" "$(date +%s)" "$HOOK_INPUT" "$TOOL_INFO" > "$TMPFILE"
mv "$TMPFILE" "$STATUS_DIR/$TTY_NAME"
