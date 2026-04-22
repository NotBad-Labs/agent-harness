---
name: update-status
description: PR 合并后将状态文件直接推送到默认分支。文档化例外 —— 状态追踪文件不需要走 PR 流程。
allowed-tools:
  - Bash
  - Read
  - Edit
context: fork
disable-model-invocation: true
user-invocable: true
---

# /update-status — 状态看板推送

## 触发条件

PR 合并后、消费项目的状态文件已在本地更新完成时执行。

**Consumer 配置**：

- `AGENT_HARNESS_STATUS_FILE`：状态文件路径（默认 `STATUS.md`）
- `AGENT_HARNESS_DEFAULT_BRANCH`：默认分支名（默认 `main`）

## 执行流程

### 1. 检查工作区是否干净

```bash
STATUS_FILE="${AGENT_HARNESS_STATUS_FILE:-STATUS.md}"

# 先检查是否有未提交的代码变更（状态文件除外）
if git diff --name-only HEAD | grep -v "$STATUS_FILE" | grep -q .; then
  echo "工作区有未提交的代码变更，请先处理后再推送 $STATUS_FILE"
  exit 1
fi
```

### 2. 确认在默认分支

```bash
DEFAULT_BRANCH="${AGENT_HARNESS_DEFAULT_BRANCH:-main}"
current_branch=$(git branch --show-current)
if [ "$current_branch" != "$DEFAULT_BRANCH" ]; then
  echo "当前不在 $DEFAULT_BRANCH 分支（$current_branch），先切换"
  git checkout "$DEFAULT_BRANCH" && git pull
fi
```

### 3. 检查是否有待推送的状态变更

```bash
git status "$STATUS_FILE"
```

如果无变更，提示「状态文件已是最新，无需推送」并退出。

### 4. 精确 stage + commit + push

```bash
git add "$STATUS_FILE"
git commit -m "status: 更新项目状态看板

Co-Authored-By: Claude Code <noreply@anthropic.com>"
git push origin "$DEFAULT_BRANCH"
```

**只 add 状态文件**，不使用 `git add .` 或 `git add -A`。

## 文档化例外

状态文件是追踪文件，不含代码逻辑：

- 不需要 Code Review（review 的是代码，不是状态记录）
- 不需要 CI 验证（不影响编译和测试）
- 每次开 PR 只为推状态文件是流程浪费

此例外需要消费项目在工作流文档里明确声明（否则默认走 PR 流程）。

## 注意事项

- 如果默认分支有远程更新（其他 PR 刚合并），先 `git pull` 再 push
- 如果有其他未提交的代码变更混在工作区，**不要执行** —— 先处理代码变更
- commit message 固定为 `status: ...`（描述本次更新内容），不需要关联 Issue
- 消费项目可以用 git hook 或 CI 规则拒绝 push 到受保护分支；本 skill 不绕过这类保护
