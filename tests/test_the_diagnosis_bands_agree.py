# -*- coding: utf-8 -*-
"""投后诊断那几段是**一条链**，不许两段给相反的结论。

这一栏是几轮里逐段加起来的：分数段回复率、猎头占比、投的地方对不对、内推、
按网站拆、被拒原因。加的时候每段单看都对，**连起来读才发现打架**
（2026-08-22 第一次整段拉出来读）：

    第 3 段：「不是简历写得不好，是投的地方不对」（数据：投出去的 63% 是
             「专业能力够、行业经验对不上」）
    第 5 段：「每个网站都是 0，那问题多半不在选哪个网站，而在简历或岗位匹配
             ——先审简历」

**隔着不到一屏，结论相反。** 而第 5 段自己列了两个可能（简历 / 岗位匹配），
然后挑了**没有数据支持的那个**。

规矩：**有数据的那一边说了算。** 能拆出来时就指过去，拆不出来才回到两条并列。
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PANEL = (ROOT / "web" / "src" / "components"
         / "OutcomeStats.tsx").read_text(encoding="utf-8")

#: 剥掉 JSX 注释之后的正文。**这一步是必须的，已经栽过三次**：
#: 这类检查查的是「某句话还在不在」，而注释里恰恰要引用旧文案说明为什么改它。
#: 连着注释一起扫 = 禁止把理由写下来，而这个仓库的做法正好相反。
_CODE = re.sub(r"\{/\*[\s\S]*?\*/\}", "", PANEL)


def _channel_note() -> str:
    i = _CODE.index("每个网站都是 0")
    return _CODE[max(0, i - 900):i + 700]


class TheChannelBandDefersToTheData(unittest.TestCase):
    def test_it_does_not_send_him_to_the_resume_when_the_split_says_otherwise(self):
        """`appliedFit` 拆得出来时，这一段不许再说「先审简历」。"""
        seg = _channel_note()
        self.assertIn("appliedFit", seg, "这一段没看那份拆分就下了结论")
        # 「先审简历」只许出现在**拆不出来**的那一支里；能拆出来时不许出现
        m = re.search(r"appliedFit\.pick \* 2 > s\.appliedFit\.total[\s\S]{0,200}?\?"
                      r"([\s\S]{0,220}?):", seg)
        self.assertIsNotNone(m, "找不到「拆得出来」那一支")
        self.assertNotIn("先审简历", m.group(1),
                         "拆得出来时还在说「先审简历」——和上一段结论相反")

    def test_it_points_at_the_band_that_has_the_number(self):
        seg = _channel_note()
        self.assertRegex(seg, r"上面那栏.{0,20}拆出来|行业经验对不上",
                         "没指向真正有数据的那一段")

    def test_it_still_says_something_when_the_split_is_missing(self):
        """老快照 / 样本不足时拆不出来 —— 那时回到两条并列，不许什么都不说。"""
        seg = _channel_note()
        self.assertIn("简历或岗位匹配这两样", seg,
                      "拆不出来时那一支被删了")

    def test_the_non_zero_case_is_untouched(self):
        """有回音时这一段本来就该说「往回复率高的那个多投」，别被改掉。"""
        self.assertIn("哪个高就往哪个多投一点", PANEL)


class TheChainStaysReadableEndToEnd(unittest.TestCase):
    """整条链的顺序有含义：先说「有多少没到用人方手里」，再说「投的地方对不对」，
    最后才说「换一种到达方式」。倒过来的话，用户会在还不知道原因时先去内推。
    """

    def test_the_bands_are_in_diagnosis_order(self):
        order = ["有多少没到用人方手里", "投的地方对不对", "还有一条没试过的路"]
        pos = [PANEL.index(k) for k in order]
        self.assertEqual(pos, sorted(pos), f"诊断链的顺序乱了：{order}")

    def test_no_band_blames_the_resume_unconditionally(self):
        """「审简历」这条结论必须带条件 —— 无条件说它就会和拆分那段打架。"""
        for m in re.finditer(r"先审简历", _CODE):
            seg = _CODE[max(0, m.start() - 600):m.start()]
            self.assertIn("appliedFit", seg,
                          "有一处「先审简历」没看拆分就说出口了")


if __name__ == "__main__":
    unittest.main()
