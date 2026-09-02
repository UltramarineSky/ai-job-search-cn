# -*- coding: utf-8 -*-
"""谈好的数和到手的数不是一个数 —— 那几条要问，而且要在还有筹码的时候问。

国内 offer 里三样东西不改年包数字，却实实在在决定拿到多少：

    试用期几个月、几折、什么条件转正
    公积金社保按什么基数缴、比例几个点
    基本工资占薪资总额多少

第三条最容易被当成「稳不稳」的问题略过，而它实际决定的是**加班费、病假工资、
经济补偿金（N / N+1）的计算基数** —— 公司把基本工资压低时这几项一起缩水。

2026-08-22 通读时发现：全仓「社保基数」「缴纳基数」零覆盖，「试用期」只出现在
评估框架里（当作岗位风险信号），`job-offer.md` 的接受前清单里一条都没有。

**时机也是内容的一部分。** 国内多轮制下，在专业面问公积金比例和在 HR 面问，
是两回事；而等 offer 下来再问，筹码已经没了。所以这三条要在两个地方各出现一次：
`07` 的反问（该问的时候）和 `job-offer.md` Step 4（最后一道关）。
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OFFER = (ROOT / "workflows" / "job-offer.md").read_text(encoding="utf-8")
PREP = (ROOT / "workflows" / "reference"
        / "07-interview-prep.md").read_text(encoding="utf-8")

#: 三条都要在两处出现。少一条，用户就在那一条上默认接受对方给的值。
ITEMS = {
    "试用期": ("80%", "转正"),
    "公积金": ("比例", "基数"),
    "基本工资": ("经济补偿金", "占"),
}


class BothPlacesAskTheSameThings(unittest.TestCase):
    def test_the_offer_checklist_has_all_three(self):
        for item, marks in ITEMS.items():
            with self.subTest(item=item):
                self.assertIn(item, OFFER, f"接受前清单里没有「{item}」")
                for m in marks:
                    self.assertIn(m, OFFER, f"「{item}」这条缺了关键的「{m}」")

    def test_the_interview_prep_has_all_three(self):
        for item in ITEMS:
            with self.subTest(item=item):
                self.assertIn(item, PREP, f"反问清单里没有「{item}」")

    def test_the_two_places_point_at_each_other(self):
        """两处各写一份必然分叉 —— 至少要互相指得到，改一处时看得见另一处。"""
        self.assertIn("job-offer.md", PREP, "反问那边没指向 offer 那道关")

    def test_the_statutory_floor_is_stated_not_guessed(self):
        """试用期工资的法定下限是 80% —— 说不出这个数，这一条就只是「记得问一下」。"""
        self.assertRegex(OFFER, r"不得低于转正工资的\s*80%|转正工资的\s*80%",
                         "没写出试用期工资的法定下限")

    def test_why_base_salary_matters_is_spelled_out(self):
        """只说「基本工资占比」没用 —— 要说清它牵着哪几项法定权益。"""
        # 定位到 Step 4 那个清单项，不是 Step 3 的那句提醒 —— 后者在文件里更靠前，
        # 拿 `index` 取到的是它，而理由写在清单项里。
        seg = OFFER[OFFER.index("基本工资占薪资总额"):][:500]
        for w in ("加班费", "经济补偿金"):
            self.assertIn(w, seg, f"没说清基本工资牵着「{w}」")


class TheTimingIsPartOfTheAdvice(unittest.TestCase):
    def test_it_says_which_round_to_ask_in(self):
        """在专业面问公积金和在 HR 面问，是两回事。"""
        self.assertRegex(PREP, r"只在 HR 那一轮问|只在 HR 面问",
                         "没说这几条该在哪一轮问")

    def test_it_warns_against_asking_too_late(self):
        """等 offer 下来再问，筹码已经没了。"""
        self.assertRegex(PREP, r"等 offer 下来再问就晚了|没有筹码",
                         "没说清为什么不能等到 offer 阶段")

    def test_it_warns_against_firing_all_four_at_once(self):
        """反问只有几分钟，连抛四个待遇问题传递的信号是「只关心钱」。"""
        self.assertRegex(PREP, r"别摆成一张清单|一次问一两条",
                         "没提醒别把待遇问题一次全抛出去")


if __name__ == "__main__":
    unittest.main()
