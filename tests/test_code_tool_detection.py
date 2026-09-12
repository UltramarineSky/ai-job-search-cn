# -*- coding: utf-8 -*-
"""宿主 AI 编码工具探测 + doctor 输出的命令形式适配。

为什么有这些断言：
- 探测信号全是对真实安装取证来的（2026-09-12）：Claude Code 注入
  `CLAUDECODE=1`（不是 `CLAUDE_CODE` / `CLAUDE`，那两个从没存在过）、
  agy 注入 `ANTIGRAVITY_AGENT=1`、Gemini CLI 给子 shell 注入 `GEMINI_CLI=1`。
  上一版因为信号是凭空写的，真 Claude Code 会话被认成 generic，整个面板
  默认变成免斜杠。所以下面专门有一组断言「假信号不许触发」。
- doctor 因「只用标准库、不 import 仓库模块」的契约保着一份逐字副本
  （见 doctor.detect_code_tool 的 docstring），这份测试同时钉两份。
"""

import contextlib
import io
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import _cli  # noqa: E402
import doctor  # noqa: E402

#: 探测会碰到的全部变量。每个用例先把它们清干净，再按需设置。
TOOL_ENV = (
    "JOBS_CODE_TOOL",
    "ANTIGRAVITY_AGENT", "ANTIGRAVITY_AGENTAPI_EXE", "ANTIGRAVITY_LS_VERSION",
    "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT",
    # 下面是上一版凭空写、实测不存在的假信号 —— 留着专门验「它们不再触发」。
    "CLAUDE_CODE", "CLAUDE", "CURSOR_VERSION", "TERM_PROGRAM", "CODEX",
    "GEMINI_CLI",
)


@contextlib.contextmanager
def tool_env(**values):
    """临时替换宿主工具相关环境变量，退出时原样还回。"""
    saved = {k: os.environ.get(k) for k in TOOL_ENV}
    try:
        for k in TOOL_ENV:
            os.environ.pop(k, None)
        os.environ.update(values)
        yield
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


@contextlib.contextmanager
def override_tool(name):
    """JOBS_CODE_TOOL 覆盖，其余信号保持环境原样（测优先级用）。"""
    saved = os.environ.get("JOBS_CODE_TOOL")
    os.environ["JOBS_CODE_TOOL"] = name
    try:
        yield
    finally:
        if saved is None:
            os.environ.pop("JOBS_CODE_TOOL", None)
        else:
            os.environ["JOBS_CODE_TOOL"] = saved


#: (环境变量, 期望判定)。两份 detect 都按这张表对拍。
SCENARIOS = [
    ({}, "generic"),
    ({"ANTIGRAVITY_AGENT": "1"}, "antigravity"),
    ({"ANTIGRAVITY_AGENTAPI_EXE": "x"}, "antigravity"),
    ({"ANTIGRAVITY_LS_VERSION": "1"}, "antigravity"),
    ({"CLAUDECODE": "1"}, "claude"),
    ({"CLAUDE_CODE_ENTRYPOINT": "cli"}, "claude"),
    ({"GEMINI_CLI": "1"}, "gemini"),
    # 旧版虚构信号 —— 一个都不许再认。
    ({"CLAUDE_CODE": "1"}, "generic"),
    ({"CLAUDE": "1"}, "generic"),
    ({"CURSOR_VERSION": "0.40.0"}, "generic"),
    ({"TERM_PROGRAM": "cursor"}, "generic"),
    ({"TERM_PROGRAM": "vscode"}, "generic"),
    ({"CODEX": "1"}, "generic"),
]


