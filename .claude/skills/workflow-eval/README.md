# 工作流评估（workflow-eval）

深度评估 skill 工作流的执行过程、输出质量和 trace，生成评估报告并提供改进建议。

## 快速开始

### 方式 1：使用 Skill（推荐）

```bash
/workflow-eval docs/eval/01.txt
```

### 方式 2：使用 Python 工具

```bash
# 自动检测最新会话（推荐）
uv run python eval_workflow.py --latest

# 评估执行历史（纯文本）
uv run python eval_workflow.py docs/eval/01.txt --type history

# 评估 JSONL 会话文件
uv run python eval_workflow.py ~/.claude/projects/-Users-Apple-mf-test-twu/613aaaf5.jsonl --type jsonl

# 评估 Git 提交范围
uv run python eval_workflow.py e6a36e5..25f79de --type git

# 评估输出目录
uv run python eval_workflow.py 相框端-轮播展示/ --type dir
```

## Claude Code 历史记录

### 历史记录存储位置

Claude Code 的对话历史存储在：

```
~/.claude/projects/{project-path}/{session-id}.jsonl
```

例如：
```
~/.claude/projects/-Users-Apple-mf-test-twu/613aaaf5-fb22-49db-9ab7-4f181c9f8aaa.jsonl
```

### 历史记录格式

JSONL 文件包含以下类型的记录：

- `type: "user"` - 用户消息（包含工具调用结果）
- `type: "assistant"` - 助手消息（包含工具调用）
- `type: "file-history-snapshot"` - 文件历史快照
- `type: "progress"` - 进度信息
- `type: "system"` - 系统消息

### 自动检测最新会话

使用 `--latest` 参数可以自动检测并评估最新的会话：

```bash
uv run python eval_workflow.py --latest
```

这会：
1. 自动查找当前项目的 Claude 历史目录
2. 按修改时间排序，选择最新的 JSONL 文件
3. 提取工具调用、Git 提交等信息
4. 生成评估报告

## 评估维度

### 1. 过程评估（Process）

- **执行流程分析**：Skill 调用顺序、工具使用、冗余操作
- **时间效率分析**：总执行时间、各阶段耗时、性能瓶颈
- **交互质量分析**：用户交互次数、引导语清晰度

### 2. 结果评估（Output）

- **文档质量**：结构完整性、格式正确性、内容准确性、可读性
- **Git 提交质量**：提交信息规范、提交粒度、文件变更
- **工具输出验证**：`uv run twu validate` 是否通过

### 3. Trace 分析（Trace）

- **工具调用链**：工具调用序列、参数传递、返回值处理
- **状态转换**：文件状态变化、数据流转
- **异常处理**：错误发生、错误恢复

## 输出示例

评估完成后会生成：

```
eval/{timestamp}/
├── report.md          # 评估报告
└── improvements.md    # 改进方案（可选）
```

### 报告结构

```markdown
# 工作流评估报告

## 一、执行概览
- Skill 调用：4 次
- 工具调用统计：Bash 16 次、Write 31 次
- 文件操作：24 个文件
- Git 提交：6 次
- 总耗时：12m 3s

## 二、过程评估（95/100）
- 执行流程 ✓
- 时间效率 ✓
- 交互质量 ✓

## 三、结果评估（90/100）
- 文档质量：req/index.md (95/100)
- Git 提交质量 ✓
- 工具验证 ✓

## 四、Trace 分析（92/100）
- 工具调用链 ✓
- 状态转换 ✓
- 异常处理 ✓

## 五、改进建议
1. 优化用户交互时间（高优先级）
2. 增强文档质量检查（中优先级）
3. 增加并行处理（低优先级）
```

## 使用场景

### 场景 1：评估完整工作流

```bash
# 保存执行历史到文件
/workflow-eval docs/eval/01.txt
```

适用于：评估一次完整的 skill 执行过程（req-parse → req-review → tc-plan → tc-gen）

