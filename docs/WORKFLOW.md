# TWU 人机协作工作流

---

## 总流程

```
raw/（原始文档）
    │
    │  /req-parse
    ▼
req/index.md（标准化需求）
    │  ← 人工审核 ①
    │  /req-review
    ▼
req/issues.md（问题清单）
    │  ← 产品填写答案
    │    答案合并回 index.md
    │  ← 人工审核 ②
    │  /tc-plan
    ▼
tc/plan.md（测试规划）
    │  ← 人工审核 ③
    │  /tc-gen
    ▼
tc/{Module}/{Scenario}.md（测试用例）
    │  ← 人工审核 ④
    ▼
（可选）twu export → Excel
```

每个阶段：AI 生成 → `git commit` → 人工审核 → AI 读取 `git diff` → 确认 → 进入下一阶段

---

## 阶段一：需求解析 `/req-parse`

**目标**：将原始文档（PDF/Word/图片/Markdown）转化为标准化的需求文档

| 项目 | 内容 |
|------|------|
| 输入 | `raw/`（任意格式原始文档） |
| 输出 | `req/index.md` |

**执行流程**：

| 步骤 | 执行者 | 动作 |
|------|--------|------|
| 1 | AI | 调用 `twu parse <需求目录>`，Docling 解析文档到 `req/chunks/` 和 `req/assets/` |
| 2 | AI | 阅读 chunks，多模态理解图片（原型图/流程图/表格） |
| 3 | AI | 生成 `req/index.md`，不确定处标记 `[待确认]` |
| 4 | AI | `git commit "req-parse: 解析需求文档"` |
| 5 | 人 | 审核 `req/index.md`，直接修改或口头反馈 |
| 6 | AI | `git diff req/` 理解改动意图，多轮对话修正 |
| 7 | AI | `git commit "req-parse: 更新需求文档"` |

**核心原则**：先读再写，还原文档本意，不是机械转换。所有 `[待确认]` 需用户确认后清空。

---

## 阶段二：需求审核 `/req-review`

**目标**：从测试视角识别需求缺陷，形成完备的需求文档

| 项目 | 内容 |
|------|------|
| 输入 | `req/index.md` |
| 输出 | `req/issues.md` + `req/index.md`（原地更新） |

**双视角分析**：

| 视角 | 方法 | 关注点 |
|------|------|--------|
| 业务视角 | 518 分析法 | 5W（背景场景）+ 1H（功能需求）+ 8C（非功能约束） |
| 测试视角 | 六维扫描 | 前因后果、边界定义、异常场景、交互细节、数据状态、性能兼容 |

**问题优先级**：

| 优先级 | 说明 |
|--------|------|
| 紧急 | 不明确则无法设计测试用例 |
| 高 | 影响核心场景的用例设计 |
| 中 | 影响边界和异常用例 |
| 低 | 体验优化、可选改进 |

**执行流程**：

| 步骤 | 执行者 | 动作 |
|------|--------|------|
| 1 | AI | 双视角扫描需求，自检过滤无效问题 |
| 2 | AI | 生成 `req/issues.md`，`git commit` |
| 3 | 人/产品 | 在 `[产品回答]` 处填写答案 |
| 4 | AI | 将答案合并回 `req/index.md`，`git commit` |
| 5 | AI | 检查是否还有未回答的紧急问题，必要时多轮迭代 |
| 6 | 人 | 确认需求完备，`git commit "req-review: 完成需求评审"` |

**多轮迭代**：合并答案后如发现新问题，继续追加到 issues.md，重复回答→合并流程。

---

## 阶段三：测试规划 `/tc-plan`

**目标**：将需求转化为 Module / Scenario 两层测试规划

| 项目 | 内容 |
|------|------|
| 输入 | `req/index.md` |
| 输出 | `tc/plan.md` |

**分层结构**：

| 层级 | 定义 | 示例 |
|------|------|------|
| Module | 业务模块 | 用户认证、订单管理 |
| Scenario | 独立操作路径（不是数据差异） | 用户名密码登录、手机验证码登录 |

