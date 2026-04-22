#!/bin/bash
# PostToolUse (Edit|Write): 对刚修改的 docs 区 Markdown 跑 docaudit links。
# broken link 时 exit 2。全量 links 扫 <1s（纯 Python 正则）。
#
# Configuration (env vars, all optional):
#   AGENT_HARNESS_DOCS_TRIGGER_GLOB   需要触发的文件 glob pattern（用 case 语法）
#                                     默认 "*/docs/*.md" 和 entry files（见下）
#   AGENT_HARNESS_ENTRY_FILES         entry doc 文件名列表（空格分隔，仅 basename）
#                                     默认 "STATUS.md CLAUDE.md"
#   AGENT_HARNESS_DOCAUDIT_CMD        docaudit 命令
#                                     默认 "python3 core/tools/docaudit/docaudit.py"（在 PROJECT_ROOT 相对）
#                                     若消费项目用 symlink/submodule，应 override 为绝对路径

set -eo pipefail

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

[ -z "$FILE_PATH" ] && exit 0

# 检查是否为 docs 区 Markdown
ENTRY_FILES="${AGENT_HARNESS_ENTRY_FILES:-STATUS.md CLAUDE.md}"
IS_DOC=0
case "$FILE_PATH" in
    */docs/*.md) IS_DOC=1 ;;
esac

if [ "$IS_DOC" = "0" ]; then
    BASENAME=$(basename "$FILE_PATH")
    for entry in $ENTRY_FILES; do
        if [ "$BASENAME" = "$entry" ]; then
            IS_DOC=1
            break
        fi
    done
fi

[ "$IS_DOC" = "0" ] && exit 0

PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
if [ -z "$PROJECT_ROOT" ] || [[ "$FILE_PATH" != "$PROJECT_ROOT"/* ]]; then
    exit 0
fi

DOCAUDIT_CMD="${AGENT_HARNESS_DOCAUDIT_CMD:-python3 core/tools/docaudit/docaudit.py}"

# 如果是相对路径形式，验证文件存在；绝对路径可直接跑
if [[ "$DOCAUDIT_CMD" == python3* ]]; then
    # Extract script path (second token)
    SCRIPT_PATH=$(echo "$DOCAUDIT_CMD" | awk '{print $2}')
    if [[ "$SCRIPT_PATH" != /* ]]; then
        # relative -> resolve under PROJECT_ROOT
        if [ ! -f "$PROJECT_ROOT/$SCRIPT_PATH" ]; then
            exit 0  # docaudit 不可用静默降级
        fi
    fi
fi

set +e
OUTPUT=$(cd "$PROJECT_ROOT" && $DOCAUDIT_CMD links 2>&1)
RESULT=$?
set -e

if [ $RESULT -eq 0 ]; then
    exit 0
fi

# broken link 命中 → stderr 打给 agent
echo "docaudit links 对 $FILE_PATH 编辑后发现 broken link：" >&2
echo "$OUTPUT" >&2
echo "请修复链接或删除引用" >&2
exit 2
