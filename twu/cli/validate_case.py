#!/usr/bin/env python3
"""
用例文件综合检验工具

检验内容：
1. 格式检验：标题格式、必填字段、步骤=结果
2. 重复检测：标题相似度、步骤相似度
3. 分布统计：优先级分布、正向/反向、测试类型
4. 乱码检测：编码问题
5. 含糊词检测：禁用词

自动修复（--fix）：
- 行尾空格
- 多余空行
- 标题格式空格
"""

import re
import sys
from pathlib import Path
from difflib import SequenceMatcher


# ============================================================
# 常量定义
# ============================================================

VALID_TEST_TYPES = {
    '功能', '兼容性', '易用性', '性能', '稳定性', '安全性',
    '可靠性', '效果（AI类、资源类）', '效果（硬件器件类）',
    '可维护性', '可移植性', '埋点',
}

# 含糊词列表（只有单独出现时才算含糊）
VAGUE_PATTERNS = [
    # 格式：(正则模式, 描述)
    # 匹配 "1. 成功" 或 "。成功。" 这种单独出现的情况
    (r'\d+\.\s*成功\s*$', '成功'),
    (r'\d+\.\s*失败\s*$', '失败'),
    (r'\d+\.\s*正常\s*$', '正常'),
    (r'\d+\.\s*异常\s*$', '异常'),
    (r'\d+\.\s*正确\s*$', '正确'),
    (r'\d+\.\s*错误\s*$', '错误'),
    (r'\d+\.\s*通过\s*$', '通过'),
    (r'\d+\.\s*有效\s*$', '有效'),
    (r'\d+\.\s*无效\s*$', '无效'),
    # 匹配句末单独出现
    (r'。\s*成功\s*$', '成功'),
    (r'。\s*失败\s*$', '失败'),
    (r'。\s*正常\s*$', '正常'),
    (r'。\s*通过\s*$', '通过'),
]

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

def count_steps(text: str) -> int:
    """计算步骤/结果数量"""
    matches = re.findall(r'(\d+)\.\s', text)
    return len(matches) if matches else 0


def similarity(a: str, b: str) -> float:
    """计算字符串相似度"""
    return SequenceMatcher(None, a, b).ratio()


def has_garbled(text: str) -> bool:
    """检测是否有乱码"""
    for pattern in GARBLED_PATTERNS:
        if re.search(pattern, text):
            return True
    return False


def find_garbled_positions(content: str, lines: list[str]) -> list[tuple[int, str]]:
    """找出乱码位置"""
    results = []
    for i, line in enumerate(lines):
        if has_garbled(line):
            # 截取片段
            snippet = line[:50] + '...' if len(line) > 50 else line
            results.append((i + 1, snippet))
    return results


def find_vague_words(content: str, lines: list[str]) -> list[tuple[int, str, str]]:
    """找出含糊词位置（只检测单独使用的含糊词）"""
    results = []
    for i, line in enumerate(lines):
        # 只检查预期结果行
        if line.startswith('[预期结果]'):
            for pattern, word in VAGUE_PATTERNS:
                if re.search(pattern, line):
                    snippet = line[:60] + '...' if len(line) > 60 else line
                    results.append((i + 1, word, snippet))
                    break  # 每行只报告一次
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

    # 3. 标题格式空格 ##[P1] → ## [P1]
    title_fixes = 0
    def fix_title(m):
        nonlocal title_fixes
        title_fixes += 1
        return f"## [{m.group(1)}]"
    content = re.sub(r'##\[([Pp][1-5])\]', fix_title, content)
    if title_fixes > 0:
        fixes.append(f"修复标题格式 ({title_fixes}处)")

    return content, fixes


# ============================================================
# 格式检验
# ============================================================

