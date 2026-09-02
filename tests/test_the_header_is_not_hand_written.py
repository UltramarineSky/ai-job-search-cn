# -*- coding: utf-8 -*-
"""话术抬头那四条里有三条不需要判断，却一直是手写的 —— 手写就会错。

`06-outreach-templates.md` 把抬头钉成四条：有没有对话方 + 猎头还是 HR 直招、
这一档是什么（分数 + 档名）、链接与日期、不许出现内部词。

**其中三条是纯函数**：渠道看 `isHeadhunter`（或猎聘的 `/a/` 路径），分数与档名看
`rank_score` / `rank_verdict`，内部词是一张固定的词表。实测活动用户 2026-08-30，
280 份话术里：

    没写是猎头还是直招   115 份
    抬头里没有分数       247 份
    抬头里写着「判词」   109 份
    渠道写反了            28 份   ← 这一条有实际后果

最后那条不是措辞问题：猎头问薪资与到岗时间要直接答、HR 直招不主动展开，
第二轮怎么说话完全取决于这半句。而写反的 28 份里 6 份（21%）正文对着猎头
顾问说了「贵司」，抬头写对的 122 份里只有 3 份（2%）。

`tools/outreach_header.py` 把这三样从手里拿走。这条守卫钉两件事：
**判据本身是对的**（尤其别被否定词骗），以及**认出来了要真的改成**。
"""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import outreach_header as oh  # noqa: E402

AUTO = (ROOT / "workflows" / "job-auto.md").read_text(encoding="utf-8")


class TheSideItReadsIsTheSideItWrote(unittest.TestCase):
    def test_it_reads_the_plain_forms(self):
        for val, want in (
                ("**有对话方 · 猎聘聊天框（猎头代招）**", "猎头代招"),
                ("**有对话方 · 猎聘聊天框（企业直招）**", "企业直招"),
                ("**HR 直招 · 聊天框**", "企业直招"),
                ("**有对话方 · HR 直招版**", "企业直招"),
                ("**有对话方 · 用人方本人**", "企业直招")):
            with self.subTest(val=val):
                self.assertEqual(oh.side_written(val)[0], want)

    def test_a_negation_is_not_a_mention(self):
        """「非猎头」是在否定，不是在说这是猎头岗。

        实测：不先剥掉它，6 份写着「（HR 直招，非猎头）」的会被判成「写了猎头」
        —— 而它们写得完全正确，工具会去「改正」一件本来就对的事。
        """
        for val in ("**有对话方 · 猎聘聊天框（HR 直招，非猎头）**",
                    "**企业直招 · 聊天框**（上市公司自有岗位，非猎头）",
                    "**有对话方 · 聊天框（直招，不是猎头）**"):
            with self.subTest(val=val):
                self.assertEqual(oh.side_written(val)[0], "企业直招")

    def test_it_says_nothing_when_the_line_says_nothing(self):
        self.assertEqual(oh.side_written("**有对话方 · 猎聘聊天框**"), ("", ""))
        self.assertEqual(oh.side_written(""), ("", ""))

    def test_the_phrase_it_returns_is_really_in_the_text(self):
        """返回的原词必须真的在串里 —— 改的时候要拿它去替换。

        第一版返回的是那一侧的**标准名**（「企业直招」），而盘上 22 份写的是
        「HR 直招」：`val.replace("企业直招", …)` 替不着，静默无操作 ——
        工具报「改了 37 份」，审计照旧报「28 份写反」。
        **认出来了不等于改成了。**
        """
        for val in ("**HR 直招 · 聊天框**", "**有对话方 · HR 直招版**",
                    "**有对话方 · 猎聘聊天框（猎头代招）**"):
            with self.subTest(val=val):
                _side, phrase = oh.side_written(val)
                self.assertIn(phrase, val)


class ItOnlyRewritesWhatItCanDerive(unittest.TestCase):
    def test_an_unknown_side_is_left_alone(self):
        """判不出渠道就不写 —— 猜一个的代价是让他按错误的路数谈。"""
        self.assertEqual(oh.side_of({"isHeadhunter": None, "url": "x"}), "")

    def test_a_liepin_agency_path_counts_even_without_the_field(self):
        """猎聘的 `/a/` 是猎头岗的路径，字段没抓到时它一样确凿。"""
        self.assertEqual(
            oh.side_of({"isHeadhunter": None,
                        "url": "https://www.liepin.com/a/1.shtml"}), "猎头代招")

    def test_it_fixes_a_reversed_side_in_place(self):
        head = ("# x 投递话术\n\n- 渠道判定：**HR 直招 · 聊天框**\n"
                "- 职位链接：https://www.liepin.com/a/1.shtml\n")
        new, notes = oh.fix_header(
            head, {"isHeadhunter": True, "url": "https://www.liepin.com/a/1.shtml",
                   "rank_score": 63, "rank_verdict": "值得投"})
        self.assertIn("猎头代招", new)
        self.assertNotIn("HR 直招", new)
        self.assertIn("- 评分：63 分，属于「值得投」", new)
        self.assertTrue(any("写反" in n for n in notes))

    def test_it_does_not_touch_a_correct_header(self):
        head = ("# x 投递话术\n\n- 渠道判定：**有对话方 · 猎聘聊天框（猎头代招）**\n"
                "- 职位链接：https://www.liepin.com/a/1.shtml\n"
                "- 评分：63 分，属于「值得投」\n")
        new, notes = oh.fix_header(
            head, {"isHeadhunter": True, "url": "https://www.liepin.com/a/1.shtml",
                   "rank_score": 63, "rank_verdict": "值得投"})
        self.assertEqual((new, notes), (head, []))

    def test_it_translates_internal_words(self):
        head = "# x\n\n- 判词：值得投\n"
        new, notes = oh.fix_header(head, {"isHeadhunter": False, "url": "u"})
        self.assertNotIn("判词", new)
        self.assertIn("结论", new)
        self.assertTrue(notes)


class TheAutoRunNamesIt(unittest.TestCase):
    def test_job_auto_runs_it(self):
        self.assertIn("outreach_header.py --apply", AUTO)


if __name__ == "__main__":
    unittest.main()
