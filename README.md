# TWU - 测试工作流工具

> Test Workflow Utility —— 基于上下文工程的人机协作测试流程

TWU 解决的核心问题：**需求不完备导致测试用例质量低**。通过 4 个阶段逐步建立共识，每个阶段都有人工确认节点，最终生成高质量的测试用例。

```
原始文档 → 需求解析 → 需求审核 → 测试规划 → 测试用例
            /req-parse  /req-review  /tc-plan    /tc-gen
```

---

## 安装

### 1. 安装 uv

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# 验证安装
uv --version
```

> uv 是高性能 Python 包管理器，比 pip 快 10-100x，本项目强制使用 uv 管理依赖。

### 2. 克隆仓库

```bash
git clone <repo-url>
cd twu
```

### 3. 安装依赖

```bash
uv pip install -e .
```

### 4. 验证安装

```bash
uv run twu
```

输出应显示：

```
TWU - 测试工作流工具

用法: twu <command> [options]

命令:
  init <name>             初始化需求目录结构
  parse <path>            解析原始文档（PDF/Word/Markdown）
  case-batch <xml-file>   批量操作用例（替换/删除）
  validate plan [file]    检验 plan.md 格式
  validate case [path]    检验用例文件格式
  export <dir> [options]  导出用例为 Excel
```

---

## 前置配置

### 编写项目业务背景（必填）

在项目根目录编写 `CLAUDE.md`，AI 执行时自动读取。

```bash
vi CLAUDE.md
```

**CLAUDE.md 建议包含**：

```markdown
# 项目名称

## 产品简介
简要描述产品是什么、面向哪些用户、核心价值。

## 关键术语
| 术语 | 说明 |
|------|------|
| 订单 | 用户下单后创建的交易记录 |
| ...  | ... |

## 测试规范
- 重点测试：...
- 接口覆盖：...
```

> 业务背景越详细，AI 生成的用例越贴合实际。参考 [CLAUDE.md](CLAUDE.md) 了解完整示例。

---

## 快速开始

以 `feature-login/` 为例，完整走一遍流程：

```bash
# 1. 初始化需求目录
uv run twu init feature-login

# 2. 放入原始文档
cp prd.pdf feature-login/raw/

# 3. 在 Claude Code 中执行（按顺序）
/req-parse    # 解析原始文档 → req/index.md
/req-review   # 审核需求问题 → req/issues.md
/tc-plan      # 生成测试规划 → tc/plan.md
/tc-gen       # 生成测试用例 → tc/{Module}/{Scenario}.md

# 4. 导出 Excel
uv run twu export feature-login/tc -o feature-login.xlsx
```

---

## CLI 命令详解

### `twu init` — 初始化需求目录

```bash
uv run twu init <name>
```

创建标准目录结构：

```
<name>/
├── raw/           # 放置原始文档（PDF/Word/图片/Markdown）
├── req/
│   ├── chunks/    # 解析后的文档片段（AI 使用）
│   └── assets/    # 图片资源（AI 使用）
└── tc/            # 测试用例输出目录
```

**示例：**

```bash
uv run twu init 用户登录
uv run twu init ./projects/需求v2 --force   # 已存在时强制覆盖
```

---

### `twu parse` — 解析原始文档

```bash
uv run twu parse <需求目录>
```

将 `raw/` 下的文档（PDF/Word/Markdown/图片）解析为结构化片段，输出到 `req/chunks/` 和 `req/assets/`。

> 通常不需要手动调用，`/req-parse` skill 会自动执行。

**示例：**

```bash
uv run twu parse 用户登录
```

---

### `twu validate plan` — 检验测试规划格式

```bash
uv run twu validate plan [file]
```

检验 `tc/plan.md` 的格式，包括：
- Module 使用 `##` 标题
- Scenario 使用 `###` 标题
- 每个 Scenario 包含风险等级（Critical/High/Medium/Low）和测试关注点
- Scenario 名称不重复
- 无乱码

**示例：**

```bash
# 检验当前目录下的 tc/plan.md
uv run twu validate plan

# 检验指定文件
uv run twu validate plan 用户登录/tc/plan.md
```

**输出示例：**

```
[格式检验]
✓ 通过

[分布统计]
Module: 3 个
Scenario: 12 个
风险等级: Critical=3 High=5 Medium=3 Low=1

[乱码检测]
✓ 无乱码

[下一步]
检验通过，请进行 Agent 自检：
- Scenario 是独立操作路径，不是数据差异？
- 测试关注点具体（有数值、有条件）？
- 分布是否合理？
```

> Scenario 重复会在 `[格式检验]` 中以错误形式报出：`行 N: Scenario 重复「XXX」`

---

### `twu validate case` — 检验用例格式

```bash
uv run twu validate case [path]
```

检验 `tc/` 目录下所有用例文件，包括：
- 标题以「验证」开头，格式为 `## [P1] 验证xxx`
- 每个用例包含必填字段：测试类型、测试步骤、预期结果
- 测试步骤数量 = 预期结果数量
- 测试类型在 12 种枚举内
- 无重复用例（相似度 > 80% 时报警）
- 无含糊词（单独的「成功」「正常」等）
- 无乱码

