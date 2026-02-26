#!/usr/bin/env python3
"""
plan.md 综合检验工具

检验内容：
1. 格式检验：Module ##、Scenario ###、必填字段
2. 重复检测：Scenario 名称重复
3. 乱码检测：编码问题
4. 枚举检验：风险等级

自动修复（--fix）：
- 行尾空格
- 多余空行
"""

import re
import sys
from pathlib import Path


# ============================================================
# 常量定义
# ============================================================

VALID_RISK_LEVELS = {'Critical', 'High', 'Medium', 'Low'}

# 乱码特征
GARBLED_PATTERNS = [
    r'\ufffd',           # Unicode 替换字符
    r'[\x00-\x08]',      # 控制字符
    r'锟斤拷',           # GBK 乱码特征
    r'烫烫烫',           # VC 调试特征
    r'屯屯屯',           # VC 调试特征
]


# ============================================================
# 工具函数
# ============================================================

def has_garbled(text: str) -> bool:
    """检测是否有乱码"""
    for pattern in GARBLED_PATTERNS:
        if re.search(pattern, text):
            return True
    return False


def find_garbled_positions(lines: list[str]) -> list[tuple[int, str]]:
    """找出乱码位置"""
    results = []
    for i, line in enumerate(lines):
        if has_garbled(line):
            snippet = line[:50] + '...' if len(line) > 50 else line
            results.append((i + 1, snippet))
    return results


# ============================================================
# 自动修复
# ============================================================

def auto_fix(content: str) -> tuple[str, list[str]]:
    """
    自动修复简单格式问题

    Returns:
        (修复后内容, 修复记录列表)
    """
    fixes = []

    # 1. 行尾空格
    lines = content.split('\n')
    trailing_count = 0
    for i, line in enumerate(lines):
        stripped = line.rstrip()
        if len(stripped) < len(line):
            trailing_count += 1
            lines[i] = stripped
    if trailing_count > 0:
        fixes.append(f"清理行尾空格 ({trailing_count}处)")

    content = '\n'.join(lines)

    # 2. 多余空行（3个以上合并为2个）
    original_len = len(content)
    content = re.sub(r'\n{3,}', '\n\n', content)
    if len(content) < original_len:
        fixes.append("合并多余空行")

    return content, fixes


# ============================================================
# 格式检验
# ============================================================

def validate_format(file_path: Path, lines: list[str]) -> tuple[list[str], dict]:
    """
    格式检验

    Returns:
        (错误列表, 统计信息)
    """
    errors = []
    stats = {
        'modules': 0,
        'scenarios': 0,
        'risk_levels': {'Critical': 0, 'High': 0, 'Medium': 0, 'Low': 0},
    }

    current_module = None
    scenarios = []
    scenario_line_map = {}

    i = 0
    while i < len(lines):
        line = lines[i]
        line_num = i + 1

        # 检查 Module（## 开头）
        if line.startswith('## ') and not line.startswith('### '):
            current_module = line[3:].strip()
            stats['modules'] += 1
            i += 1
            continue

        # 检查 Scenario（### 开头）
        if line.startswith('### '):
            scenario_name = line[4:].strip()
            clean_name = re.sub(r'\[待确认\]\s*', '', scenario_name)

            stats['scenarios'] += 1

            # 检查重复
            if clean_name in scenarios:
                errors.append(f"行 {line_num}: Scenario 重复「{clean_name}」（首次在行 {scenario_line_map[clean_name]}）")
            else:
                scenarios.append(clean_name)
                scenario_line_map[clean_name] = line_num

            # 检查是否在 Module 下
            if current_module is None:
                errors.append(f"行 {line_num}: Scenario「{scenario_name}」不在任何 Module 下")

            # 检查后续元数据
            has_risk = False
            has_focus = False
            j = i + 1

            while j < len(lines):
                meta_line = lines[j]
                if meta_line.startswith('> 风险等级:'):
                    has_risk = True
                    risk_match = re.search(r'风险等级:\s*(\S+)', meta_line)
                    if risk_match:
                        risk_level = risk_match.group(1)
                        if risk_level not in VALID_RISK_LEVELS:
                            errors.append(f"行 {j+1}: 风险等级无效「{risk_level}」，应为 Critical/High/Medium/Low")
                        else:
                            stats['risk_levels'][risk_level] += 1
                elif meta_line.startswith('> 测试关注点:'):
                    has_focus = True
                    focus_content = meta_line.replace('> 测试关注点:', '').strip()
                    if not focus_content:
                        errors.append(f"行 {j+1}: Scenario「{scenario_name}」测试关注点为空")
                elif meta_line.startswith('>'):
                    pass
                else:
                    break
                j += 1

            if not has_risk:
                errors.append(f"行 {line_num}: Scenario「{scenario_name}」缺少风险等级")
            if not has_focus:
                errors.append(f"行 {line_num}: Scenario「{scenario_name}」缺少测试关注点")

            i = j
            continue

        i += 1

    if stats['scenarios'] == 0:
        errors.append("plan.md 中没有找到任何 Scenario")

    return errors, stats