**Scenario 划分原则**（容易出错）：

```
✅ 正确（3 个 Scenario）：
- 用户名密码登录
- 手机验证码登录
- 第三方登录

❌ 错误（这是 1 个 Scenario 的等价类，不是 3 个 Scenario）：
- 密码 <8 位
- 密码 8-20 位
- 密码 >20 位
```

**执行流程**：

| 步骤 | 执行者 | 动作 |
|------|--------|------|
| 1 | AI | 划分 Module 和 Scenario，提取每个 Scenario 的测试关注点 |
| 2 | AI | 生成 `tc/plan.md`，`git commit` |
| 3 | 人 | 审核模块划分和测试关注点是否合理 |
| 4 | AI | 根据反馈调整，`git commit` |

---

## 阶段四：用例生成 `/tc-gen`

**目标**：根据测试规划生成每个 Scenario 的具体测试用例

| 项目 | 内容 |
|------|------|
| 输入 | `tc/plan.md` |
| 输出 | `tc/{Module}/{Scenario}.md` |

**用例格式**：

```markdown
## [P1] 验证有效用户名和密码登录成功
[测试类型] 功能
[前置条件] 已注册用户 test_user，密码 Test1234
[测试步骤] 1. 输入用户名 test_user，输入密码 Test1234，点击登录
[预期结果] 1. 登录成功，跳转到 /home 页面
```

**优先级定义**：

| 优先级 | 定义 |
|--------|------|
| P1 | 核心功能正向流程 |
| P2 | 基本功能正向流程 |
| P3 | 核心功能异常场景 |
| P4 | 边界条件 |
| P5 | 低频场景 |

**执行流程**：

| 步骤 | 执行者 | 动作 |
|------|--------|------|
| 1 | AI | 按 plan.md 的 Scenario，逐个生成用例文件 |
| 2 | AI | 不确定的预期结果标记 `[待确认]` |
| 3 | AI | `git commit` |
| 4 | 人 | 审核用例，确认 `[待确认]` 内容 |
| 5 | AI/人 | 批量修正：生成 XML → `twu case-batch operations.xml` |

---

## 目录结构

```
{项目根目录}/
├── CLAUDE.md                     # 业务背景（必填，AI 执行时读取）
├── .claude/skills/               # Skills（所有需求共享）
│   ├── req-parse/SKILL.md
│   ├── req-review/SKILL.md
│   ├── tc-plan/SKILL.md
│   └── tc-gen/SKILL.md
│
├── {需求目录1}/
│   ├── raw/                      # 原始文档（PDF/Word/图片）
│   ├── req/
│   │   ├── index.md              # 标准化需求文档
│   │   ├── issues.md             # 需求问题清单
│   │   ├── chunks/               # 解析中间产物
│   │   └── assets/               # 图片资源
│   └── tc/
│       ├── plan.md               # 测试规划
│       └── {Module}/
│           └── {Scenario}.md     # 测试用例
│
└── {需求目录2}/
    └── ...
```

---

## 命令速查

| 命令 | 输入 | 输出 |
|------|------|------|
| `/req-parse` | `raw/` | `req/index.md` |
| `/req-review` | `req/index.md` | `req/index.md` + `req/issues.md` |
| `/tc-plan` | `req/index.md` | `tc/plan.md` |
| `/tc-gen` | `tc/plan.md` | `tc/{Module}/{Scenario}.md` |
| `twu parse <dir>` | `raw/` | `req/chunks/` + `req/assets/` |
| `twu export <dir>` | `tc/` | Excel |
| `twu case-batch <xml>` | 操作文件 | 批量修改用例 |

---

## 异常处理

| 场景 | 处理方式 |
|------|----------|
| PDF 加密 | 提示用户提供密码 |
| 文件损坏 | 跳过并记录 |
| Docling 解析失败 | 降级到 PyPDF2 / python-docx |
| 紧急问题未回答 | 阻止进入下一阶段 |
| 图片无法识别 | 标记 `[图片缺失]`，继续执行 |