### 场景 2：评估 Git 提交

```bash
/workflow-eval e6a36e5..25f79de
```

适用于：评估指定范围内的 git 提交质量

### 场景 3：评估输出目录

```bash
/workflow-eval 相框端-轮播展示/
```

适用于：静态分析输出目录，评估文档质量

## 评估指标

### 过程评估指标

| 指标 | 说明 | 评分标准 |
|------|------|---------|
| Skill 调用顺序 | 是否按正确顺序调用 | 正确 100 / 有问题 60 |
| 工具使用 | 是否使用合适的工具 | 合理 100 / 有冗余 80 |
| 时间效率 | 总耗时是否合理 | <15min 100 / <30min 80 |
| 交互质量 | 引导语是否清晰 | 清晰 100 / 模糊 70 |

### 结果评估指标

| 指标 | 说明 | 评分标准 |
|------|------|---------|
| 文档结构 | 章节是否完整 | 完整 100 / 缺失 60 |
| 格式正确性 | Markdown 语法 | 正确 100 / 有错误 70 |
| 内容准确性 | 是否符合需求 | 准确 100 / 有偏差 70 |
| Git 提交 | 提交信息是否规范 | 规范 100 / 不规范 60 |

### Trace 分析指标

| 指标 | 说明 | 评分标准 |
|------|------|---------|
| 工具调用链 | 调用序列是否清晰 | 清晰 100 / 混乱 60 |
| 状态转换 | 文件状态变化 | 符合预期 100 / 异常 60 |
| 异常处理 | 错误恢复 | 成功 100 / 失败 50 |

## 改进建议优先级

### 高优先级（立即实施）

- 影响用户体验的问题
- 导致输出质量下降的问题
- 明显的性能瓶颈

### 中优先级（短期实施）

- 可以优化但不紧急的问题
- 提升文档质量的改进
- 增强工具验证的改进

### 低优先级（长期实施）

- 锦上添花的优化
- 性能提升但影响不大
- 需要较大改动的优化

## 最佳实践

### 1. 定期评估

建议在每次完成一个完整工作流后进行评估，及时发现问题。

### 2. 对比评估

保存多次评估报告，对比不同版本的改进效果。

### 3. 迭代优化

根据评估报告的改进建议，逐步优化工作流。

### 4. 文档归档

将评估报告归档到 `docs/eval/` 目录，便于追溯。

## 扩展

### 自定义评估维度

可以在 `eval_workflow.py` 中添加自定义的评估维度：

```python
def _evaluate_custom(self):
    """自定义评估逻辑"""
    # 添加你的评估逻辑
    pass
```

### 集成到 CI/CD

可以将评估工具集成到 CI/CD 流程中，自动评估每次提交：

```yaml
# .github/workflows/eval.yml
name: Workflow Evaluation

on: [push]

jobs:
  eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run evaluation
        run: uv run python eval_workflow.py . --type dir
```

## 常见问题

### Q: 评估报告中的评分是如何计算的？

A: 评分基于多个维度的加权平均，具体权重可以在代码中调整。

### Q: 如何保存执行历史？

A: Claude Code 会自动保存对话历史到 `~/.claude/projects/{project-path}/{session-id}.jsonl`。

你可以：
1. 使用 `--latest` 参数自动检测最新会话
2. 手动指定 JSONL 文件路径
3. 将终端输出复制到文本文件（如 `docs/eval/01.txt`）

### Q: 评估工具支持哪些输入格式？

A: 目前支持：
- **JSONL 格式**（推荐）：Claude Code 原生历史格式，包含完整的工具调用信息
- 纯文本执行历史（.txt）：从终端输出复制的文本
- Git 提交范围（hash..hash）：评估指定范围的提交
- 输出目录（dir/）：静态分析输出文件

## 参考

- [Skill 开发指南](../../README.md)
- [测试工作流文档](../../docs/)
- [skill-creator](../.claude/skills/skill-creator/)
