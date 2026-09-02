# -*- coding: utf-8 -*-
"""落盘前那道话术闸门，真的拦得住。

`/job-auto` 2026-09-02 起每批写完盘跑一条 `python tools/check_outreach.py`。
它存在的理由是**自检拦不住**：那天 129 + 24 份踩线的产出，全都带着自检小节、
逐条打着勾（其中一份写着「无 JD 原文照抄（引用那半句是刻意的，且加了引号）✓」）。

所以这条测试要钉两头：

1. **踩线的必须退出码 1** —— 闸门不放行；
2. **干净的必须退出码 0** —— 收窄错了会把合规的一起拦下，那样闸门第二天就会被绕过。

外加一条覆盖检查：**工作流里真的写着这条命令**。工具存在而没人跑，
正是这个仓库反复栽的那件事（判据在 `check_outreach.py` 的模块 docstring 里）。
"""
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "check_outreach.py"

CLEAN = """# t

## 打招呼开场白（≤200 字）

您好，我做的就是把模型能力变成普通人用得顺手的交互，开源作品累计 1 万+ stars。
详细的经历和作品都在简历里，方便的话您看一下，期待您的回复。

## 邮件

**主题**：应聘 X

您好，我做过 A 和 B，成果都在公开仓库里。
"""

#: 一段同时踩好几类的开场白。**每一类都要是文档里逐字列过的反例**，
#: 自己编一个「看起来不对」的句子测不出规则有没有在执行。
DIRTY = CLEAN.replace(
    "您好，我做的就是把模型能力变成普通人用得顺手的交互，开源作品累计 1 万+ stars。",
    "您好，看到您写「不要求系统级工程能力」——我这三年就是这么做产品的："
    "一年 40 个开源项目。想问下期望薪资怎么谈？")


def _run(*args, stdin=None):
    return subprocess.run(
        [sys.executable, str(TOOL), *args], input=stdin,
        capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT))


class TheGateBlocksWhatItShould(unittest.TestCase):
    def _file(self, d, text):
        p = pathlib.Path(d) / "outreach.md"
        p.write_text(text, encoding="utf-8")
        return p

    def test_a_clean_one_passes(self):
        with tempfile.TemporaryDirectory() as d:
            r = _run(str(self._file(d, CLEAN)))
        self.assertEqual(r.returncode, 0, f"合规的被拦下了：\n{r.stdout}{r.stderr}")

    def test_a_dirty_one_is_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            r = _run(str(self._file(d, DIRTY)))
        self.assertEqual(r.returncode, 1, "踩线的放过去了 —— 闸门等于不存在")

    def test_it_names_every_class_it_found(self):
        """只说「有问题」没用 —— 要说出是哪一句、踩了哪一类，人才改得动。"""
        with tempfile.TemporaryDirectory() as d:
            r = _run(str(self._file(d, DIRTY)))
        for cat in ("先谈钱", "复述职位描述", "拿年头自证"):
            with self.subTest(cat=cat):
                self.assertIn(cat, r.stdout)

    def test_stdin_works_before_anything_is_written(self):
        """起草到一半就能查 —— 不然只能等写完盘再返工。"""
        r = _run("--stdin", stdin="您好，这件事是我这三年一直在做的事。")
        self.assertEqual(r.returncode, 1)
        self.assertIn("拿年头自证", r.stdout)

    def test_the_hint_names_a_command_you_can_actually_type(self):
        """`AGENTS.md`「每一处引导都要写出该敲的命令」。

        `--stdin` 那条路上文件列表是空的，直接拼进去会印出一条尾巴空着的命令 ——
        指了个方向，没给能敲的东西。
        """
        r = _run("--stdin", stdin="您好，这件事是我这三年一直在做的事。")
        line = [ln for ln in r.stdout.splitlines()
                if ln.strip().startswith("python tools/check_outreach.py")]
        self.assertTrue(line, "报错了却没给出重跑的命令")
        self.assertNotEqual(line[0].strip(), "python tools/check_outreach.py",
                            "命令尾巴是空的，敲下去查不了任何东西")

    def test_a_missing_file_is_reported_not_silently_passed(self):
        r = _run(str(ROOT / "tools" / "没有这个文件.md"))
        self.assertEqual(r.returncode, 1, "文件不存在却算通过 —— 那是静默放行")


