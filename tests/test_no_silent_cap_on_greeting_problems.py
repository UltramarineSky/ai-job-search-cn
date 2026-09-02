# -*- coding: utf-8 -*-
"""开场白的问题列表截到 3 条就收尾，不说还有没有。

面板在「复制开场白」旁边印 `greeting_problems` 的结果：

    发之前删掉：「是几薪」是先谈钱；「随时到岗」是抢答到岗时间；「目前离职」是抢答到岗时间。

用户把列出来的三条删完，以为这段干净了 —— **而第四条还在里面**。
实测活动用户 2026-08-23，37 份踩线的开场白里有 1 份命中 4 条：

    是几薪 / 随时到岗 / 目前离职 / 期望 45-60k     ← 五类里踩了四类

一份只有 1-2 条是常态（37 份里 35 份），所以上限本身留着。要修的是**沉默**：
这个仓库对截断有成文的做法 —— 审计每条都写「另有 N 份硬门 FAIL 的没算」，
`query_yield` 的停用清单只印前 10 个但先报总数。只有这里例外。

## 为什么这条值得单独有守卫

它**不会红**：删掉那句提示，测试全绿、面板照常显示三条、审计的总数
（按文件数）也一点不变 —— 只有第四条问题悄悄不见了。
同族的还有 `test_test_anchors_are_unambiguous`、`code_of` 那个空串坑。
"""
import sys
import unittest
from pathlib import Path

NL = chr(10)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
import _cli  # noqa: E402
from _srcscan import strip_comments  # noqa: E402


def _greeting(*words):
    """拼一段必然命中给定禁语的开场白。"""
    return "您好，" + "。".join(words) + "。我做过多智能体的数据管线。"


def _all_bans():
    """**跳过「开场铺垫」。** 这份夹具靠「一个短语 = 一处命中」凑条数，
    而那一类 2026-08-24 起按**开头**判（`_cli.opening_padding`）：
    拼进句子中段的那几个不再各算一处，凑不够 `GREETING_SHOW + 2`，
    整组截断测试就失去了它要测的前提。其余四类仍然是全文短语匹配，用它们。"""
    return [(cat, w) for cat, ws in _cli.GREETING_BANS.items()
            if cat != "开场铺垫" for w in ws]


class TheCapAnnouncesItself(unittest.TestCase):
    def test_more_than_the_cap_says_how_many_more(self):
        words = [w for _c, w in _all_bans()[:_cli.GREETING_SHOW + 2]]
        got = _cli.greeting_problems(_greeting(*words))
        self.assertTrue(any("还有" in x for x in got),
                        f"截断了却没说还有几条：{got}")
        self.assertIn(f"还有 2 条", " ".join(got))

    def test_exactly_the_cap_says_nothing_extra(self):
        """不多不少时不该吊一句「还有 0 条」。"""
        words = [w for _c, w in _all_bans()[:_cli.GREETING_SHOW]]
        got = _cli.greeting_problems(_greeting(*words))
        self.assertEqual(len(got), _cli.GREETING_SHOW)
        self.assertFalse(any("还有" in x for x in got), got)

    def test_under_the_cap_says_nothing_extra(self):
        got = _cli.greeting_problems(_greeting(_all_bans()[0][1]))
        self.assertEqual(len(got), 1)
        self.assertNotIn("还有", got[0])

    def test_the_listed_ones_come_first(self):
        """那句话是补充说明，不能挤掉一条真问题。"""
        words = [w for _c, w in _all_bans()[:_cli.GREETING_SHOW + 1]]
        got = _cli.greeting_problems(_greeting(*words))
        named = [x for x in got if x.startswith("「")]
        self.assertEqual(len(named), _cli.GREETING_SHOW,
                         "「还有 N 条」占掉了一条本该列出来的")

    def test_a_clean_greeting_stays_empty(self):
        clean = "您好，多智能体的数据管线和多轮自检我自己搭过，产品也从 0 跑到有人用。"
        self.assertEqual(_cli.greeting_problems(clean), [])

    def test_the_length_check_still_runs_past_the_cap(self):
        """字数是另一类问题，不受这个上限管 —— 原有行为，别一起改掉。"""
        words = [w for _c, w in _all_bans()[:_cli.GREETING_SHOW + 1]]
        long = _greeting(*words) + "啊" * _cli.GREETING_MAX
        got = _cli.greeting_problems(long)
        self.assertTrue(any("超了" in x for x in got), got)
        self.assertTrue(any("还有" in x for x in got), got)


