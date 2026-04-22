---
last_verified: 2026-04-22
layer: core-tool
status: draft-pr-d2
---
# docaudit — documentation audit engine

> agent-harness 核心工具：对消费项目的知识体系（文档 / 规则 / 链接 / 归档引用）跑一组可配置检查，输出分级 finding 报告。

## 设计原则

- **引擎与内容分离**：引擎不假设任何具体目录 / 术语 / 规则 ID 格式。所有消费项目特定的约定通过 `policy.yaml` 的 `layout` 段注入。
- **fail-closed**：配置错误（无效日期 / 未知 check / 缺必填字段）一律 exit 2，不静默降级。
- **finding-level baseline**：支持 `legacy_whitelist` 按 check + paths + categories 降级单个 finding；新增违规（不匹配白名单）仍原级别阻断，防回归。
- **可逆性优先**：所有输出只读，不修改被审文件。

## 子命令

```text
docaudit <subcommand> [--policy PATH] [--repo-root PATH]
                      [--strict] [--report] [--baseline] [--verbose]
```

| 子命令 | 默认级别 | 含义 |
|---|---|---|
| `all` | — | 跑所有 6 检查 + frontmatter（若 `layout.frontmatter_validator` 配置） |
| `links` | error | Markdown 内部链接目标不存在 |
| `archived-refs` | error | 对 policy 声明的旧路径的活跃硬引用 |
| `orphans` | warning | `layout.orphan_scan_dir` 下零引用 Markdown |
| `home-path-refs` | warning | 仓库内对用户 home 私有路径的硬编码 |
| `rule-pointer-sync` | error | `layout.rules_dir` 下规则指针文件目标校验 |
| `rule-usage` | info | `layout.rules_file` 中规则 ID 外部引用计数 |

## 退出码

| code | 含义 |
|---|---|
| 0 | 通过（无 error；无 warning 或 `--strict` 未启用） |
| 1 | 有 error-level finding，或 `--strict` 下有 warning-level finding |
| 2 | 配置 / 调用错误（policy 文件缺失 / 无效 / 白名单日期无效等） |

## repo root / policy 解析优先级

**repo root**：

1. `--repo-root` CLI 参数
2. `AGENT_HARNESS_REPO_ROOT` 环境变量
3. `git rev-parse --show-toplevel`（若在 git 仓库内）
4. CWD（fallback）

**policy**：

1. `--policy` CLI 参数
2. `AGENT_HARNESS_POLICY` 环境变量
3. `<repo-root>/.agent-harness/policy.yaml`
4. `<repo-root>/Scripts/audit/policy.yaml`（legacy consumer 布局）

## policy schema

见 [`policy.schema.yaml`](./policy.schema.yaml)。消费项目根据 schema 写自己的 `policy.yaml`；引擎对 schema 外字段宽容（忽略），对必填 layout 字段缺失则 skip 对应 check 并记录 `missing_layout_config` warning。

## 安装与依赖

- Python 3.9+（使用 `from __future__ import annotations` 兼容 3.9）
- PyYAML（`pip3 install pyyaml`）

## 测试

```bash
cd core/tools/docaudit
python3 -m unittest tests.test_docaudit
```

self-test 覆盖：

- 每个 check 的 clean / hit 路径
- Whitelist 过滤（按 path / 过期规则 fail-closed / unknown check exit 2 / 无效日期 exit 2）
- strict 模式升级
- 报告输出
- `all` 子命令（含 frontmatter subprocess）
- CLI help 独立性
- Policy 边界（缺失 / 无效版本）

## 与消费项目的集成

消费项目在根目录提供 `policy.yaml`，声明自己的 `layout`（目录 / 文件 / 正则）+ `scan`（include / exclude）+ `checks` 级别。具体模板由 agent-harness 后续 PR 以 adapter preset 形式提供。

消费项目可选：

- 通过 CI 跑 `docaudit all --strict --baseline` 作为合并门禁
- 通过 agent adapter 的 PreToolUse/PostToolUse hook 自动触发（具体 adapter preset 目录提供对应模板）

## 版本与演进

- PR-D2（2026-04-22）：从孵化项目的 docaudit 参数化迁入，去除所有消费项目硬编码
- 未来 PR：根据真实 consumer 反哺需求扩展（候选：墓碑识别 / rule-usage 语义感知 / 多规则 ID 前缀）
