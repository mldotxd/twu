#!/usr/bin/env python3
"""
用例批量操作工具

解析 XML 格式的操作文件，批量替换或删除用例。
"""

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def normalize_title(title: str) -> str:
    """标准化用例标题：去掉优先级和反向标记"""
    return re.sub(r'^\[P[1-5]\](\[反向\])?\s*', '', title.strip())


def find_case_pattern(title: str) -> str:
    """生成用例匹配的正则表达式"""
    normalized = normalize_title(title)
    # 匹配 ## [P1-5][可选反向] 标题，到下一个 ## 或文件结尾
    return rf'(## \[P[1-5]\](?:\[反向\])?\s*{re.escape(normalized)}.*?)(?=\n## |\Z)'


def replace_case(file_path: Path, title: str, new_content: str) -> tuple[bool, str]:
    """
    替换用例

    Returns:
        (success, message)
    """
    if not file_path.exists():
        return False, f"文件不存在: {file_path}"

    content = file_path.read_text(encoding='utf-8')
    pattern = find_case_pattern(title)

    # 检查用例是否存在
    if not re.search(pattern, content, flags=re.DOTALL):
        return False, f"用例不存在: {title}"

    # 替换
    new_content = new_content.strip()
    if not new_content.endswith('\n'):
        new_content += '\n'

    new_file_content = re.sub(pattern, new_content, content, flags=re.DOTALL)
    file_path.write_text(new_file_content, encoding='utf-8')

    return True, "替换成功"


def delete_case(file_path: Path, title: str) -> tuple[bool, str]:
    """
    删除用例

    Returns:
        (success, message)
    """
    if not file_path.exists():
        return False, f"文件不存在: {file_path}"

    content = file_path.read_text(encoding='utf-8')
    pattern = find_case_pattern(title)

    # 检查用例是否存在
    if not re.search(pattern, content, flags=re.DOTALL):
        return False, f"用例不存在: {title}"

    # 删除
    new_content = re.sub(pattern, '', content, flags=re.DOTALL)
    # 清理多余空行
    new_content = re.sub(r'\n{3,}', '\n\n', new_content)
    file_path.write_text(new_content.strip() + '\n', encoding='utf-8')

    return True, "删除成功"


def process_operations(xml_path: Path, base_dir: Path | None = None) -> tuple[int, int]:
    """
    处理 XML 操作文件

    Args:
        xml_path: XML 文件路径
        base_dir: 基础目录（用例文件的相对路径基于此目录）

    Returns:
        (success_count, total_count)
    """
    if base_dir is None:
        base_dir = Path.cwd()

    tree = ET.parse(xml_path)
    root = tree.getroot()

    cases = root.findall('case')
    total = len(cases)
    success = 0

    for i, case in enumerate(cases, 1):
        action = case.get('action')
        file_path = base_dir / case.get('file')
        title = case.get('title')
        content = case.text or ''

        # 显示进度
        short_file = '/'.join(file_path.parts[-2:]) if len(file_path.parts) >= 2 else str(file_path)
        prefix = f"[{i}/{total}] {action}: {short_file} :: {normalize_title(title)}"

        if action == 'replace':
            ok, msg = replace_case(file_path, title, content)
        elif action == 'delete':
            ok, msg = delete_case(file_path, title)
        else:
            ok, msg = False, f"未知操作: {action}"

        if ok:
            print(f"{prefix} ✓")
            success += 1
        else:
            print(f"{prefix} ✗")
            print(f"      错误: {msg}")

    return success, total


def main():
    """CLI 入口"""
    if len(sys.argv) < 2:
        print("用法: twu case-batch <xml-file> [--base-dir <dir>]")
        print()
        print("示例:")
        print("  twu case-batch operations.xml")
        print("  twu case-batch operations.xml --base-dir /path/to/project")
        sys.exit(1)

    xml_path = Path(sys.argv[1])

    # 解析 --base-dir 参数
    base_dir = None
    if '--base-dir' in sys.argv:
        idx = sys.argv.index('--base-dir')
        if idx + 1 < len(sys.argv):
            base_dir = Path(sys.argv[idx + 1])

    if not xml_path.exists():
        print(f"错误: 文件不存在 {xml_path}")
        sys.exit(1)

    try:
        success, total = process_operations(xml_path, base_dir)
        print()
        print(f"完成: {success}/{total}")
        sys.exit(0 if success == total else 1)
    except ET.ParseError as e:
        print(f"错误: XML 解析失败 - {e}")
        sys.exit(1)
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
