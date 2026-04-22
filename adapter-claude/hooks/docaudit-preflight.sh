#!/bin/bash
# PreToolUse (Bash): 在 push / merge / amend / rebase 前跑 docaudit all --strict --baseline。
# 防止 error 级命中推到远端再被 CI 阻断（本地兜底）。
# 被 legacy_whitelist 豁免的历史违规不阻断；新增违规阻断。
#
# Configuration (env vars, all optional):
#   AGENT_HARNESS_DOCAUDIT_CMD   docaudit 命令
#                                默认 "python3 core/tools/docaudit/docaudit.py"

set -eo pipefail

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# 锚定命令匹配
if ! echo "$COMMAND" | grep -qE '^[[:space:]]*(git[[:space:]]+push|gh[[:space:]]+pr[[:space:]]+merge|git[[:space:]]+commit[[:space:]]+.*--amend|git[[:space:]]+rebase)\b'; then
    exit 0
fi

PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
[ -z "$PROJECT_ROOT" ] && exit 0

DOCAUDIT_CMD="${AGENT_HARNESS_DOCAUDIT_CMD:-python3 core/tools/docaudit/docaudit.py}"

# 验证 docaudit 可用（相对路径形式）
if [[ "$DOCAUDIT_CMD" == python3* ]]; then
    SCRIPT_PATH=$(echo "$DOCAUDIT_CMD" | awk '{print $2}')
    if [[ "$SCRIPT_PATH" != /* ]]; then
        [ ! -f "$PROJECT_ROOT/$SCRIPT_PATH" ] && exit 0
    fi
fi

set +e
OUTPUT=$(cd "$PROJECT_ROOT" && $DOCAUDIT_CMD all --strict --baseline 2>&1)
RESULT=$?
set -e

if [ $RESULT -eq 0 ]; then
    exit 0
fi

echo "docaudit preflight 阻断命令：$COMMAND" >&2
echo "---" >&2
echo "$OUTPUT" >&2
echo "---" >&2
echo "修复 error 级命中，或在消费项目的 policy.yaml legacy_whitelist 登记理由（含 expires_on）" >&2
exit 2
