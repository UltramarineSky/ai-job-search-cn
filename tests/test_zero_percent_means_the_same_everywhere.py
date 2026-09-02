# -*- coding: utf-8 -*-
"""「有回音 0%」这个数，在哪一处都得按同一条规矩显示。

总览页早就有这条（`export_web_data.too_early`）：**一个回音都没有、而「还在等」的
超过总数一半 → 不给这个率，显示「还没有」。** 理由记在那段注释里：

> 实测 2026-08-21：85 个投出去、66 个还在等（中位已等 9 天，静默线 10 天）。
> 印一个大号「有回音 0%」，读者看到的是「市场把你全拒了」，
> 而实际是近八成还没到该回的时候。

**而 `/job-html-report` 算同一个率，没有这条规矩** —— 同一个人、同一批数据，
打开总览页看到「还没有」，导出报表看到「0%」。

顺带还有一处：报表自己的「分母为零不写 0%」写在 Step 2，**而结论印在 Step 4 的
小结模板里，那里没有这条**。规矩写在一处、印在另一处，用户信的是印出来的那一行。
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import export_web_data as X  # noqa: E402

RPT = (ROOT / "workflows" / "job-html-report.md").read_text(encoding="utf-8")


class TheReportKnowsTheRule(unittest.TestCase):
    def test_it_covers_the_still_waiting_case(self):
        self.assertRegex(RPT, r"多数还在等待窗口内",
                         "报表没有「还没到时候」这条规矩")

    def test_it_says_the_two_cases_are_different(self):
        """「没有分母」和「分母有但还没到时候」是两件事，合并会漏掉后者。"""
        self.assertRegex(RPT, r"上一条是「没有分母」|治的\s*\n?不是一件事",
                         "没说清这两条治的不是一件事")

    def test_the_threshold_is_a_majority_not_any(self):
        """写成「有一个在等就藏」的话，199 个已读不回也会被吞掉。"""
        self.assertRegex(RPT, r"不是「有一个在等」", "没挡住把判据放宽成「有就藏」")

    def test_it_does_not_define_its_own_silence_line(self):
        """静默线只有一个出处，报表里不许另定一个数。"""
        self.assertIn("followups.QUIET_DAYS", RPT, "没指向静默线的正本")
        seg = RPT[RPT.index("多数还在等待窗口内"):][:900]
        self.assertNotRegex(seg, r"\b(7|14|30)\s*天", "报表里另写了一个静默天数")


class TheSummaryLineObeysItToo(unittest.TestCase):
    def test_the_step4_template_repeats_the_rule(self):
        """规矩写在 Step 2、结论印在 Step 4 —— 用户信的是印出来的那一行。"""
        i = RPT.index("## Step 4")
        seg = RPT[i:]
        self.assertIn("过了简历关的占", seg, "小结模板里那一行不见了")
        self.assertRegex(seg, r"不写\s*`0%`", "小结那一行没带上这条规矩")


class ThePanelStillHasIt(unittest.TestCase):
    """判据的前提。总览页那条没了，上面几条就成了单方面的规矩。"""

    def test_the_panel_rule_exists(self):
        src = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        self.assertIn("too_early", src)
        self.assertRegex(src, r'buckets\["还在等"\] > total \* TOO_EARLY_SHARE',
                         "总览页的判据从「多数」变回「有就算」了")

    def test_the_share_is_a_majority(self):
        self.assertGreaterEqual(X.TOO_EARLY_SHARE, 0.5)


if __name__ == "__main__":
    unittest.main()
