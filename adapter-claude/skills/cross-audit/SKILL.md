---
name: cross-audit
description: 三方对抗性审查工作流（Claude 主线程 + Codex + Gemini）。强制"相同完整任务，不分工"纪律。当用户要求"三方审计 / 对抗性审查 / 独立审计 / cross-audit"，或 PR 合并前需对抗性 review 时触发。
allowed-tools:
  - Bash
  - Read
  - Grep
  - Glob
  - Agent
  - Write
context: fork
disable-model-invocation: false
user-invocable: true
---

# /cross-audit — 三方对抗性审查工作流

## 触发场景

- 用户说："三方审计 / 对抗性审查 / 独立审计 / cross-audit"
- PR 合并前需对抗性 review
- 大型重构 / 文档系统性变更前

## 必须遵守的三纪律

1. **相同完整任务**：三家审同**同一批文件**完整集合，**不分工**。冗余是刻意的 —— 通过"你发现了我没发现的"暴露盲区
2. **审计期间只读**：三方启动后不得修改被审文件，等汇总后统一修复
3. **不偷懒**：禁止抽查后声称"基本准确"，必须全量

Consumer 项目可以在本 skill 的行为之外定义自己的 F-NNN 规则对应上述纪律（例如 feedback.md 中的 F-008/F-011/F-012）。

## 启动前 checklist

- [ ] 已读取消费项目的 Codex 委派规范（默认 effort high for 审计 / Review）
- [ ] 已读取消费项目的 Gemini 委派规范（不加 sandbox，防卡死）
- [ ] 已读取消费项目的委派共享约束（必须内联到 prompt）
- [ ] 已读取消费项目的反哺纪律（对应"相同完整任务 / 审计期间只读 / 不偷懒"三条规则）
- [ ] 审计目标和文件清单已明确（写下来，不要口头默认）

## 三方启动模板

### 给 Claude 主线程

```text
你审 [审计目标]，范围 [完整文件清单]，维度（DRY / YAGNI / 方法论适配 / 一致性 / 时效性）。
不分工，独立完成全部。
PR 审查场景必须补 4 维评分：Scope Fidelity / Code Quality / Test Coverage /
Architecture Fit（0-10 分，整数），见 /cross-audit-consensus 评分规范。
```

### 给 Codex（Agent 委派或 codex exec）

```text
模型：gpt-5.4，effort: high
范围：与 Claude 完全一致 [审计目标 + 完整文件清单]
维度：DRY / YAGNI / 方法论适配 / 一致性 / 时效性
内联约束：[消费项目的委派共享约束全文]
输出格式：结构化报告，分级 Critical / Warning / Info，每项含证据
PR 审查场景必须在报告末尾补 4 维评分表（0-10 整数分 + 综合平均），
维度：Scope Fidelity / Code Quality / Test Coverage / Architecture Fit
不参考 Claude 的中间结论
```

调用方式优先级：

1. `codex exec --model gpt-5.4 --full-auto "<prompt>"`（最稳定，可写文件）
2. `Agent(subagent_type=codex:codex-rescue, prompt=...)`（fallback，注意 plan mode 误判风险）

### 给 Gemini（Bash）

```bash
gemini -p "你审 [审计目标]
范围：与 Claude / Codex 完全一致 [完整文件清单]
维度同上
内联约束：[消费项目的委派共享约束全文]
输出：结构化中文报告，分级 Critical / Warning / Info
PR 审查场景末尾补 4 维评分表

评分纪律（强制）：
1. 每维度必须引用 plan / Issue Sprint Contract 明文条目作锚点；禁止感性打分
2. 默认从 8.0 起评，每个正向证据 +1，每个负向证据 -1
3. 10.0 分硬门槛：仅在 plan 每一条都明文命中 + 无任何 scope 外增量 + 架构严格遵守时给
4. 若某维度无 plan/contract 可对照，降权或标 N/A（不折算为 10.0）
5. 方差自检：若你的分数与 Codex 可能差 >= 2 分，在报告末尾解释原因
6. 裁决权重：你守纪律时作次锚点（不等于主锚点 Codex），不守时降为参考
" 2>&1
```

注意：

- 不加 `--sandbox`（性能 2x+ 损失）
- 单次 prompt 不超 5 个长文件，超出则分批
- 大型审计可能触发 429 速率限制，需 retry

## 汇总表格

| # | 维度 | 发现 | Claude | Codex | Gemini | 共识 | 证据 |
|---|---|---|---|---|---|---|---|
| R1 | ... | ... | Critical | Critical | — | 2/3 | ... |

**共识度判定**：

- ≥ 2/3 → 高置信度，进入修复
- 单家 → 必须实证验证（深度读源码）
- 实证否定 → 归档为"误判"案例

## 反模式

- 错：「Gemini 擅长 X，让它审 X；Codex 擅长 Y，让它审 Y」— 违反"相同完整任务"
- 错：「为节省时间，三家分工」— 失去对抗性，盲区无法暴露
- 错：「Gemini 报 Critical 直接修」— 未经实证验证，可能是误判
- 错：审计期间提前修改被审文件
- 错：抽查 10 处说"全部一致"

## 完成标准

1. 三家独立报告全部到位（通常写到 `~/.claude/plans/<topic>-{claude,codex,gemini}.md`）
2. 汇总表格按共识度排序
3. 每个 Critical 经实证验证（Read + Grep）
4. 综合报告归档（建议路径：消费项目的 `docs/archive/<topic>-audit-<YYYYMMDD>.md` 或等价位置）

## 上游引用（消费项目应提供对应文档）

- Codex 委派详细规范
- Gemini 委派详细规范
- 三方协作总体架构 + 汇总表格模板
- 委派 prompt 共享约束
- 反哺纪律（对应"相同完整任务 / 审计期间只读 / 不偷懒"三条）

具体文件路径由消费项目决定。本 skill 的 checklist 段列出需读取的文档类型。
