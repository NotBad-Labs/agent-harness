# preset-ios/ — iOS / Swift 领域 preset

本目录按 `docs/contracts/project-overlay.md` 第 2 层契约：

- **可含** Swift / SwiftUI / Xcode 相关的 hooks / skills / 原则模板
- **不得含**消费项目具体产品名（SnapDrill / 某个表名 / 某个业务术语）

## 当前状态

**Phase D PR-D1：空**（只有本 README 占位）

## 存在理由

snapdrill-ios 是第一个 consumer，其 iOS / Swift / Xcode 相关的模式在消费项目内积累。当满足以下条件时反哺到 `preset-ios/`：

- 至少 ≥ 3 次使用
- two-consumer rule（说明第二类 iOS 项目如何使用）
- 去消费项目术语化

## 预期迁入路径

| 来源 | 可能的 preset-ios 条目 |
|---|---|
| `snapdrill-ios/.claude/hooks/swift-autolint.sh` | 可能改造为 `preset-ios/hooks/swift-autolint.sh`，policy 文件驱动 |
| `snapdrill-ios/docs/principles/apple-native.md` | 可能抽为 `preset-ios/principles/apple-native.md`（去 SnapDrill 产品术语） |
| `snapdrill-ios/docs/principles/coding.md` Swift 规范部分 | 可能抽为 `preset-ios/principles/swift-style.md` |

**Phase D/E 不强制做**。等第二个 iOS consumer 出现或 snapdrill-ios 反哺 PR 驱动。
