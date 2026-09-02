"""Tests for the /job-html-report command and its gitignore rule.

Mirrors the pattern in test_security_guards.py: one class that verifies
properties of the real repo, testing the things CI would catch if the
command file or gitignore rule were wrong.
"""

import subprocess
import sys
import unittest
from pathlib import Path

try:
    import yaml  # noqa: F401 - only probing availability for the lint integration test
    _HAVE_YAML = True
except ImportError:
    _HAVE_YAML = False

REPO_ROOT = Path(__file__).resolve().parent.parent
COMMAND_FILE = REPO_ROOT / "workflows" / "job-html-report.md"
LINT_SCRIPT = REPO_ROOT / "tools" / "lint_skills.py"
GITIGNORE = REPO_ROOT / ".gitignore"


class HtmlReportCommandFileTests(unittest.TestCase):
    """Structural checks on the command file itself."""

    def test_command_file_exists(self):
        self.assertTrue(COMMAND_FILE.exists(), f"{COMMAND_FILE} not found")

    def test_command_file_starts_with_correct_header(self):
        """lint_skills.py rejects command files that don't start with '# /<name>'."""
        text = COMMAND_FILE.read_text(encoding="utf-8")
        first_line = text.lstrip().splitlines()[0]
        self.assertTrue(
            first_line.startswith("# /job-html-report"),
            f"Command file must start with '# /job-html-report', got: {first_line!r}",
        )

    def test_command_file_is_non_empty(self):
        text = COMMAND_FILE.read_text(encoding="utf-8").strip()
        self.assertGreater(len(text), 100, "Command file appears suspiciously short")


class TheOpenFlagActuallyOpens(unittest.TestCase):
    """索引承诺「出完直接打开」，正文就得真打开。

    2026-09-02 通读时抓到两边对着干：

    - 索引（**同时是面板上那份帮助**）：`/job-html-report --open`（出完直接打开）
    - 正文：「带 `--open` → 写完之后告诉用户去打开这个文件
      （**这条命令打不开浏览器**）」

    而不带 `--open` 也会告诉他路径 —— 也就是说这个开关**什么都没改变**。
    一个点了没反应的开关比没有更坏：用户会以为是自己敲错了。

    `test_index_matches_the_workflows` 那两组管的是「开关**在不在**」
    （索引有的正文要有、正文有的索引要能查到），管不到「它**做不做**
    索引说的那件事」—— 两边都提到 `--open`，所以两组都是绿的。

    修的是正文不是承诺：`AGENTS.md`「有一件事不必回命令行」立的就是这个立场
    ——「不要产出一个 HTML 再把路径贴给他让他双击」。
    """

    def test_the_index_still_promises_it(self):
        """控制用例：承诺还在，否则下面那条在为一个不存在的承诺把关。"""
        ag = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        i = ag.index("`workflows/job-html-report.md`")
        self.assertIn("直接打开", ag[i:i + 300], "索引不再承诺「直接打开」了？")

    def test_the_workflow_opens_it(self):
        t = COMMAND_FILE.read_text(encoding="utf-8")
        body = "\n".join(l for l in t.splitlines()
                         if not l.lstrip().startswith(">"))
        self.assertRegex(
            body, r"webbrowser|xdg-open|start \"\"|open -a",
            "--open 那一支没有任何真的打开动作 —— 而索引承诺了「出完直接打开」")
        self.assertNotIn(
            "这条命令打不开浏览器", body,
            "正文又宣称自己打不开浏览器，与索引的承诺对着干")

    def test_it_still_has_a_fallback(self):
        """要不到执行权限时要如实说，别假装打开了。"""
        t = COMMAND_FILE.read_text(encoding="utf-8")
        self.assertRegex(t, r"没有执行权限|要不到",
                         "没写权限拿不到时怎么办")


class HtmlReportGitignoreTests(unittest.TestCase):
    """reports/ must be gitignored — it holds personal generated output."""

    def test_reports_folder_is_gitignored(self):
        rules = {line.strip() for line in GITIGNORE.read_text(encoding="utf-8").splitlines()}
        self.assertIn(
            "reports/",
            rules,
            "reports/ must be listed in .gitignore — generated dashboards are personal output",
        )


@unittest.skipUnless(
    _HAVE_YAML,
    "PyYAML not installed (the CI Python-test job omits it; the lint job runs lint_skills.py directly)",
)
class HtmlReportLintIntegrationTests(unittest.TestCase):
    """lint_skills.py must pass after the command is added."""

    def test_lint_passes_on_real_repo(self):
        result = subprocess.run(
            [sys.executable, str(LINT_SCRIPT)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode,
            0,
            f"lint_skills.py failed:\n{result.stdout}{result.stderr}",
        )
        self.assertIn("OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
