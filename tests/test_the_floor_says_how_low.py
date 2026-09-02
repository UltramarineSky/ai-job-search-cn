# -*- coding: utf-8 -*-
"""「按 12 薪保守算」要说清保守到什么程度。

平台只在薪数 >12 时才标 `·N薪`（那是卖点），没标的按 12 折 —— **保守是对的，
宁可低不可高**。但此前没有任何地方说得出来低多少。

实测活动用户 2026-08-22：

    有薪资的岗            2554
    其中没写薪数的        1162（45%）
    明写薪数的            1346 —— **12 薪出现 0 次**，从 13 起，中位 15

薪资维占 25% 权重，实测薪数未知那批的中位分比已知那批低 4 分（51 对 55）。
不给参照的话，「保守算」听起来像「差不多」，而它大概率低两三成。

**不拿这个数去改折算** —— 那会把保守估变成猜测，而且这批样本本身有选择偏差
（肯标薪数的多半就是高的那些）。只在悬浮说明里给一句参照。

**从他自己的库里现算，不写死** —— 各行各业的薪数惯例差得远（互联网 15、
外企 13、部分制造 12），写死一个就成了行业预设。
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import _cli  # noqa: E402
import export_web_data as X  # noqa: E402

SL = (ROOT / "web" / "src" / "components"
      / "Shortlist.tsx").read_text(encoding="utf-8")


def _jobs(months):
    return [{"salary": f"30-60k·{m}薪"} for m in months]


class TheReferenceComesFromHisOwnData(unittest.TestCase):
    def test_it_is_the_median_of_what_is_stated(self):
        self.assertEqual(X.observed_months(_jobs([13] * 20 + [15] * 20)), 15)

    def test_a_thin_sample_says_nothing(self):
        """不足 30 个就闭嘴 —— 拿 5 个岗算出来的中位去当参照只会误导。"""
        self.assertIsNone(X.observed_months(_jobs([15] * 10)))

    def test_jobs_without_a_stated_month_are_skipped(self):
        """没写薪数的正是要参照的那批，把它们算进来就成了自证。"""
        js = _jobs([15] * 30) + [{"salary": "30-60k"}] * 50
        self.assertEqual(X.observed_months(js), 15)

    def test_insane_values_are_dropped_via_the_single_source(self):
        """30 薪这种平台噪音不参与 —— 合理区间只有一个出处。"""
        js = _jobs([15] * 30 + [30] * 30)
        self.assertLessEqual(X.observed_months(js), _cli.SALARY_MONTHS_SANE[1])
        src = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        seg = src[src.index("def observed_months("):]
        seg = seg[:seg.index("\ndef ", 1)]
        self.assertIn("_cli.SALARY_MONTHS_SANE", seg, "区间被抄了一份")


class TheTooltipUsesItWithoutChangingTheMath(unittest.TestCase):
    def test_the_tooltip_names_the_reference(self):
        self.assertIn("observedMonths", SL, "悬浮说明没接上这个参照")
        self.assertRegex(SL, r"真实数多半比这里显示的高",
                         "没说清这个地板价偏在哪一边")

    def test_it_falls_back_to_the_bare_sentence(self):
        """样本不足时不许硬凑一个数 —— 退回原来那句就好。"""
        # 这个表达式在文件里有两处（一处在注释里解释它、一处是 `data-assumed`）。
        # 要的是「样本不足就退回原话」那一支，锚它自己那句话。
        i = SL.index("平台只给了月薪、没写几薪")
        seg = SL[max(0, i - 700):i + 700]
        self.assertIn(": \"平台只给了月薪、没写几薪，这里按 12 薪保守算。\"", seg,
                      "没有「算不出参照时」的那一支")

    def test_the_conversion_still_uses_twelve(self):
        """参照只是说明，**不许拿它去折算** —— 那会把保守估变成猜测。"""
        src = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        i = src.index("def annual_package(")
        seg = src[i:i + 4000]
        self.assertNotIn("observed_months", seg, "折算里用上了这个参照")


if __name__ == "__main__":
    unittest.main()
