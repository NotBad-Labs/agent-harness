# PHILOSOPHY — agent-harness 战略锚

> 这份文档是 agent-harness 的**战略 SSOT**。任何功能 / PR / 反哺决策，都要回到这里问一遍"是否符合三原则"。

## 一、三原则

### 1. 空白 + 演进（Blank + Evolving）

**初始骨架接近空白，只有机制契约，不预设内容。**

- 骨架 = 目录结构 + 契约文档 + CLI 脚手架
- 内容 = 反哺而来（真实项目实战证明通用后才抽入）
- 未经证明的抽象 = 禁止（参考 YAGNI）

判定："这个 hook / skill / 规则我想放进核心"—— **先问是否已有真实项目用过 ≥ 3 次？是否能说明第二个消费项目怎么用？** 达不到就不准进。

### 2. 共生（Symbiosis）

**消费项目和 agent-harness 是双向关系，不是单向引用。**

- 消费项目 = 孵化器（在实战中发现新模式）+ 消费者（拉核心来用）
- agent-harness = 反哺沉淀（被多个项目实战锻造）+ 契约提供者（给出边界和接入模板）
- 不是"agent-harness 是源，消费项目是下游"——第一个 consumer（snapdrill-ios）的实战经验就是 agent-harness 的起源

### 3. 可被复用不重复造轮子（Reuse over Reinvent）

**一旦证明通用，只维护一份。**

- 不同项目遇到同一个模式 → 进 agent-harness，各自 overlay 里不重复
- 反哺门槛必须合理（太高 → 大家堆在本地不反哺；太低 → 核心被污染）
- 反哺流程要有 CLI 工具辅助，不能全靠手工操作（降低摩擦）

---

## 二、定位边界

### 面向任何 agent

**架构上不绑定单一 agent / CLI / 厂商**。核心契约应该能让未来新 agent（OpenAI Agent SDK / Cursor / Copilot / 未知新出的 agent）通过编写新 adapter 接入。

### 当前实现 = Claude Code + Codex CLI + Gemini CLI

**诚实标注**：PR-D1 时点，实际 adapter 只有 Claude Code 一家，Codex / Gemini 是 Claude Code 会话内的委派 CLI（不是独立 agent）。这是**现实**而不是**限制**。

未来可能的扩展路径：

- `adapter-claude/` — Claude Code（当前）
- `adapter-openai/` — OpenAI Agents SDK（假想）
- `adapter-cursor/` — Cursor（假想）
- ...

`core/` 层不得硬编码任何 agent CLI 路径 / 模型名 / 环境变量名。

### 不是什么

- ❌ **通用 CI/CD 工具**：不替代 GitHub Actions / Jenkins，docs-audit job 只是模板
- ❌ **通用 AI 框架**：不提供"调用 LLM 的封装"，只做 agent 协同的工作流层
- ❌ **一次性脚手架**：`init` 后不是就结束了，`upgrade` / `sync --check` 持续协作才是本体

---

## 三、反模式（明确禁止）

### 机制崇拜

把"自省 / 反哺 / cross-audit"变成仪式，每次都跑一遍，影响实际开发速度。

**守门**：每个机制必须有明确的触发条件 + 退出条件 + 成本预算（时间 / token）。不符合就不跑。

### 过度抽象 / YAGNI 违反

为"假想的未来消费项目"预先抽象接口 / 配置层 / 插件系统。

**守门**：所有抽象必须来自**至少 2 个真实 consumer 的重复需求**（two-consumer rule）。"我觉得未来可能有人用"不算证据。

### 假通用陷阱

对外号称"通用"，实际上每个模式都只在 snapdrill-ios 跑过，第二个项目拿去一接入就大改。

**守门**：Phase E 硬性要求至少 1 个第二 consumer（哪怕玩具级）跑通完整闭环后，才允许标榜"通用"。

### 被消费项目污染核心

消费项目的术语（SnapDrill / Swift / iOS / SwiftUI / 某个产品术语）出现在核心目录。

**守门**：

- CI denylist 拦住特定术语
- `core/` 目录 PR 必须通过 `grep -rE "snapdrill|swift|ios|swiftui" core/` 为空
- `adapter-claude/` 允许 Claude Code 相关术语，`preset-ios/` 允许 iOS 术语，严格目录分层

---

## 四、核心不变式

| 不变式 | 违反时怎么办 |
|---|---|
| `core/` 不得引用具体 agent CLI | PR 拒绝合入 |
| `core/` 不得引用具体编程语言 / 产品术语 | PR 拒绝合入 |
| 所有反哺必过 two-consumer rule（除安全/数据丢失级） | proposal 标注"Safety Override"理由，由人工 approve |
| 新机制有触发条件 + 退出条件 + 成本预算 | 缺失则设为 draft，不合并 |
| 消费项目的 drift 只报告不自动同步 | `sync --check` 是默认，`--apply` 需显式 flag |

---

## 五、演进路线（大致，不承诺）

| Phase | 目标 | consumer 验证 |
|---|---|---|
| Phase D（进行中） | 骨架 + CLI + docaudit 迁入 + snapdrill-ios 消费试点 | snapdrill-ios（并行跑，不破坏） |
| Phase E | 反哺协议 + 自省 skill + 首次反哺实战 | snapdrill-ios 反哺 1 次 |
| Phase F（候选） | 第二 consumer（玩具级）验证通用性 | 第二个项目 |
| Phase G（候选） | 版本发布机制 + preset 成熟化 | ≥ 2 consumer |

Phase 不承诺时间表，按 consumer 实战节奏推进。

---

**签名**：本 PHILOSOPHY.md 由 Phase D/E cross-audit consensus 三方独立起草共识裁定（Claude Opus 4.7 / Codex gpt-5.4 high effort / Gemini 3.1-pro），用户最终拍板。修改须经过 cross-audit 流程。
