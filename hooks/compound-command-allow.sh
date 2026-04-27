#!/bin/bash
# PreToolUse hook: auto-allow compound Bash commands where every subcommand
# matches an allow pattern from settings.json and none matches a disallow
# pattern. When any subcommand is unknown, output nothing and exit 0 —
# falls through to the normal permission prompt (not a deny).
#
# Reads patterns from:
#   1. ~/.claude/settings.json (global)
#   2. .claude/settings.json (project, if present)
#   3. .claude/settings.local.json (project local, if present)
#
# Pattern format in settings: "Bash(<prefix>:*)"
# The hook extracts <prefix> and does a starts-with match against each
# subcommand in the compound command.

set -uo pipefail

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
[ -z "$COMMAND" ] && exit 0

CWD=$(echo "$INPUT" | jq -r '.cwd // empty' 2>/dev/null)
[ -z "$CWD" ] && CWD="."

# --- Build allow/disallow prefix lists from settings files ---

GLOBAL_SETTINGS="$HOME/.claude/settings.json"
PROJECT_SETTINGS="$CWD/.claude/settings.json"
PROJECT_LOCAL_SETTINGS="$CWD/.claude/settings.local.json"

extract_bash_prefixes() {
    local file="$1"
    local key="$2"
    [ -f "$file" ] || return
    # Extract "Bash(<prefix>:*)" patterns, pull out <prefix>
    jq -r ".permissions.${key}[]? // empty" "$file" 2>/dev/null \
        | sed -n 's/^Bash(\([^)]*\))/\1/p' \
        | sed -E 's/:?\*$//' \
        | sed 's/:$//'
}

ALLOW_PREFIXES=""
DISALLOW_PREFIXES=""

for f in "$GLOBAL_SETTINGS" "$PROJECT_SETTINGS" "$PROJECT_LOCAL_SETTINGS"; do
    ALLOW_PREFIXES="$ALLOW_PREFIXES
$(extract_bash_prefixes "$f" "allow")"
    DISALLOW_PREFIXES="$DISALLOW_PREFIXES
$(extract_bash_prefixes "$f" "disallow")"
done

# Deduplicate and remove empty lines
ALLOW_PREFIXES=$(echo "$ALLOW_PREFIXES" | sort -u | sed '/^$/d')
DISALLOW_PREFIXES=$(echo "$DISALLOW_PREFIXES" | sort -u | sed '/^$/d')

# If no allow prefixes found, can't make a decision — fall through
[ -z "$ALLOW_PREFIXES" ] && exit 0

# --- Decompose compound command (respects quoted strings) ---

PARTS=$(python3 -c "
import shlex, sys
cmd = sys.stdin.read().strip()
# Replace comments
import re
cmd = re.sub(r'#.*$', '', cmd, flags=re.MULTILINE)
# Split on unquoted shell operators: &&, ||, ;, |
# Strategy: use shlex to tokenize (respects quotes), then rejoin
# tokens into subcommands by splitting on operator tokens.
parts = []
current = []
i = 0
tokens = shlex.split(cmd, posix=True)
# shlex loses operators, so instead split the raw string respecting quotes
in_single = False
in_double = False
escaped = False
buf = []
for ch in cmd:
    if escaped:
        buf.append(ch)
        escaped = False
        continue
    if ch == '\\\\':
        buf.append(ch)
        escaped = True
        continue
    if ch == \"'\" and not in_double:
        in_single = not in_single
        buf.append(ch)
        continue
    if ch == '\"' and not in_single:
        in_double = not in_double
        buf.append(ch)
        continue
    if not in_single and not in_double:
        buf.append(ch)
    else:
        buf.append(ch)
raw = ''.join(buf)
# Now split on operators outside quotes
result = []
current_part = []
i = 0
in_sq = False
in_dq = False
while i < len(cmd):
    c = cmd[i]
    if c == \"'\" and not in_dq:
        in_sq = not in_sq
        current_part.append(c)
        i += 1
    elif c == '\"' and not in_sq:
        in_dq = not in_dq
        current_part.append(c)
        i += 1
    elif not in_sq and not in_dq:
        if cmd[i:i+2] == '&&':
            result.append(''.join(current_part).strip())
            current_part = []
            i += 2
        elif cmd[i:i+2] == '||':
            result.append(''.join(current_part).strip())
            current_part = []
            i += 2
        elif c == '|':
            result.append(''.join(current_part).strip())
            current_part = []
            i += 1
        elif c == ';':
            result.append(''.join(current_part).strip())
            current_part = []
            i += 1
        else:
            current_part.append(c)
            i += 1
    else:
        current_part.append(c)
        i += 1
if current_part:
    result.append(''.join(current_part).strip())
for p in result:
    if p:
        print(p)
" <<< "$COMMAND")

# --- Check each subcommand ---

matches_any_prefix() {
    local cmd="$1"
    local prefixes="$2"
    while IFS= read -r prefix; do
        [ -z "$prefix" ] && continue
        # [[ == ]] supports glob matching natively in bash.
        # The pattern is unquoted on the RHS so * expands as a glob.
        # shellcheck disable=SC2053
        if [[ "$cmd" == ${prefix}* ]]; then
            return 0
        fi
    done <<< "$prefixes"
    return 1
}

ALL_SAFE=true
CHECKED_ANY=false
while IFS= read -r part; do
    part=$(echo "$part" | sed 's/^\s*//;s/\s*$//')
    [ -z "$part" ] && continue
    CHECKED_ANY=true

    # Check disallow first — any match means unsafe
    if matches_any_prefix "$part" "$DISALLOW_PREFIXES"; then
        ALL_SAFE=false
        break
    fi

    # Check allow — must match at least one prefix
    if ! matches_any_prefix "$part" "$ALLOW_PREFIXES"; then
        ALL_SAFE=false
        break
    fi
done <<< "$PARTS"

if [ "$ALL_SAFE" = true ] && [ "$CHECKED_ANY" = true ]; then
    jq -n '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"allow",permissionDecisionReason:"All components of compound command match allow patterns"}}'
fi
exit 0