def validate_format(file_path: Path, lines: list[str]) -> list[str]:
    """格式检验"""
    errors = []
    rel_path = file_path.name

    i = 0
    while i < len(lines):
        line = lines[i]
        line_num = i + 1

        # 检查用例标题
        case_match = re.match(r'^## \[P([1-5])\](\[反向\])?\s*(.+)$', line)
        if case_match:
            title = case_match.group(3).strip()

            # 检查标题是否以"验证"开头
            if not title.startswith('验证'):
                errors.append(f"{rel_path}:{line_num} 用例标题应以「验证」开头: 「{title}」")

            # 检查后续字段
            has_type = False
            has_steps = False
            has_results = False
            steps_count = 0
            results_count = 0

            j = i + 1
            while j < len(lines):
                field_line = lines[j]

                if field_line.startswith('[测试类型]'):
                    has_type = True
                    test_type = field_line.replace('[测试类型]', '').strip()
                    if test_type and test_type not in VALID_TEST_TYPES:
                        errors.append(f"{rel_path}:{j+1} 测试类型无效: 「{test_type}」")
                elif field_line.startswith('[测试步骤]'):
                    has_steps = True
                    steps_content = field_line.replace('[测试步骤]', '').strip()
                    steps_count = count_steps(steps_content)
                    if steps_count == 0:
                        errors.append(f"{rel_path}:{j+1} 测试步骤格式错误，应使用「1. 步骤1。2. 步骤2」")
                elif field_line.startswith('[预期结果]'):
                    has_results = True
                    results_content = field_line.replace('[预期结果]', '').strip()
                    results_count = count_steps(results_content)
                    if results_count == 0:
                        errors.append(f"{rel_path}:{j+1} 预期结果格式错误，应使用「1. 结果1。2. 结果2」")
                elif field_line.startswith('## ') or field_line.startswith('# '):
                    break
                j += 1

            if not has_type:
                errors.append(f"{rel_path}:{line_num} 用例缺少 [测试类型]: 「{title}」")
            if not has_steps:
                errors.append(f"{rel_path}:{line_num} 用例缺少 [测试步骤]: 「{title}」")
            if not has_results:
                errors.append(f"{rel_path}:{line_num} 用例缺少 [预期结果]: 「{title}」")

            if has_steps and has_results and steps_count != results_count:
                errors.append(f"{rel_path}:{line_num} 步骤数({steps_count})与结果数({results_count})不一致: 「{title}」")

            i = j
            continue

        i += 1

    return errors


# ============================================================
# 重复检测
# ============================================================

def detect_duplicates(cases: list[dict], threshold: float = 0.8) -> list[dict]:
    """
    检测相似用例

    Args:
        cases: [{'file': str, 'line': int, 'title': str, 'steps': str}]
        threshold: 相似度阈值

    Returns:
        [{'similarity': float, 'case1': dict, 'case2': dict}]
    """
    duplicates = []

    for i in range(len(cases)):
        for j in range(i + 1, len(cases)):
            c1, c2 = cases[i], cases[j]

            # 计算综合相似度：标题 40% + 步骤 40% + 结果 20%
            title_sim = similarity(c1.get('title', ''), c2.get('title', ''))
            steps_sim = similarity(c1.get('steps', ''), c2.get('steps', ''))
            results_sim = similarity(c1.get('results', ''), c2.get('results', ''))

            total_sim = title_sim * 0.4 + steps_sim * 0.4 + results_sim * 0.2

            if total_sim >= threshold:
                duplicates.append({
                    'similarity': total_sim,
                    'case1': c1,
                    'case2': c2,
                })

    return sorted(duplicates, key=lambda x: -x['similarity'])


# ============================================================
# 提取用例信息
# ============================================================

def extract_cases(file_path: Path, lines: list[str]) -> list[dict]:
    """从文件中提取用例信息"""
    cases = []
    rel_path = str(file_path)

    i = 0
    while i < len(lines):
        line = lines[i]
        case_match = re.match(r'^## \[P([1-5])\](\[反向\])?\s*(.+)$', line)

        if case_match:
            priority = int(case_match.group(1))
            is_reverse = case_match.group(2) is not None
            title = case_match.group(3).strip()

            case_info = {
                'file': rel_path,
                'line': i + 1,
                'priority': priority,
                'is_reverse': is_reverse,
                'title': title,
                'steps': '',
                'results': '',
                'test_type': '',
            }

            # 提取字段内容
            j = i + 1
            while j < len(lines):
                field_line = lines[j]
                if field_line.startswith('[测试类型]'):
                    case_info['test_type'] = field_line.replace('[测试类型]', '').strip()
                elif field_line.startswith('[测试步骤]'):
                    case_info['steps'] = field_line.replace('[测试步骤]', '').strip()
                elif field_line.startswith('[预期结果]'):
                    case_info['results'] = field_line.replace('[预期结果]', '').strip()
                elif field_line.startswith('## ') or field_line.startswith('# '):
                    break
                j += 1

            cases.append(case_info)
            i = j
            continue

        i += 1

    return cases


