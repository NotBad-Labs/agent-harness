---
name: pr-review-workflow
description: PR 创建后的 review 工作流。写消费项目 Review 工具的提示词、核实 finding、合并后更新状态文件。
allowed-tools:
  - Bash
  - Read
  - Grep
  - Edit
context: fork
disable-model-invocation: true
user-invocable: true
---

# PR Review 工作流

## 触发条件

`gh pr create` 成功后执行。

## 流程

### 1. 写 Review 提示词（若消费项目有 IDE 级 Review 工具）

消费项目可能配置 IDE 级代码审查工具或线上 Review 服务。为该工具撰写 review 提示词，输出给用户复制。

提示词应包含：

- PR 变更范围
- 重点检查项
- 项目约束（通常在消费项目的 `docs/principles/coding.md` 或等价文档中）

消费项目应提供自己的提示词模板（常见位置：`docs/principles/review-prompt-guide.md`）。若无该工具，跳过本步。

### 2. 核实每条 Finding

无论 Review 工具（IDE 级 / 线上服务 / 人工评审）给出的结论，必须独立核实：

1. 读源文件确认问题是否真实存在
2. 确认是否在 diff 范围内（reviewer 经常审 diff 之外的代码）
3. 对照消费项目的原则文档（`CLAUDE.md` / `docs/principles/*`）确认是否属于已批准例外

### 3. 采纳有价值的建议

采纳后推送 fix commit。

### 4. 用户确认后合并

所有 PR 必须经用户确认后方可合并。禁止自审自批。

### 5. Review 留痕

Review 结论必须记录在 PR comment 或 PR 描述中。Review 无留痕的 PR 不得合并。

### 6. 合并后更新状态文件

执行 `/update-status`（如果消费项目采用该 skill 约定的"状态文件直推"例外）。

## Gotchas

- **禁止自审自批**：fix 后必须让原 reviewer 验收
- **Review 无留痕不得合并**：结论必须在 PR comment 或描述中可追溯
- **状态文件合并后立即推送**：不等下一个 PR
- **Review 查两处**：`gh pr view --json comments` + `--json reviews`

## Consumer 扩展点

消费项目可以通过以下方式扩展本 skill：

- 提供 `docs/principles/review-prompt-guide.md` 模板
- 在 `.agent-harness/project.yaml` 声明启用的 Review 工具（IDE / 线上 / 无）
- 自定义 "自审自批"豁免规则（例如纯文档 PR 允许 consumer 自合并）
