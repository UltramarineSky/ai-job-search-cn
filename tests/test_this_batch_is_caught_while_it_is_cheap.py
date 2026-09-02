# -*- coding: utf-8 -*-
"""收尾那一档存在的理由就是这一条检查，而它自己进不去。

`run()` 的说明里把它点名成**最典型的**那一例：

> 最典型的是「判词自称读过 JD，库里却没有」—— 浏览器读来的正文只活在读它的
> 那一刻，当批发现只要跑一次 `jd_store.py --save`，全量跑完再发现就得重开页面。
> 实测 2026-08-30：这一条积到了 145 个岗，而规则在三个工作流里都写着。
> **规则没缺，缺的是「什么时候查」。**

而 `--actionable`（`/job-auto` 收尾跑的那一档）此前只认一个信号 ——
「调没调过 `sendable_state`」。这条检查不调它，于是**理由写在那儿、例子也写在
那儿，就是没接上**：那 145 个里，每一批新出的那几个本来都能当场几秒钟补掉。

2026-08-31 用第二个信号接上（`_cli.note_round_scoped()`，见
`test_the_closing_only_says_what_he_can_still_do`）。

## 只为「这一批」喊

存量补不回来（浏览器渠道的正文只活在抓取当次），收尾印它只会把还来得及的
淹掉 —— 那正是这一档要防的事。所以：

    这一批刚判的（`rank_date` 落在这一批）→ 喊一声，并说清能当场做什么
    存量                                  → 照旧报，不喊

## 「这一批」只有一份定义

`this_batch_days()`：今天，加上凌晨 `_MIDNIGHT_GRACE_H` 点之前的昨天
（一轮 `/job-auto` 会跨过午夜：23:55 写完、00:05 跑收尾）。

⚠️ 它 2026-08-31 险些成了第二份 —— `--sections` 那道闸门里本来就内联着同样
三行，加这条时我在文件另一头又写了一遍。
"""
import datetime as dt
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
from _live import user_or_skip  # noqa: E402
import _cli  # noqa: E402
import audit_pipeline as ap  # noqa: E402

AUDIT = (ROOT / "tools" / "audit_pipeline.py").read_text(encoding="utf-8")


def _seen(day):
    """一个「判词说读过 JD、库里没有」的岗，评分日期由调用方给。"""
    return {"k1": {"url": "https://x.com/a", "title": "t", "company": "c",
                   "rank_date": day,
                   "rank_breakdown": {"来源": "深评：读过 JD 正文"}}}


def _run(day):
    user_or_skip()   # 没有真实数据可读时 skip（见 tests/_live.py）
    before = _cli._ROUND_SCOPED_CALLS[0]
    rows = ap.check_claimed_reads_are_stored(_seen(day), {})
    return rows, _cli._ROUND_SCOPED_CALLS[0] - before


class ThisBatchReachesTheClosing(unittest.TestCase):

    def test_a_fresh_one_shouts(self):
        rows, shouted = _run(dt.date.today().isoformat())
        self.assertEqual(len(rows), 1, "这一批刚判的没报出来")
        self.assertEqual(shouted, 1, "没喊 —— 收尾那一档还是看不见它")

    def test_a_fresh_one_says_what_to_do_right_now(self):
        rows, _ = _run(dt.date.today().isoformat())
        msg = rows[0][2]
        self.assertIn("这一批刚判的", msg, "没把这一批和存量分开说")
        self.assertIn("jd_store.py --save", msg,
                      "没给能当场做的那条 —— 正文还在手上时它只要几秒")

    def test_a_backlog_one_is_reported_but_quiet(self):
        """存量照报，但不喊 —— 收尾印它只会把还来得及的淹掉。"""
        rows, shouted = _run("2026-01-01")
        self.assertEqual(len(rows), 1, "存量不报了？")
        self.assertEqual(shouted, 0, "存量也喊了")
        self.assertNotIn("这一批刚判的", rows[0][2])

    def test_nothing_wrong_means_nothing_said(self):
        """控制用例：没东西可报时既不报也不喊。"""
        before = _cli._ROUND_SCOPED_CALLS[0]
        self.assertEqual(ap.check_claimed_reads_are_stored({}, {}), [])
        self.assertEqual(_cli._ROUND_SCOPED_CALLS[0], before,
                         "什么都没报却喊了一声")


class OneDefinitionOfThisBatch(unittest.TestCase):

    def test_it_covers_today(self):
        self.assertIn(dt.date.today().isoformat(), ap.this_batch_days())

    def test_it_stretches_back_only_across_midnight(self):
        days = ap.this_batch_days()
        want = 2 if dt.datetime.now().hour < ap._MIDNIGHT_GRACE_H else 1
        self.assertEqual(len(days), want,
                         f"这一批覆盖了 {sorted(days)} —— 与宽限窗口对不上")

    def test_the_gate_does_not_recompute_it(self):
        """`--sections` 那道闸门要用这一份，不许自己再算一遍。

        判据是**构造**：整份文件里比较宽限小时数的地方只许有一处。
        """
        n = len(re.findall(r"\.hour < _MIDNIGHT_GRACE_H", AUDIT))
        self.assertEqual(n, 1,
                         f"宽限窗口被算了 {n} 遍 —— 改一处忘一处的老样子")
        i = AUDIT.index("def _sections_cli")
        seg = AUDIT[i:i + 4000]
        self.assertIn("this_batch_days()", seg, "闸门没走那一份")


if __name__ == "__main__":
    unittest.main()
