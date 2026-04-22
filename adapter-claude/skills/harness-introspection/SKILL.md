---
name: harness-introspection
description: 元审查 agent-harness 仓库自身健康。扫描 denylist 残余、skill frontmatter 合法性、hook 可执行性、CLI 可调用性、docs 内部链接、PHILOSOPHY 反模式证据，产出分层修复 plan。只产 plan，不改文件。触发：用户说"自省 / harness 体检 / introspect"；或维护者准备切 release / 大 PR 前。
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

# /harness-introspection — agent-harness 自省体检

> 元审查 agent-harness **仓库自身**健康。与 `/knowledge-health` 的角色区别：
>
> - `/knowledge-health` 是 **consumer 项目** 跑的（扫 consumer 的 docaudit + 私有空间）
> - `/harness-introspection` 是 **agent-harness 维护者 / 贡献者** 跑的（扫 agent-harness 仓库本身）

## 设计原则

- **只产 plan，不改任何文件**：可逆性 + 幂等性
- **聚焦 SSOT 一致性**：agent-harness 立的规矩（PHILOSOPHY / contribution-rubric / project-overlay 契约）自己是否遵守
- **分层报告**：按 `docs/contracts/project-overlay.md` 4 层（core / adapter / preset / examples）组织发现
- **可回溯**：plan 文件命名含日期，每次运行产出新文件不覆盖旧 plan

## 触发场景

- 用户说："自省 / harness 体检 / introspect / agent-harness 健康检查"
- 维护者准备切 release / 大 PR 前
- 合并 ≥ 3 PR 后的阶段性 check
- `/phase-closeout` 末尾建议跑一次（agent-harness 仓库的 phase 收官）

## 执行步骤

### 1. 契约层自检（`docs/contracts/project-overlay.md` 4 层）

```bash
# 1.1 core/ denylist 扫（与 CI 一致 + 扩展词）
DENYLIST="claude|codex|gemini|openai|cursor|swift|swiftui|swiftdata|xcode|kotlin|flutter|<known-consumer-names>"
grep -riE "$DENYLIST" core/ \
  --exclude="cmd_extract_candidate.py" \
  --exclude-dir="tests" \
  || echo "core/ clean"

# 1.2 adapter-claude/ 其他 adapter 词扫
# adapter-claude/ 允许 claude/codex/gemini，禁其他 adapter 和消费项目术语
grep -riE "openai|cursor|<other-agent-names>" adapter-claude/ || echo "adapter-claude/ clean"

# 1.3 preset-<domain>/ 消费项目具体产品名扫
for d in preset-*/; do
  grep -riE "<known-product-names>" "$d" || echo "$d clean"
done

# 1.4 examples/ 允许完整 overlay 片段（最宽松），不扫
```

### 2. Skills 结构合法性

```bash
# 2.1 每个 skill 有 SKILL.md
find adapter-*/skills -maxdepth 2 -type d ! -name skills -exec test -f {}/SKILL.md \; -o -print

# 2.2 每个 SKILL.md 有合法 YAML frontmatter
for f in adapter-*/skills/*/SKILL.md; do
  python3 -c "
import yaml, sys
text = open('$f').read()
parts = text.split('---', 2)
if len(parts) < 3:
    print('$f: missing frontmatter')
    sys.exit(1)
try:
    meta = yaml.safe_load(parts[1])
    assert 'name' in meta and 'description' in meta, 'missing name/description'
    print(f'$f OK: {meta[\"name\"]}')
except Exception as e:
    print(f'$f: {e}')
    sys.exit(1)
"
done
```

### 3. Hooks 健康（adapter-claude/hooks/）

```bash
# 3.1 每个 .sh 文件可执行
ls -la adapter-claude/hooks/*.sh | awk '$1 !~ /x/ {print "NOT EXECUTABLE: "$NF}'

# 3.2 每个 hook 顶部有 #!/bin/bash shebang
for h in adapter-claude/hooks/*.sh; do
  head -1 "$h" | grep -q '^#!/bin/bash' || echo "$h: missing shebang"
done

# 3.3 shellcheck clean（如 CI）
if command -v shellcheck >/dev/null; then
  shellcheck --severity=warning adapter-claude/hooks/*.sh
fi
```