自动修复：行尾空格、多余空行、标题格式空格（无需 `--fix` 参数，默认修复）。

**示例：**

```bash
# 检验当前目录下的 tc/
uv run twu validate case

# 检验指定目录
uv run twu validate case 用户登录/tc
```

**输出示例：**

```
检验目录: tc/
检验文件: 12 个

[格式检验]
✓ 通过

[重复检测]
相似度 0.85:
  - 资源管理/普通图片.md:12 「验证未下载图片不进入轮播列表」
  - 资源管理/普通视频.md:8  「验证未下载视频不进入轮播列表」

[分布统计]
优先级: P1=8 P2=15 P3=20 P4=18 P5=6 (共67)
类型: 正向=45 反向=22
测试类型: 功能=60 性能=4 稳定性=3

[含糊词检测]
⚠ 登录功能/密码登录.md:23 含糊词「成功」

[下一步]
请根据以上检测结果判断和修复：
- 重复检测：判断是否需要合并或删除
- 含糊词：判断是否需要具体化预期结果
```

---

### `twu case-batch` — 批量修改用例

```bash
uv run twu case-batch <xml-file>
```

通过 XML 批量替换或删除用例，适合审核后大批量修正。

**XML 格式：**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<operations>
  <!-- 替换用例 -->
  <case action="replace" file="tc/登录功能/密码登录.md" title="验证有效密码登录成功">
## [P1] 验证有效密码登录成功
[测试类型] 功能
[前置条件] 已注册用户 test_user，密码 Test1234
[测试步骤] 1. 输入用户名 test_user。2. 输入密码 Test1234。3. 点击登录按钮
[预期结果] 1. 用户名输入框显示 test_user。2. 密码输入框显示掩码。3. 跳转到首页，顶部显示 test_user 的头像
  </case>

  <!-- 删除用例 -->
  <case action="delete" file="tc/登录功能/密码登录.md" title="验证登录页面加载">
  </case>
</operations>
```

**示例：**

```bash
uv run twu case-batch operations.xml
```

> 通常由 `/tc-gen` skill 在审核闭环时自动生成并执行，也可以手动编写。

---

### `twu export` — 导出 Excel

```bash
uv run twu export <tc-dir> [-o output.xlsx]
```

将 `tc/` 目录下的用例文件导出为 Excel，包含以下列：

| 列名 | 说明 |
|------|------|
| 一级分组 | Module 名称 |
| 二级分组 | Scenario 名称 |
| 测试项 | Scenario 名称 |
| 优先级 | P1-P5 |
| 用例标题 | 用例标题（去掉优先级标记） |
| 前置条件 | 测试前的准备 |
| 操作步骤 | 测试步骤 |
| 预期结果 | 预期结果 |
| 是否反向用例 | 是/否 |
| 测试类型 | 功能/性能/... |
| AI生成 | 是 |
| 备注 | 空 |

**示例：**

```bash
# 导出到默认文件名（testcase_YYYYMMDD.xlsx）
uv run twu export 用户登录/tc

# 指定输出路径
uv run twu export 用户登录/tc -o 用户登录_用例_v1.xlsx
```

---

## Skills（Claude Code 指令）

Skills 在 Claude Code 中通过 `/` 前缀触发，执行测试工作流的各个阶段。

> **前提**：需要安装 Claude Code 并在项目根目录打开。

### `/req-parse` — 需求解析

**触发词**：`/req-parse`、`解析需求`、`解析文档`

**作用**：读取 `raw/` 下的原始文档，还原文档本意，输出标准化的 `req/index.md`。

**使用方式**：

```
/req-parse
```

AI 会自动：
1. 调用 `twu parse` 解析文档
2. 阅读所有片段，理解图片/流程图/表格
3. 生成结构化的 `req/index.md`，不确定处标记 `[待确认]`
4. git commit 并引导人工审核

**人工审核**：直接修改 `req/index.md` 或口头告知 AI，AI 通过 `git diff` 理解改动。

---

### `/req-review` — 需求审核

**触发词**：`/req-review`、`审核需求`、`检查需求`

**作用**：从测试视角审核 `req/index.md`，识别缺失、歧义、矛盾等问题，生成 `req/issues.md`。

**使用方式**：

```
/req-review
```

AI 会自动：
1. 用 518 分析法（5W+1H+8C）理解业务全貌
2. 用六维扫描（前因后果、边界定义、异常场景、交互细节、数据状态、性能兼容）识别问题
3. 自检过滤（删除常识问题、装饰性细节、纯技术实现）
4. 生成 `req/issues.md`（含问题描述、需要澄清、影响范围、参考），git commit

**产品填写答案**：在 `req/issues.md` 每个 `[产品回答]` 处填写，完成后在对话中告知 AI：

```
请合并 issues.md 中的答案到 req/index.md
```

AI 会将答案合并到对应段落并 git commit，无需重新运行 `/req-review`。

---

### `/tc-plan` — 测试规划

**触发词**：`/tc-plan`、`生成测试规划`、`测试计划`

**作用**：将 `req/index.md` 转化为 Module / Scenario 两层测试规划，输出 `tc/plan.md`。

**使用方式**：

```
/tc-plan
```

AI 会自动：
1. 识别 Module（业务模块）和 Scenario（独立操作路径）
2. 为每个 Scenario 提取测试关注点（必须包含数值和条件）
3. 运行 `uv run twu validate plan` 检验格式
4. git commit 并引导人工审核

**plan.md 格式示例**：

```markdown
## 用户登录

