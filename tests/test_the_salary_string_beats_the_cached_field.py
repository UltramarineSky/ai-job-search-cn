# -*- coding: utf-8 -*-
"""薪资串里的「N 薪」压过 `salaryMonths` 字段 —— 串是事实，字段只是缓存。

## 为什么要钉这个次序

实测活动用户 2026-08-30：1831 个有薪资串的岗里 **11 个**串里明写着
`·15薪` / `·18薪`，而 `salaryMonths` 是空的。

那**看起来像一个很贵的 bug**：几薪未知时 `annual_package` 按 12 薪保守折，
15 薪当 12 薪算就低估 25%，18 薪低估 50% —— 足以把一个岗压到薪资底线以下、
被预筛结案。顺着这个念头去「修」，最直觉的改法是「先读字段、字段空了再看串」，
或者写个回填把字段补上。

**两种都会把事情弄坏**，因为实情是：三个消费者
（薪资维 `scoring.pay_dim`、预筛 `prescreen`、面板薪资栏）**全都走
`annual_package`**，而它自己读串。那 11 个的年包、分数、档位一直都是对的。

字段是抓取那一刻记下的，串是页面上写的；两者不一致时对的是后者。
**把缓存放到事实前面，才是真的引入 bug。**

## 这条守的是次序，不是那 11 个

那 11 个不需要修。这条钉住的是：串 > 字段 > 12 薪保守估。
"""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import export_web_data as ex  # noqa: E402


class TheStringWins(unittest.TestCase):
    def test_the_string_beats_a_disagreeing_field(self):
        """串写 15 薪、字段说 12 —— 按 15 算。"""
        got = ex.annual_package("40-70K·15薪", 12)
        self.assertEqual((got["low"], got["high"]), (60.0, 105.0))
        self.assertFalse(got["assumed12"])

    def test_the_string_alone_is_enough(self):
        """字段为 `None` 不影响结果 —— 那 11 个岗就是这个形状。"""
        self.assertEqual(ex.annual_package("40-70K·15薪", None),
                         ex.annual_package("40-70K·15薪", 15))


class TheFieldFillsInWhenTheStringIsSilent(unittest.TestCase):
    def test_field_used_when_the_string_says_nothing(self):
        got = ex.annual_package("40-70K", 15)
        self.assertEqual((got["low"], got["high"]), (60.0, 105.0))
        self.assertFalse(got["assumed12"])

    def test_twelve_is_the_conservative_fallback(self):
        """两边都没有 → 按 12 薪保守折，并标出来让页面说明。"""
        got = ex.annual_package("40-70K", None)
        self.assertEqual((got["low"], got["high"]), (48.0, 84.0))
        self.assertTrue(got["assumed12"],
                        "假设了 12 薪却不标 —— 页面就会把估算说成事实")


class EveryConsumerGoesThroughIt(unittest.TestCase):
    """**没有第二份折算。** 有第二份，那 11 个就真会被低估。"""

    def test_the_pay_dimension_delegates(self):
        src = (ROOT / "tools" / "scoring.py").read_text(encoding="utf-8")
        self.assertIn("annual_package", src)

    def test_prescreen_delegates(self):
        src = (ROOT / "tools" / "prescreen.py").read_text(encoding="utf-8")
        self.assertIn("annual_package", src)
        self.assertIn("不写第二份", src)

    def test_the_order_is_written_down(self):
        """写下来才拦得住下一个人「先读字段」。"""
        src = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        i = src.index("def annual_package(")
        seg = " ".join(src[i:i + 2600].split())
        self.assertIn("薪资串里的「N 薪」 > `months` 参数 > 12 薪保守估", seg)
        self.assertIn("别去「修」成先看字段", seg)


if __name__ == "__main__":
    unittest.main()