### 4. CLI 可调用性

```bash
# 4.1 各子命令 --help 不 crash
for sub in init doctor sync extract-candidate propose-upstream; do
  python3 bin/agent-harness "$sub" --help > /dev/null || echo "$sub --help crashed"
done

# 4.2 CLI tests 跑通
python3 -m unittest discover -s core/cli/tests -p 'test_*.py' -q

# 4.3 docaudit 引擎 self-test 跑通
python3 -m unittest discover -s core/tools/docaudit/tests -p 'test_*.py' -q
```

### 5. Schema / policy 合法性

```bash
# 5.1 policy.schema.yaml 合法 YAML
python3 -c "import yaml; yaml.safe_load(open('core/tools/docaudit/policy.schema.yaml'))"

# 5.2 adapter-claude/policy.starter.yaml 合法 + 可被 docaudit load
python3 -c "import yaml; p=yaml.safe_load(open('adapter-claude/policy.starter.yaml')); assert p['version']==1"

# 5.3 templates/base/.agent-harness/project.yaml 合法
python3 -c "import yaml; yaml.safe_load(open('templates/base/.agent-harness/project.yaml'))"

# 5.4 settings.example.json 合法 JSON
python3 -c "import json; json.load(open('adapter-claude/settings.example.json'))"
```

### 6. Docs 内部链接健康

```bash
# 6.1 Markdown 内部链接目标存在（参考 docaudit links check）
# 本 skill 对 agent-harness 仓库自己跑一遍 docaudit 逻辑（或手写简化版）
grep -rEo '\[[^]]+\]\(\./[^)]+\)' README.md PHILOSOPHY.md BOOTSTRAP.md CONTRIBUTING.md docs/ adapter-claude/README.md \
  | while read -r line; do
    path=$(echo "$line" | grep -oE '\([^)]+\)' | tr -d '()')
    # relative path resolution + exist check（伪代码）
  done
```

简化策略：让作者手动 `grep -n '](./' <file>` + spot check。完整链接检查留给 CI docs-audit job（未来可加）。

### 7. PHILOSOPHY 反模式证据扫描

根据 [PHILOSOPHY.md 第 3 节反模式](../../../PHILOSOPHY.md)：

#### 反模式 1：机制崇拜

- 扫 skill / hook / doc 里"每次必跑"、"强制"、"总是"类硬词
- 如果某个机制没有**触发条件 / 退出条件 / 成本预算**三段，flag 为机制崇拜候选

```bash
# 启发式：skill 文件含"必须" + 没有"何时退役" / "成本预算"
for s in adapter-*/skills/*/SKILL.md; do
  has_must=$(grep -c '必须\|强制\|每次' "$s")
  has_exit=$(grep -c '退役\|退出条件\|停用' "$s")
  if [ "$has_must" -gt 2 ] && [ "$has_exit" -eq 0 ]; then
    echo "SUSPECT 机制崇拜: $s (must=$has_must exit=0)"
  fi
done
```

#### 反模式 2：过度抽象 / YAGNI 违反

- 扫 `core/` 新增的"假想未来消费者"式抽象
- Two-consumer rule 在 CONTRIBUTING/rubric 是硬门槛；本 skill check 现状：
  - `core/` 有几个文件？每个是否真的由 ≥ 2 consumer 需求验证？
  - 如果只有 1 consumer（snapdrill-ios）且无"第二 consumer 实证"归档，标 "单 consumer 风险"

#### 反模式 3：假通用陷阱

- 扫 `preset-ios/` 是否还是 placeholder（Phase D 初始空）
- 如果所有 preset 都空或都来自单一 consumer，**agent-harness 仍是"一个项目的 generalized 版本"** — 在 README 诚实声明
- 检查 README Project status 段是否还标 "experimental"（不要偷偷改为 "production" 除非真有 2+ consumer）

#### 反模式 4：被消费项目污染

- 已由 denylist 扫（步骤 1.1-1.3）覆盖

### 8. 产出 plan 文件

**路径**：`<repo-root>/.harness-introspection/introspection-<YYYY-MM-DD>.md`

