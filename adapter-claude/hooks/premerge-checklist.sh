#!/bin/bash
# PreToolUse (Bash): 拦截 gh pr merge，提示消费项目 status 文件是否最近更新。
# 近 N 小时无更新 → exit 2 提示。
#
# Configuration (env vars, all optional):
#   AGENT_HARNESS_STATUS_FILE           status 文件名（相对 repo root）
#                                       默认 "STATUS.md"
#   AGENT_HARNESS_STATUS_WINDOW_HOURS   最近更新窗口（小时）
#                                       默认 "24 hours ago"
#   AGENT_HARNESS_STATUS_SKIP           设为 "1" 跳过本 hook

set -euo pipefail

if [ "${AGENT_HARNESS_STATUS_SKIP:-0}" = "1" ]; then
    exit 0
fi

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if ! echo "$COMMAND" | grep -qE '^[[:space:]]*gh pr merge\b'; then
    exit 0
fi

PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
[ -z "$PROJECT_ROOT" ] && exit 0

cd "$PROJECT_ROOT"

STATUS_FILE="${AGENT_HARNESS_STATUS_FILE:-STATUS.md}"
WINDOW="${AGENT_HARNESS_STATUS_WINDOW_HOURS:-24 hours ago}"

# 如果消费项目不使用 status 文件（空值），跳过
if [ -z "$STATUS_FILE" ]; then
    exit 0
fi

# 如果文件根本不存在，跳过（consumer 可能用其他状态机制）
[ ! -f "$STATUS_FILE" ] && exit 0

LAST_STATUS_COMMIT=$(git log -1 --since="$WINDOW" --format=%H -- "$STATUS_FILE" 2>/dev/null || echo "")

if [ -z "$LAST_STATUS_COMMIT" ]; then
    echo "PR 合并前提示：" >&2
    echo "  近 $WINDOW 未更新 $STATUS_FILE。" >&2
    echo "  合并后应立即更新 $STATUS_FILE + 确认 Review 结论已留痕。" >&2
    echo "  若已在 PR 描述里完成留痕，可让用户显式授权后重试（AGENT_HARNESS_STATUS_SKIP=1）。" >&2
    exit 2
fi

exit 0
