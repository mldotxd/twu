#!/usr/bin/env python3
"""
工作流数据收集工具

收集 TWU 工作流执行的原始数据，供 Claude 进行分析评估。
输出 data.json（结构化数据）和 raw_data.md（可读摘要）。

用法：
    uv run python eval_workflow.py --latest              # 自动检测最新会话
    uv run python eval_workflow.py <file.jsonl>          # 指定 JSONL 文件
    uv run python eval_workflow.py HEAD~5..HEAD --type git
    uv run python eval_workflow.py 相框端-轮播展示/ --type dir
"""

import re
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import subprocess


class WorkflowDataCollector:
    """工作流数据收集器，只收集事实，不做分析判断"""

    def __init__(self, input_source: str, input_type: str = "jsonl"):
        self.input_source = input_source
        self.input_type = input_type
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.eval_dir = Path(f"eval/{self.timestamp}")
        self.eval_dir.mkdir(parents=True, exist_ok=True)

        self.data: Dict[str, Any] = {
            "meta": {
                "source": input_source,
                "type": input_type,
                "collected_at": datetime.now().isoformat(),
            },
            "skills": [],       # Skill 调用序列
            "tools": {},        # 工具调用统计 {name: count}
            "interactions": 0,  # 用户交互次数
            "files": [],        # 操作的文件列表
            "commits": [],      # Git 提交记录
            "errors": [],       # 错误信息
            "duration_seconds": None,
            "validate_results": {},
        }

    def collect(self) -> Dict[str, Any]:
        """收集数据并写入文件"""
        print(f"收集数据：{self.input_source} (类型: {self.input_type})")

        try:
            if self.input_type == "jsonl":
                self._collect_from_jsonl()
            elif self.input_type == "git":
                self._collect_from_git()
            elif self.input_type == "dir":
                self._collect_from_directory()
            else:
                raise ValueError(f"不支持的输入类型: {self.input_type}")
        except Exception as e:
            self.data["errors"].append({"stage": "collect", "error": str(e)})
            print(f"收集出错: {e}")

        # 补充当前目录的 Git 提交（如果还没有）
        if not self.data["commits"]:
            self._collect_recent_commits()

        # 写入文件
        self._write_outputs()
        return self.data

    def _collect_from_jsonl(self):
        """从 Claude Code JSONL 会话文件收集数据"""
        jsonl_file = Path(self.input_source).expanduser()
        if not jsonl_file.exists():
            raise FileNotFoundError(f"文件不存在: {self.input_source}")

        print(f"读取 JSONL: {jsonl_file}")

        messages = []
        with open(jsonl_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    messages.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        print(f"读取 {len(messages)} 条记录")

        tool_counts: Dict[str, int] = {}
        user_texts: List[str] = []
        written_files: List[str] = []

        for msg in messages:
            msg_type = msg.get("type")
            message = msg.get("message", {})
            role = message.get("role", "")
            content = message.get("content", [])

            if not isinstance(content, list):
                continue

            if role == "user":
                self.data["interactions"] += 1
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        user_texts.append(item.get("text", ""))

            elif role == "assistant":
                for item in content:
                    if not isinstance(item, dict):
                        continue
                    if item.get("type") == "tool_use":
                        tool_name = item.get("name", "")
                        tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1

                        # 收集写入的文件路径
                        if tool_name in ("Write", "Edit"):
                            params = item.get("input", {})
                            fp = params.get("file_path", "")
                            if fp:
                                written_files.append(fp)

        self.data["tools"] = tool_counts
        self.data["files"] = list(set(written_files))

        # 从用户消息提取 Skill 调用（/req-parse 等）
        skill_pattern = re.compile(r"/([a-z][a-z0-9-]+)")
        known_skills = {"req-parse", "req-review", "tc-plan", "tc-gen", "workflow-eval"}
        seen_skills: List[str] = []
        for text in user_texts:
            for m in skill_pattern.finditer(text):
                skill = m.group(1)
                if skill in known_skills:
                    seen_skills.append(skill)
        self.data["skills"] = seen_skills

        print(f"Skills: {seen_skills}")
        print(f"工具调用: {tool_counts}")

    def _collect_from_git(self):
        """从 Git 提交范围收集数据"""
        result = subprocess.run(
            ["git", "log", "--oneline", self.input_source],
            capture_output=True, text=True,
        )
        for line in result.stdout.strip().split("\n"):
            if line:
                parts = line.split(" ", 1)
                if len(parts) == 2:
                    self.data["commits"].append({
                        "hash": parts[0],
                        "message": parts[1],
                    })

        result = subprocess.run(
            ["git", "diff", "--name-only", self.input_source],
            capture_output=True, text=True,
        )
        self.data["files"] = [f for f in result.stdout.strip().split("\n") if f]

    def _collect_from_directory(self):
        """从输出目录收集数据（扫描文件 + 运行 validate）"""
        dir_path = Path(self.input_source)
        if not dir_path.exists():
            raise FileNotFoundError(f"目录不存在: {self.input_source}")

        # 扫描输出文件
        files = []
        for pattern in ["req/**/*.md", "tc/**/*.md"]:
            for f in dir_path.glob(pattern):
                files.append(str(f.relative_to(dir_path)))
        self.data["files"] = files

        # 运行验证工具
        for cmd_key, cmd in [
            ("validate_plan", "uv run twu validate plan"),
            ("validate_case", "uv run twu validate case"),
        ]:
            try:
                r = subprocess.run(
                    cmd.split(), capture_output=True, text=True, cwd=dir_path,
                )
                self.data["validate_results"][cmd_key] = {
                    "returncode": r.returncode,
                    "stdout": r.stdout[:2000],
                    "stderr": r.stderr[:500],
                }
            except Exception as e:
                self.data["validate_results"][cmd_key] = {"error": str(e)}

    def _collect_recent_commits(self):
        """补充最近 Git 提交（最多 10 条）"""
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "-10"],
                capture_output=True, text=True, cwd=Path.cwd(),
            )
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split(" ", 1)
                    if len(parts) == 2:
                        self.data["commits"].append({
                            "hash": parts[0],
                            "message": parts[1],
                        })
        except Exception:
            pass

    def _write_outputs(self):
        """写入 data.json 和 raw_data.md"""
        # data.json
        data_path = self.eval_dir / "data.json"
        data_path.write_text(
            json.dumps(self.data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # raw_data.md - 人类可读摘要
        md = self._build_raw_data_md()
        raw_path = self.eval_dir / "raw_data.md"
        raw_path.write_text(md, encoding="utf-8")

        print(f"✅ 数据已保存: {self.eval_dir}/")
        print(f"   data.json   — 结构化数据")
        print(f"   raw_data.md — 可读摘要")

    def _build_raw_data_md(self) -> str:
        d = self.data
        lines = [
            f"# 工作流原始数据",
            f"",
            f"> 采集时间：{d['meta']['collected_at']}",
            f"> 数据来源：{d['meta']['source']}（{d['meta']['type']}）",
            f"",
            f"## Skill 调用序列",
            f"",
        ]

        if d["skills"]:
            lines.append(" → ".join(f"`/{s}`" for s in d["skills"]))
        else:
            lines.append("（未检测到 Skill 调用）")

        lines += ["", "## 工具调用统计", ""]
        if d["tools"]:
            for tool, count in sorted(d["tools"].items(), key=lambda x: -x[1]):
                lines.append(f"- {tool}: {count} 次")
        else:
            lines.append("（无工具调用数据）")

        lines += ["", f"## 用户交互次数", "", f"{d['interactions']} 次", ""]

        lines += ["", "## 操作的文件", ""]
        if d["files"]:
            for f in sorted(d["files"]):
                lines.append(f"- `{f}`")
        else:
            lines.append("（无文件数据）")

        lines += ["", "## Git 提交记录", ""]
        if d["commits"]:
            for c in d["commits"]:
                lines.append(f"- `{c['hash']}` {c['message']}")
        else:
            lines.append("（无提交记录）")

        if d["validate_results"]:
            lines += ["", "## 验证工具结果", ""]
            for key, result in d["validate_results"].items():
                rc = result.get("returncode", "?")
                status = "✅ 通过" if rc == 0 else f"❌ 失败（exit {rc}）"
                lines.append(f"**{key}**: {status}")
                if result.get("stderr"):
                    lines.append(f"```\n{result['stderr']}\n```")

        if d["errors"]:
            lines += ["", "## 采集错误", ""]
            for e in d["errors"]:
                lines.append(f"- [{e.get('stage', '?')}] {e.get('error', '')}")

        return "\n".join(lines) + "\n"


def find_latest_session() -> Optional[str]:
    """查找当前项目最新的 Claude Code 会话文件"""
    cwd = Path.cwd()
    project_key = "-" + str(cwd).replace("/", "-")
    claude_dir = Path.home() / ".claude" / "projects" / project_key

    if not claude_dir.exists():
        print(f"未找到项目目录: {claude_dir}")
        return None

    jsonl_files = list(claude_dir.glob("*.jsonl"))
    if not jsonl_files:
        print(f"未找到 JSONL 文件: {claude_dir}")
        return None

    latest = max(jsonl_files, key=lambda p: p.stat().st_mtime)
    print(f"最新会话: {latest}")
    return str(latest)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="TWU 工作流数据收集工具")
    parser.add_argument("input", nargs="?", help="输入来源（JSONL 文件 / Git 范围 / 目录）")
    parser.add_argument(
        "--type", choices=["jsonl", "git", "dir"], default="jsonl",
        help="输入类型（默认：jsonl）",
    )
    parser.add_argument(
        "--latest", action="store_true",
        help="自动检测当前项目最新会话文件",
    )

    args = parser.parse_args()

    if args.latest:
        session = find_latest_session()
        if not session:
            print("未找到最新会话，请手动指定文件路径")
            return
        args.input = session
        args.type = "jsonl"

    if not args.input:
        parser.print_help()
        return

    collector = WorkflowDataCollector(args.input, args.type)
    collector.collect()


if __name__ == "__main__":
    main()