# ============================================================
# 分布统计
# ============================================================

def calc_statistics(all_cases: list[dict]) -> dict:
    """计算分布统计"""
    stats = {
        'total': len(all_cases),
        'priority': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
        'direction': {'positive': 0, 'reverse': 0},
        'test_type': {},
    }

    for case in all_cases:
        # 优先级
        p = case.get('priority', 0)
        if p in stats['priority']:
            stats['priority'][p] += 1

        # 正向/反向
        if case.get('is_reverse'):
            stats['direction']['reverse'] += 1
        else:
            stats['direction']['positive'] += 1

        # 测试类型
        tt = case.get('test_type', '未知')
        if tt:
            stats['test_type'][tt] = stats['test_type'].get(tt, 0) + 1

    return stats


# ============================================================
# 主检验流程
# ============================================================

def validate_directory(dir_path: Path, do_fix: bool = False) -> dict:
    """
    检验目录下所有用例文件

    Returns:
        {
            'files': int,
            'format_errors': [...],
            'duplicates': [...],
            'statistics': {...},
            'garbled': [...],
            'vague': [...],
            'fixes': {...},
        }
    """
    result = {
        'files': 0,
        'format_errors': [],
        'duplicates': [],
        'statistics': {},
        'garbled': [],
        'vague': [],
        'fixes': {},
    }

    if not dir_path.exists():
        result['format_errors'].append(f"目录不存在: {dir_path}")
        return result

    all_cases = []

    # 遍历所有 .md 文件（排除 plan.md）
    for md_file in sorted(dir_path.rglob('*.md')):
        if md_file.name == 'plan.md':
            continue

        result['files'] += 1
        rel_path = md_file.relative_to(dir_path)

        content = md_file.read_text(encoding='utf-8')
        lines = content.split('\n')

        # 自动修复
        if do_fix:
            new_content, fixes = auto_fix(content)
            if fixes:
                md_file.write_text(new_content, encoding='utf-8')
                result['fixes'][str(rel_path)] = fixes
                # 重新读取修复后的内容
                content = new_content
                lines = content.split('\n')

        # 格式检验
        errors = validate_format(rel_path, lines)
        result['format_errors'].extend(errors)

        # 提取用例
        cases = extract_cases(rel_path, lines)
        all_cases.extend(cases)

        # 乱码检测
        garbled = find_garbled_positions(content, lines)
        for line_num, snippet in garbled:
            result['garbled'].append({
                'file': str(rel_path),
                'line': line_num,
                'snippet': snippet,
            })

        # 含糊词检测
        vague = find_vague_words(content, lines)
        for line_num, word, context in vague:
            result['vague'].append({
                'file': str(rel_path),
                'line': line_num,
                'word': word,
                'context': context,
            })

    # 重复检测
    result['duplicates'] = detect_duplicates(all_cases)

    # 分布统计
    result['statistics'] = calc_statistics(all_cases)

    return result


# ============================================================
# 输出格式化
# ============================================================

