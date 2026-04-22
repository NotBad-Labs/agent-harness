---
name: knowledge-health
description: 知识体系体检。跑 docaudit all + 扫描 CI 看不到的私有空间（`~/.claude/plans/`、`~/.claude/projects/.../memory/`），产出分层修复计划到 `~/.claude/plans/knowledge-health-YYYY-MM-DD.md`。不改任何文件，只产 plan。触发时机：用户说"体检 / 知识体系审计 / /knowledge-health"，或 /phase-closeout 收官末尾。
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

# /knowledge-health — 知识体系体检

## 设计原则

- **只产 plan，不改任何文件**：所有修复动作写到 plan 文件，由用户或后续 PR 执行。可逆性 + 幂等性基线。
- **覆盖 CI 盲区**：`docaudit` 只扫 workspace（CI 可见部分）；skill 补扫 Claude 私有空间（CI 不可见）。
- **分层报告**：CI-visible（docaudit 原始输出）+ CI-invisible（Claude 本地视角）清晰分段。

## 触发场景

- 用户说："体检 / 知识体系审计 / `/knowledge-health`"
- `/phase-closeout` 末尾建议跑一次（phase 合并 ≥ 3 PR 后）
- 接手新 session 发现状态文件过期 / 有待办积压时

## 执行步骤

### 1. 跑 docaudit 全量扫描

```bash
${AGENT_HARNESS_DOCAUDIT_CMD:-python3 core/tools/docaudit/docaudit.py} all --verbose
${AGENT_HARNESS_DOCAUDIT_CMD:-python3 core/tools/docaudit/docaudit.py} all --baseline --verbose
${AGENT_HARNESS_DOCAUDIT_CMD:-python3 core/tools/docaudit/docaudit.py} all --report --baseline
```

消费项目可以通过 `AGENT_HARNESS_DOCAUDIT_CMD` 环境变量指定具体的 docaudit 调用命令（例如若 agent-harness 以 submodule 方式嵌入，指向 submodule 内路径）。

### 2. 扫描 CI 看不到的私有空间

**`~/.claude/plans/`**：

- 列出所有 plans，按文件名 pattern 分类：
  - 对应已合并 PR（`<feature>-pr<N>.md` / branch name 匹配）→ 可删
  - 研究归档（`doc-audit-*.md` / `*-cross-audit-*.md`）→ 归档或保留
  - 进行中（最近 30 天修改）→ 保留
  - UNCERTAIN（无法分类）→ 标记人工判断

**`~/.claude/projects/<project-slug>/memory/`**：

- 读 MEMORY.md 索引
- 对每个 `feedback_*.md`，grep 消费项目的反哺规则源（通常是 `docs/memory/feedback.md`）的规则是否已覆盖
  - 已覆盖 → dead memory 候选（建议退役）
  - 未覆盖 → 保留

### 3. 产出 plan 文件

**路径**：`~/.claude/plans/knowledge-health-<YYYY-MM-DD>.md`

**格式**：

```markdown
# Knowledge Health Report <YYYY-MM-DD>

## 1. CI-visible（docaudit 输出）

<粘贴 docaudit all --verbose 完整输出>

### 分级摘要

- Critical（error 级）: <数量>
- High（warning 级）: <数量>
- Info（info 级）: <数量>
- Suppressed（legacy_whitelist）: <数量>

## 2. CI-invisible（Claude 本地视角）

### ~/.claude/plans/ 分类

- 对应已合并 PR（可删）：
  - <文件名>（已合并：PR #N）
- 研究归档（保留）：
  - <文件名>
- 进行中（保留）：
  - <文件名>
- UNCERTAIN（人工判断）：
  - <文件名>

### ~/.claude/projects/.../memory/ 去重候选

- <memory 文件>: 已被消费项目的反哺规则覆盖，建议退役

## 3. 建议动作清单（分优先级）

### P1（本周处理）

- [ ] <动作>

### P2（本 sprint）

- [ ] <动作>

### P3（Phase 收官）

- [ ] <动作>

## 4. 元数据

- 生成时间：<ISO 8601>
- 触发：<用户命令 / phase-closeout / 手动>
- docaudit 版本：<脚本最后修改日期>
```

### 4. 降级路径

- `docaudit` 不可用：CI-visible 段标记 `(engine missing)`，继续私有部分
- `~/.claude/plans/` 不存在：CI-invisible 段标记 `(no local plans dir)`，不视为错误
- `~/.claude/projects/.../memory/` 不存在：同上标记 `(no local memory)`

## 严格要求

- **不自动执行修复动作**：只写 plan，不 `rm` / `mv` / `git` 动作
- **不合并文件**：plan 里可以建议"合并 A 与 B"，但不实际合并
- **不跨会话持久化**：plan 文件命名含日期，每次运行产出新文件，不覆盖旧 plan

## 失败行为

- 任一步骤出错：继续其他步骤，plan 里标记 `(step X failed: <reason>)`
- plan 文件写入失败（磁盘满 / 权限）：stderr 告警，退出 0（不阻断对话）

## 返回信息（skill 执行完毕）

给主线程 ≤ 150 字摘要：

- plan 文件路径
- 发现的 P1 条目数
- 下一步建议（"按 P1 清单逐条处理" / "Phase 收官启动" / "无需操作" 等）

## 与审计命中处置协议的关系

消费项目可能定义"审计命中处置协议"（必须修复 / 可豁免 / 豁免如何留痕）。本 skill 的产出 plan 是处置协议的**输入**（人读后决定如何闭环），不是自动化执行器。
