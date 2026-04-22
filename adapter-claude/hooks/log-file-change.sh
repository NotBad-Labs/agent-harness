#!/bin/bash
# PostToolUse (Edit|Write): 记录文件修改到 session log。
# 由 PostToolUse hook 触发（matcher: Edit|Write）。
# 压缩后仍可查阅。
#
# Configuration (env vars, all optional):
#   AGENT_HARNESS_SESSION_LOG  session log 路径
#                              默认 "$PROJECT_ROOT/.claude/session-log.txt"

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [ -n "$FILE_PATH" ]; then
    PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
    [ -z "$PROJECT_ROOT" ] && exit 0
    REL_PATH="${FILE_PATH#$PROJECT_ROOT/}"
    TIMESTAMP=$(date '+%H:%M')
    SESSION_LOG="${AGENT_HARNESS_SESSION_LOG:-$PROJECT_ROOT/.claude/session-log.txt}"
    mkdir -p "$(dirname "$SESSION_LOG")"
    echo "$TIMESTAMP $REL_PATH" >> "$SESSION_LOG"
fi

exit 0
