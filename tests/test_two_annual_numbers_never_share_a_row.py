# -*- coding: utf-8 -*-
"""同一个岗的年包被算两遍，而两个数并排显示在同一行上。

年包在这个仓库里有两个算法，**各自都对**：

| 算的人 | 未标薪数时 | 为什么 |
|---|---|---|
| `prescreen.annual_high_wan` | 按最乐观的 16 薪 | 用途是**淘汰**，误杀的代价是一个好岗静默消失 |
| `export_web_data.annual_package` | 按 12 薪保守折 | 用途是**显示**，吹高了是在骗自己 |

分歧本身是设计。出事的是它们**同屏**：`Shortlist.tsx` 搁置区那一行先渲染
`annual`，同一行的 `.shelf-why` 再渲染预筛存下的结案理由。

实测（2026-08-26）：178 个岗的那一行字面读作

    … · 30-33.6万　年包上沿约 45 万，低于底线 45 万（原文：25-28k，未标薪数…）

同一个岗两个年包，而「按 12 薪保守算」那句说明只在悬浮提示里。
`rule_annual` 自己的注释早就判过这个形状的死刑 ——「理由自己打自己的时候，
用户没有办法判断是数据错了还是工具错了」—— 那次说的是取整撞车（11 条），
这次是跨模块口径撞车（178 条），同一类，规模大 16 倍。

修法不是统一口径（那会让淘汰变激进、或让显示变虚高），而是让未标薪数那一支
**说成条件句**：并排读作「就算按最乐观的算法也不够」，而不是第二个年包。

## 这里钉两半

- 未标薪数那一支不以断言语气给年包（下面第一组）
- **标了薪数时两边必须算得一样**（第二组）—— 那是「分歧只许出在假设上」的
  全部依据。任一侧的解析改动一旦让它们在有确切薪数时也分叉，两个数就会
  在同一行上打架，而且那次连「按最乐观估」这句遮羞布都没有。
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import export_web_data as ex  # noqa: E402
import prescreen  # noqa: E402

ROW = (ROOT / "web" / "src" / "components" / "Shortlist.tsx").read_text(encoding="utf-8")


class TheAssumedBranchDoesNotAssertAnAnnualFigure(unittest.TestCase):
    CASES = ["25-28k", "15-25k", "4-5k", "15-18k"]

    def test_the_optimistic_estimate_actually_spares_jobs(self):
        """`1.5-3万` 按 12 薪是 36 万、按 16 薪是 48 万 —— 这条 docstring 里的
        原例就是「按 12 薪会误杀」。它在 45 万底线下必须**活着**，
        否则上面那一支的措辞再讲究也没有意义。"""
        self.assertIsNone(prescreen.rule_annual({"salary": "1.5-3万"}, 45.0))

    def test_it_leads_with_the_assumption(self):
        for sal in self.CASES:
            with self.subTest(salary=sal):
                why = prescreen.rule_annual({"salary": sal}, 45.0)
                self.assertIsNotNone(why, f"{sal} 本该被 45 万底线判掉")
                self.assertTrue(why.startswith("未标薪数"),
                                f"以断言语气开头，会被读成第二个年包：{why}")

    def test_it_still_names_the_assumed_months(self):
        why = prescreen.rule_annual({"salary": "15-25k"}, 45.0)
        self.assertIn(f"{prescreen.OPTIMISTIC_MONTHS} 薪", why,
                      "没说按几薪估 —— 那这个数就无从解释")

    def test_a_stated_month_count_keeps_the_plain_wording(self):
        """薪数写明了就没有假设可言，这一支照旧直述。"""
        why = prescreen.rule_annual({"salary": "20-25k", "salaryMonths": 13}, 42.0)
        self.assertTrue(why.startswith("年包上沿约"), why)
        self.assertNotIn("未标薪数", why)


class BothNumbersReallyShareARow(unittest.TestCase):
    """这不是推测出来的：搁置区那一行的 JSX 里两者都在。"""

    def test_the_row_renders_the_annual(self):
        self.assertIn("job.annual.low}-${job.annual.high}万", ROW)

    def test_the_same_row_renders_the_reason(self):
        self.assertIn('className="shelf-why"', ROW)
        self.assertIn("job.skipReason", ROW)


class WithStatedMonthsTheTwoSidesAgree(unittest.TestCase):
    """跨模块不变量：薪数确切时，淘汰用的数和显示用的数必须是同一个。"""

    CASES = [
        ("20-25k", 13), ("25-28k", 16), ("40-70k", 16), ("15-30k", 14),
        ("30-35k", 15), ("8-12k", 12), ("3.5-5万", 14),
    ]

    def test_they_compute_the_same_upper_bound(self):
        for sal, months in self.CASES:
            with self.subTest(salary=sal, months=months):
                hi, assumed = prescreen.annual_high_wan({"salary": sal,
                                                         "salaryMonths": months})
                ap = ex.annual_package(sal, months)
                self.assertFalse(assumed, "薪数是给了的，不该走假设那一支")
                self.assertIsNotNone(ap, f"显示侧算不出 {sal}·{months}薪")
                self.assertAlmostEqual(
                    hi, ap["high"], places=1,
                    msg=f"{sal}·{months}薪：淘汰按 {hi} 万、显示按 {ap['high']} 万——"
                        f"两个数会并排出现在搁置区同一行上")

    def test_only_the_unstated_case_may_diverge(self):
        hi, assumed = prescreen.annual_high_wan({"salary": "25-28k"})
        ap = ex.annual_package("25-28k", None)
        self.assertTrue(assumed)
        self.assertTrue(ap["assumed12"])
        self.assertGreater(hi, ap["high"],
                           "淘汰那侧本该更乐观（16 薪 > 12 薪）——反了就是在误杀")


if __name__ == "__main__":
    unittest.main()
