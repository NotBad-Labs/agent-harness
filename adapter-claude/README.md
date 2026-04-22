# adapter-claude/ — Claude Code 适配层

本目录按 `docs/contracts/project-overlay.md` 第 1 层契约：

- **可含** Claude Code 相关的具体内容（`.claude/hooks/` 模板、skill YAML、settings.json 模板）
- **不得含**其他 adapter 的内容（OpenAI / Cursor / 未来新 adapter）
- **不得含**消费项目具体术语（SnapDrill / Swift / iOS / Xcode）

## 当前状态

**Phase D PR-D1：空**（只有本 README 占位）

## 后续迁入计划

| PR | 内容 |
|---|---|
| PR-D4 | `adapter-claude/hooks/`：通用 hooks（`block-dangerous-bash` / `long-session-guard` / `session-metrics` / `log-file-change` / `docaudit-on-doc-edit` / `docaudit-preflight` / `premerge-checklist` 等） |
| PR-D4 | `adapter-claude/skills/`：方法论 skills（`cross-audit` / `cross-audit-consensus` / `knowledge-health` / `phase-closeout` / `resume-from-handoff` / `update-status` / `pr-review-workflow`），去消费项目术语化 |
| PR-D4 | `adapter-claude/settings.example.json`：Claude Code settings 模板，hooks 接线骨架 |

## 未来扩展

如果其他 agent 生态出现真实需求（OpenAI Agents SDK / Cursor / 新 agent），按 `PHILOSOPHY.md` two-consumer rule 验证后可加：

- `adapter-openai/` — 假想
- `adapter-cursor/` — 假想

**但不预先创建空 adapter 目录**（YAGNI）。
