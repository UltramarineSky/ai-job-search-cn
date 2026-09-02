# -*- coding: utf-8 -*-
"""聊到求职就自动接管的那个壳，手里没有跑投递所需的任何一件工具。

`.claude/skills/job-application-assistant/` 是**自动触发**的壳（触发词里就有
「投递」「apply」）。它原来只用一句话交代下一步：

> 实际投递走 `workflows/job-apply.md`（Claude Code 下即 `/job-apply`）。

而那份工作流真要跑的东西，这个壳一件都没有 —— 实测 2026-08-24：

    job-apply.md 的代码块里要跑   typst compile · typst fonts
                                pdftotext -layout -enc UTF-8 · 渠道 CLI（node）
    还要                        并行子代理做双角色审稿（Agent）
    壳的 allowed-tools           Read, Glob, Grep, WebFetch, WebSearch,
                                Edit, Write, AskUserQuestion
                                —— **Bash 和 Agent 一个都没有**

这是 `CLAUDE.md` 点名的那一族：「A 说去用 B，而 B 够不着」。它自己那条规矩写着
「**壳上的 `allowed-tools` 要盖得住它那份工作流**」，并记着 `job-upskill` 栽过一次。

## 但这里的正解不是给它开权限

一个**凭一句话就自动接管**的壳，手里不该攥着编译、写盘、起子代理这些能力。
`test_skill_permissions_cover_its_workflow` 也早就把这个壳排除在「要盖住工作流」
之外了（它的正文里没有「读取并严格执行 `workflows/<名>.md`」那一句）。

**权限窄是这个壳的边界，不是它的缺陷** —— 缺的是把这句话说出来，并在到那一步时
**把命令交给用户**（`AGENTS.md`「每一处引导都要写出该敲的命令」）。

## 两条最容易走歪的路，要点名挡掉

- **硬走**：照着 `job-apply.md` 跑到一半撞权限 —— 用户看到的是一串失败的命令。
- **绕道**：用手里有的 `Write` 手搓一份材料 —— 那会绕过 typst 编译、PDF 文本层
  校验、双角色审稿全部把关，产出一份看着像、其实没过任何一道检查的东西。
"""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SHELL = (ROOT / ".claude" / "skills" / "job-application-assistant"
         / "SKILL.md").read_text(encoding="utf-8")
APPLY = (ROOT / "workflows" / "job-apply.md").read_text(encoding="utf-8")

_FENCE = re.compile(r"```(?:bash|sh|shell|console)\n(.*?)```", re.S)
RUNNERS = ("python", "python3", "node", "bun", "typst", "pdftotext", "pdftoppm")


def flat(s: str) -> str:
    s = " ".join(re.sub(r"^\s*>\s?", "", s, flags=re.M).split())
    return re.sub(r"(?<=[一-鿿，。；：、（）「」])"
                  r" +(?=[一-鿿，。；：、（）「」])", "", s)


def allowed() -> str:
    return re.search(r"^allowed-tools:(.*)$", SHELL, re.M).group(1)


def body() -> str:
    i = SHELL.index("## 这个壳自己做不了投递")
    return flat(SHELL[i:])


class TheShellStaysNarrow(unittest.TestCase):
    """自动接管的壳不该有编译、写盘、起子代理的能力。"""

    def test_it_has_no_bash(self):
        self.assertNotIn("Bash", allowed(),
                         "自动触发的咨询壳拿到了 Bash —— 一句话就能触发的东西"
                         "不该能跑 shell")

    def test_it_has_no_subagents(self):
        self.assertNotIn("Agent", allowed().replace("AskUserQuestion", ""),
                         "自动触发的咨询壳拿到了子代理")

    def test_it_still_has_what_consulting_needs(self):
        a = allowed()
        for t in ("Read", "Glob", "Grep", "WebFetch", "AskUserQuestion"):
            with self.subTest(t=t):
                self.assertIn(t, a, f"少了 {t}，咨询本身都做不了")

    def test_it_still_auto_triggers_on_applying(self):
        """触发词里有「投递」——这正是它会走到那一步的原因，别顺手删掉。"""
        head = SHELL[:SHELL.index("---", 4)]
        self.assertIn("投递", head)


