# TWU 后续开发规划

---

## 当前状态（v1.0）

已实现的 CLI 命令（`twu`）：

| 命令 | 功能 |
|------|------|
| `twu parse <dir>` | 调用 Docling 解析文档，提取到 `req/chunks/` 和 `req/assets/` |
| `twu export <dir>` | 导出测试用例为 Excel |
| `twu case-batch <xml>` | 批量执行用例的 replace / delete 操作 |
| `twu validate-case <dir>` | 校验用例格式是否符合规范 |
| `twu validate-plan <dir>` | 校验测试规划格式是否符合规范 |
| `twu init <dir>` | 初始化需求目录结构 |

---

## twu CLI 增强

### 工作流状态追踪

当前问题：不清楚某个需求目录处于哪个阶段。

```bash
twu status <dir>
```

预期输出：

```
需求目录: feature-login/
  ✓ req-parse    req/index.md (2026-02-20, 3次修订)
  ✓ req-review   req/issues.md (12个问题，已全部回答)
  ✓ tc-plan      tc/plan.md (4个Module，15个Scenario)
  ○ tc-gen       未开始
```

### 批量初始化

```bash
twu init --batch requirements.txt   # 从文件批量创建需求目录
```

### 用例统计

```bash
twu stats <dir>                     # 统计用例数量、优先级分布、覆盖模块
```

---

## twucli（交互式 CLI）

**目标**：在终端中以交互式向导引导用户完成整个测试工作流，降低使用门槛。

### 核心功能

```
$ twucli

? 选择需求目录: feature-login/
? 当前阶段: req-parse 已完成，进入 req-review？ Yes

> 正在分析 req/index.md...
> 发现 8 个需求问题
> 已生成 req/issues.md

? 请将 issues.md 发给产品确认，完成后按 Enter 继续
```

### 设计要点

- 自动检测当前阶段（根据产物文件是否存在）
- 引导式操作，每步有提示和确认
- 集成 `git commit` 提醒
- 支持 `--dry-run` 预览将要执行的操作

---

## 质量追踪

**目标**：追踪用例质量随需求迭代的变化。

```bash
twu diff-tc <dir> --from v1.0 --to v2.0    # 对比两个版本的用例变化
twu coverage <dir>                          # 分析需求条目到用例的覆盖率
```

---

## 导出增强

| 格式 | 状态 | 说明 |
|------|------|------|
| Excel | 已实现 | 按 Module/Scenario/Case 三级结构 |
| XMind | 规划中 | 思维导图格式，便于评审 |
| JSONL | 规划中 | 标准化数据格式，对接用例管理系统 |
| Markdown 汇总 | 规划中 | 所有用例合并为单文件 |

---

## MCP Server（远期）

将 TWU 的核心能力封装为 MCP Server，使 AI Agent 可以直接调用：

```
tools:
  - twu_parse_doc      # 解析文档
  - twu_get_issues     # 获取问题清单
  - twu_get_plan       # 获取测试规划
  - twu_get_cases      # 获取测试用例
  - twu_export         # 导出
```

适用场景：在 CI/CD 流水线中自动触发测试规划更新、与其他测试平台集成。

---

## 版本节奏

| 版本 | 主要内容 |
|------|----------|
| v1.0 | 当前：基础 CLI + 4 个 Skills |
| v1.1 | twu status + twu stats + JSONL 导出 |
| v1.2 | twucli 交互式向导 |
| v2.0 | 质量追踪 + XMind 导出 |
| v3.0 | MCP Server |
