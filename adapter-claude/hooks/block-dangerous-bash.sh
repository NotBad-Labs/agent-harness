#!/bin/bash
# PreToolUse (Bash): 阻塞已知危险命令。
# 匹配到 → exit 2 + stderr 提示。
#
# 用户显式授权后绕过：设置环境变量 CLAUDE_HOOK_ALLOW_DANGEROUS=1
#
# Configuration (env vars, all optional):
#   CLAUDE_HOOK_ALLOW_DANGEROUS=1  绕过本 hook（需要用户显式授权）

set -eo pipefail

if [ "${CLAUDE_HOOK_ALLOW_DANGEROUS:-0}" = "1" ]; then
    exit 0
fi

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if [ -z "$COMMAND" ]; then
    exit 0
fi

# 单个 ERE 正则，| 分隔多个危险模式
DANGEROUS_RE='rm -rf /[^/]|rm -rf ~|rm -rf \$HOME|git push --force|git push -f[[:space:]]|git reset --hard|git clean -[fdx]+|git branch -D|sudo rm'

if echo "$COMMAND" | grep -qE "$DANGEROUS_RE"; then
    echo "拦截危险命令：" >&2
    echo "  $COMMAND" >&2
    echo "" >&2
    echo "匹配模式：$DANGEROUS_RE" >&2
    echo "如确需执行，请让用户在终端直接运行；或让用户显式授权后" >&2
    echo "通过 CLAUDE_HOOK_ALLOW_DANGEROUS=1 环境变量绕过。" >&2
    exit 2
fi

exit 0
