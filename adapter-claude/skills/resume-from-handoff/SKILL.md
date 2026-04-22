---
name: resume-from-handoff
description: 新 Claude 会话接手项目时，按最小上下文加载顺序读取，避免强吃长 transcript。当会话开始或用户说"接手 / 续上次工作 / resume / handoff"时触发。
allowed-tools:
  - Read
  - Bash
  - Glob
  - Grep
context: fork
disable-model-invocation: false
user-invocable: true
---

# /resume-from-handoff — 接手时最小上下文加载

## 触发场景

- 新会话第一次工作于消费项目
- 用户说："接手 / 续上次工作 / resume / 你看看现状 / 我们到哪了"
- 长会话 compact 后需要重建上下文

## 加载顺序（严格按序，少即是多）

核心思想：**less context, more retrieval**。先加载项目入口 + 快照 + 纪律，延后加载任务细节。

### Tier 1：必读（通常 4-5 文件，约 800 行）

消费项目应在 `.agent-harness/project.yaml` 或文档里声明自己的 Tier 1 文件清单。推荐包括：

1. 项目入口（通常 `CLAUDE.md`）— 路由信息，可能已自动加载
2. 项目状态快照（通常 `STATUS.md` 或等价文件）
3. 接手状态文件（通常 `docs/memory/handoff.md` 或等价）
4. 反哺纪律（通常 `docs/memory/feedback.md` 或等价）
5. 协作规范（通常 `docs/principles/collaboration.md`，如即将做对抗审查）

### Tier 2：按需（用户描述任务后再读）

- 最近 1-2 个 checkpoint（通常 `docs/memory/checkpoints/<date>-*.md`）
- 任务相关的原则文档（如改代码 → `coding.md` 等）
- 任务相关的产品文档
- 当前 git 状态：`git status` + `git log --oneline -10` + `gh pr list --state open --author '@me'`

### Tier 3：避免（除非明确需要）

- 错：一上来读全部 ADR 历史（除非要写新 ADR）
- 错：一上来读全部 `~/.claude/plans/*`（仅相关任务时按需）
- 错：展开状态文件所有历史段（看头部"当前状态"段即可）

## 不加载长 transcript

- 不强吃"上次会话的全部对话"
- 不读完整 ADR 历史
- 不展开所有产品文档内容

如果 Tier 1 + 2 不足以回答用户问题：

- 用 Grep 检索相关关键词
- 不要"先读所有文件再说"

## 启动报告模板

接手完成后给用户一句话简报：

```markdown
**接手完成**

- 当前焦点：[状态文件"当前状态"段]
- 待合并 PR：#NNN ([标题简短])
- 阻塞：[handoff 阻塞链]
- 最近 checkpoint：[最新 checkpoints 文件]
- 我准备 [下一步动作]，你确认或修正？
```

## 反模式

- 错：一上来读 20+ 文件再开始（违反 Tier 原则）
- 错：跳过状态文件 / handoff 直接写代码（必失上下文）
- 错：读完 Tier 1 不简报就开干（用户不知道 agent 抓了什么）

## Consumer 配置

消费项目可以在 `.agent-harness/project.yaml` 下声明 Tier 1 / Tier 2 清单，让本 skill 自动读对应文件。没有声明时 skill 按推荐默认尝试读 `CLAUDE.md` / `STATUS.md` / `docs/memory/handoff.md` / `docs/memory/feedback.md`。
