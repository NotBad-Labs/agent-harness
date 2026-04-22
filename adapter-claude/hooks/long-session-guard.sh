#!/bin/bash
# PreToolUse (Bash): 会话时长检查，超过阈值提示先 /compact 或 /phase-closeout。
# 不阻塞（exit 0），仅 stderr 输出提醒，每会话只提示一次。
#
# 时长基于 session log 第一行时间戳（由 log-file-change.sh 写入）。
#
# Configuration (env vars, all optional):
#   AGENT_HARNESS_SESSION_LOG         session log 路径
#                                     默认 "$PROJECT_ROOT/.claude/session-log.txt"
#   AGENT_HARNESS_SESSION_WARN_FLAG   提示标志文件路径
#                                     默认 "$PROJECT_ROOT/.claude/.long-session-warned"
#   AGENT_HARNESS_SESSION_THRESHOLD   阈值（分钟，默认 60）

set -eo pipefail

PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
[ -z "$PROJECT_ROOT" ] && exit 0

SESSION_LOG="${AGENT_HARNESS_SESSION_LOG:-$PROJECT_ROOT/.claude/session-log.txt}"
[ ! -f "$SESSION_LOG" ] && exit 0

# 提示标志文件（每会话只提一次）
SEEN_FLAG="${AGENT_HARNESS_SESSION_WARN_FLAG:-$PROJECT_ROOT/.claude/.long-session-warned}"
[ -f "$SEEN_FLAG" ] && exit 0

# 读 session log 第一行时间（HH:MM 格式）
FIRST_LINE=$(head -1 "$SESSION_LOG" 2>/dev/null || echo "")
[ -z "$FIRST_LINE" ] && exit 0

FIRST_TIME=$(echo "$FIRST_LINE" | awk '{print $1}')
[ -z "$FIRST_TIME" ] && exit 0
echo "$FIRST_TIME" | grep -qE '^[0-9]{2}:[0-9]{2}$' || exit 0

# 计算分钟差（使用 GNU date 或 BSD date -j -f）
NOW=$(date '+%H:%M')
if date -j -f "%H:%M" "$FIRST_TIME" "+%s" >/dev/null 2>&1; then
    # BSD (macOS)
    FIRST_EPOCH=$(date -j -f "%H:%M" "$FIRST_TIME" "+%s" 2>/dev/null || echo "0")
    NOW_EPOCH=$(date -j -f "%H:%M" "$NOW" "+%s" 2>/dev/null || echo "0")
else
    # GNU (Linux)
    FIRST_EPOCH=$(date -d "$FIRST_TIME" "+%s" 2>/dev/null || echo "0")
    NOW_EPOCH=$(date -d "$NOW" "+%s" 2>/dev/null || echo "0")
fi

[ "$FIRST_EPOCH" = "0" ] || [ "$NOW_EPOCH" = "0" ] && exit 0

DIFF_SECONDS=$(( NOW_EPOCH - FIRST_EPOCH ))
# 跨日处理（负数加 24h）
[ "$DIFF_SECONDS" -lt 0 ] && DIFF_SECONDS=$(( DIFF_SECONDS + 86400 ))
DIFF_MIN=$(( DIFF_SECONDS / 60 ))

THRESHOLD="${AGENT_HARNESS_SESSION_THRESHOLD:-60}"

if [ "$DIFF_MIN" -gt "$THRESHOLD" ]; then
    echo "" >&2
    echo "Long Session 提示：" >&2
    echo "  本会话已持续约 ${DIFF_MIN} 分钟（阈值 ${THRESHOLD} 分钟）" >&2
    echo "  建议：先调用 /compact 或 /phase-closeout 再继续，避免上下文过载" >&2
    echo "  本提示每会话只显示一次" >&2
    echo "" >&2
    mkdir -p "$(dirname "$SEEN_FLAG")"
    touch "$SEEN_FLAG"
fi

exit 0
