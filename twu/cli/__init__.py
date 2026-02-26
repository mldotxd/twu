# TWU CLI 工具

import sys


def main():
    """TWU CLI 入口"""
    if len(sys.argv) < 2:
        print("TWU - 测试工作流工具")
        print()
        print("用法: twu <command> [options]")
        print()
        print("命令:")
        print("  init <name>             初始化需求目录结构")
        print("  parse <path>            解析原始文档（PDF/Word/Markdown）")
        print("  case-batch <xml-file>   批量操作用例（替换/删除）")
        print("  validate plan [file]    检验 plan.md 格式")
        print("  validate case [path]    检验用例文件格式")
        print("  export <dir> [options]  导出用例为 Excel")
        print()
        print("示例:")
        print("  twu init 需求1")
        print("  twu parse 需求1")
        print("  twu case-batch operations.xml")
        print("  twu validate plan")
        print("  twu validate case")
        print("  twu export 需求1/tc -o output.xlsx")
        sys.exit(0)

    command = sys.argv[1]

    if command == 'init':
        from twu.cli.init_req import main as init_main
        sys.argv = sys.argv[1:]  # 移除 'twu'
        init_main()
    elif command == 'parse':
        from twu.cli.parse_doc import main as parse_main
        sys.argv = sys.argv[1:]  # 移除 'twu'
        parse_main()
    elif command == 'case-batch':
        from twu.cli.case_batch import main as case_batch_main
        sys.argv = sys.argv[1:]
        case_batch_main()
    elif command == 'validate':
        if len(sys.argv) < 3:
            print("用法: twu validate <plan|case> [path]")
            print()
            print("子命令:")
            print("  plan    检验 plan.md 格式")
            print("  case    检验用例文件格式")
            sys.exit(1)

        sub_command = sys.argv[2]
        sys.argv = sys.argv[2:]  # 移除 'twu validate'

        if sub_command == 'plan':
            from twu.cli.validate_plan import main as validate_plan_main
            validate_plan_main()
        elif sub_command == 'case':
            from twu.cli.validate_case import main as validate_case_main
            validate_case_main()
        else:
            print(f"未知子命令: {sub_command}")
            print("可用子命令: plan, case")
            sys.exit(1)
    elif command == 'export':
        from twu.cli.export_excel import main as export_main
        sys.argv = sys.argv[1:]  # 移除 'twu'
        export_main()
    else:
        print(f"未知命令: {command}")
        print("运行 'twu' 查看可用命令")
        sys.exit(1)
