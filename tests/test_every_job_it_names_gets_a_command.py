# -*- coding: utf-8 -*-
"""「照下面那几条各自的链接一个一个跑」—— 下面根本没有那几条链接。

收尾把总数拆成两半（补一节 / 改已有内容）之后，「改」那半印的是一句指路：
照下面每条检查各自给的链接去跑。而**每条检查只印一个链接**
（`_cli.live_tail` 印的是 `live[0][0]`，其余只出现在「例：某某、某某」
那三个公司名里）。

实测 2026-08-31：10 个岗要改，分散在两条检查下，屏幕上一共 2 个链接 ——
另外 8 个**一处都没印过**。那句引导对其中八成的岗根本没法执行。

`AGENTS.md`「每一处引导都要写出该敲的命令」写着判据：指一个文件名或指一件事
都不够，读完这句他要能直接动手。指「下面那几条」比指文件名更远一层 ——
他先得去找，而找得到的只有两条。

## 为什么 `LIVE_REWRITE` 从 set 改成 dict

键仍要归一化（同一个岗被两条检查点到时只算一次），而值要留**原样链接** ——
归一化过的链接剥掉了协议，敲出去不是他从网站上复制的那个形状。
一个集合同时担这两件事担不了，所以改成「归一键 -> 原样链接」。

## 超上限那一支为什么单独成函数

内联在 `main` 里时它只有喂进一份十几个岗的真数据才跑得到，也就是实际上没人
验过。`rewrite_commands` 独立出来之后两支都能直接喂。
"""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))

import _cli                     # noqa: E402
import audit_pipeline as ap     # noqa: E402
from _srcscan import code_of    # noqa: E402


class EveryNamedJobGetsItsCommand(unittest.TestCase):

    def test_none_is_left_without_one(self):
        """上限之内，一个岗一条命令 —— 不许只印第一个。"""
        links = ["https://x.com/job/%d" % i for i in range(ap._REWRITE_SHOWN)]
        out = ap.rewrite_commands(links)
        for u in links:
            with self.subTest(u):
                self.assertIn("    /job-apply " + u, out,
                              "这个岗被点了名，却没给它那条命令")

    def test_each_line_is_runnable_as_printed(self):
        """原样链接，不是归一化过的 —— 剥了协议的那种敲出去不是他复制的形状。"""
        u = "https://www.liepin.com/job/1984499023.shtml"
        # 判据自检：这两个形状得真不一样，否则下面那条断言什么都没验。
        self.assertNotEqual(_cli.norm_url(u), u, "归一化没剥掉协议？")
        self.assertEqual(ap.rewrite_commands([u])[0], "    /job-apply " + u,
                         "印的不是他从网站上复制的那个链接")

    def test_it_says_how_many_it_dropped(self):
        """截断了要说截了多少 —— 沉默的截断在这个仓库里是有名字的一类。"""
        n = ap._REWRITE_SHOWN + 8
        out = ap.rewrite_commands(["https://x.com/%d" % i for i in range(n)])
        cmds = [x for x in out if "/job-apply" in x]
        self.assertEqual(len(cmds), ap._REWRITE_SHOWN, "上限没生效")
        self.assertTrue(any("另有 8 个" in x for x in out),
                        "截了 8 个，一个字没说")

    def test_the_rest_are_reachable_by_a_command(self):
        """「等」和「自己去找」都不是下一步，得给一条能敲的。"""
        out = ap.rewrite_commands(
            ["https://x.com/%d" % i for i in range(ap._REWRITE_SHOWN + 1)])
        self.assertTrue(
            any("audit_pipeline.py --actionable" in x for x in out),
            "说了还有剩下的，却没说怎么把它们拿出来")

    def test_nothing_is_printed_when_there_is_nothing(self):
        self.assertEqual(ap.rewrite_commands([]), [])

    def test_the_lines_carry_no_markdown(self):
        """这几行直接上终端。`AGENTS.md`：给用户看的字先剥标记。"""
        for line in ap.rewrite_commands(["https://x.com/1"] * 1):
            self.assertNotIn("**", line)
            self.assertNotIn("`", line)


class TheClosingUsesIt(unittest.TestCase):
    """判据在函数里，而调用要真的发生 —— 否则上面全是自娱自乐。"""

    def test_main_prints_what_the_function_returns(self):
        seg = code_of("tools/audit_pipeline.py", "def main(")
        self.assertIn("rewrite_commands(_rw)", seg,
                      "收尾没调它 —— 那几条命令还是印不出来")
        self.assertIn("print(_line)", seg, "算出来了却没印")

    def test_the_sentence_no_longer_points_at_the_lines_below(self):
        """旧措辞把人支到下面去找，而下面只有两条。"""
        seg = code_of("tools/audit_pipeline.py", "def main(")
        self.assertNotIn("照下面那几条各自的", seg)

    def test_the_set_keeps_the_original_link(self):
        """⚠️ **钉行为。** 原来查的是 `live_tail` 体内那一行长什么样 ——
        记账 2026-08-31 搬进 `note_live`（手写尾巴的两条检查也要调它），
        这条当场红。判据钉实现位置，重构本身就成了违规。
        """
        keep = dict(_cli.LIVE_REWRITE)
        try:
            _cli.LIVE_REWRITE.clear()
            _cli.note_live(["https://www.liepin.com/job/1.shtml"], rewrite=True)
            self.assertEqual(list(_cli.LIVE_REWRITE.values()),
                             ["https://www.liepin.com/job/1.shtml"],
                             "值不是原样链接的话，印出来的命令敲不出他复制的那个形状")
        finally:
            _cli.LIVE_REWRITE.clear()
            _cli.LIVE_REWRITE.update(keep)


class TheSignalIsReal(unittest.TestCase):
    """有语料时验一次：收集到的那些确实各自有命令。"""

    def test_the_live_set_maps_to_runnable_links(self):
        if not _cli.LIVE_REWRITE:
            self.skipTest("这轮没跑过审计，集合是空的 —— 这条这次什么都没验")
        for k, v in _cli.LIVE_REWRITE.items():
            with self.subTest(k):
                self.assertTrue(v.startswith("http"), "值不是原样链接")
                self.assertEqual(_cli.norm_url(v), k, "键值对不上同一个岗")


if __name__ == "__main__":
    unittest.main()