class ScanningNothingIsNotPassing(unittest.TestCase):
    """扫了个空却印 ✓ —— 这是这个仓库反复栽的那一类。

    `_named_section` 走 `_strip_wordcount`，它会剥掉整段 `> 引用块`
    （那层兜底是防「照模板抄的人把引用符号一起粘给 HR」）。而 `06` 的
    「产出格式」明文规定话术小节里不许写成 `> 引用块` —— 一旦写成了，
    剥完什么都不剩，检查器查的是空字符串。

    实测 2026-09-02：全库 1 节这样，而那一节里真躺着一处「拿年头自证」。
    **闸门对它印的是 ✓。**
    """

    QUOTED = """# t

## 打招呼开场白

您好，我做过 A 和 B，开源作品累计 1 万+ stars。详细的经历在简历里，期待您的回复。

## 邮件

**正文**

> 您好，
>
> 这件事是我这三年一直在做的事，所以想先聊聊。前一条我做过不少，
> 后一条要补。我做过 A 和 B，成果都在公开仓库里，方便的话您看一下。
"""

    def test_a_body_written_as_a_quote_block_is_reported(self):
        with tempfile.TemporaryDirectory() as d:
            f = pathlib.Path(d) / "outreach.md"
            f.write_text(self.QUOTED, encoding="utf-8")
            r = _run(str(f))
        self.assertEqual(r.returncode, 1,
                         "整段写成引用块 → 检查器扫了个空，却算通过了")
        self.assertIn("剥完只剩", r.stdout)

    def test_the_same_body_without_the_quote_marks_is_caught_properly(self):
        """去掉 `> ` 之后，藏在里面那句必须被认出来 —— 否则上一条只是
        换了个理由报错，真正的规则仍然没在查。"""
        import re as _re
        plain = _re.sub(r"(?m)^>\s?", "", self.QUOTED)
        with tempfile.TemporaryDirectory() as d:
            f = pathlib.Path(d) / "outreach.md"
            f.write_text(plain, encoding="utf-8")
            r = _run(str(f))
        self.assertEqual(r.returncode, 1)
        self.assertIn("拿年头自证", r.stdout)
        self.assertNotIn("剥完只剩", r.stdout, "去掉引用符号后不该再报空扫")

    def test_a_short_section_is_not_falsely_reported(self):
        """判据有个 30 字下限 —— 「无」「同上」这类短节不该被当成空扫。"""
        short = "# t\n\n## 打招呼开场白\n\n您好，我做过 A。详细的经历在简历里，期待您的回复。\n\n## 求职信\n\n无\n"
        with tempfile.TemporaryDirectory() as d:
            f = pathlib.Path(d) / "outreach.md"
            f.write_text(short, encoding="utf-8")
            r = _run(str(f))
        self.assertEqual(r.returncode, 0, f"短节被误报了：\n{r.stdout}")


class TheWorkflowActuallyRunsIt(unittest.TestCase):
    """工具存在 ≠ 有人跑它。那正是这道闸门要修的病。

    ## 它为什么装在 `/job-auto` 而不是 `/job-apply`

    第一版装在了 `job-apply.md` 里，当场被三条既有测试拦下
    （`test_no_python_sneaks_in`、`test_apply_still_has_no_python`、
    `test_the_batch_does_not_introduce_a_python_dependency`）——
    **`/job-apply` 承诺不依赖 Python**，原话是「没装 Python 的人就用不了它了」。

    仓库对同一件事早有样板：「落盘前对一眼小节」那一步就是
    **单岗肉眼对、批量跑工具、审计兜底**三层，而且那段自己写着
    「这里不写它，因为 `/job-apply` 承诺不依赖 Python」。照抄它的形状就对了。
    """

    AUTO = (ROOT / "workflows" / "job-auto.md").read_text(encoding="utf-8")
    APPLY = (ROOT / "workflows" / "job-apply.md").read_text(encoding="utf-8")

    def test_job_auto_runs_it_per_batch(self):
        self.assertIn("python tools/check_outreach.py", self.AUTO,
                      "/job-auto 没有跑这条 —— 判据回到了只有自检")

    def test_it_runs_in_the_same_block_as_the_sections_check(self):
        """要和 `--sections` 同一批跑 —— 那一格的语境是「这一批还在手里」。
        挪到收尾那段就变成第三道网了，材料早落盘。"""
        i = self.AUTO.index("python tools/audit_pipeline.py --sections")
        j = self.AUTO.index("python tools/check_outreach.py")
        self.assertLess(abs(j - i), 900, "两条检查离得太远，不在同一批的语境里了")
        self.assertLess(j, self.AUTO.index("收尾（无条件）"), "掉到收尾去了")

    def test_apply_stays_python_free_but_still_says_to_check(self):
        """单岗那条路不许出现 python 命令，**但也不能因此就不查**。"""
        self.assertNotRegex(self.APPLY, r"python\s+tools/check_outreach",
                            "/job-apply 又引入 Python 依赖了")
        self.assertIn("落盘前把话术对一遍禁语", self.APPLY,
                      "单岗那条路连「对一遍」这一步都没有了")

    def test_apply_points_at_the_batch_net(self):
        """指出批量有兜底，否则读的人以为只有自己这一眼。
        判据抄的是兄弟条目 `test_apply_points_at_the_batch_net`。"""
        i = self.APPLY.index("### 落盘前把话术对一遍禁语")
        seg = self.APPLY[i:self.APPLY.index("### 落盘\n")]
        self.assertIn("每批写完盘就跑一条逐份检查", seg)
        self.assertIn("不依赖 Python", seg)

    def test_the_tool_ships(self):
        """新工具忘了 `git add` 是静默故障 —— 本机全绿，发出去是坏的。
        （`tests/test_cross_references_resolve.py` 也钉这一条，这里钉的是这个工具。）"""
        import subprocess
        r = subprocess.run(["git", "ls-files", "--error-unmatch",
                            "tools/check_outreach.py"],
                           capture_output=True, text=True, cwd=str(ROOT))
        self.assertEqual(r.returncode, 0, "tools/check_outreach.py 还没进版本库")


if __name__ == "__main__":
    unittest.main()
