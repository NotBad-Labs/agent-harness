# core/ — 语言 / 工具 / agent 全无关核心层

本目录按 `docs/contracts/project-overlay.md` 第 0 层契约约束：

- **不含**任何编程语言提及、特定 agent CLI、消费项目术语、OS 特定语法
- **只含**抽象工程哲学、通用 docaudit 引擎、跨 agent 协同抽象 protocol、通用 git workflow 基础字段

## 当前状态

**Phase D PR-D1：空**（只有本 README 占位）

## 后续迁入计划

| PR | 内容 |
|---|---|
| PR-D2 | `core/tools/docaudit/`：通用 docaudit 引擎（从 snapdrill-ios 参数化迁入） |
| PR-D2 | `core/policy.schema.yaml`：docaudit 策略 schema |
| PR-D5（部分） | `core/principles/engineering.md` 等通用工程哲学（从 consensus 三方认定的"通用"原则迁入） |

## 入口守门

CI 的 `denylist` job 强制扫描本目录，禁止词命中 = 合并拒绝。见 `.github/workflows/ci.yml`。
