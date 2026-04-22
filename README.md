# agent-harness

> **Any-agent harness** — meta-dev-loop kit for autonomous iteration.

`agent-harness` 是一个可被任何项目复用的"自主迭代系统"骨架：把多个 AI agent 的协同、质量门禁、文档审计、记忆路由、反哺机制抽象成一套独立的 meta-dev-loop 工具链。

## 定位

- **面向任何 agent**（架构上不绑定单一 CLI / 厂商）
- **当前实现 adapter**：Claude Code + Codex CLI + Gemini CLI（三方 harness）
- **初始骨架接近空白**，靠真实项目实战反哺演进
- **孵化自** [`snapdrill-ios`](https://github.com/NotBad-Labs/snapdrill-ios) 的 Phase A→B→C 自主迭代系统实战经验

## 不是什么

- 不是通用 CI/CD 工具（不替代 GitHub Actions / Jenkins）
- 不是通用 AI 框架（不替代 Claude Agent SDK / OpenAI Assistants）
- 不是 SnapDrill 的派生物（snapdrill-ios 是第一个 consumer，不是 owner）

## 三原则

1. **空白 + 演进**：初始只有骨架 + 契约，靠项目实战反哺积累实物
2. **共生**：第一个 consumer (snapdrill-ios) 既是**孵化器**（贡献新模式），又是**消费者**（拉核心来用）
3. **可被复用不重复造轮子**：工具一旦证明通用就只维护一份

详见 [PHILOSOPHY.md](./PHILOSOPHY.md)。

## 快速上手

- 新项目接入 → [BOOTSTRAP.md](./BOOTSTRAP.md)
- 反哺核心 → [CONTRIBUTING.md](./CONTRIBUTING.md)
- 核心 vs overlay 边界 → [docs/contracts/project-overlay.md](./docs/contracts/project-overlay.md)

## 当前状态

**Phase D PR-D1（2026-04-22）**：骨架建仓。CLI / 核心工具 / adapter 实现在后续 PR 逐步迁入。

见 `docs/` 和 consensus 归档：`phase-de-consensus-20260422.md`（在孵化项目的 plans 归档中）。

## License

MIT（见 [LICENSE](./LICENSE)）
