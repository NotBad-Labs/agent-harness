# adapter-claude/ — Claude Code 适配层

按 `docs/contracts/project-overlay.md` 第 1 层契约，本目录的边界：

- **可含** Claude Code 相关的具体内容：`.claude/hooks/` / `.claude/skills/` / `.claude/settings.json` 模板
- **不得含**其他 agent adapter 的内容（对应未来的 `adapter-<other>/`）
- **不得含**消费项目具体产品术语（那些属于 `preset-<domain>/` 或 consumer 自己的 overlay）

## 当前内容（PR-D4 起）

```text
adapter-claude/
  README.md                   # 本文件
  hooks/                      # 8 个通用 Claude Code hooks（详见 hooks/README.md）
    README.md
    block-dangerous-bash.sh
    log-file-change.sh
    session-metrics.sh
    long-session-guard.sh
    docaudit-on-doc-edit.sh
    docaudit-preflight.sh
    premerge-checklist.sh
    post-merge-checkpoint.sh
  skills/                     # 7 个通用方法论 skills
    cross-audit/SKILL.md              # 三方对抗性审查工作流
    cross-audit-consensus/SKILL.md    # 三方结果汇总裁决
    knowledge-health/SKILL.md         # 知识体系体检（产 plan 不改文件）
    phase-closeout/SKILL.md           # 长任务 checkpoint 生成
    resume-from-handoff/SKILL.md      # 接手时最小上下文加载
    update-status/SKILL.md            # 状态文件直推默认分支
    pr-review-workflow/SKILL.md       # PR 创建后 review 工作流
  settings.example.json       # Claude Code settings.json 接线模板
  policy.starter.yaml         # docaudit policy 起点（Claude Code 消费项目常见约定）
```

## 消费项目集成

### 方式 A：submodule + symlink（推荐）

消费项目把 agent-harness 作为 git submodule 挂载（如 `.meta/`），然后 symlink：

```bash
ln -s ../.meta/adapter-claude/hooks .claude/hooks
ln -s ../.meta/adapter-claude/skills .claude/skills
cp .meta/adapter-claude/settings.example.json .claude/settings.json
cp .meta/adapter-claude/policy.starter.yaml Scripts/audit/policy.yaml
```

消费项目可以在 `.claude/hooks/` 里额外放**项目特定 hooks**（如某 lint）作为 symlink 的补充。

### 方式 B：CLI install（未来）

`agent-harness install --adapter claude` 计划在 Phase E+ 实现，自动做 symlink + 配置合并。

### 方式 C：直接拷贝

适合不想跟踪 upstream 的消费项目。失去 upgrade path，不推荐长期使用。

## 参数化

所有 hooks 和 skills 假设消费项目可能有自己的目录约定，通过 `AGENT_HARNESS_*` 环境变量注入：

- `AGENT_HARNESS_DOCAUDIT_CMD` — docaudit 调用命令
- `AGENT_HARNESS_STATUS_FILE` — 状态文件名
- `AGENT_HARNESS_DEFAULT_BRANCH` — 默认分支
- `AGENT_HARNESS_CHECKPOINT_DIR` — checkpoint 目录
- 更多见 `hooks/README.md`

## 未来扩展

如果其他 agent 生态出现真实需求（需通过 PHILOSOPHY `two-consumer rule` 验证），未来可加：

- `adapter-<other>/` — 假想
- `adapter-<another>/` — 假想

**但不预先创建空 adapter 目录**（YAGNI）。