### 用户名密码登录
> 风险等级: Critical
> 测试关注点: 密码错误次数限制（5次）、密码长度边界（8-20位）、账户锁定后解锁

### 手机验证码登录
> 风险等级: High
> 测试关注点: 验证码过期（60秒）、错误次数限制（3次）、短信发送频率限制（1分钟）
```

---

### `/tc-gen` — 用例生成

**触发词**：`/tc-gen`、`生成测试用例`、`生成用例`

**作用**：根据 `tc/plan.md` 为每个 Scenario 生成具体的测试用例文件。

**使用方式**：

```
/tc-gen
```

AI 会自动：
1. 逐个 Scenario 提取等价类，设计用例
2. 生成 `tc/{Module}/{Scenario}.md`
3. 运行 `uv run twu validate case` 检验格式
4. 预期结果质量自检（避免模糊词汇）
5. git commit 并引导人工审核

**用例文件格式示例**：

```markdown
# 用户名密码登录

> 所属模块: 用户登录
> 风险等级: Critical
> 用例数量: 5

## [P1] 验证有效用户名和密码登录成功
[测试类型] 功能
[前置条件] 已注册用户 test_user，密码 Test1234
[测试步骤] 1. 输入用户名 test_user。2. 输入密码 Test1234。3. 点击登录
[预期结果] 1. 用户名输入框显示 test_user。2. 密码显示掩码。3. 跳转首页，导航栏显示用户头像

## [P3][反向] 验证密码错误第5次后账户锁定
[测试类型] 功能
[前置条件] 已注册用户 test_user，密码 Test1234
[测试步骤] 1. 输入用户名 test_user，连续输入5次错误密码 wrong123，每次点击登录
[预期结果] 1. 第5次登录失败后提示「账户已锁定，请30分钟后重试」，登录按钮置灰
```

---

## 完整工作流

```
1. 初始化
   uv run twu init <需求目录>
   → 放入原始文档到 raw/

2. 需求解析（Claude Code）
   /req-parse
   → AI 生成 req/index.md
   → 人工审核：直接修改或告知 AI
   → AI 理解 git diff，确认闭环

3. 需求审核（Claude Code）
   /req-review
   → AI 生成 req/issues.md（问题清单）
   → 产品填写 [产品回答]
   → 告知 AI 合并 → AI 更新 req/index.md

4. 测试规划（Claude Code）
   /tc-plan
   → AI 生成 tc/plan.md
   → 人工审核：Module/Scenario 划分是否合理
   → AI 读取 git diff，确认闭环

5. 用例生成（Claude Code）
   /tc-gen
   → AI 生成 tc/{Module}/{Scenario}.md
   → 人工审核：用例覆盖是否完整
   → 批量修正（可选）：uv run twu case-batch operations.xml

6. 导出
   uv run twu export <需求目录>/tc -o output.xlsx
```

每个阶段：AI 生成 → `git commit` → 人工审核 → AI 读取 `git diff` → 确认 → 下一阶段

---

## 目录结构

```
{项目根目录}/
├── CLAUDE.md                     # 业务背景（必填，AI 执行时自动读取）
├── .claude/skills/               # Skills（所有需求共享）
│   ├── req-parse/SKILL.md
│   ├── req-review/SKILL.md
│   ├── tc-plan/SKILL.md
│   └── tc-gen/SKILL.md
│
├── {需求目录}/
│   ├── raw/                      # 原始文档
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
└── testcase_YYYYMMDD.xlsx        # 导出产物
```

---

## 常见问题

**Q: Skills 不触发？**

确保在项目根目录（包含 `.claude/skills/`）打开 Claude Code。

**Q: `twu` 命令找不到？**

使用 `uv run twu` 代替直接调用 `twu`，或确认已激活 venv（`source .venv/bin/activate`）。

**Q: PDF 解析失败？**

- 检查 PDF 是否加密（需要密码）
- 扫描版 PDF 解析效果较差，建议提供原始文本版

**Q: validate case 提示步骤和结果数量不一致？**

检查用例中步骤和预期结果的编号，确保 `1. ... 2. ...` 的数量完全一致。

---

## 文档

- [CONCEPTS.md](docs/CONCEPTS.md) — 核心思想：上下文工程与 HITL 设计
- [WORKFLOW.md](docs/WORKFLOW.md) — 四阶段人机协作流程详解
- [ROADMAP.md](docs/ROADMAP.md) — 后续开发规划