消费项目的 `~/.claude/plans/` 与 agent-harness 的 `.harness-introspection/` 分开，避免混淆。

**格式**：

```markdown
# agent-harness Introspection Report <YYYY-MM-DD>

## Meta

- Repo HEAD: <commit SHA>
- Triggered by: <user / phase-closeout / manual>
- Executed on: <ISO timestamp>

## 1. 契约层自检

### core/ denylist
<粘贴 grep 结果>

### adapter-claude/ other-adapter 残余
<粘贴结果>

### preset-<domain>/ 产品名残余
<粘贴结果>

## 2. Skills 合法性

- 总 skill 数: N
- Frontmatter 合法: N/N
- 问题：<清单>

## 3. Hooks 健康

- 可执行: N/N
- Shebang 合规: N/N
- shellcheck warning: N

## 4. CLI 可调用性

- 子命令 --help 全通过: <Y/N>
- docaudit tests: <通过数/总数>
- CLI tests: <通过数/总数>

## 5. Schema / policy

- policy.schema.yaml: <valid / error>
- policy.starter.yaml: <valid / error>
- project.yaml template: <valid / error>
- settings.example.json: <valid / error>

## 6. Docs 链接

- Spot check: <通过 / 问题清单>

## 7. PHILOSOPHY 反模式证据

### 机制崇拜候选
<清单（skill path + must/exit 比）>

### 单 consumer 风险
- core/ 文件数: N
- adapter-claude/ 文件数: N
- preset-* 非空目录数: N
- 结论：<是 / 否>

### README Project status 段
- 声明: experimental / production / ...
- 是否 ≥ 2 真实 consumer: <Y/N>
- 一致性: <通过 / 需修复>

## 8. 建议动作清单（分优先级）

### P1（本周处理）
- [ ] <动作>

### P2（本 release）
- [ ] <动作>

### P3（长期）
- [ ] <动作>
```

## 降级路径

- `git rev-parse HEAD` 失败：标 `(not a git repo)`，继续其他步骤
- `shellcheck` 不存在：跳过步骤 3.3，不视为错误
- `python3` / `yaml` 缺失：标 `(python yaml missing, please pip install pyyaml)`
- 任一步骤 exit 非 0：plan 里标 `(step X failed: <reason>)`，继续下一步

## 严格要求

- **不修任何文件**（唯一写操作：plan 文件本身）
- **不 git commit / push**
- **不改 CI workflow**
- plan 里可以建议"修 X"，但不实际执行

## 失败行为

- 任一步骤出错：继续其他步骤，plan 里标 failed
- plan 写入失败（磁盘满 / 权限）：stderr 告警，退出 0（不阻断）

## 返回信息（skill 执行完毕）

给主线程 ≤ 150 字摘要：

- plan 文件路径
- 发现的 P1 条目数
- 红线 check（若 denylist 命中 / CLI crash / skill frontmatter 失败）→ 明确标出
- 下一步建议

## 与 knowledge-health 的分工

| 维度 | `/knowledge-health` | `/harness-introspection` |
|---|---|---|
| 扫描对象 | Consumer 项目（docaudit + 私有 plans / memory） | agent-harness 仓库本身 |
| 角色 | Consumer 项目维护者 | agent-harness 维护者 / 贡献者 |
| 输出位置 | `~/.claude/plans/knowledge-health-YYYY-MM-DD.md` | `<agent-harness-repo>/.harness-introspection/introspection-YYYY-MM-DD.md` |
| 重点 | 知识体系过期 / dead rule / plans 归档 | PHILOSOPHY 契约一致性 / 反模式证据 / 单 consumer 风险 |

两个 skill 互补，都遵循"只产 plan 不改文件"原则。

## 与 PHILOSOPHY 对齐

- 三原则 #1 空白+演进：本 skill 是"演进健康度"的测量仪
- 反模式 #1 机制崇拜：**本 skill 自身也适用** — 如果维护者从不跑 introspection，说明该机制应该降级为可选
- 反模式 #3 假通用：step 7 的"单 consumer 风险"check 是唯一硬 check — 如果 agent-harness 长期只有 1 真实 consumer，README 定位必须保持 experimental
