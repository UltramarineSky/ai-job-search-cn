# -*- coding: utf-8 -*-
"""缺口排在匹配点前面 —— 五类禁区之外的第六条，此前没有任何一处在执行。

`06-outreach-templates.md`「缺口：只有「一眼可见」的才写」那一节有两条规则：

1. **写哪些**：一眼可见的（年龄超线、学历专业不符、**行业背景与 JD 不符**、
   地点对不上、岗位名点着的能力你没有）→ 写；不写不会被当场识破的 → 不写。
2. **写在哪**：一眼可见的也不许排在匹配点前面 —— 把「我 <年龄> 岁超了线」
   放开头，等于让对方在读到你能干什么之前先读到一条过滤理由。

第 1 条是**语义判断**，机械查不了：实测活动用户 2026-08-26，253 份开场白里
96 份点了缺口，写法集中在「我没做过」59、「没做过」17、「我没接触过」7 ——
而它们几乎全是**行业不符**，正是那张表列在第一档的「该写」，例句逐字就是
「保险我没做过，承保、理赔都得从头学」。给这一类上正则只会误报，
而这个仓库自己写着「这类检查误报一次就会被整条忽略」。

**第 2 条是机械可验的，所以补上了。** 实测那 96 份**全部**排在佐证之后，
一份没犯 —— 加它不是因为有存量要清，是因为五类禁区里四类有词表盯着，
位置这条只写在散文里。

## 为什么挂在 `greeting_hits` 上

面板（`greeting_problems`）和全库自检（`check_greeting_keeps_the_five_rules`）
共用那一个函数，`_cli` 的注释写着理由：「所以不会再出现『面板说没问题、
审计说有』」。新判据挂在别处就会立刻打破这一点。
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import _cli  # noqa: E402

REF = (ROOT / "workflows" / "reference"
       / "06-outreach-templates.md").read_text(encoding="utf-8")
CLI = (ROOT / "tools" / "_cli.py").read_text(encoding="utf-8")

EVIDENCE = "我一年做了 40 个开源项目，其中一条线专做流程提效。"
GAP = "保险我没做过，承保理赔都得从头学。"
ASK = "想问下这个岗前期先啃哪一类场景？"


class TheOrderIsWhatIsChecked(unittest.TestCase):
    def test_a_gap_after_the_evidence_is_fine(self):
        self.assertEqual(_cli.gap_before_evidence("您好，" + EVIDENCE + GAP + ASK), "")

    def test_a_gap_in_the_first_clause_is_caught(self):
        got = _cli.gap_before_evidence("您好，" + GAP + EVIDENCE + ASK)
        self.assertTrue(got, "缺口在第一句却没报")
        self.assertIn("没做过", got)

    def test_the_greeting_word_is_not_counted_as_evidence(self):
        """「您好，」要留（06 专门交代过），但它不是佐证 —— 剥掉再判。

        **句号那一版是关键用例。** 逗号的「您好，」不切句，剥不剥都一样；
        而写成「您好。」时，不剥的话第一小句只剩「您好」两个字，
        紧跟其后的缺口就漏了。第一版只测了逗号那一版 —— 变异当场露馅：
        把剥问候语那一步整个删掉，测试照样绿。
        """
        for lead in ("您好，", "您好。", "你好，", ""):
            with self.subTest(lead=lead):
                self.assertTrue(_cli.gap_before_evidence(lead + GAP),
                                f"「{lead}」之后紧跟的缺口没被认出来")

    def test_other_gap_wordings_are_caught_too(self):
        for w in ("我没接触过这个行业。", "这块不是我的强项。", "这类系统我完全没碰过。",
                  "这个领域我零经验。"):
            with self.subTest(wording=w):
                self.assertTrue(_cli.gap_before_evidence("您好，" + w + EVIDENCE))

    def test_a_greeting_with_no_gap_says_nothing(self):
        self.assertEqual(_cli.gap_before_evidence("您好，" + EVIDENCE + ASK), "")

    def test_empty_input_does_not_crash(self):
        for t in ("", None, "   "):
            with self.subTest(text=t):
                self.assertEqual(_cli.gap_before_evidence(t), "")


class BothConsumersSeeIt(unittest.TestCase):
    """挂在共用的那个函数上，面板和自检才不会各说各的。"""

    def test_it_reaches_greeting_problems(self):
        probs = _cli.greeting_problems("您好，" + GAP + EVIDENCE + ASK)
        self.assertTrue(any("排在了匹配点前面" in p for p in probs), probs)

    def test_it_comes_out_of_the_shared_hits(self):
        cats = [c for c, _ in _cli.greeting_hits("您好，" + GAP + EVIDENCE + ASK)]
        self.assertIn("缺口排在了匹配点前面", cats,
                      "没走 greeting_hits —— 自检那一侧就看不到它")

    def test_the_shared_seam_is_still_documented(self):
        self.assertIn("两处共用", CLI)
        self.assertIn("面板说没问题、审计说有", CLI)


class TheRuleItSaysItEnforcesIsStillThere(unittest.TestCase):
    def test_the_placement_rule_is_in_the_framework(self):
        self.assertIn("一眼可见的也**不许排在匹配点前面**", REF)

    def test_the_other_half_is_deliberately_not_checked(self):
        """「写哪些」那一条留给人判断 —— 行业不符是**该写**的，别上正则。"""
        self.assertIn("行业背景与 JD 点名的不符", REF)
        i = CLI.index("_GREETING_GAP = re.compile(")
        seg = CLI[max(0, i - 700):i]
        self.assertIn("点缺口本身是对的，不是违规", seg,
                      "没写清这个正则不是用来抓「点了缺口」的 —— 下一个人会拿它去报警")

    def test_the_ladder_records_a_criteria_change_with_no_count_change(self):
        """判据变了就要说一声，哪怕数没动。"""
        self.assertIn("102 → 102", CLI)
        self.assertIn("判据变了、数没变，这一格照样要记", CLI)


if __name__ == "__main__":
    unittest.main()
