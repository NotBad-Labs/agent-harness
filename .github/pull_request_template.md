<!--
agent-harness PR 模板

根据 PR 类型选择：
- **反哺 PR**（consumer → core / adapter / preset）：填写完整模板
- **Bug fix / enhancement / 文档改进**：删除"反哺专用字段"段，简化即可
- **Safety-critical fix**（绕过 rubric）：使用 Safety Override 段

详细 rubric 见 docs/contracts/contribution-rubric.md
-->

## PR 类型

- [ ] 反哺（consumer → agent-harness core / adapter / preset）
- [ ] Bug fix（仅修 agent-harness 本身）
- [ ] Enhancement / refactor（仅改 agent-harness 本身）
- [ ] 文档 / typo / lint
- [ ] Safety-critical fix（Safety Override，下方说明）

## Summary

<!-- 一句话说明本 PR 的目的和内容 -->

---

## 反哺专用字段（如 PR 类型为"反哺"，填写以下段）

### 起源

- Consumer 项目：<!-- 项目名，可以是私有 -->
- Consumer 触发 PR / issue：<!-- link 或脱敏描述 -->
- 积累时间窗：<!-- YYYY-MM-DD ~ YYYY-MM-DD -->
- 有效使用次数：<!-- N 次，证据见下 -->

### 已有使用证据

<!-- 描述在 consumer 里的使用场景 / 命中次数 / 节省的时间 / 防止的事故 -->

### P1 六门槛 checklist

- [ ] **two-consumer rule** — 第二类项目使用场景（见下方）
- [ ] **去项目化残余 = 0**（grep 报告见下方）
- [ ] **通用性可配置**（diff 不含 `if project == X` 式分支）
- [ ] **可测试**（测试清单见下方）
- [ ] **低污染**（`core/` 无语言 / 产品特定术语）
- [ ] **生命周期清楚**（启用 / 退役 / 升级段见下方）

#### 第二 consumer 使用场景

<!-- ≥ 100 字。具体技术栈 + 调用方式 + 配置差异。
     反模式："这个很通用，任何项目都能用" -->

#### 去项目化 grep 报告

```bash
$ grep -riE "<denylist-pattern>" <proposed-files>
# 粘贴扫描结果（应为空）
```

### P2 3 迭代周期

- [ ] consumer 已独立有效使用 ≥ 3 次
- [ ] 或申请 Safety Override（见 Safety-critical 段）

**证据**：
<!-- git log / telemetry 摘录 -->

### 安全级别

- [ ] **S-critical**（数据丢失 / 安全漏洞 / CI 绕过） — Safety Override 标注理由
- [ ] **S-normal**（工具 / 方法论 / 质量门禁）
- [ ] 不确定 — 请 reviewer 判断

### 层分配

- [ ] `core/`（语言 / 工具 / agent 全无关）
- [ ] `adapter-<agent>/`（具体 agent 适配）
- [ ] `preset-<domain>/`（具体技术栈 preset）
- [ ] `examples/`

### 测试

<!-- 新增 / 修改的测试清单。若豁免（纯文档 / 纯原则），说明理由 -->

### 迁移说明

<!-- 已有 consumer 如何 bump .agent-harness/lock.json 并适应本 PR 的 breaking change。
     如无 breaking 写 N/A -->

### 生命周期

- **启用条件**：<!-- consumer 什么时候会用到 -->
- **退役条件**：<!-- 什么情况下应该废弃 / 被新方案取代 -->
- **升级路径**：<!-- breaking change 时 consumer 怎么迁移 -->

---

## Safety Override 段（如 PR 类型为 Safety-critical fix）

**Safety Override**: <!-- 明确标出理由 -->

- 影响面：<!-- 哪些 consumer 被影响 / 数据范围 -->
- 证据：<!-- 日志 / reproduce steps / 漏洞描述 -->
- Post-merge 后续：<!-- 是否需要补测试 / 在后续 PR 收紧 -->

---

## Test plan

- [ ] CI: markdownlint / shellcheck / denylist / core-tests 全绿
- [ ] <!-- 列出 PR 作者本地跑过的额外验证 -->

## 关联

<!-- 关联 issue / upstream 讨论 / RFC / cross-audit 归档等 -->

---

**Reviewer checklist**（由 reviewer 填）：

- [ ] Scope 合理（层分配正确，无 scope 蔓延）
- [ ] 去项目化验证通过（grep 0 命中 + CI denylist 绿）
- [ ] two-consumer rule 独立思考通过（reviewer 能自己想出第二场景）
- [ ] 可配置性 diff 扫描通过（无硬编码项目分支）
- [ ] 测试覆盖合理（主路径 + 至少 1 边界）
- [ ] 生命周期描述合理

详细 reviewer 流程见 [`docs/contracts/contribution-rubric.md`](../../docs/contracts/contribution-rubric.md) §5。
