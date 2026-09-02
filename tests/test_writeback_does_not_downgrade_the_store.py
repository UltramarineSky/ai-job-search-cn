# -*- coding: utf-8 -*-
"""硬门判词在存档里是四个字，在库里带门名 —— 那不是漂移。

`build_dashboard.parse_evaluation` 对硬门 FAIL **只返回「硬门 FAIL」四个字**，
它自己的注释写着理由：

> 门名要 `parse_gates`（在导出器里，反向依赖会成环），所以这里只给到
> 「硬门 FAIL」四个字；**带门名的完整写法由 `resolve_score` 从库里补**。

也就是说**存档那一侧本来就不带门名，库才带**。而 `writeback` 原来拿整串比，
于是每一个带门名的硬门判词都被报成「漂移」，`--apply` 会拿存档的四个字
**覆盖**库里「硬门 FAIL (候选人明确排除（行业背景硬要求）)」这种完整写法。

**把更全的信息降级成更少的** —— 而这个仓库刚花了一整轮把那些门名和理由补上
（`name_the_exclusion.py` 一次补了 94 个）。2026-08-30 某连锁餐饮公司那份 JD
（同一份挂了四处）读全后一次翻案 4 个岗时撞见：writeback 当场要把刚写进去的
「（行业背景硬要求）」抹掉。
"""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import writeback as wb  # noqa: E402


class TwoGateFailsAreNotADrift(unittest.TestCase):
    def test_the_store_may_be_richer(self):
        self.assertFalse(wb._verdict_moved(
            "硬门 FAIL (候选人明确排除（行业背景硬要求）)", "不满足硬性条件"))

    def test_either_spelling_counts(self):
        for a in ("硬门 FAIL", "硬门FAIL", "不满足硬性条件", "硬门 FAIL (学历与院校)"):
            for b in ("硬门 FAIL", "不满足硬性条件"):
                with self.subTest(a=a, b=b):
                    self.assertFalse(wb._verdict_moved(a, b))

    def test_the_triage_prefix_is_still_not_a_drift(self):
        self.assertFalse(wb._verdict_moved("粗筛：值得投", "值得投"))


class ARealMoveStillReports(unittest.TestCase):
    def test_a_band_to_a_gate_fail(self):
        self.assertTrue(wb._verdict_moved("值得投", "硬门 FAIL"))

    def test_a_gate_fail_to_a_band(self):
        self.assertTrue(wb._verdict_moved("硬门 FAIL (学历)", "值得投"))

    def test_band_to_band(self):
        self.assertTrue(wb._verdict_moved("值得投", "可以考虑"))

    def test_nothing_in_the_store_yet(self):
        self.assertTrue(wb._verdict_moved(None, "值得投"))


class TheReasonIsRecordedWhereItBroke(unittest.TestCase):
    def test_it_says_who_holds_the_richer_form(self):
        doc = wb._verdict_moved.__doc__ or ""
        self.assertIn("存档那一侧本来就不带门名", doc)
        self.assertIn("降级", doc)


if __name__ == "__main__":
    unittest.main()
