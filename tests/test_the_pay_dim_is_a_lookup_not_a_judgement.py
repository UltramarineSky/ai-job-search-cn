# -*- coding: utf-8 -*-
"""薪资那一维是查表，不是打分——而 32% 的岗上写的是别的数。

`04-job-evaluation.md`「打分口径：比的是够不够」给的是一张四行的查表：
年包**下沿**到顶 90 / 落在期望区间 85 / 低于期望但过底线 55 / 低于底线 25。
输入只有 `salary` + `salaryMonths` + 资料里的两个数，**没有判断余地**——
它是四维里唯一能被机器完整验算的一维。

旁边此前有两条检查，各守一个特例（`check_negotiable_salary_is_not_scored`
守面议不该打分、`check_unknown_months_is_not_a_death_sentence` 守没标薪数
不该被埋），**主表本身没人守**。

实测 2026-08-27：全库 763 个填了薪资维的岗，**247 个（32%）对不上**，
其中 146 个取的是表上根本没有的值（70、72、75、80…… 一整条连续刻度）。
本会话自己也犯了另一种：`20-40K·15薪` 的下沿 30 万低于 45 万底线，
写的却是 55，附一句「门槛低说明定级弹性大」——04 早给这句话起过名字，
叫「折算一个中性值」，那一节的标题就是**别走第三条路**。

薪资维占 25% 权重，一档之差是综合分 7.5 分，足以翻一整档判词。
"""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import audit_pipeline as ap  # noqa: E402

FLOOR, EXPECT = 45.0, (72.0, 96.0)


def dim(salary, months=None):
    return ap._pay_dim_should_be({"salary": salary, "salaryMonths": months},
                                 FLOOR, EXPECT)


class TheTableHasFourRowsAndOnlyFour(unittest.TestCase):
    CASES = [
        # (薪资串, 薪数, 该给几分, 为什么)
        ("80-110K", None, 90, "按 12 薪下沿 96 万，正好顶到期望上沿"),
        ("50-80K", 16, 85, "下沿 80 万落在 72-96 万里"),
        ("60-90K", 15, 85, "下沿 90 万，还在区间内——没到顶就不是 90"),
        ("40-70K", 16, 55, "下沿 64 万，低于期望下沿、高于底线"),
        ("30-60K", 16, 55, "下沿 48 万"),
        ("20-40K", 15, 25, "下沿 30 万，低于 45 万底线"),
        ("20-35k·14薪", 14, 25, "下沿 28 万"),
        ("35-55k", None, 55, "12 薪下沿 42 万够不着，16 薪 56 万够得着 → 55"),
        ("25-50k", None, 25, "12 薪 30 万、16 薪 40 万都够不着底线 → 才给 25"),
    ]

    def test_each_case_lands_on_its_row(self):
        for salary, months, want, why in self.CASES:
            with self.subTest(salary=salary, why=why):
                self.assertEqual(dim(salary, months), want, why)

    def test_nothing_ever_lands_between_the_rows(self):
        """**这才是当初露出来的那一头。** 70、72、75、80 这些数不该出得来。"""
        allowed = {ap._PAY_TOP, ap._PAY_IN, ap._PAY_OK, ap._MONTHS_LOW}
        for lo in range(5, 200, 3):
            for months in (None, 12, 13, 14, 15, 16):
                got = dim(f"{lo}-{lo * 2}k", months)
                with self.subTest(salary=f"{lo}-{lo*2}k", months=months):
                    self.assertIn(got, allowed, f"{got} 不在那张表上")

    def test_it_compares_the_low_edge_not_the_high_one(self):
        """上沿是给最理想候选人的，拿它打分等于按最好情况算。

        `20-100k·16薪` 的上沿 192 万远超期望，下沿只有 32 万——按下沿是 25。
        """
        self.assertEqual(dim("20-100k·16薪", 16), 25)

    def test_negotiable_is_left_to_the_other_check(self):
        """面议归 `check_negotiable_salary_is_not_scored`，这里返回 None。"""
        for s in ("薪资面议", "面议", "另议", ""):
            with self.subTest(salary=s):
                self.assertIsNone(dim(s))


class TheCheckReadsTheNumbersFromTheProfile(unittest.TestCase):
    """底线与期望**从资料里读**，不写死在工具里。

    读不出就如实说没查——「没查」和「查过没有」是两件事，这条仓库规矩
    在 `_annual_floor` / `_candidate_years` 上已经执行了两次。
    """

    def test_it_says_so_instead_of_guessing(self):
        old = list(ap._USER)
        try:
            ap._USER[:] = ["查无此人"]
            out = ap.check_pay_dim_matches_its_own_number({}, {})
        finally:
            ap._USER[:] = old
        self.assertEqual(len(out), 1)
        self.assertIn("没查", out[0][1])

    def test_the_expected_range_parses_from_the_active_profile(self):
        p = ROOT / ".active_user"
        if not p.is_file():
            self.skipTest("没有活动用户")
        user = p.read_text(encoding="utf-8").strip()
        if not (ROOT / "users" / user / "profile" / "candidate.md").is_file():
            self.skipTest("活动用户还没建档")
        old = list(ap._USER)
        try:
            ap._USER[:] = [user]
            got = ap._annual_expect()
        finally:
            ap._USER[:] = old
        self.assertIsNotNone(got, "「期望区间」那一行里读不出年包数")
        self.assertLess(got[0], got[1])
        self.assertGreater(got[0], 0)


class ItIsWiredIntoTheAudit(unittest.TestCase):
    def test_the_check_is_registered(self):
        self.assertIn(ap.check_pay_dim_matches_its_own_number,
                      [fn for _, fn in ap.CHECKS])

    def test_it_does_not_print_markdown(self):
        """终端输出不带标记——同 `check_negotiable_salary_is_not_scored` 那条注释。"""
        fn = ap.check_pay_dim_matches_its_own_number
        # 文档字符串是给读代码的人看的，带标记没问题；印出去的是别的常量。
        for const in fn.__code__.co_consts:
            if not isinstance(const, str) or const == fn.__doc__:
                continue
            if "**" in const:
                self.fail(f"消息里带了 markdown：{const[:60]}")


if __name__ == "__main__":
    unittest.main()
