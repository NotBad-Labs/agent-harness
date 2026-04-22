# agent-harness

> **Any-agent harness** — a meta-dev-loop kit for autonomous iteration.
> 一个面向任意 agent 的"自主迭代系统"骨架，让 AI 开发闭环可被复用。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Status](https://img.shields.io/badge/status-experimental-orange.svg)](#project-status)
[![Phase](https://img.shields.io/badge/phase-D%20closed-green.svg)](./PHILOSOPHY.md)

## Why this exists / 为什么有这个项目

随着 Claude Code / Codex CLI / Cursor 等 AI agent 进入真实软件工程流程，每个项目都在**重新发明轮子**：hooks / skills / 文档审计 / 三方对抗协议 / 记忆路由 / 反哺机制。这些模式反复出现，但散落在各自项目的 `.claude/` / `.codex/` 目录里，没有沉淀，也无法跨项目复用。

`agent-harness` 抽出这些**经过实战验证的通用骨架**，作为独立工具供任何 agent-driven 项目作为基线使用。

项目本身也遵循自己立的 [`PHILOSOPHY.md`](./PHILOSOPHY.md)：**初始接近空白，靠真实项目实战反哺演进**。目前是第一个孵化器（一个私有 iOS 项目）贡献的骨架，未来靠更多 consumer 的反哺积累。

## Who is this for

- 正在用 Claude Code / Codex CLI / Gemini CLI 做 agent-driven 开发的个人或团队
- 已经在 `.claude/hooks/`、`.claude/skills/`、`Scripts/audit/` 里积累了一堆脚本，想抽出来共用
- 关心"AI agent 协同质量"的工程师（cross-audit / 对抗性审查方法论）
- 对 docaudit / 知识体系健康机制感兴趣的文档体系建设者

## Three core principles

1. **空白 + 演进（Blank + Evolving）** — 初始骨架接近空白；内容由真实项目实战反哺积累
2. **共生（Symbiosis）** — consumer 项目既是孵化器（贡献模式）又是消费者（拉核心来用）
3. **可被复用不重复造轮子（Reuse over Reinvent）** — 一旦证明通用，只维护一份

详见 [PHILOSOPHY.md](./PHILOSOPHY.md)。

## What's inside

```text
agent-harness/
  core/                        # 层 0：语言 / 工具 / agent 全无关
    tools/docaudit/            #   docaudit 引擎（参数化，6 子命令 + 34 tests）
    cli/                       #   agent-harness CLI（init / doctor / sync --check）
  adapter-claude/              # 层 1：Claude Code 适配层
    hooks/                     #   8 个通用 hooks（参数化 env var）
    skills/                    #   7 个方法论 skills（cross-audit / knowledge-health / ...）
    settings.example.json      #   Claude Code settings 接线模板
    policy.starter.yaml        #   docaudit policy 起点
  preset-ios/                  # 层 2：iOS / Swift 领域 preset（初期空，反哺积累）
  examples/                    # 层 3：使用示例
  bin/agent-harness            # CLI entry point（Python）
  docs/contracts/              # 4 层分层契约 SSOT
```

## Quick start

### 新项目接入（3 行命令）

```bash
# 克隆或把 agent-harness 作为 submodule 放到你的项目旁
git clone https://github.com/NotBad-Labs/agent-harness.git
cd your-new-project
/path/to/agent-harness/bin/agent-harness init --pragmatic .
```

这会生成：

- `.agent-harness/project.yaml` — 消费项目契约
- `.agent-harness/lock.json` — 锁定 agent-harness upstream commit
- `Scripts/audit/policy.yaml` — docaudit policy stub（`--pragmatic` 档）

之后填 `project.yaml` 的 `project.name` / `layout` / `scan` 字段，跑 `agent-harness doctor` 验证。

### 已有项目接入

见 [BOOTSTRAP.md](./BOOTSTRAP.md)。

### 反哺你的模式给 agent-harness

见 [CONTRIBUTING.md](./CONTRIBUTING.md) — 反哺硬门槛（two-consumer rule + 3 迭代周期）+ 流程。

## Project status

**Phase D 收官（2026-04-22）**：骨架建仓 + 首个消费者试点接入。

| 模块 | 状态 |
|---|---|
| `core/tools/docaudit/` | ✅ 可用（34 tests 全绿） |
| `core/cli/`（init / doctor / sync --check） | ✅ 可用（21 tests 全绿） |
| `adapter-claude/` hooks + skills | ✅ 可用（人工验证，参数化完成） |
| `preset-ios/` | 🚧 空（待反哺积累） |
| 反哺 CLI（`extract-candidate` / `propose-upstream`） | 🚧 Phase E 规划中 |
| `sync --apply` 自动升级 | 🚧 Phase E 规划中 |

**当前定位**：早期 experimental。适合有经验的 agent 开发者按 `Quick start` 尝试接入，**不建议**尚未形成自己 agent 流程的团队作为生产基线依赖。Phase E 完成后会稳定。

**唯一现实 consumer**：一个私有 iOS 项目（本仓库孵化源）。按 PHILOSOPHY "假通用陷阱" 反模式，**在出现第二个独立 consumer 之前，本项目只是"一个项目的 generalized 版本"**。Phase E 会做第二 consumer 实证。

## Arch docs

- [PHILOSOPHY.md](./PHILOSOPHY.md) — 三原则 + 反模式 + 定位边界（**战略 SSOT**）
- [BOOTSTRAP.md](./BOOTSTRAP.md) — 新项目接入指南
- [CONTRIBUTING.md](./CONTRIBUTING.md) — 反哺协议
- [docs/contracts/project-overlay.md](./docs/contracts/project-overlay.md) — 4 层分层契约
- [core/tools/docaudit/README.md](./core/tools/docaudit/README.md) — docaudit 引擎文档
- [adapter-claude/README.md](./adapter-claude/README.md) — Claude Code 适配层

## Contributing

欢迎 issue / PR。请先读 [CONTRIBUTING.md](./CONTRIBUTING.md) 理解反哺协议。

**报告 bug** 或 **提建议**：使用 [issue templates](./.github/ISSUE_TEMPLATE/)。

**报告安全问题**：见 [SECURITY.md](./SECURITY.md)，**不要通过 public issue 报告**。

## License

[MIT](./LICENSE) © 2026 NotBad Labs L.L.C.

---

**孵化历史**：本项目的骨架 / 方法论由作者的一个私有商业 iOS 项目 (SnapDrill) 在 Phase A→B→C→D（2026-04-21 ~ 22）的自主迭代系统建设中积累。SnapDrill 本身保持私有（公司项目），但其上形成的 agent 协同 / 文档审计 / 质量门禁方法论被抽到本仓库，供任何 agent-driven 开发项目复用。

> Tool abstractions should survive their original host. This is that attempt.
