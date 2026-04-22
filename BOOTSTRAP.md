# BOOTSTRAP — 新项目接入 agent-harness

> 新项目第一次集成 agent-harness 的指南。当前是 Phase D PR-D1 状态，CLI / 核心工具尚未完整实现，本文件描述**目标形态**，实际执行以最新 `docs/contracts/project-overlay.md` 为准。

## 谁应该读这份

- 新起一个项目，希望从第一天就有完整的 agent 协同 / 文档审计 / 质量门禁基建
- 已有项目，想引入 agent-harness 替代自研的 `.claude/` / `Scripts/audit/` 等散装机制

## 接入前提

- 项目使用 Git + GitHub
- 项目至少接入 Claude Code（当前唯一实现的 adapter）
- 可选：接入 Codex CLI / Gemini CLI 用于三方对抗审查

## 两档初始化（预期 Phase D PR-D3 完成）

### `init --minimal`（极简档）

只产出战略文件和空骨架：

```text
my-project/
  .agent-harness/
    project.yaml      # 项目 metadata + upstream version lock
    lock.json         # 锁定的 upstream commit
  docs/principles/
    project-*.md      # 项目特定原则（空，待 consumer 填）
  CLAUDE.md           # 入口路由（模板）
```

适合**高度定制的项目**，不想一开始就背上 agent-harness 的通用机制，只要契约层。

### `init --pragmatic`（务实档，默认推荐）

在 `minimal` 基础上 symlink / 拷贝以下通用机制到项目：

- `docaudit` 引擎（`Scripts/audit/`）
- 通用 hooks（`block-dangerous-bash` / `long-session-guard` / `session-metrics` / `log-file-change` / `docaudit-on-doc-edit` 等）
- 通用 skills（`cross-audit` / `cross-audit-consensus` / `knowledge-health` / `phase-closeout` / `resume-from-handoff` / `update-status` / `pr-review-workflow`）
- 通用原则文档（`engineering.md` / `collaboration.md` / `codex-delegation.md` / `gemini-delegation.md` / `memory-routing.md` / `permission-model.md` / `review-prompt-guide.md`）
- 记忆模板（`feedback.md` / `decisions.md` / `handoff.md` / `checkpoints/` 空模板）
- PR 模板 / CI docs job 示例

适合**想立即拥有 Phase B/C 级基础设施**的项目。

## 接入后日常工作

1. 项目实战中发现有用的新 hook / skill / F 规则
2. 先放在项目本地 overlay（不直接 upstream）
3. 积累到 ≥ 3 次有效迭代后，运行 `agent-harness extract-candidate <path>`（Phase E PR-E2 实现）
4. 生成 upstream proposal，在 `agent-harness` 仓库开 PR
5. PR 通过 two-consumer rule + 去项目化检查后合并
6. 项目 bump `.agent-harness/lock.json`，可选择删除本地重复 overlay

## 当前孵化项目接入状态

**Phase D PR-D5（已合并 2026-04-22）**：孵化项目（一个私有 iOS 项目）作为第一个 consumer 试点接入 agent-harness，**但不破坏本地现有机制**（双轨并行，`sync --check` 对照）。这也是 agent-harness 的第一个"实战验证 consumer"。

由于孵化项目是私有仓库（公司项目），外部观察者看不到该项目的 `.agent-harness/` 契约文件。agent-harness 本身保持公开，供所有项目作为基线使用。

## FAQ

### Q: agent-harness 能用于非 iOS / 非 Swift 项目吗？

A: 核心设计目标就是**任何项目**。当前 `preset-ios/` 是 SnapDrill 孵化带来的示例，其他项目可以忽略它，或者贡献 `preset-python/` / `preset-rust/` 等。

### Q: 不用 Claude Code 能用 agent-harness 吗？

A: 目前 adapter 只有 `adapter-claude/`。未来 `adapter-openai/` / `adapter-cursor/` 等按需求迁入（只要有真实需求 + 第二 consumer 配合）。**现在**不用 Claude Code 的项目，只能用 `core/` 层（docaudit / 原则文档）。

### Q: agent-harness 自己怎么迭代？

A: 见 [CONTRIBUTING.md](./CONTRIBUTING.md) 反哺协议。核心不允许"没有 consumer 证据的抽象"。

---

**注**：本文件是目标形态，实际 CLI 命令 (`init --minimal` / `init --pragmatic` / `extract-candidate` / `sync --check`) 在 Phase D PR-D3 + Phase E PR-E2 完成。当前 PR-D1 不提供可执行 CLI，只定义契约 + 骨架。
