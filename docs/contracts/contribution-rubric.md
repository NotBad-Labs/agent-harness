---
last_verified: 2026-04-22
layer: contract
status: phase-e-pr-e1
---
# Contribution Rubric — 反哺详细协议

> 本文件是 [CONTRIBUTING.md](../../CONTRIBUTING.md) 的详细版。CONTRIBUTING 是总览和流程图；本文是具体 checklist、技术指南、reviewer 规范、常见异议处理。

## 0. 适用范围

### 什么是"反哺"

从某个 consumer 项目（例如 `snapdrill-ios`）向 `agent-harness` 发起的、**把在 consumer 上实战验证的模式抽象到 agent-harness 核心**的 PR。

### 什么**不是**反哺（但也欢迎 PR）

- **Bug fix**：docaudit 引擎的正则 bug、CLI 的 crash、hook 的误拦截 — 直接修，不经过反哺 rubric
- **Enhancement 只改 agent-harness 本身**：新增 `bin/agent-harness doctor` 的检查项、CI workflow 优化、README 文案改进
- **Typo / lint 修复**：小改动走 fast track
- **第三方 agent adapter 提议**：例如 `adapter-<other>/`，属于"新建 adapter"而非反哺已有内容；走单独的 adapter-proposal 流程（Phase F+ 规范，尚未形式化）

### 什么**必须**走反哺 rubric

- 把 consumer 的 hook / skill / docaudit policy 模式 / F 规则 / 工作流模板 **添加到 `core/` 或 `adapter-<agent>/` 或 `preset-<domain>/`** 的 PR
- 这类 PR 必须通过本文档所有硬门槛

---

## 1. 反哺的六硬门槛（P1）

来自 Codex 三方 consensus 主锚建议。必须**全部**满足（除非 Safety Override）。

### P1.1 two-consumer rule

**规则**：必须能说明**第二类项目**如何使用这个机制。即使只是假想的玩具场景，也要具体。

**验收**：

- [ ] PR body "第二 consumer 使用场景" 字段非空
- [ ] 场景描述可读、可想象，不是"这个东西通用所以通用"式空话
- [ ] 至少 100 字，含具体示例（技术栈 / 调用方式 / 配置差异）

**Good 示例**：

> 「对于一个用 Cursor + Python FastAPI 做后端的项目，`knowledge-health` skill 会扫描 `.cursor/rules/` 和 `docs/rules/` 分类 plans，按 `.agent-harness/project.yaml` 的 `layout.rules_dir` 字段工作。使用场景：当 backend 迭代 20 个 API 后运行 `/knowledge-health`，会产出 plan 列出 dead rule 候选（引用计数 < 1 的规则文件）。」

**Bad 示例**：

> 「这个 skill 很通用，任何项目都能用。」

**例外**：Safety Override（P2）可以 1 consumer 就 upstream。

### P1.2 去项目化残余 = 0

**规则**：grep 消费项目特定术语返回空。

**执行**：

```bash
# 禁用术语（按 agent-harness CI denylist）：
# core/ 扫：claude|codex|gemini|openai|cursor|swift|swiftui|swiftdata|xcode|<consumer-names>
# adapter-<agent>/ 扫：除本 adapter 和通用 agent 外的所有
grep -riE "<denylist-pattern>" <proposed-files>
```

**验收**：

- [ ] PR body "去项目化 grep 报告" 字段粘贴扫描结果（应为空）
- [ ] CI denylist job 通过

**重命名技巧**：

