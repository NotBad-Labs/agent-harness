---
last_verified: 2026-04-22
layer: adapter
status: draft-pr-d4
---
# adapter-claude hooks

> 通用 Claude Code hooks 模板：由消费项目 symlink / 拷贝到自己的 `.claude/hooks/`，并在 `.claude/settings.json` 中接线。

## 文件清单（8 个）

| Hook | 触发 | 目的 | 阻塞策略 |
|---|---|---|---|
| `block-dangerous-bash.sh` | PreToolUse on Bash | 拦截危险命令（`rm -rf /` / `git push -f` 等） | exit 2 阻塞；env `CLAUDE_HOOK_ALLOW_DANGEROUS=1` 绕过 |
| `log-file-change.sh` | PostToolUse on Edit/Write | 记录文件修改到 session log | 非阻塞 |
| `session-metrics.sh` | PostToolUse on `.*` | 记录 tool call 时间戳 + 名称到 TSV | 非阻塞 |
| `long-session-guard.sh` | PreToolUse on Bash | 会话超时（默认 60min）stderr 提醒 | 非阻塞 |
| `docaudit-on-doc-edit.sh` | PostToolUse on Edit/Write | 编辑 docs Markdown 后跑 docaudit links | exit 2 阻塞（broken link 时） |
| `docaudit-preflight.sh` | PreToolUse on Bash | `git push` / `gh pr merge` 前跑 docaudit all --strict --baseline | exit 2 阻塞（error 级命中时） |
| `premerge-checklist.sh` | PreToolUse on Bash | `gh pr merge` 前检查状态文件近 24h 是否更新 | exit 2 阻塞；env `AGENT_HARNESS_STATUS_SKIP=1` 绕过 |
| `post-merge-checkpoint.sh` | PostToolUse on Bash | PR 合并后近 7 天 ≥ 3 次合并提示 checkpoint | 非阻塞 |

## 参数化环境变量

所有 hooks 通过环境变量接受消费项目特定配置。**合理默认值**让零配置也能工作；消费项目在 `.claude/settings.json` 或 shell profile 里 `export` 覆盖。

| 变量 | 默认值 | 作用 |
|---|---|---|
| `CLAUDE_HOOK_ALLOW_DANGEROUS` | `0` | `block-dangerous-bash` 绕过 |
| `AGENT_HARNESS_SESSION_LOG` | `$PROJECT_ROOT/.claude/session-log.txt` | `log-file-change` / `long-session-guard` 目标文件 |
| `AGENT_HARNESS_METRICS_TSV` | `$PROJECT_ROOT/.claude/session-metrics.tsv` | `session-metrics` 目标文件 |
| `AGENT_HARNESS_SESSION_THRESHOLD` | `60` (min) | `long-session-guard` 会话超时阈值 |
| `AGENT_HARNESS_SESSION_WARN_FLAG` | `$PROJECT_ROOT/.claude/.long-session-warned` | `long-session-guard` 提示标志文件 |
| `AGENT_HARNESS_ENTRY_FILES` | `"STATUS.md CLAUDE.md"` | `docaudit-on-doc-edit` 触发的 entry 文件列表（空格分隔） |
| `AGENT_HARNESS_DOCAUDIT_CMD` | `python3 core/tools/docaudit/docaudit.py` | docaudit 调用命令（相对 `$PROJECT_ROOT`） |
| `AGENT_HARNESS_STATUS_FILE` | `STATUS.md` | `premerge-checklist` 检查的状态文件 |
| `AGENT_HARNESS_STATUS_WINDOW_HOURS` | `"24 hours ago"` | `premerge-checklist` 时间窗 |
| `AGENT_HARNESS_STATUS_SKIP` | `0` | `premerge-checklist` 绕过 |
| `AGENT_HARNESS_CHECKPOINT_DIR` | `docs/memory/checkpoints` | `post-merge-checkpoint` 检查目录 |
| `AGENT_HARNESS_MERGE_WINDOW_DAYS` | `7` | `post-merge-checkpoint` 统计窗口 |
| `AGENT_HARNESS_MERGE_THRESHOLD` | `3` | `post-merge-checkpoint` 触发阈值 |
| `AGENT_HARNESS_POST_MERGE_EXTRA_SCRIPT` | `""` | `post-merge-checkpoint` 可选额外脚本（接收 PR 号参数） |

## 消费项目接线

在消费项目的 `.claude/settings.json` 中引用（示例）：

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": "bash .claude/hooks/log-file-change.sh" },
          { "type": "command", "command": "bash .claude/hooks/docaudit-on-doc-edit.sh" }
        ]
      },
      {
        "matcher": ".*",
        "hooks": [
          { "type": "command", "command": "bash .claude/hooks/session-metrics.sh" }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          { "type": "command", "command": "bash .claude/hooks/block-dangerous-bash.sh" },
          { "type": "command", "command": "bash .claude/hooks/long-session-guard.sh" },
          { "type": "command", "command": "bash .claude/hooks/docaudit-preflight.sh" },
          { "type": "command", "command": "bash .claude/hooks/premerge-checklist.sh" }
        ]
      }
    ]
  }
}
```

完整模板见 `../settings.example.json`。

## 消费项目集成方式

1. **submodule + symlink**：agent-harness 作为 submodule 挂载，本目录 `adapter-claude/hooks/*.sh` symlink 到消费项目 `.claude/hooks/`
2. **CLI install**：未来 `agent-harness install --hooks` 可以自动做 symlink（Phase E+ 候选）
3. **直接拷贝**：适合不想跟踪 upstream 的消费项目（失去 upgrade path，不推荐）

## 依赖

- bash 4+
- `jq`（解析 hook input JSON）
- `git`（定位 PROJECT_ROOT）
- Python 3.9+（`docaudit-*.sh` 依赖）
- macOS 和 Linux 兼容（`long-session-guard.sh` 兼容 BSD / GNU date）
