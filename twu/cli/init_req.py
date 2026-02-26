# TWU init 命令 - 初始化需求目录结构

import argparse
import sys
from pathlib import Path


def main():
    """初始化需求目录结构"""
    parser = argparse.ArgumentParser(
        description='初始化需求目录结构',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  twu init 需求1           # 在当前目录创建 需求1/ 目录结构
  twu init ./项目/需求1    # 指定路径创建目录结构

创建的目录结构:
  <name>/
  ├── raw/           # 原始文档（PDF/Word/图片）
  ├── req/           # 需求文档
  │   ├── chunks/    # 解析后的文档片段
  │   └── assets/    # 图片资源
  └── tc/            # 测试用例
'''
    )
    parser.add_argument('name', help='需求目录名称或路径')
    parser.add_argument('--force', '-f', action='store_true',
                        help='强制创建（覆盖已存在的目录）')

    args = parser.parse_args()

    # 解析路径
    req_path = Path(args.name)

    # 检查是否已存在
    if req_path.exists() and not args.force:
        print(f"错误: 目录已存在: {req_path}")
        print("使用 --force 强制创建")
        sys.exit(1)

    # 创建目录结构
    dirs_to_create = [
        req_path / 'raw',
        req_path / 'req' / 'chunks',
        req_path / 'req' / 'assets',
        req_path / 'tc',
    ]

    for dir_path in dirs_to_create:
        dir_path.mkdir(parents=True, exist_ok=True)

    # 输出结果
    print(f"已创建需求目录: {req_path}")
    print()
    print("目录结构:")
    print(f"  {req_path}/")
    print(f"  ├── raw/           # 放置原始文档（PDF/Word/图片）")
    print(f"  ├── req/           # 需求文档")
    print(f"  │   ├── chunks/    # 解析后的文档片段")
    print(f"  │   └── assets/    # 图片资源")
    print(f"  └── tc/            # 测试用例")
    print()
    print("下一步:")
    print(f"  1. 将原始需求文档放入 {req_path}/raw/")
    print(f"  2. 运行 /req-parse {req_path}/raw 解析文档")


if __name__ == '__main__':
    main()
