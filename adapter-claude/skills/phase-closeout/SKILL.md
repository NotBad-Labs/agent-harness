---
name: phase-closeout
description: 长任务（多 PR / 跨多天的 phase）收官时，生成结构化 checkpoint summary 并固化到消费项目的 checkpoints 目录。当用户说"收官 / 阶段总结 / 写 checkpoint"或单个 phase 合并 ≥ 3 PR 时触发。
allowed-tools:
  - Bash
  - Read
  - Grep
  - Glob
  - Write
context: fork
disable-model-invocation: false
user-invocable: true
---

# /phase-closeout — 长任务 checkpoint 生成

## 触发场景

- 用户说："phase 结束 / 收官 / 写 checkpoint / 阶段总结"
- 单个 phase / sprint 合并 ≥ 3 PR 后
- 接手前发现状态文件落后多个 PR

## 标准输出

```markdown
---
last_verified: <YYYY-MM-DD>
layer: snapshot
freshness:
  max_age_days: 30
  decay_trigger: [phase_change]
---
# Phase Checkpoint <YYYY-MM-DD> <主题>

## Goal

本 phase 想解决的问题（一句话；引用 Issue / ADR）

## Done

- PR #N <主题>（关键改动 + 受影响 layer + 测试增量）
- ...

## Open

- 待合并 PR
- 待解决子任务（指针到 Issue）

## Decisions

- 关键技术 / 产品决策（指针到 ADR / discussion / 三方研究）
- 拒绝的方案 + 理由

## Risks

- 已知风险
- 阻塞链

## Next

- 下一组工作清单（可执行优先级排序）
- 阻塞解除后的解锁顺序

## Metrics（可选，若 session metrics TSV 存在则填充）

- 本 phase tool call 总数：N
- 调用最频繁的 tool（top-3）：Edit × N1 / Bash × N2 / Read × N3
- session 起止时间（UTC）：YYYY-MM-DDTHH:MM → YYYY-MM-DDTHH:MM
- session 时长：~X.X 小时
```

### Metrics 段填充方法

若消费项目的 session metrics TSV 存在（由 `session-metrics.sh` hook 记录 PostToolUse 的**所有 tool**），填充 Metrics 段：

```bash
METRICS_TSV="${AGENT_HARNESS_METRICS_TSV:-.claude/session-metrics.tsv}"

# 总数
wc -l "$METRICS_TSV"

# top-3 tool
cut -f2 "$METRICS_TSV" | sort | uniq -c | sort -rn | head -3

# 起止时间 + 时长（小时，保留 1 位小数）
FIRST=$(head -1 "$METRICS_TSV" | cut -f1)
LAST=$(tail -1 "$METRICS_TSV" | cut -f1)
# 使用 BSD date -j -f 或 GNU date -d，根据 OS 选择
```

**限制**：

- 覆盖**所有** tool（hook matcher `.*`）
- 不含 token 成本（Claude Code hook 当前不暴露该数据）
- 跨 session 累计：hook 追加模式写入，不主动轮转；可手动 `truncate -s 0 <METRICS_TSV>` 重置
- tsv 可能膨胀（一次活跃 session 数百 - 千行）

## 位置

`${AGENT_HARNESS_CHECKPOINT_DIR:-docs/memory/checkpoints}/<YYYY-MM-DD>-<topic>.md`

命名建议：`YYYY-MM-DD-<短主题>.md`，主题用 kebab-case。

## 启动 checklist

- [ ] `git log --since="<phase 开始>" --oneline` 收集本 phase 所有 commit
- [ ] `gh pr list --state merged --search "merged:<日期范围>"` 收集 merged PR
- [ ] Read 当前状态文件找未固化的 OPEN
- [ ] Read 私有记忆（如 `~/.claude/plans/`）找本 phase 决策记录
- [ ] 三方对抗起草 → 引用 `/cross-audit-consensus` 产出的汇总文件

## 与状态文件 / handoff 的分工

| 文件 | 内容 | 频率 |
|---|---|---|
| 消费项目状态文件（如 STATUS.md） | 项目当前快照 | 每次 PR 合并 |
| 消费项目 handoff 文件 | 智能体接手状态 / 待合并 PR / 阻塞 | 每次接手 |
| checkpoints / `<YYYY-MM-DD>-<topic>.md` | **特定 phase 的复盘** | phase 收官 / 每 3-5 PR |

Checkpoint 不替代状态文件 / handoff，而是补充"phase 内细节"，避免状态文件越长越糙。

## 反模式

- 错：把 checkpoint 写到状态文件（污染快照层）
- 错：checkpoint 只罗列 PR 不写 Decisions / Risks（失去复盘价值）
- 错：多个 phase 共用一个 checkpoint 文件（无法独立 revert / 审计）
- 错：checkpoint 时间窗 > 1 月（半衰期超 freshness max_age_days=30）
