---
last_verified: 2026-04-22
layer: contract
status: draft-pr-d1
---
# 核心 vs 项目 overlay 边界契约

> 这是 agent-harness 最底层的架构契约。定义**什么算 agent-harness 核心、什么算消费项目 overlay**、两者如何互动。

## 目录分层（4 层）

```
agent-harness/
  core/                        # 层 0：语言/工具/agent 全无关
  adapter-<agent>/             # 层 1：特定 agent 适配层（当前仅 adapter-claude/）
  preset-<domain>/             # 层 2：特定领域 preset（初期空，反哺积累）
  examples/                    # 层 3：使用示例（含 snapdrill-overlay 片段）

<consumer-project>/            # 消费项目本身
  .agent-harness/
    project.yaml               # 项目 metadata + upstream version
    lock.json                  # upstream commit/tag 锁
  docs/principles/project-*.md # 项目特定原则（overlay）
  .claude/skills/project-*/    # 项目特定 skill（overlay，若用 Claude adapter）
  # ... 其他 overlay 路径由 project.yaml 声明
```

## 每层的承诺

### 层 0：`core/`

**绝对不含**：
- 任何编程语言提及（Swift / Python / Rust / ...）
- 任何特定 agent CLI / SDK 名（Claude Code / Codex / Gemini / OpenAI / Cursor / ...）
- 任何消费项目产品术语（SnapDrill / ...）
- 任何 OS 特定语法（macOS 特定的 `date -j` / GNU 特定的 `sed -i` 无后缀，等）

**可以含**：
- 抽象工程哲学（YAGNI / 奥卡姆 / SSOT / 可逆性）
- 通用 docaudit 引擎（参数化，不硬编码路径）
- 跨 agent 协同的抽象 protocol 定义
- 通用 git workflow / PR 模板的基础字段

**测试**：
```bash
# 核心 denylist 扫描（CI 强制）
grep -riE "claude|codex|gemini|openai|cursor|swift|python|rust|snapdrill|ios|xcode" core/
# 应返回空；如命中必须在 PR 解释或重构
```

### 层 1：`adapter-<agent>/`

**可以含特定 agent 相关的具体内容**：
- `adapter-claude/hooks/`：Claude Code 的 `.claude/hooks/` 模板
- `adapter-claude/skills/`：Claude Code skill 模板（YAML frontmatter 含 Claude Code 特定字段）
- `adapter-claude/settings.json`：Claude Code settings 模板

**不得含**：
- 其他 adapter 的内容
- 消费项目的具体术语

**未来扩展**：`adapter-openai/` / `adapter-cursor/` 按需出现，各自独立不互相依赖。

### 层 2：`preset-<domain>/`

**可以含特定技术栈 / 领域相关的模板**：
- `preset-ios/`：Swift / SwiftUI / Xcode 相关的 hooks / skills / 原则（初期空，反哺积累）
- `preset-python/` / `preset-web/`：未来按需

**不得含**：
- 消费项目具体产品名 / 表名 / 文件名

### 层 3：`examples/`

**展示用**，不作为功能性代码被引用：
- `examples/snapdrill-overlay/`：SnapDrill 的 overlay 片段示例（不是完整副本）
- 新 consumer 可以看 examples 学习接入模式

---

## 消费项目的 overlay 边界

消费项目根目录必须有 `.agent-harness/project.yaml` 声明 overlay 范围：

```yaml
# 详细 schema 见 templates/base/.agent-harness/project.yaml
version: 1
upstream:
  repo: NotBad-Labs/agent-harness
  lock: <commit-sha>
presets:
  - adapter-claude
  - preset-ios        # 如果是 iOS 项目
overlay_paths:
  skills: .claude/skills/project-*
  principles: docs/principles/project-*
  hooks: .claude/hooks/project-*
```

**overlay 原则**：
- **消费项目只能覆盖，不能改核心**：核心内容通过 symlink / 引用使用，不在消费项目内 fork
- **overlay 路径**：所有项目特定内容必须在 `project-*` 前缀或独立目录
- **drift 检测**：`agent-harness sync --check` 报告本地 vs upstream 的差异（不自动同步）

## PR 规则（agent-harness 仓库）

| PR 触及目录 | 要求 |
|---|---|
| 只动 `core/` | 跨 agent / 跨语言 denylist 强制通过 |
| 只动 `adapter-<agent>/` | 只允许该 agent 相关内容；不得反向引用 `core/` 以外的层 |
| 只动 `preset-<domain>/` | 只允许该领域相关内容；不得硬编码某个消费项目 |
| 只动 `examples/` | 最宽松，允许完整 overlay 片段 |
| 跨层 PR | 必须拆分为独立 PR，除非 scope contract 明确豁免 |

## 当前 Phase D PR-D1 状态

- `core/` 空（占位 README）
- `adapter-claude/` 空（占位 README），PR-D4 迁入通用 hooks / skills
- `preset-ios/` 空（占位 README），Phase E / Phase F 反哺积累
- `examples/` 空（占位 README）
- 消费项目契约 schema 见 `templates/base/.agent-harness/project.yaml`（草案）

后续 PR 每次迁入内容时，都必须遵循本契约的层次划分。
