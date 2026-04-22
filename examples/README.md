# examples/ — 使用示例

本目录按 `docs/contracts/project-overlay.md` 第 3 层契约：

- **最宽松**：允许完整 overlay 片段、消费项目具体名
- **展示用**，不作为功能性代码被引用
- 新 consumer 接入时可参考 examples 学习模式

## 当前状态

**Phase D PR-D1：空**（只有本 README 占位）

## 预期示例

| 示例 | 用途 |
|---|---|
| `examples/snapdrill-overlay/` | snapdrill-ios 作为第一个 consumer，展示其 overlay 片段（不是完整副本，只是"如何接入"的示例） |
| `examples/hello-world/`（Phase E 候选） | 玩具级 consumer，验证 agent-harness 跨项目可用性 |

## 为什么不直接把 snapdrill-ios 整个放进来

- `examples/` 只是**学习材料**，不是项目副本
- snapdrill-ios 是独立仓库，作为 consumer 持续演进
- 把完整 snapdrill-ios 放进来会污染 agent-harness（违反 PHILOSOPHY 第 3 反模式"被消费项目污染核心"）
