#!/bin/bash
# PostToolUse (Bash gh pr merge): PR 合并后提示创建 checkpoint。
# 不阻塞合并（exit 0），仅 stderr 输出提醒。
#
# 触发条件：近 N 天 merge commits 达到阈值，建议运行 /phase-closeout skill。
#
# Configuration (env vars, all optional):
#   AGENT_HARNESS_CHECKPOINT_DIR            checkpoint 目录（相对 repo root）
#                                           默认 "docs/memory/checkpoints"
#   AGENT_HARNESS_MERGE_WINDOW_DAYS         merge 统计窗口天数
#                                           默认 "7"
#   AGENT_HARNESS_MERGE_THRESHOLD           触发 checkpoint 提示的合并数阈值
#                                           默认 "3"
#   AGENT_HARNESS_POST_MERGE_EXTRA_SCRIPT   合并后额外运行的可选脚本（接收 PR 号作参数）
#                                           默认 ""（不运行）

set -eo pipefail

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# 仅处理 gh pr merge
if ! echo "$COMMAND" | grep -qE '^[[:space:]]*gh pr merge\b'; then
    exit 0
fi

PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
[ -z "$PROJECT_ROOT" ] && exit 0
cd "$PROJECT_ROOT"

WINDOW_DAYS="${AGENT_HARNESS_MERGE_WINDOW_DAYS:-7}"
THRESHOLD="${AGENT_HARNESS_MERGE_THRESHOLD:-3}"
CHECKPOINT_DIR_REL="${AGENT_HARNESS_CHECKPOINT_DIR:-docs/memory/checkpoints}"

RECENT_MERGES=$(git log --since="${WINDOW_DAYS} days ago" --merges --first-parent --oneline 2>/dev/null | wc -l | tr -d ' ')

if [ "${RECENT_MERGES:-0}" -ge "$THRESHOLD" ]; then
    CHECKPOINT_DIR="$PROJECT_ROOT/$CHECKPOINT_DIR_REL"
    LATEST_CHECKPOINT=$(ls -t "$CHECKPOINT_DIR"/*.md 2>/dev/null | head -1 | xargs -I{} basename {} 2>/dev/null || echo "无")

    echo "" >&2
    echo "Phase Compaction 提示：" >&2
    echo "  近 ${WINDOW_DAYS} 天合并 ${RECENT_MERGES} 个 PR（阈值 ${THRESHOLD}）" >&2
    echo "  最近 checkpoint：${LATEST_CHECKPOINT}" >&2
    echo "  建议：调用 /phase-closeout skill 生成 checkpoint" >&2
    echo "  位置：${CHECKPOINT_DIR_REL}/<YYYY-MM-DD>-<topic>.md" >&2
    echo "" >&2
fi

# 可选：运行 consumer 自定义后合并脚本（如 anti-pattern scan / lint 报告等）
LAST_PR=$(echo "$COMMAND" | grep -oE 'gh pr merge[[:space:]]+[0-9]+' | awk '{print $NF}')
EXTRA_SCRIPT="${AGENT_HARNESS_POST_MERGE_EXTRA_SCRIPT:-}"
if [ -n "$LAST_PR" ] && [ -n "$EXTRA_SCRIPT" ] && [ -x "$EXTRA_SCRIPT" ]; then
    "$EXTRA_SCRIPT" "$LAST_PR" || true
fi

exit 0
