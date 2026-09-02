# -*- coding: utf-8 -*-
"""自检报对了一件事，却把原因说反了。

`check_out_records_carry_their_own_date` 报的是「出局的岗，日期没记在自己那条
路的键上」（`skipped` → `skip_date`、`expired` → `expired_date`）。事实成立。
但它给的后果是：

    归档算这条出局多久时会退到「抓到它的日子」—— 比出局早得多，于是它被提前埋掉

**对着代码是错的，而且它举的头一个例子恰好就是错的那一类。**
`archive._age_days` 取的是这几个日期里**最晚**的一个：

    [叠加层 date, skip_date, expired_date, rank_date, first_seen]

所以「记在另一条键上」照样被读到，归档一点不受影响。实测那条错键的岗
（`skipped` 却记着 `expired_date=2026-08-13`）算出 13 天，门槛 30 天，
离归档还远。真正会退的是「两条都没记」，而且退到的是
`max(rank_date, first_seen)`，通常是评分那天，不是抓到那天。

## 为什么一条说错原因的自检比不报更糟

用户读的是那句解释。按「会被提前埋掉」去理解，他会以为数据有丢失风险、
要赶紧处理；而真正的代价是**搁置区那一行不显示日期** ——
`_decision_date` 对 `skipped` 只读 `skip_date`，于是那行只剩「你排除的」。
`Shortlist.tsx` 自己写着这为什么要紧：「两周后回看会想不起当初为什么，
那个『当初』是几号，正是判断这条结论还作不作数的依据」。

本仓库对「理由自己打自己」判过死刑（`rule_annual` 那段注释）。理由**说错机制**
是同一类：用户没有办法判断该信哪一句。

## 这里钉的是行为，不是措辞

下面第一组直接跑 `archive._age_days`：错键的日期必须被算进去。措辞可以再改，
这条性质不能变 —— 一旦哪天 `_age_days` 真的只认自己那条键了，
第一组会红，那时才轮到改文案。
"""
import datetime as dt
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import archive  # noqa: E402

SRC = (ROOT / "tools" / "audit_pipeline.py").read_text(encoding="utf-8")
TODAY = dt.date(2026, 8, 26)


def _seg() -> str:
    i = SRC.index("def check_out_records_carry_their_own_date(")
    return SRC[i:SRC.index("\ndef ", i + 10)]


class AMisfiledDateStillCounts(unittest.TestCase):
    """`_age_days` 取最晚的那个 —— 键写岔了照样读到。"""

    BASE = {"first_seen": "2026-07-30", "rank_date": "2026-07-31"}

    def test_the_wrong_key_is_still_read(self):
        e = {**self.BASE, "status": "skipped", "expired_date": "2026-08-13"}
        self.assertEqual(archive._age_days(e, {}, TODAY), 13,
                         "错键的日期没被算进去 —— 那自检那句「不受影响」就不成立了")

    def test_the_right_key_gives_the_same_answer(self):
        e = {**self.BASE, "status": "skipped", "skip_date": "2026-08-13"}
        self.assertEqual(archive._age_days(e, {}, TODAY), 13,
                         "记对键和记错键算出来的年龄不一样")

    def test_with_no_date_it_falls_back_to_the_later_of_two(self):
        """真正会退的是这一类，退到 `max(rank_date, first_seen)` —— 评分那天。"""
        e = {**self.BASE, "status": "expired"}
        self.assertEqual(archive._age_days(e, {}, TODAY), 26,
                         "退错了地方：应当是评分那天（07-31），不是抓到那天（07-30）")

    def test_the_overlay_date_wins_when_it_is_the_latest(self):
        e = {**self.BASE, "status": "skipped", "skip_date": "2026-08-01"}
        self.assertEqual(archive._age_days(e, {"date": "2026-08-20"}, TODAY), 6)


class TheAuditNoLongerTellsTheWrongStory(unittest.TestCase):
    def test_it_dropped_the_claim_that_does_not_match_the_code(self):
        seg = _seg()
        self.assertNotIn("退到「抓到它的日子」", seg,
                         "那句话对着 `archive._age_days` 是错的")

    def test_it_separates_the_two_shapes(self):
        """错键与漏记后果不同，报的时候要分开 —— 修的紧迫程度不一样。"""
        seg = _seg()
        self.assertIn("归档不受影响", seg)
        self.assertIn("退到评分那天", seg)

    def test_it_names_the_real_cost_of_a_wrong_key(self):
        seg = _seg()
        self.assertIn("不显示日期", seg, "没说出错键真正的代价")

    def test_it_still_says_what_to_do(self):
        seg = _seg()
        self.assertIn("放回来", seg, "只报不给动作，看见了也只能干看着")


class TheEvidenceIsOnRecord(unittest.TestCase):
    def test_the_writer_side_is_named_as_the_root_cause(self):
        """坏的全部来自手改 JSON 那条路，面板写的叠加层一条没坏 ——
        这是「写入端没有约束」的证据，不是用户手滑。"""
        seg = _seg()
        self.assertIn("手改 JSON", seg)
        self.assertIn("108", seg)
        self.assertIn("17", seg, "没记下叠加层那批一条都没坏")


if __name__ == "__main__":
    unittest.main()
