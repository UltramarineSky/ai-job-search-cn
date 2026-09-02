# -*- coding: utf-8 -*-
"""开场白第一行是会话列表里唯一看得见的字，不能拿去说对方已经知道的事。

`06-outreach-templates.md` 把「开场铺垫」列进五类禁区：「看到贵司这个岗」
说的是 JD 是他写的、消息是你发的 —— 对方全知道。它平均吃掉 15 个字，
而一份的预算只有 200 字。

实测活动用户 2026-08-30：280 份里 **71 份**开头是铺垫，是五类禁区里最大的一类。
`tools/trim_opening.py` 删掉了其中 48 句（省出 720 字），这一类降到 23 份。

## 这条守卫钉的是「删得干净」，不是「删得多」

删词是在改**他要发出去的字**，比改一个抬头字段风险高。所以工具不靠正则自证，
而是**拿 `_cli.greeting_hits` 当验收**：改完的必须是改前的真子集 ——
少了铺垫，且没多出任何一条。达不到就整条跳过（实测拦下 1 份）。
"""
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import _cli  # noqa: E402
import trim_opening as t  # noqa: E402

AUTO = (ROOT / "workflows" / "job-auto.md").read_text(encoding="utf-8")


class ItTrimsOnlyWhatIsSafe(unittest.TestCase):
    def test_a_full_stop_makes_it_safe(self):
        g = "您好，看到这个 AI 产品经理岗。一年 40 个开源项目，代码由 AI 生成我来验收。"
        out, pad = t.trim(g)
        self.assertTrue(out.startswith("您好，一年 40 个开源项目"), out)
        self.assertEqual(pad, "看到这个 AI 产品经理岗")

    def test_a_colon_makes_it_safe_too(self):
        g = "您好，这个岗方向上很对：营销这条链路我做了十年，Agent 是我的日常。"
        out, _pad = t.trim(g)
        self.assertTrue(out.startswith("您好，营销这条链路"), out)

    def test_a_comma_does_not_cut_mid_sentence(self):
        """后面接逗号说明那半句跟着铺垫走 —— **只删匹配那一截**是不行的。

        2026-08-30 起还有第二条路：整句都是铺垫时删整句。这一份走不到那条 ——
        它整句就是一句话，删完什么也不剩，所以理由换成了「删完剩下的太短」。
        两种拒绝都对，**要紧的是它一个字都没动**。
        """
        g = "您好，看到这个岗，我觉得挺合适的，一年 40 个开源项目都是我自己做的。"
        out, why = t.trim(g)
        self.assertEqual(out, "")
        self.assertTrue("剩半句" in why or "太短" in why, why)


class AWholePaddingSentenceGoes(unittest.TestCase):
    """整句就是铺垫时删整句 —— 这 16 份此前只能靠人重写。

    ## 实测

    2026-08-30：23 份「开场铺垫」里 **22 份**后面不是句号或冒号 ——
    也就是说匹配到的那一截几乎都不是独立的铺垫句，而是**真句子的开头**：

        我想应聘 + 智能体平台资深产品经理。   ← 整句都是铺垫，该删整句
        看到岗   + 位写「不要求编程基础…」    ← 有内容，一个字都不该删

    只删匹配那一截会把话截成半句（`_SEP` 那条判据挡的就是这个，它是对的）。
    而整句删掉之后剩下的正是该占第一行的东西 —— 那 16 份删完从
    「Claude、Cursor、Dify 这些平台我每天…」「JD 那句「技术是门票…」」起头。

    三道闸门：这一句要短、后面要真有正文、以及检查器验收（新的必须是旧的真子集）。
    """

    def test_the_padding_sentence_is_dropped(self):
        g = ("您好，我想应聘 AI 产品经理。ChatGPT、Claude、DeepSeek 各自能做"
             "什么、边界在哪我都横着比过，Prompt、RAG、Function Call 也都落过地。")
        out, why = t.trim(g)
        self.assertTrue(out, "整句都是铺垫，却没删")
        self.assertNotIn("我想应聘", out)
        self.assertIn("ChatGPT", out)
        self.assertIn("我想应聘", why, "删掉的那句要原样报出来")

    def test_a_long_first_sentence_is_left_alone(self):
        """开头那句长了，多半带着正文 —— 不敢整句删。

        实测那一类长这样：「看到岗位写「不要求编程基础，重点是让 AI 工具
        真正解决问题」——…」，第一行就在交付内容。
        """
        g = ("您好，看到岗位写「不要求编程基础，重点是让 AI 工具真正解决问题」，"
             "这正是我这三年在做的事。一年 40 个开源项目都是这么出来的。")
        out, why = t.trim(g)
        self.assertEqual(out, "", "把带着正文的第一句整句删了")
        self.assertIn("太长", why)

    def test_it_still_needs_something_left(self):
        g = "您好，我想应聘 AI 产品经理。"
        self.assertEqual(t.trim(g)[0], "", "删完什么都不剩，还删")

    def test_the_limit_is_a_named_constant(self):
        """判据要有名字和理由 —— 一个裸数字下次会被随手调。"""
        self.assertTrue(hasattr(t, "_PAD_SENTENCE_MAX"))
        src = (pathlib.Path(t.__file__).read_text(encoding="utf-8"))
        i = src.index("_PAD_SENTENCE_MAX")
        self.assertIn("17 字", src[max(0, i - 400):i], "没写实测出处")

    def test_it_keeps_the_greeting_word(self):
        for hello in ("您好，", "你好，"):
            g = hello + "看到这个岗。一年 40 个开源项目，代码由 AI 生成我来验收。"
            with self.subTest(hello=hello):
                self.assertTrue(t.trim(g)[0].startswith(hello))

    def test_nothing_to_do_is_not_an_error(self):
        g = "您好，一年 40 个开源项目，代码由 AI 生成我来验收，开源累计 1 万 stars。"
        out, why = t.trim(g)
        self.assertEqual(out, "")
        self.assertIn("没有铺垫", why)


