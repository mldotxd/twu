# TWU - 测试工作流工具

> Test Workflow Utility —— 基于上下文工程的人机协作测试流程

## 是什么

TWU 是一套运行在 Claude Code 上的测试工作流技能包 + CLI 工具链。

它解决的核心问题：**需求不完备导致测试用例质量低**。传统做法是直接让 AI 生成用例，实测用例歧义率约 27%，大量时间浪费在返工上。TWU 的做法是先修需求，再写规划，最后生成用例，每个阶段都有人工确认节点。

## 工作流

```
原始文档 → 需求解析 → 需求审核 → 测试规划 → 测试用例
            /req-parse  /req-review  /tc-plan    /tc-gen
```

每个阶段：AI 生成产物 → git commit → 人工审核 → 确认 → 下一阶段

## 快速开始

```bash
# 安装
uv pip install -e .

# 编写项目业务背景（必填，AI 执行时自动读取）
# 写入：产品是什么、核心术语、用户角色、测试规范等
# 参考 CLAUDE.md 模板
vi CLAUDE.md

# 初始化需求目录
twu init feature-login/

# 放入原始文档
cp prd.pdf feature-login/raw/

# 在 Claude Code 中执行各阶段
/req-parse    # 生成标准化需求
/req-review   # 审核需求问题
/tc-plan      # 生成测试规划
/tc-gen       # 生成测试用例

# 导出
twu export feature-login/
```

## CLI 命令

| 命令 | 说明 |
|------|------|
| `twu init <dir>` | 初始化需求目录 |
| `twu parse <dir>` | 解析文档（Docling） |
| `twu export <dir>` | 导出用例为 Excel |
| `twu case-batch <xml>` | 批量修改用例 |
| `twu validate-case <dir>` | 校验用例格式 |
| `twu validate-plan <dir>` | 校验规划格式 |

## 文档

- [CONCEPTS.md](docs/CONCEPTS.md) — 核心思想：上下文工程与 HITL 设计
- [WORKFLOW.md](docs/WORKFLOW.md) — 四阶段人机协作流程详解
- [ROADMAP.md](docs/ROADMAP.md) — 后续开发规划（twucli 等）