| 消费项目术语 | 中性表达 |
|---|---|
| SnapDrill / MyApp | "consumer project" / "target project" |
| iOS / Android / Swift / Kotlin | "the platform" / 泛称技术栈 / 参数化 |
| develop / main / trunk | "default branch"（env var 参数化） |
| STATUS.md / ROADMAP.md | "status file"（env var 参数化） |
| 具体 issue / PR 号 (#626) | "historical example" / 删除 |
| 具体产品名词（Profile / Subject / Review） | 删除或泛化为"domain entity" |

### P1.3 通用性可配置

**规则**：项目差异**必须通过 config 注入**（policy.yaml / project.yaml / env var），**不改核心代码**。

**验收**：

- [ ] 若 PR 改了 `core/` 代码，diff 里没有新增任何"如果是 X 项目则 Y"的分支
- [ ] 配置项有默认值 + 文档 + schema（若 `policy.schema.yaml` 相关则同步更新）

**反模式**：

```python
# ❌ 不允许
if project_name == "SnapDrill":
    validate_ios_schema()
elif project_name == "WebApp":
    validate_typescript()
```

```python
# ✅ 允许（参数化）
validator_path = policy.get("layout", {}).get("frontmatter_validator")
if validator_path:
    run_subprocess(validator_path)
```

### P1.4 可测试

**规则**：有 test / fixture / doctor 检查 / 明确的人工验收标准。

**验收**：

- [ ] 代码类反哺：新增或修改 unit test，测试在 `core/tools/*/tests/` 或 `core/cli/tests/` 下
- [ ] Hook 类反哺：有 fixture 或至少一个 shell test script，CI 能跑
- [ ] Skill 类反哺（纯 Markdown，无可执行）：必须有"验收标准"段，描述如何人工验证
- [ ] Config schema 类反哺：schema 文件含示例 + 边界测试

**豁免**：纯文档 / 纯原则 / 纯 UX 改进，说明豁免理由。

### P1.5 低污染

**规则**：核心不得知道消费项目的具体事实（表名 / 类名 / 命令 / 特定路径）。

**检查点**：

- [ ] `core/` 下无 `.swift` / `.kt` / `.ts` 等语言特定扩展名引用（字符串里也不行）
- [ ] `core/` 下无具体 DB 表名 / Pydantic model / SwiftData model 名
- [ ] `adapter-<agent>/` 下仅含该 agent 的术语，不涉及其他 agent
- [ ] `preset-<domain>/` 下仅含该技术领域的术语，不涉及具体产品

### P1.6 生命周期清楚

**规则**：知道**何时启用、何时退役、如何升级**。

**验收（PR body 填写）**：

- [ ] 启用条件（consumer 什么时候会用到）
- [ ] 退役条件（什么情况下应该废弃 / 被新方案取代）
- [ ] 升级路径（breaking change 时 consumer 怎么迁移）

---

## 2. 反哺的次门槛 — 3 迭代周期规则（P2）

来自 Gemini 三方 consensus 次锚建议。

**规则**：同类模式在 consumer 内至少 **已有效使用 3 次**（或导致过 1 次严重事故级影响），才考虑反哺。

**如何证明"已用 3 次"**：

- Git log：`git log --oneline -- <path>` 显示至少 3 次**独立触发**（不是同一个 sprint 的修 bug）
- Usage log：如果 hook 有 telemetry（session-metrics.tsv），可以 grep 确认触发次数
- Review 记录：PR description 引用至少 3 个不同的 PR / issue / incident

**例外（免 3 次）**：

- **S-critical**（安全 / 数据丢失 / 严重 CI 绕过）：1 次复现即可
- **明显反模式的修复**：比如"hook 绕过"这类逻辑漏洞，不需要 3 次才修

---

## 3. 安全级别 (Safety Levels)

| 级别 | 范围 | 反哺门槛 |
|---|---|---|
| **S-critical** | 数据丢失 / 安全漏洞 / CI 绕过 / credential leak | 1 次复现即可 upstream + PR body 标 "Safety Override" + 说明理由 |
| **S-normal** | 工具 / 方法论 / 质量门禁 / 新 hook / 新 skill / 新规则 | 完整 P1 六门槛 + P2 3 迭代周期 |
| **S-experimental** | 实验性模式 / 临时 workaround / prompt 技巧 | **不反哺**，留 overlay 直到升级为 normal 级 |

**S-critical 申请 Override 需要**：

- PR body 开头 `**Safety Override**:` 明确标出
- 证据（日志 / reproduce steps / 影响面分析）
- 接受 maintainer 在合并后可能要求补测试或在后续 PR 收紧

---

## 4. PR 必填字段（checklist）

开 PR 时请使用 [`.github/pull_request_template.md`](../../.github/pull_request_template.md)，自动加载以下字段。

````text
## 起源

- Consumer 项目：<private / public 项目名>
- Consumer 触发 PR / issue：<link，可以是私有仓库无法访问，说明情况>
- 积累时间窗：<YYYY-MM-DD ~ YYYY-MM-DD>
- 有效使用次数：<N 次，引用 git log / telemetry>

## 已有使用证据

<具体描述在 consumer 里命中 / 修复 / 节省的场景。如果仓库私有，描述性证明而非链接>

## P1 六门槛

- [ ] two-consumer rule：第二类项目使用场景（下方展开）
- [ ] 去项目化残余 = 0（下方 grep 报告）
- [ ] 通用性可配置（diff 不含项目名条件分支）
- [ ] 可测试（新测试 / fixture / 人工验收标准）
- [ ] 低污染（core/ 无语言特定 / 产品特定术语）
- [ ] 生命周期清楚（启用 / 退役 / 升级段）

### 第二 consumer 使用场景

<至少 100 字，具体技术栈 + 调用方式 + 配置差异>

### 去项目化 grep 报告

```bash
$ grep -riE "<denylist>" <proposed-files>
# 输出应为空
```

## P2 3 迭代周期

- [ ] consumer 已独立有效使用 ≥ 3 次（证据见下）
- [ ] 或申请 Safety Override（S-critical，下方说明）

### 证据

<git log / telemetry 摘录>

## 安全级别

- [ ] S-critical（Safety Override 标注理由）
- [ ] S-normal（走完整六门槛）
- [ ] 不确定 — 请 reviewer 判断

## 层分配

- [ ] core/
- [ ] adapter-<agent>/
- [ ] preset-<domain>/
- [ ] examples/

## 测试

<新增 / 修改的测试清单；如果豁免（纯文档），说明理由>

## 迁移说明

<已有 consumer 如何 bump `.agent-harness/lock.json` 并适应本 PR 的 breaking change；如无 breaking 写 N/A>

## 生命周期

- 启用条件：
- 退役条件：
- 升级路径：
````

---

## 5. Reviewer checklist

**Primary reviewer 审查顺序**：

1. **Scope 检查**（5 分钟）
   - [ ] PR body 所有字段填写
   - [ ] 没有明显的 "我觉得通用" 类空话
   - [ ] 层分配合理（core / adapter / preset / examples 对应正确）

2. **去项目化验证**（10 分钟）
   - [ ] 跑 `grep -riE "<denylist>" <PR-touched-files>` 确认 0 命中
   - [ ] 确认 CI denylist job 通过

3. **two-consumer rule 独立思考**（15 分钟）
   - [ ] 读 PR body 的"第二 consumer 使用场景"，问：**"我不看 PR body 能不能自己想出第二场景？"**
   - [ ] 如果想不出 → **退回 overlay**（P1.1 不满足）

4. **可配置性 diff 扫描**（10 分钟）
   - [ ] 检查 `core/` 代码 diff，grep `if.*project|if.*consumer|hardcoded` 等
   - [ ] 确认配置项有 default + schema + doc

5. **测试覆盖 sanity check**（10 分钟）
   - [ ] 新测试覆盖主路径 + 至少 1 个边界
   - [ ] 若 hook 类，有 CI 可运行的 smoke test

6. **生命周期审查**（5 分钟）
   - [ ] 退役条件合理（不是"永不退役"式宣言）
   - [ ] 升级路径可行

**Secondary reviewer（cross-audit，architecture-level 改动必跑）**：

- 用 `/cross-audit` skill 三方独立起草 review
- 用 `/cross-audit-consensus` 汇总裁决
- 方差 > 2.5 → retry；Codex < 7.0 → 必须修

---

## 6. 常见异议处理

### "这个模式在我们项目很核心，应该反哺"

**判定**：不一定。项目核心 ≠ 跨项目核心。问三个问题：

- 脱离 consumer 的产品领域后，这个模式还有意义吗？
- 第二 consumer 使用时，至少 50% 内容保留不改？
- 如果保留，它是 method（可复用）还是 data（属于消费项目）？

只有前两问 Yes + 第三问"method"才反哺。

### "consumer 是私有仓库，我无法 public link 证据"

可以：描述性证明（"我们有 3 个 PR 用到这个 hook"）+ 如果可能，提供**脱敏的 diff / log 截图**作为附件。**不强制 public link**。

Reviewer 可以接受作者信誉，但保留在 repo 公开出现"假反哺"时追溯的权利。

### "我改了一小行 core/ 代码，没必要走这么重的流程"

看改的是什么：

- **纯 bug fix / typo**：走 fast track（不是反哺）
- **新增配置项 / 行为**：走完整 rubric
- **改默认值**：走完整 rubric（即使一行，可能有 breaking change 影响 existing consumer）

### "我想加 adapter-openai/" / "adapter-cursor/"

**不走反哺 rubric**。这是"新建 adapter"，属于 Phase F+ 的 adapter-proposal 流程。在此期间可以在 issue 讨论 + PoC，但不合并进 main 除非有独立的设计 review。

### Gemini 评分很高我是不是就过了

按 `cross-audit-consensus` SKILL.md §2.5 权重表：**Codex 是主锚点**。Gemini 守纪律才是次锚点。只看 Gemini 分数不够。

---

## 7. 示例（一个完整的反哺 PR body）

以下是一个**假想**的反哺 PR body，演示字段填写：

```text
## 起源

- Consumer 项目：snapdrill-ios（私有）
- Consumer 触发 PR：#XX（私有，无法公开链接；脱敏 diff 见附件 diff.txt）
- 积累时间窗：2026-03-15 ~ 2026-04-20
- 有效使用次数：5 次（PR #XX / #YY / #ZZ / #WW / #VV）

## 已有使用证据

在 snapdrill-ios 内，发现 `docs/memory/feedback.md` 新增 F 规则后，经常忘记在 `docs/workflow.md` 引用。每次漏引用都导致后续接手的 agent 读不到该规则。5 次后我们加了一个 `/feedback-crossref-check` skill，每次 feedback.md 变更就提示要更新 workflow.md。5 次实战下来 0 漏引用。

这个 skill 本身**与 iOS 无关**，是所有用"feedback + workflow"双文档体系的项目都会遇到的问题。

## P1 六门槛

- [x] two-consumer rule（下方展开）
- [x] 去项目化残余 = 0（下方 grep 报告）
- [x] 通用性可配置（feedback 文件路径从 policy.layout 读）
- [x] 可测试（新增 3 个单测覆盖 cross-ref 检测）
- [x] 低污染（skill prompt 不含 SnapDrill / Swift / iOS 字样）
- [x] 生命周期清楚（见"生命周期"段）

### 第二 consumer 使用场景

假想一个 Python FastAPI 后端项目用 Cursor，有 `docs/rules.md` + `docs/workflow.md` 双文档。当 rules 新增 "所有 API 必须有 rate limit" 后，workflow 里"发版前 checklist"段应引用该 rule。本 skill 在 Cursor 的 PostToolUse hook 里跑，提示作者更新 workflow。配置差异：Cursor 下 skill 触发是 `.cursor/rules/` 里的 yaml，不是 Claude 的 SKILL.md，需要 `adapter-cursor/` 里重新包装。但 skill 的**检测逻辑**（feedback 变更触发 workflow 引用审查）100% 通用。

### 去项目化 grep 报告

$ grep -riE "snapdrill|swift|ios|swiftui|swiftdata|xcode" adapter-claude/skills/feedback-crossref-check/
(empty)

## P2 3 迭代周期

- [x] consumer 已独立有效使用 5 次（> 3）

### 证据

git log 摘录：（5 次 PR 合并记录）

## 安全级别

- [x] S-normal

## 层分配

- [x] adapter-claude/（skill 形态）

## 测试

- 新增 3 个单测（core/skills-test/test_feedback_crossref.py）
- skill prompt 的 trigger 检测通过 grep-based smoke test

## 迁移说明

无 breaking change。已有 consumer bump lock.json 后可选 enable 本 skill。

## 生命周期

- 启用：consumer 的 policy.layout 含 rules_file + workflow_file 时自动 enable
- 退役：若 consumer 改用单一 rules-workflow 合并文档，可禁用
- 升级：检测算法改动时保持 API 兼容；breaking 改动走新 skill 名 + migration note
```

---

## 8. 元数据

- **本文件所在层**：`docs/contracts/`（第 0 层 core 边界契约）
- **SSOT 来源**：PR-E1（Phase E 反哺机制 setup）
- **last_verified**：2026-04-22
- **何时更新**：每次合并涉及"反哺 rubric" 调整的 PR 时（而不是每次反哺实例）