class TheCheckerIsTheAcceptanceTest(unittest.TestCase):
    def test_the_result_must_be_a_strict_subset(self):
        """改完必须更干净 —— 这是它敢动外发文案的全部理由。"""
        src = t.trim.__doc__ + open(t.__file__, encoding="utf-8").read()
        self.assertIn("after < before", src)

    def test_it_refuses_when_the_result_is_not_cleaner(self):
        """构造一条：删完会新增一类违规，工具必须拒绝。"""
        g = ("您好，看到这个岗。我想 9 月 1 日入职，一年 40 个开源项目，"
             "代码由 AI 生成我来验收。")
        out, _why = t.trim(g)
        if out:
            before = {h[0] for h in _cli.greeting_hits(g)}
            after = {h[0] for h in _cli.greeting_hits(out)}
            self.assertTrue(after < before, f"{sorted(before)} → {sorted(after)}")

    def test_it_never_exceeds_the_limit(self):
        """删只会变短，但这条断言是白纸黑字的合同，不靠「显然」。"""
        g = "您好，看到这个岗。" + "一年 40 个开源项目。" * 3
        out, _ = t.trim(g)
        if out:
            self.assertLessEqual(len(re.sub(r"\s", "", out)), _cli.GREETING_MAX)


class ItDropsWhatCarriesNoInformation(unittest.TestCase):
    """「我目前离职随时到岗」删得，「30-50k 按几薪算」删不得。

    两者都在五类禁区里，但**性质不同**：前者是主动透露的信息，删了什么都不丢；
    后者是**该问的问题，只是问错了地方**（属于评估里的「投前必问」）。
    实测 2026-08-30：谈钱那几份里只有一半的「投前必问」已经收了同类问题，
    自动删会真的丢掉一个他想问的事。**删掉零信息的，报出走错地方的。**
    """

    def test_a_whole_sentence_goes(self):
        g = ("您好，一年 40 个开源项目、累计 1 万 stars，AI 编码工具是我的日常。"
             "我目前离职随时到岗。想问下这个岗现在到哪一步了？")
        out, why = t.drop_when_available(g)
        self.assertNotIn("随时到岗", out)
        self.assertIn("想问下这个岗", out)
        self.assertEqual(why, "抢答到岗时间")

    def test_it_does_not_cut_inside_a_sentence(self):
        """一句里塞了两类违规的，整句删 —— 切一半会留下不通的残句。"""
        g = ("您好，一年 40 个开源项目、累计 1 万 stars，AI 编码工具是我的日常。"
             "已离职、随时到岗，期望 45-60k。这个岗前半年主要产出什么？")
        out, _why = t.drop_when_available(g)
        if out:
            self.assertNotIn("随时到岗", out)
            self.assertNotIn("45-60k", out, "整句该一起删，不做句内手术")

    def test_it_keeps_a_question(self):
        """删完不能只剩自述 —— 打招呼要留一个问题给对方。"""
        g = ("您好，一年 40 个开源项目、累计 1 万 stars，代码由 AI 生成、"
             "我负责设计和验收，主力产品有 10 万注册用户。我目前离职随时到岗？")
        out, why = t.drop_when_available(g)
        self.assertEqual(out, "")
        self.assertIn("没有问句", why)

    def test_nothing_to_do_is_not_an_error(self):
        g = "您好，一年 40 个开源项目、累计 1 万 stars。这个岗现在到哪一步了？"
        out, why = t.drop_when_available(g)
        self.assertEqual(out, "")
        self.assertIn("没有抢答到岗时间", why)

    def test_the_checker_is_the_acceptance_test_here_too(self):
        src = open(t.__file__, encoding="utf-8").read()
        i = src.index("def drop_when_available")
        j = src.index("\ndef ", i + 1)
        self.assertIn("after < before", src[i:j])

    def test_money_is_reported_not_deleted(self):
        """谈钱那一类不许进删除名单 —— 它要人来搬，不是工具来删。"""
        src = open(t.__file__, encoding="utf-8").read()
        self.assertIn("先谈钱", src)
        i = src.index("def drop_when_available")
        j = src.index("\ndef ", i + 1)
        self.assertNotIn("先谈钱", src[i:j], "删除那一支不该认得「先谈钱」")


class TheAutoRunNamesIt(unittest.TestCase):
    def test_job_auto_runs_it(self):
        self.assertIn("trim_opening.py", AUTO)


if __name__ == "__main__":
    unittest.main()
