# -*- coding: utf-8 -*-
"""「年包上沿约 45 万，低于底线 45 万」——一条有结案权的规则，理由自己打自己。

`rule_annual` 判掉一个岗就进搁置区（`粗筛：跳过`），而它给的理由被存进
`rank_breakdown.依据`、原样显示在面板上。两个数都取整到万之后，
28k × 16 薪 = 44.8 万 撞上 45 万底线，印出来是同一个「45」：

    [粗筛：跳过] 算法开发与应用工程师   年包上沿约 45 万，低于底线 45 万（…）

**理由自相矛盾时，用户没有办法判断是数据错了还是工具错了。**
实测活动用户 2026-08-23：这条规则判掉的 635 个里 11 个这样，
库里已经存着 9 条（那批不迁移 —— 9 个悬浮提示不值得为它写一次带备份的写盘，
代码修好之后新判的不会再有）。

**只在撞上时补一位小数。** 1.7% 的情形不该让所有人都多看一个小数点。

顺带记下**没有**做的两件事：

- **没有动淘汰线。** 那 11 个都在 1 万以内，看着像该放过；但
  `OPTIMISTIC_MONTHS` 那段 docstring 已经把召回与抓取额度两边都称过一次
  （抬到 24 薪要多花约四天额度），而搁置区有「放回可以投」的按钮。
  1.7% 不构成重称的理由。
- **没有加容差。** 同上，而且 `test_one_file_one_tolerance` 盯着容差扩散。
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import prescreen as ps  # noqa: E402

#: 把理由里那两个数抠出来。**认两种句式**：薪数写明了就直述
#: 「年包上沿约 X 万，低于底线 Y 万」；未标薪数那一支说成条件句
#: 「未标薪数：按最乐观的 16 薪估，上沿也只有 X 万，仍低于底线 Y 万」
#: —— 因为面板薪资栏按 12 薪保守折，断言语气会被读成第二个年包
#: （2026-08-26，见 `test_two_annual_numbers_never_share_a_row.py`）。
#:
#: **这里钉的是「两个数不许印成一样」，不是某一种措辞。** 原来这条正则写死了
#: 前一种句式，于是措辞一改它就红 —— 而它要验的那件事其实分毫未变。
#: 守卫钉实现形状而不是行为，本仓库为此栽过好几次。
_TWO = re.compile(r"上沿[^\d]{0,12}([\d.]+) 万[^\d]{0,8}底线 ([\d.]+) 万")


def _reason(salary, months, floor):
    return ps.rule_annual({"salary": salary, "salaryMonths": months}, floor)


class TheTwoNumbersAreNeverThePrintedSame(unittest.TestCase):
    def test_the_borderline_case_shows_the_decimal(self):
        """28k × 16 薪 = 44.8 万。取整到万就和 45 撞上。"""
        r = _reason("15-28k", None, 45.0)
        self.assertIsNotNone(r, "这个岗本来就该被判掉")
        m = _TWO.search(r)
        self.assertIsNotNone(m, f"理由的写法变了：{r}")
        self.assertNotEqual(m.group(1), m.group(2),
                            f"两个数印成一样了：{r}")
        self.assertEqual(m.group(1), "44.8")

    def test_an_ordinary_case_keeps_whole_numbers(self):
        """1.7% 的情形不该让所有人都多看一个小数点。"""
        r = _reason("15-30k", 14, 45.0)
        m = _TWO.search(r)
        self.assertNotIn(".", m.group(1), f"平时也印小数了：{r}")
        self.assertNotIn(".", m.group(2))

    def test_it_holds_across_a_sweep(self):
        """扫一遍会撞的组合 —— 单挑一个例子挡不住下一次取整撞车。"""
        for k in range(20, 40):
            for months in (12, 13, 14, 15, 16):
                floor = round(k * months / 10 + 0.2, 1)
                r = _reason(f"10-{k}k", months, floor)
                if not r:
                    continue
                m = _TWO.search(r)
                with self.subTest(salary=f"{k}k", months=months, floor=floor):
                    self.assertIsNotNone(m, r)
                    self.assertNotEqual(m.group(1), m.group(2), r)

    def test_the_rule_itself_did_not_move(self):
        """**只改印法，不改判法。** 判据仍是「上沿够不着底线」，
        一分钱都不放宽 —— 那条线有过完整的敏感度分析。"""
        self.assertIsNone(_reason("15-28k", None, 44.8),
                          "上沿正好等于底线时不该判掉")
        self.assertIsNotNone(_reason("15-28k", None, 44.9),
                             "差一点也是够不着，判掉是对的")

    def test_the_assumption_is_still_disclosed(self):
        """未标薪数时那句「按最乐观的 N 薪估都不够」不许被顺手弄丢 ——
        它是这条结案的前提，读的人要能看见它是估的。"""
        r = _reason("15-28k", None, 45.0)
        self.assertIn("未标薪数", r)
        self.assertIn(str(ps.OPTIMISTIC_MONTHS), r)

    def test_the_reason_is_what_reaches_the_panel(self):
        """这句话不是终端里一闪而过的字：它进 `rank_breakdown.依据`，
        面板逐行显示。改它的写法要知道有人在读。"""
        src = (ROOT / "tools" / "prescreen.py").read_text(encoding="utf-8")
        i = src.index("def rule_annual(")
        self.assertRegex(src[i:i + 1600], r"依据|面板",
                         "没写清这句话会流到哪儿")


class TheDecisionsNotTakenAreWrittenDown(unittest.TestCase):
    """看着像该顺手改的两件事，都有不改的理由 —— 不写下来，
    下一个人会把它们当遗漏补上。"""

    def _seg(self):
        src = (ROOT / "tools" / "prescreen.py").read_text(encoding="utf-8")
        i = src.index("def rule_annual(")
        return src[i:i + 1600]

    def test_no_tolerance_was_added(self):
        seg = self._seg()
        self.assertNotRegex(seg, r"high \+ [\d.]+ >=|floor_wan - [\d.]+",
                            "偷偷加了容差 —— 那要过 test_one_file_one_tolerance")

    def test_the_sensitivity_analysis_is_still_there(self):
        """`OPTIMISTIC_MONTHS` 那段把召回与抓取额度都称过一次。
        它是「不动这条线」的全部依据，删了就没人知道为什么是 16。"""
        src = (ROOT / "tools" / "prescreen.py").read_text(encoding="utf-8")
        i = src.index("OPTIMISTIC_MONTHS = ")
        seg = src[max(0, i - 2000):i + 3000]
        # **按「那句话在不在」验，不按「关键词出现过没有」验。**
        # 「百分位」「额度」在这段里各出现两次（推算那句、限流那句），
        # 删掉第一处照样绿 —— 变异实测漏过一次。
        self.assertRegex(seg, r"超过 16 薪的只有 [\d.]+%",
                         "16 是怎么定的没了")
        self.assertRegex(seg, r"第 \d+ 百分位", "分布结论没了")
        self.assertRegex(seg, r"抬到 24.*额度", "成本那一侧没了")


if __name__ == "__main__":
    unittest.main()