def print_result(result: dict, dir_path: Path):
    """格式化输出检验结果"""
    print(f"检验目录: {dir_path}/")
    print(f"检验文件: {result['files']} 个")
    print()

    # 自动修复
    if result['fixes']:
        print("=" * 50)
        print("[自动修复]")
        print("=" * 50)
        for file_path, fixes in result['fixes'].items():
            for fix in fixes:
                print(f"✓ {file_path}: {fix}")
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

    # 重复检测
    print("=" * 50)
    print("[重复检测]")
    print("=" * 50)
    if result['duplicates']:
        for dup in result['duplicates']:
            sim = dup['similarity']
            c1, c2 = dup['case1'], dup['case2']
            print(f"相似度 {sim:.2f}:")
            print(f"  - {c1['file']}:{c1['line']} 「{c1['title']}」")
            print(f"  - {c2['file']}:{c2['line']} 「{c2['title']}」")
    else:
        print("✓ 无重复")
    print()

    # 分布统计
    print("=" * 50)
    print("[分布统计]")
    print("=" * 50)
    stats = result['statistics']
    if stats.get('total', 0) > 0:
        # 优先级
        p = stats['priority']
        print(f"优先级: P1={p[1]} P2={p[2]} P3={p[3]} P4={p[4]} P5={p[5]} (共{stats['total']})")

        # 正向/反向
        d = stats['direction']
        print(f"类型: 正向={d['positive']} 反向={d['reverse']}")

        # 测试类型
        tt = stats['test_type']
        if tt:
            tt_str = ' '.join([f"{k}={v}" for k, v in sorted(tt.items(), key=lambda x: -x[1])])
            print(f"测试类型: {tt_str}")
    else:
        print("无用例")
    print()

    # 乱码检测
    print("=" * 50)
    print("[乱码检测]")
    print("=" * 50)
    if result['garbled']:
        for g in result['garbled']:
            print(f"✗ {g['file']}:{g['line']} 发现乱码，建议重新生成")
            print(f"  片段: {g['snippet']}")
    else:
        print("✓ 无乱码")
    print()

    # 含糊词检测
    print("=" * 50)
    print("[含糊词检测]")
    print("=" * 50)
    if result['vague']:
        for v in result['vague']:
            print(f"⚠ {v['file']}:{v['line']} 含糊词「{v['word']}」")
    else:
        print("✓ 无含糊词")
    print()

    # 引导语
    print("=" * 50)
    print("[下一步]")
    print("=" * 50)
    has_issues = result['format_errors'] or result['garbled'] or result['duplicates'] or result['vague']

    if has_issues:
        print("请根据以上检测结果判断和修复：")
        if result['format_errors']:
            print("- 格式错误：必须修复")
        if result['garbled']:
            print("- 乱码：重新生成对应用例")
        if result['duplicates']:
            print("- 重复检测：判断是否需要合并或删除")
        if result['vague']:
            print("- 含糊词：判断是否需要具体化预期结果")
        print()
        print("分布统计供参考，判断是否合理")
    else:
        print("检验通过，请进行 Agent 自检：")
        print("- 用例从测试关注点展开，不是简单复述？")
        print("- 测试数据具体（非占位符）？")
        print("- 分布是否合理？")
    print()


# ============================================================
# CLI 入口
# ============================================================

def main():
    """CLI 入口"""
    default_path = Path('tc')

    args = [a for a in sys.argv[1:] if a not in ['-h', '--help']]

    if '-h' in sys.argv or '--help' in sys.argv:
        print("用法: twu validate case [path]")
        print()
        print("检验用例文件（自动修复简单格式问题）")
        print()
        print("参数:")
        print("  path    用例目录（默认: tc/）")
        print()
        print("检验内容:")
        print("  - 格式检验：标题格式、必填字段、步骤=结果")
        print("  - 重复检测：标题相似度、步骤相似度")
        print("  - 分布统计：优先级、正向/反向、测试类型")
        print("  - 乱码检测：编码问题")
        print("  - 含糊词检测：禁用词")
        print()
        print("自动修复:")
        print("  - 行尾空格")
        print("  - 多余空行")
        print("  - 标题格式空格")
        sys.exit(0)

    target = Path(args[0]) if args else default_path

    result = validate_directory(target, do_fix=True)
    print_result(result, target)

    # 返回码：有格式错误或乱码时返回 1
    has_errors = bool(result['format_errors']) or bool(result['garbled'])
    sys.exit(1 if has_errors else 0)


if __name__ == '__main__':
    main()