class ItHandsOverTheCommand(unittest.TestCase):
    def test_it_names_the_command(self):
        b = body()
        self.assertRegex(b, r"\*\*让用户敲 `/job-apply <职位链接>`\*\*")

    def test_it_names_the_tailoring_one_too(self):
        """定制简历是另一条命令 —— 只给 `/job-apply` 会把人卡在那儿。"""
        self.assertIn("/job-cv <职位链接>", body())

    def test_it_says_the_stubs_are_unrestricted(self):
        """不说这句，读的人会以为敲了命令一样受限、于是还是不敢交出去。"""
        self.assertRegex(body(), r"不受本壳的权限限制")

    def test_it_says_the_narrowness_is_deliberate(self):
        b = body()
        self.assertRegex(b, r"\*\*权限窄是有意的，不是漏了。\*\*")
        self.assertRegex(b, r"\*\*够不着不是缺陷，是这个壳的边界\*\*")

    def test_it_lists_what_it_cannot_run(self):
        """光说「做不了」太虚 —— 列出来，下一个人才验得了。"""
        b = body()
        for cmd in ("typst compile", "typst fonts",
                    "pdftotext -layout -enc UTF-8"):
            with self.subTest(cmd=cmd):
                self.assertIn(cmd, b)
        self.assertRegex(b, r"\*\*Bash 和 Agent 一个都没有\*\*")

    def test_the_claim_carries_a_date(self):
        self.assertIn("2026-08-24", body())


class TheTwoWrongPathsAreNamed(unittest.TestCase):
    def test_it_forbids_pushing_through(self):
        self.assertRegex(body(), r"别硬走")
        self.assertRegex(body(), r"用户看到的是一堆失败的\s*命令|用户看到的是一堆失败的命令")

    def test_it_forbids_hand_writing_the_materials(self):
        """`Write` 它是有的 —— 挡不住就会绕过 typst、PDF 校验、双角色审稿。"""
        self.assertRegex(body(), r"别绕道用 `Write` 手搓一份材料")

    def test_it_cites_the_rule_it_follows(self):
        self.assertIn("每一处引导都要写出该敲的命令", body())


class TheClaimAboutJobApplyIsTrue(unittest.TestCase):
    """壳里列的那几条命令，得真是 job-apply 要跑的 —— 它变了这段就要改。"""

    def _needs(self):
        out = set()
        for m in _FENCE.finditer(APPLY):
            for ln in m.group(1).splitlines():
                ln = ln.strip()
                for r in RUNNERS:
                    if ln.startswith(r + " "):
                        out.add(" ".join(ln.split()[:2]))
        return out

    def test_apply_really_needs_a_shell(self):
        needs = self._needs()
        self.assertTrue(needs, "job-apply 的代码块里一条命令都没有了 —— 这段要重写")
        self.assertIn("typst compile", needs)

    def test_every_command_the_shell_names_is_real(self):
        needs = " ".join(self._needs())
        for cmd in ("typst compile", "typst fonts", "pdftotext -layout"):
            with self.subTest(cmd=cmd):
                self.assertIn(cmd, needs,
                              f"壳里说 job-apply 要跑 {cmd}，而工作流里没有")

    def test_apply_really_uses_subagents(self):
        self.assertRegex(flat(APPLY), r"起草者|审稿者",
                         "双角色审稿没了 —— 「还要起子代理」那句就成了假话")


class TheOtherShellsAreUnaffected(unittest.TestCase):
    """另外两个自动触发的壳有 Bash，那是对的 —— 它们有自己的工作流要跑。"""

    def test_scrape_and_upskill_keep_their_bash(self):
        for name in ("job-scrape", "job-upskill"):
            with self.subTest(name=name):
                t = (ROOT / ".claude" / "skills" / name
                     / "SKILL.md").read_text(encoding="utf-8")
                self.assertIn("Bash(", re.search(r"^allowed-tools:(.*)$",
                                                 t, re.M).group(1),
                              f"{name} 的 Bash 权限没了 —— 它的工作流跑不动")

    def test_they_execute_a_workflow_of_their_own(self):
        """这两个壳和咨询壳的区别就在这一句 —— 它决定要不要盖住工作流。"""
        for name in ("job-scrape", "job-upskill"):
            with self.subTest(name=name):
                t = (ROOT / ".claude" / "skills" / name
                     / "SKILL.md").read_text(encoding="utf-8")
                self.assertIn("读取并严格执行", t)

    def test_the_consulting_shell_does_not_claim_to_execute_one(self):
        self.assertNotIn("读取并严格执行", SHELL,
                         "咨询壳自称要执行某份工作流了 —— "
                         "那 test_skill_permissions_cover_its_workflow "
                         "会要求它盖住那份工作流的全部命令")


if __name__ == "__main__":
    unittest.main()