class TestCodeToolDetection(unittest.TestCase):

    def test_detect_matrix(self):
        for env, expected in SCENARIOS:
            with self.subTest(env=env):
                with tool_env(**env):
                    self.assertEqual(_cli.detect_code_tool(), expected)

    def test_detect_code_tool_agrees_between_doctor_and_cli(self):
        """doctor 的副本与正本 _cli.detect_code_tool 判得完全一样。"""
        for env, expected in SCENARIOS:
            with self.subTest(env=env):
                with tool_env(**env):
                    self.assertEqual(
                        doctor.detect_code_tool(), _cli.detect_code_tool())
                    self.assertEqual(doctor.detect_code_tool(), expected)

    def test_override_beats_autodetect(self):
        with tool_env(ANTIGRAVITY_AGENT="1"), override_tool("claude"):
            self.assertEqual(_cli.detect_code_tool(), "claude")
            self.assertEqual(doctor.detect_code_tool(), "claude")

    def test_override_passes_unknown_name_through(self):
        # cursor / codex 自动探测分不出来，但 JOBS_CODE_TOOL=cursor 这类
        # 手工指定要原样透传 —— doctor 的脚注靠这个叫出工具名。
        with tool_env(CLAUDECODE="1"), override_tool("cursor"):
            self.assertEqual(_cli.detect_code_tool(), "cursor")
            self.assertEqual(doctor.detect_code_tool(), "cursor")

    # ---- adapt_commands：非 Claude 环境去斜杠，Claude 原样 ----

    def test_adapt_strips_slash_everywhere_except_claude(self):
        for tool in ("antigravity", "gemini", "generic", "cursor"):
            with self.subTest(tool=tool):
                self.assertEqual(
                    doctor.adapt_commands("跑 /job-auto 接着抓", tool),
                    "跑 job-auto 接着抓")
                self.assertEqual(
                    doctor.adapt_commands("/job-apply <url>", tool),
                    "job-apply <url>")
                self.assertEqual(
                    doctor.adapt_commands("`/job-rank --all`", tool),
                    "`job-rank --all`")
                # 路径与 URL 里的片段不是命令，不许动。
                self.assertEqual(
                    doctor.adapt_commands(
                        "workflows/job-apply.md 里写着 /job-setup", tool),
                    "workflows/job-apply.md 里写着 job-setup")
                self.assertEqual(
                    doctor.adapt_commands("https://x//job-auto", tool),
                    "https://x//job-auto")
        # Claude Code：一切原样。
        self.assertEqual(
            doctor.adapt_commands("跑 /job-auto 接着抓", "claude"),
            "跑 /job-auto 接着抓")

    def test_adapt_passes_non_string_through(self):
        self.assertIs(doctor.adapt_commands(None, "generic"), None)

    # ---- doctor.main 全输出适配（48 个 print 点一起被盖住）----

    def _run_main(self, tool):
        with override_tool(tool), contextlib.redirect_stdout(io.StringIO()) as buf:
            rc = doctor.main([])
        return rc, buf.getvalue()

    def test_main_antigravity_has_no_slash_commands_left(self):
        rc, out = self._run_main("antigravity")
        self.assertEqual(rc, 0)
        # 全文任何位置都不许漏出 /job- 记号（脚注也不例外）。
        self.assertNotRegex(out, doctor._SLASH_CMD)
        self.assertIn("Antigravity", out)
        self.assertNotIn("去掉开头的斜杠", out)  # 旧脚注：让用户自己翻译

    def test_main_generic_footnote_keeps_claude_example_slash(self):
        _rc, out = self._run_main("generic")
        # 全文只剩脚注里那一条示范 Claude Code 写法的 /job-auto，
        # 它必须活着穿过剥离流；正文里的命令全部已去斜杠。
        self.assertEqual(doctor._SLASH_CMD.findall(out), ["job-auto"])
        self.assertIn("用 Claude Code 时带斜杠", out)

    def test_main_claude_has_no_adaptation_footnote(self):
        _rc, out = self._run_main("claude")
        self.assertNotIn("💡 已识别", out)
        self.assertNotIn("用 Claude Code 时带斜杠", out)


if __name__ == "__main__":
    unittest.main()