# ============================================================
# 主检验流程
# ============================================================

def validate_plan(file_path: Path, do_fix: bool = False) -> dict:
    """
    检验 plan.md

    Returns:
        {
            'format_errors': [...],
            'garbled': [...],
            'statistics': {...},
            'fixes': [...],
        }
    """
    result = {
        'format_errors': [],
        'garbled': [],
        'statistics': {},
        'fixes': [],
    }

    if not file_path.exists():
        result['format_errors'].append(f"文件不存在: {file_path}")
        return result

    content = file_path.read_text(encoding='utf-8')
    lines = content.split('\n')

    # 自动修复
    if do_fix:
        new_content, fixes = auto_fix(content)
        if fixes:
            file_path.write_text(new_content, encoding='utf-8')
            result['fixes'] = fixes
            content = new_content
            lines = content.split('\n')

    # 格式检验
    errors, stats = validate_format(file_path, lines)
    result['format_errors'] = errors
    result['statistics'] = stats

    # 乱码检测
    garbled = find_garbled_positions(lines)
    for line_num, snippet in garbled:
        result['garbled'].append({
            'line': line_num,
            'snippet': snippet,
        })

    return result


# ============================================================
# 输出格式化
# ============================================================

def print_result(result: dict, file_path: Path):
    """格式化输出检验结果"""
    print(f"检验文件: {file_path}")
    print()

    # 自动修复
    if result['fixes']:
        print("=" * 50)
        print("[自动修复]")
        print("=" * 50)
        for fix in result['fixes']:
            print(f"✓ {fix}")
        print()

    # 格式检验
    print("=" * 50)
    print("[格式检验]")
    print("=" * 50)
    if result['format_errors']:
        for error in result['format_errors']:
            print(f"✗ {error}")
    else:
        print("✓ 通过")
    print()

    # 分布统计
    print("=" * 50)
    print("[分布统计]")
    print("=" * 50)
    stats = result['statistics']
    if stats:
        print(f"Module: {stats.get('modules', 0)} 个")
        print(f"Scenario: {stats.get('scenarios', 0)} 个")
        risk = stats.get('risk_levels', {})
        print(f"风险等级: Critical={risk.get('Critical', 0)} High={risk.get('High', 0)} Medium={risk.get('Medium', 0)} Low={risk.get('Low', 0)}")
    print()

    # 乱码检测
    print("=" * 50)
    print("[乱码检测]")
    print("=" * 50)
    if result['garbled']:
        for g in result['garbled']:
            print(f"✗ 行 {g['line']}: 发现乱码，建议重新生成")
            print(f"  片段: {g['snippet']}")
    else:
        print("✓ 无乱码")
    print()

    # 引导语
    print("=" * 50)
    print("[下一步]")
    print("=" * 50)
    if result['format_errors'] or result['garbled']:
        print("请根据以上检测结果进行修复：")
        if result['format_errors']:
            print("- 格式错误：必须修复")
        if result['garbled']:
            print("- 乱码：重新生成对应内容")
    else:
        print("检验通过，请进行 Agent 自检：")
        print("- Scenario 是独立操作路径，不是数据差异？")
        print("- 测试关注点具体（有数值、有条件）？")
        print("- 分布是否合理？")
    print()


# ============================================================
# CLI 入口
# ============================================================

def main():
    """CLI 入口"""
    default_path = Path('tc/plan.md')

    args = [a for a in sys.argv[1:] if a not in ['-h', '--help']]

    if '-h' in sys.argv or '--help' in sys.argv:
        print("用法: twu validate plan [file]")
        print()
        print("检验 plan.md（自动修复简单格式问题）")
        print()
        print("参数:")
        print("  file    plan.md 文件路径（默认: tc/plan.md）")
        print()
        print("检验内容:")
        print("  - 格式检验：Module ##、Scenario ###、必填字段")
        print("  - 重复检测：Scenario 名称重复")
        print("  - 乱码检测：编码问题")
        print("  - 枚举检验：风险等级")
        print()
        print("自动修复:")
        print("  - 行尾空格")
        print("  - 多余空行")
        sys.exit(0)

    file_path = Path(args[0]) if args else default_path

    result = validate_plan(file_path, do_fix=True)
    print_result(result, file_path)

    # 返回码
    has_errors = bool(result['format_errors']) or bool(result['garbled'])
    sys.exit(1 if has_errors else 0)


if __name__ == '__main__':
    main()
