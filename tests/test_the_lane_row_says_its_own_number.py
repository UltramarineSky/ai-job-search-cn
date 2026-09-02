# -*- coding: utf-8 -*-
"""通道那一行印的必须是**这条通道**的数，不是它全家的。

## 这一条从哪来

`--round` 那张单子每行前缀是**通道**（`liepin-browser`），而 `check()` 回的
那句主语是**家**（「猎聘 今天已发 1 次」）。句子没错，位置让人误读。

实测 2026-08-30：`猎聘.actions` 今天只有一条 `00:37:07`，那是 **CLI 撞限流的
那次请求**；而单子上 `liepin-browser` 那行照样印着「今天已发 1 次」。
同一份输出下面两行才写「一家的主通道被挡住 ≠ 这一轮没有这家」——
**工具自己先请出了它要警告的那个误读。**

而那个误读正是这条规则连着犯的那个错：写在四处（`AGENTS.md`、
`job-scrape.md` Step 0.4、`portal_budget` 的 `SLOW_GAP_FACTOR` 那段、
`--check` 的回话），2026-08-25 用户当场纠正过一次，08-27、08-30 又各来一次。

## 两个粒度都要留着

`actions` 按**家**记是对的 —— 限流按 IP / 站点来。`query_log` 按**通道**记
也是对的 —— 「这一轮浏览器那条接上了没有」只有它答得了。
错的不是任何一份，是**拿一份去回答另一份的问题**。
"""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
from _srcscan import code_of  # noqa: E402
import portal_budget as pb  # noqa: E402

DAY = "2026-08-30"
FAM = {"猎聘": {"actions": [DAY + "T00:37:07"]}}


class TheClauseAppearsOnlyWhenItMisleads(unittest.TestCase):

    def test_lane_zero_family_nonzero_is_called_out(self):
        """这一种就是 2026-08-30 那次 —— 必须说破。"""
        out = pb._own_count("liepin-browser", "猎聘", {}, FAM, DAY)
        self.assertIn("这条通道今天一次查询都没跑", out)
        self.assertIn("全家", out)

    def test_both_zero_says_nothing(self):
        """`check()` 已经说了「还没动过」，再补一句是噪音。"""
        self.assertEqual(pb._own_count("boss-browser", "BOSS", {}, {}, DAY), "")

    def test_a_lane_that_ran_says_so(self):
        out = pb._own_count("liepin-browser", "猎聘", {"liepin-browser": 3},
                            FAM, DAY)
        self.assertIn("跑过 3 次", out)
        self.assertNotIn("全家", out)

    def test_yesterdays_family_action_does_not_count(self):
        """按天切 —— 昨天那次不该让今天这一行说话。"""
        old = {"猎聘": {"actions": ["2026-08-29T10:00:00"]}}
        self.assertEqual(pb._own_count("liepin-browser", "猎聘", {}, old, DAY), "")


class TheBlockedLaneIsLeftAlone(unittest.TestCase):
    """被封的那条上，那半句既是噪音又是错的。

    全家今天那一次动作**恰恰就是它自己**（撞限流的那次请求 —— 没返回结果，
    所以 `query_log` 里没有它），而那半句会说成「落在另一条上」。
    第一版就是这么印的。
    """

    def test_round_plan_gates_on_runnable(self):
        seg = code_of("tools/portal_budget.py", "def round_plan(")
        self.assertIn("if ok else", seg,
                      "被封的通道也被贴上了那半句 —— 在那一行它是错的")


class TheTwoRecordsKeepTheirOwnJobs(unittest.TestCase):

    def test_the_lane_counter_reads_the_lane_record(self):
        """通道数只能来自 `query_log`；`actions` 里没有通道这一维。"""
        seg = code_of("tools/portal_budget.py", "def _lane_runs(")
        self.assertIn("query_log", seg)
        self.assertNotIn("actions", seg)

    def test_the_family_counter_still_reads_actions(self):
        seg = code_of("tools/portal_budget.py", "def _own_count(")
        self.assertIn('"actions"', seg)

    def test_a_broken_log_does_not_break_the_round(self):
        """读不出就当没有 —— 一张单子不该因为日志坏了整个印不出来。"""
        self.assertEqual(pb._lane_runs("不存在的用户", DAY), {})


if __name__ == "__main__":
    unittest.main()