class TheCapItselfIsNamedAndReasoned(unittest.TestCase):
    def test_it_is_a_constant_not_a_literal(self):
        """`[:3]` 写死在函数里时，改它要动代码、也没人说得清 3 是怎么来的。

        **钉的是性质，不是位置。** 这条原来把窗口切在 `greeting_problems`
        的函数体上，而 2026-08-31 截断那几行被抽进了 `_as_problems`
        （第二个消费方 `style_problems` 来了，措辞与截断不能有两份）——
        用意一个字没变，守卫却当场红。同一课这一轮撞过好几次：
        判据钉实现位置，收重复时它会把收拢本身判成违规。
        """
        self.assertIsInstance(_cli.GREETING_SHOW, int)
        code = strip_comments((ROOT / "tools" / "_cli.py").read_text(encoding="utf-8"))
        # 截断用的是具名常量，而且只有一处在做这件事。
        self.assertEqual(code.count("[:GREETING_SHOW]"), 1,
                         "截断不止一处，或者没用那个常量")
        self.assertNotIn("hits[:3]", code, "上限又写死回字面量了")
        # 开场白那条仍然经过它 —— 抽走之后总得还连着。
        i = code.index("def greeting_problems(")
        seg = code[i:code.index("\ndef ", i + 10)]
        self.assertIn("_as_problems(", seg,
                      "开场白不再走那个共用的截断了")

    def test_the_number_has_a_stated_basis(self):
        src = (ROOT / "tools" / "_cli.py").read_text(encoding="utf-8")
        i = src.index("GREETING_SHOW = ")
        seg = " ".join(src[max(0, i - 400):i].split())
        self.assertRegex(seg, r"37 份踩线的里 35 份只有 1-2 条",
                         "这个数没说出处")
        self.assertRegex(seg, r"列满不代表列全")

    def test_the_measured_case_is_written_down(self):
        src = (ROOT / "tools" / "_cli.py").read_text(encoding="utf-8")
        i = src.index("def greeting_problems(")
        # 取整个函数，不要固定字符窗口。原来是 `i + 2200` —— 那份 docstring 里
        # 有一道逐次记录的台阶，每加一格就往后推一截；2026-08-27 加第六格时
        # 把「沉默的截断」那句挤出了窗口，测试当场红，而它要验的东西一个字没变。
        # 同一形状同一天在 `test_the_panel_reads_keys_that_are_written` 也踩过一次：
        # **中文一占位，按字符数取的窗口就够不着后面。**
        end = src.find("\ndef ", i + 10)
        seg = " ".join(src[i:end if end > 0 else len(src)].split())
        self.assertIn("期望 45-60k", seg, "没留下那个实测的四条例子")
        self.assertRegex(seg, r"沉默的截断")


class TheJudgeItselfIsUnchanged(unittest.TestCase):
    """这次只动「怎么报」，不动「判什么」—— 判据两处共用，动它会连累审计。"""

    def test_the_word_list_is_still_the_single_source(self):
        import export_web_data as E
        self.assertIs(E.GREETING_BANS, _cli.GREETING_BANS)
        self.assertIs(E.greeting_problems, _cli.greeting_problems)

    def test_hits_are_not_truncated(self):
        """上限只管**显示**。审计按 `greeting_hits` 分档统计，
        它要是也被截，全库那份报告就会少算。"""
        words = [w for _c, w in _all_bans()[:_cli.GREETING_SHOW + 2]]
        self.assertGreater(len(_cli.greeting_hits(_greeting(*words))),
                           _cli.GREETING_SHOW)

    def test_the_audit_counts_files_not_listed_items(self):
        """审计的总数按文件数走，所以它一直看不见这次的截断 ——
        这句话解释了为什么这条守卫非有不可。"""
        raw = (ROOT / "tools" / "audit_pipeline.py").read_text(encoding="utf-8")
        # **判据要剥注释再查。** 那一段的注释里逐字写着「判据走
        # `_cli.greeting_hits()`」—— 连注释一起扫，把真正那行换成 `[]`
        # 这条照样绿（变异实测）。而「一份只记一次」是写在注释里的规矩，
        # 要在原文里查。
        code = strip_comments(raw)
        i = code.index("def check_greeting_keeps_the_five_rules(")
        self.assertIn("_cli.greeting_hits(", code[i:i + 2000], "审计改用别的判据了")
        j = raw.index("def check_greeting_keeps_the_five_rules(")
        # **窗口锚到函数末尾，不写定长。** `raw[j:j + 3000]` 那一版是随手写的，
        # 而这个函数的说明后来长了一截（多了一张分档表），3000 字就切在
        # 「一份只记一次」前面 —— 断言当场落空，而代码一个字没动。
        # 同族前科在这个仓库里已经栽过四次（`src[i:i+3000]`、`_body()[i:]`、
        # `PORTALS[i:i+2200]`、这一处）：**窗口有上界没下界，长一点就废。**
        end = raw.index(NL + "def ", j)
        self.assertIn("一份只记一次", raw[j:end])


if __name__ == "__main__":
    unittest.main()
