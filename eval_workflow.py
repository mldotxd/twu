#!/usr/bin/env python3
"""
工作流评估工具

用法：
    uv run python eval_workflow.py <input> [--type history|git|dir]

示例：
    uv run python eval_workflow.py docs/eval/01.txt --type history
    uv run python eval_workflow.py e6a36e5..25f79de --type git
    uv run python eval_workflow.py 相框端-轮播展示/ --type dir
"""

import re
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import subprocess


class WorkflowEvaluator:
    """工作流评估器"""

    def __init__(self, input_source: str, input_type: str = "history"):
        self.input_source = input_source
        self.input_type = input_type
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.eval_dir = Path(f"eval/{self.timestamp}")
        self.eval_dir.mkdir(parents=True, exist_ok=True)

        self.data = {
            "skills": [],
            "tools": [],
            "files": [],
            "commits": [],
            "errors": [],
            "timings": {},
        }

    def evaluate(self) -> Dict[str, Any]:
        """执行评估"""
        print(f"开始评估：{self.input_source} (类型: {self.input_type})")

        if self.input_type == "history":
            self._evaluate_history()
        elif self.input_type == "git":
            self._evaluate_git()
        elif self.input_type == "dir":
            self._evaluate_directory()
        else:
            raise ValueError(f"不支持的输入类型: {self.input_type}")

        # 生成评估报告
        report = self._generate_report()

        # 写入报告
        report_path = self.eval_dir / "report.md"
        report_path.write_text(report, encoding="utf-8")

        print(f"评估完成：{report_path}")
        return self.data

    def _evaluate_history(self):
        """评估执行历史"""
        history_file = Path(self.input_source)
        if not history_file.exists():
            raise FileNotFoundError(f"历史文件不存在: {self.input_source}")

        content = history_file.read_text(encoding="utf-8")

        # 提取 Skill 调用
        skill_pattern = r"❯ /(\S+)"
        skills = re.findall(skill_pattern, content)
        self.data["skills"] = skills

        # 提取工具调用
        tool_pattern = r"⏺ (Read|Write|Edit|Bash)\("
        tools = re.findall(tool_pattern, content)
        self.data["tools"] = tools

        # 提取文件操作
        file_pattern = r"(req/\S+\.md|tc/\S+\.md)"
        files = list(set(re.findall(file_pattern, content)))
        self.data["files"] = files

        # 提取时间信息
        time_pattern = r"✻ \w+ for (\d+)m (\d+)s"
        times = re.findall(time_pattern, content)
        total_seconds = sum(int(m) * 60 + int(s) for m, s in times)
        self.data["timings"]["total"] = total_seconds

        # 提取 Git 提交
        commit_pattern = r"\[main (\w+)\] (.+)"
        commits = re.findall(commit_pattern, content)
        self.data["commits"] = [{"hash": h[:7], "message": m} for h, m in commits]

    def _evaluate_git(self):
        """评估 Git 提交范围"""
        # 获取提交列表
        result = subprocess.run(
            ["git", "log", "--oneline", self.input_source],
            capture_output=True,
            text=True,
        )

        for line in result.stdout.strip().split("\n"):
            if line:
                parts = line.split(" ", 1)
                if len(parts) == 2:
                    self.data["commits"].append({
                        "hash": parts[0],
                        "message": parts[1],
                    })

        # 获取文件变更
        result = subprocess.run(
            ["git", "diff", "--name-only", self.input_source],
            capture_output=True,
            text=True,
        )

        self.data["files"] = result.stdout.strip().split("\n")

    def _evaluate_directory(self):
        """评估输出目录"""
        dir_path = Path(self.input_source)
        if not dir_path.exists():
            raise FileNotFoundError(f"目录不存在: {self.input_source}")

        # 扫描文件
        for pattern in ["req/**/*.md", "tc/**/*.md"]:
            for file in dir_path.glob(pattern):
                self.data["files"].append(str(file.relative_to(dir_path)))

        # 运行验证工具
        for cmd in ["uv run twu validate plan", "uv run twu validate case"]:
            try:
                result = subprocess.run(
                    cmd.split(),
                    capture_output=True,
                    text=True,
                    cwd=dir_path,
                )
                if result.returncode != 0:
                    self.data["errors"].append({
                        "command": cmd,
                        "error": result.stderr,
                    })
            except Exception as e:
                self.data["errors"].append({
                    "command": cmd,
                    "error": str(e),
                })

    def _generate_report(self) -> str:
        """生成评估报告"""
        report = f"""# 工作流评估报告

> 评估时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
> 评估来源：{self.input_source}
> 评估类型：{self.input_type}

## 一、执行概览

"""

        if self.data["skills"]:
            report += f"**Skill 调用：** {len(self.data['skills'])} 次\n\n"
            for i, skill in enumerate(self.data["skills"], 1):
                report += f"{i}. /{skill}\n"
            report += "\n"

        if self.data["tools"]:
            tool_counts = {}
            for tool in self.data["tools"]:
                tool_counts[tool] = tool_counts.get(tool, 0) + 1

            report += "**工具调用统计：**\n\n"
            for tool, count in sorted(tool_counts.items()):
                report += f"- {tool}: {count} 次\n"
            report += "\n"

        if self.data["files"]:
            report += f"**文件操作：** {len(self.data['files'])} 个文件\n\n"
            for file in sorted(self.data["files"]):
                report += f"- {file}\n"
            report += "\n"

        if self.data["commits"]:
            report += f"**Git 提交：** {len(self.data['commits'])} 次\n\n"
            for commit in self.data["commits"]:
                report += f"- `{commit['hash']}` {commit['message']}\n"
            report += "\n"

        if self.data["timings"].get("total"):
            total = self.data["timings"]["total"]
            minutes = total // 60
            seconds = total % 60
            report += f"**总耗时：** {minutes}m {seconds}s\n\n"

        if self.data["errors"]:
            report += "## 二、错误信息\n\n"
            for error in self.data["errors"]:
                report += f"**命令：** `{error['command']}`\n\n"
                report += f"```\n{error['error']}\n```\n\n"

        report += """## 三、评估维度

### 过程评估

- [ ] Skill 调用顺序是否正确
- [ ] 工具使用是否合理
- [ ] 是否有冗余操作
- [ ] 错误处理是否得当

### 结果评估

- [ ] 文档结构是否完整
- [ ] 格式是否正确
- [ ] 内容是否准确
- [ ] Git 提交是否规范

### Trace 分析

- [ ] 工具调用链是否清晰
- [ ] 状态转换是否符合预期
- [ ] 异常处理是否完整

## 四、改进建议

（待人工分析后填写）

### 高优先级

1.

### 中优先级

2.

### 低优先级

3.

## 五、总结

**优点：**

-

**不足：**

-

**总体评价：**

"""

        return report


def main():
    import argparse

    parser = argparse.ArgumentParser(description="工作流评估工具")
    parser.add_argument("input", help="输入来源（文件路径/Git 范围/目录）")
    parser.add_argument(
        "--type",
        choices=["history", "git", "dir"],
        default="history",
        help="输入类型",
    )

    args = parser.parse_args()

    evaluator = WorkflowEvaluator(args.input, args.type)
    evaluator.evaluate()


if __name__ == "__main__":
    main()
