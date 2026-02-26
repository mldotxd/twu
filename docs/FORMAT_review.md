# 待确认点审核流程

## 1. 概述

用例生成后，可能存在 `[待确认]` 标记的内容。本文档定义审核流程和工具使用方式。

---

## 2. 流程

```
生成用例（含 [待确认] 标记）
    ↓
提取待确认点 → 生成审核清单
    ↓
用户填写确认结果
    ↓
Agent 生成批量操作文件（XML）
    ↓
执行 twu case-batch 修改原文件
    ↓
完成
```

---

## 3. 审核清单格式

```markdown
# 待确认点审核

## 订单管理 / 创建订单

> 文件：test-case/订单管理/创建订单.md

### [P1] 验证正常创建订单

**完整用例**：
## [P1] 验证正常创建订单
[测试类型] 功能
[前置条件] 用户已登录，商品A库存充足
[测试步骤] 1. 选择商品A，数量1，点击下单
[预期结果] 1. 订单创建成功，[待确认] 库存扣减数量

**待确认点**：库存扣减数量

**确认结果**：
（用户填写）

---
```

---

## 4. 批量操作文件格式（XML）

Agent 根据用户确认结果生成：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<operations>

<case action="replace" file="test-case/订单管理/创建订单.md" title="验证正常创建订单">
## [P1] 验证正常创建订单
[测试类型] 功能
[前置条件] 用户已登录，商品A库存充足
[测试步骤] 1. 选择商品A，数量1，点击下单
[预期结果] 1. 订单创建成功，库存扣减1
</case>

<case action="delete" file="test-case/登录功能/用户名密码登录.md" title="验证重复登录" />

</operations>
```

**标签属性：**

| 属性 | 必填 | 说明 |
|------|------|------|
| action | 是 | `replace` 或 `delete` |
| file | 是 | Scenario 文件路径 |
| title | 是 | 用例标题（可含或不含优先级，工具内部兼容） |

**标签内容：**
- `replace`：完整的新用例内容
- `delete`：空（自闭合标签）

---

## 5. CLI 工具

### 5.1 批量操作

```bash
twu case-batch <xml-file>
```

**示例：**

```bash
twu case-batch operations.xml
```

**输出：**

```
[1/3] replace: 订单管理/创建订单.md :: 验证正常创建订单 ✓
[2/3] replace: 订单管理/创建订单.md :: 验证库存不足下单 ✓
[3/3] delete: 登录功能/用户名密码登录.md :: 验证重复登录 ✓

完成: 3/3
```

### 5.2 单条操作（可选）

```bash
twu case-replace --file <file> --title <title> --content <content>
twu case-replace --file <file> --title <title> --delete
```

---

## 6. 工具匹配逻辑

用例标题匹配时，工具内部兼容处理：

```python
# 输入标题标准化：去掉可能存在的优先级和反向标记
normalized = re.sub(r'^\[P[1-5]\](\[反向\])?\s*', '', title)

# 匹配原文件中的用例
pattern = rf'## \[P[1-5]\](?:\[反向\])?\s*{re.escape(normalized)}'
```

支持输入：
- `验证正常创建订单` ✓
- `[P1] 验证正常创建订单` ✓
- `[P1][反向] 验证用户名为空` ✓
