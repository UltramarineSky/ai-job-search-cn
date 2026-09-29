# -*- coding: utf-8 -*-
"""守卫认得的权限条目，必须是生成器清单推得出来的。

`security_guards.py` 原来只管 `.claude/settings.json` 一个文件，判据是「key 在不在
白名单里」。四家之后判据要更严：**条目本身**也要有出处。否则往任何一个权限文件里
手加一条 `Bash(python tools/:*)`（开宽授权）都能过白名单——key 是合法的，值不是。

「限定到入口，不开宽授权」这条规则本来只写在 `CONTRIBUTING.md`，**任何地方都没执行**
（2026-09-29 Task 9）。本文件把它落成判据，并且自带变异对照：同一棵临时树，
干净的那份必须绿、加了宽授权的那份必须红——否则「红」可能只是树本身跑不起来。
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import security_guards  # noqa: E402


def _mini_tree(settings_entries: list[str]) -> Path:
    """一棵能跑守卫的最小树：`tools/` + `workflows/` + `.claude/settings.json`。

    守卫要拿生成器的清单比条目，所以 `tools/` 得整份带上（与
    `tests/test_generated_entries_are_current.py` 里那条对照用例同一套理由：
    只拷两三个文件会让子进程死在 ModuleNotFoundError 上，那时 `returncode != 0`
    只是「撞死」，不是「发现条目没出处」）。`__pycache__` 不拷，白省 1.6 MB。
    """
    tmp = Path(tempfile.mkdtemp())
    shutil.copytree(ROOT / "tools", tmp / "tools",
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(ROOT / "workflows", tmp / "workflows")
    (tmp / ".claude").mkdir()
    (tmp / ".claude" / "settings.json").write_text(
        json.dumps({"permissions": {"allow": settings_entries}}), encoding="utf-8")
    (tmp / ".gitignore").write_text(
        "\n".join(security_guards.REQUIRED_IGNORE_RULES), encoding="utf-8")
    return tmp


def _run(tmp: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "tools/security_guards.py"],
                          cwd=tmp, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


class TheGeneratorAndTheGuardAgree(unittest.TestCase):
    def test_every_allow_entry_has_a_source(self):
        allowed = security_guards.derivable_entries()
        for rel, entries in security_guards.permission_entries().items():
            stray = [e for e in entries
                     if security_guards.normalize_entry(e) not in allowed]
            self.assertEqual(stray, [],
                             f"{rel} 里这些条目不是生成器清单能推出的"
                             f"（开宽授权？手加的？）：{stray}")

    def test_no_entry_opens_a_whole_directory(self):
        for rel, entries in security_guards.permission_entries().items():
            for e in entries:
                self.assertNotIn("tools/:*", e, f"{rel}: {e} 把整个目录授权出去了")
                self.assertNotIn("Skill(*)", e, f"{rel}: {e} 是通配技能授权")

    def test_the_guard_sees_every_permission_file(self):
        seen = set(security_guards.permission_entries())
        for rel in security_guards.PERMISSION_FILES:
            if (ROOT / rel).is_file():
                self.assertIn(rel, seen, f"{rel} 存在但守卫没在看它")

    def test_the_guard_still_requires_the_claude_file(self):
        """对照用例：`.claude/settings.json` 是必需的，缺了要报。"""
        self.assertIn(".claude/settings.json", security_guards.PERMISSION_FILES)

    def test_the_derivation_is_not_an_empty_set(self):
        """元测试：清单要是空了，上面那条「每条都有出处」就恒真。

        空集的来源很具体——临时树里没有 `workflows/`，或 `INDEX.md` 解析不出任何
        一行。恒绿的守卫比没有守卫更糟：它让人以为有人在盯。
        """
        allowed = security_guards.derivable_entries()
        self.assertTrue(allowed, "生成器清单推不出任何条目 —— 比对是空转")
        self.assertIn("pdftotext:*", allowed,
                      "`.claude/settings.json` 预批的 pdftotext 不在清单里")


class TheGuardActuallyGoesRed(unittest.TestCase):
    """变异证据：判据真的会红，而干净树真的会绿。"""

    def _tree(self, entries):
        tmp = _mini_tree(entries)
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        return tmp

    def test_control_clean_tree_passes(self):
        """对照：合法条目（都是清单推得出的）→ 退 0。

        没有这条，下面那条「红」可能只是临时树跑不起来。
        """
        import gen_entries
        res = _run(self._tree(list(gen_entries.SETTINGS_ALLOW)))
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("security_guards: OK", res.stdout)

    def test_hand_added_wide_directory_entry_is_red(self):
        """`Bash(python tools/:*)`：key 合法（就在 `permissions.allow` 里），
        值不是清单能推出的 —— CONTRIBUTING.md「限定到入口，不开宽授权」的执行版。"""
        import gen_entries
        entries = list(gen_entries.SETTINGS_ALLOW) + ["Bash(python tools/:*)"]
        res = _run(self._tree(entries))
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn("Bash(python tools/:*)", res.stdout)
        self.assertIn("not in the reviewed allowlist", res.stdout)
        self.assertNotIn("Traceback", res.stderr)

    def test_hand_added_interpreter_wildcard_is_red(self):
        """`Bash(python:*)` = 任意 Python 命令，历史上真提交过又撤掉的那条。"""
        import gen_entries
        entries = list(gen_entries.SETTINGS_ALLOW) + ["Bash(python:*)"]
        res = _run(self._tree(entries))
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn("Bash(python:*)", res.stdout)

    def test_wrong_tool_syntax_entry_is_red_even_when_the_key_is_legal(self):
        """守卫按「授权了哪条命令」比，不按哪家的语法比：Gemini 的
        `run_shell_command(python tools/:*)` 与 Claude 的同一条同样没出处。"""
        tmp = self._tree(list(__import__("gen_entries").SETTINGS_ALLOW))
        gemini = tmp / ".gemini"
        gemini.mkdir()
        (gemini / "settings.json").write_text(json.dumps({
            "tools": {"allowed": ["run_shell_command(pdftotext)"]}}), encoding="utf-8")
        res = _run(tmp)
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn("run_shell_command(pdftotext)", res.stdout)


class TheRetractedPermissionFiles(unittest.TestCase):
    """Step 1 的分支：核不到 schema 的那几家，**一个文件都不生成**。

    一个猜出来的 key 名会被信任、被提交、然后静默什么都不做 —— 比没有这个文件坏。
    `.gemini/settings.json` 原来就在生成，而它写着的那两样正好各中一条：
    `tools.autoAccept` 在装好的 0.58.0 里没有这个键，`tools.allowed` 里那条
    不带括号的 `run_shell_command` 是「所有 shell 命令免确认」。取证见
    `SETUP.md`「各家工具的权限文件」一节。
    （这里原来还写着「与 spec §5.3」——`.gitignore` 把 `docs/superpowers/` 整个排除
    出版本库，clone 出去的人点不到那个出处。「规则真、出处假」是本仓库点名的失败
    模式，所以出处只留入库的那一份。）
    """

    def test_no_gemini_or_codex_permission_file_is_generated(self):
        import gen_entries
        owned = {str(k.relative_to(ROOT)).replace("\\", "/")
                 for k in gen_entries.desired_files(ROOT)}
        for rel in (".gemini/settings.json", ".codex/config.toml"):
            self.assertNotIn(rel, owned, f"{rel} 还在生成清单里 —— 它的 schema 没核实到")

    def test_no_retracted_permission_file_is_on_disk(self):
        """盘上也得没有：留下旧文件就是留着那份静默不生效的配置在教别人抄。"""
        for rel in (".gemini/settings.json", ".codex/config.toml"):
            self.assertFalse((ROOT / rel).is_file(), f"{rel} 还在盘上")

    def test_gemini_no_longer_has_a_paste_snippet(self):
        """`--print gemini` 也一起删了（2026-09-30：Gemini CLI 已停）。

        片段是**推荐** —— SETUP.md 让用户照着粘。给一个装不上的工具留一段可粘配置
        比不提它更坏：粘进去那份静默不生效，而用户以为已经批过了。

        这与 `security_guards` 里 `.gemini/settings.json` 的 key 面**不矛盾**，两者
        做的是相反方向的事：那是**检查**（万一有人手放一份，裸 `run_shell_command`
        那种宽授权照样红），这是**推荐**。删推荐、留检查。
        """
        import gen_entries
        self.assertNotIn("gemini", gen_entries.SNIPPET_TOOLS)
        res = subprocess.run(
            [sys.executable, "tools/gen_entries.py", "--print", "gemini"],
            cwd=ROOT, capture_output=True, text=True,
            encoding="utf-8", errors="replace")
        self.assertNotEqual(res.returncode, 0, res.stdout)
        self.assertIn(".gemini/settings.json", security_guards.PERMISSION_FILES,
                      "守卫那一半不该跟着推荐一起删 —— 它是防手放野文件的")


class TheSnippetsArePerTool(unittest.TestCase):
    """`--print <家>` 给的是**那一家**的写法，不是把 Claude 的清单抄过去。

    上一版 `--print agy` 印的是 Claude 那四条，里面 `Skill(job-application-assistant)`
    是 Claude 独有语法，而那段是要贴进 SETUP.md 给用户照着粘的（2026-09-29 评审抓到）。
    """

    def _snippet(self, tool: str) -> str:
        res = subprocess.run([sys.executable, "tools/gen_entries.py", "--print", tool],
                             cwd=ROOT, capture_output=True, text=True,
                             encoding="utf-8", errors="replace")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        return res.stdout

    def test_claude_keeps_the_skill_entry(self):
        out = self._snippet("claude")
        self.assertIn("Skill(job-application-assistant)", out)
        self.assertIn("Bash(pdftotext:*)", out)

    def test_other_tools_do_not_carry_claude_syntax(self):
        for tool in ("codex", "agy"):
            with self.subTest(tool=tool):
                out = self._snippet(tool)
                self.assertNotIn("Skill(job-application-assistant)", out,
                                 f"{tool} 的片段里混进了 Claude 的技能授权")
                self.assertNotIn("Bash(", out,
                                 f"{tool} 的片段里混进了 Claude 的 Bash(...) 包装")
                self.assertIn("pdftotext", out, f"{tool} 的片段少了该授权的那条命令")

    def test_portal_wildcard_is_expanded_not_copied(self):
        """Claude 那条 `.agents/skills/*/cli/src/cli.ts` 的通配在别家不成立：
        Codex 实测按 token 逐段比，`*` 匹配不上任何渠道，所以片段给的是具体路径。

        **名单从 `SNIPPET_TOOLS` 取**（只排掉 claude —— 它那一份本来就该是通配形），
        所以将来加一家，这条自动盖到它，不必记得回来改。
        """
        import gen_entries
        portals = sorted(p.relative_to(ROOT).as_posix().replace("\\", "/")
                         for p in (ROOT / ".agents" / "skills").glob("*/cli/src/cli.ts"))
        self.assertTrue(portals, "盘上一个渠道 CLI 都没有，这条对照就空转了")
        others = [t for t in gen_entries.SNIPPET_TOOLS if t != "claude"]
        self.assertTrue(others, "除了 claude 一家都没有片段可对了")
        for tool in others:
            out = self._snippet(tool)
            for portal in portals:
                self.assertIn(portal, out, f"{tool} 的片段没展开成具体渠道 {portal}")

    def test_setup_md_carries_the_current_agy_snippet(self):
        """SETUP.md 里那一段是 `--print agy` 的**原文**，不是手抄的第二份。

        片段里的渠道路径按盘上装着的展开（`_concrete_prefixes`），所以新接一个渠道
        那一刻，文档里那段就过期了 —— 而过期的文档比没有文档更没人会去核对。
        修法一条命令：`python tools/gen_entries.py --print agy`，重新粘一次。
        """
        import gen_entries
        want = gen_entries.snippet("agy").rstrip("\n")
        text = (ROOT / "SETUP.md").read_text(encoding="utf-8")
        blocks = [b.strip() for b in re.findall(r"```text\n(.*?)```", text, re.S)]
        agy = [b for b in blocks if b.startswith("# Antigravity CLI")]
        self.assertEqual(len(agy), 1,
                         "SETUP.md 里应当恰好有一段 ```text 的 agy 片段")
        self.assertEqual(agy[0], want,
                         "SETUP.md 里那段与 `--print agy` 现在的输出不一致 —— "
                         "跑那条命令重新粘一次")


if __name__ == "__main__":
    unittest.main()
