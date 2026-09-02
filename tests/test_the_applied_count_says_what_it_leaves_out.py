# -*- coding: utf-8 -*-
"""「投了多少」这一页有两个数，差 3，而一个字都没解释。

    流水线第 4 格「已投递」    85     ← 走 `funnels_of`
    「投出去的那些」那颗按钮    88     ← 走投递记录的行数

两个数上下摆在同一屏上。实测 2026-08-31 的快照就是这一对。

## 两个都没算错

`funnels_of` 排掉判词出局与三类搁置，是**有意的**：它自己的说明写着
「格子上的数必须等于点开看到的行数」——那 4 个岗投过，但评下来不满足硬性
条件，已经收进搁置区，点开这一格是看不到它们的。

那颗按钮数的是投递记录，投了就是投了，也没错。

## 错的是**不说**

同一屏两个数不一样、又都对，用户只能自己猜哪个是真的 —— 而这一格
**本来就有说这种话的地方**：「另有 N 个被你在「这几类岗要不要看」里关掉了」。
那句话存在的理由（写在源码里）是「否则用户会以为岗位凭空少了」，
这里一字不差是同一件事。

## 理由要现数，不许写死

今天 4 个全是判词出局（其中 1 个他后来还标了不投）。明天可能全是「已下线」。
写死一句「评下来不满足硬性条件」，等语料一变，那句话就成了假话。
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
from _live import user_or_skip  # noqa: E402
import export_web_data as ex  # noqa: E402

SNAP = ROOT / "web" / "public" / "data.json"
APP = (ROOT / "web" / "src" / "App.tsx").read_text(encoding="utf-8")
TYPES = (ROOT / "web" / "src" / "types.ts").read_text(encoding="utf-8")


def _job(**kw):
    j = {"url": kw.pop("url", "https://x/1"), "title": "t", "company": "c"}
    j.update(kw)
    j["funnels"] = ex.funnels_of(j)
    return j


class TheNumberAccountsForWhatItDrops(unittest.TestCase):
    """格子数 + 搁置区里投过的 = 投过的全部。少一个都不许静默。"""

    def setUp(self):
        if not SNAP.is_file():
            self.skipTest("还没导出过面板数据")
        self.d = json.loads(SNAP.read_text(encoding="utf-8"))
        self.jobs = self.d.get("jobs") or []
        if not self.jobs:
            self.skipTest("快照里一个岗都没有")
        self.step = next((s for s in self.d.get("pipeline") or []
                          if s.get("step") == 4), None)
        self.assertIsNotNone(self.step, "流水线里没有第 4 格")

    def test_the_scan_sees_applications(self):
        """**先证明这份语料里真有投递。** 一个都没有时下面几条全是空转。"""
        user_or_skip()   # 没有真实数据可读时 skip（见 tests/_live.py）
        n = sum(1 for j in self.jobs if j.get("applied"))
        self.assertGreater(n, 0, "快照里一条投递都没有，这几条验不了")

    def test_the_two_halves_add_up(self):
        """格子数 + 搁置区里投过的 = 投过的全部。

        **两边都现算**，不读快照里那两个数：快照是上一次导出的产物，照它比
        等于拿结果验结果 —— 变异实测把 `_parked_sent` 整个短路，这一条一声不响。
        """
        applied = sum(1 for j in self.jobs if j.get("applied"))
        n_cell = sum(1 for j in self.jobs
                     if "applied" in (j.get("funnels") or []))
        n_parked, _ = ex._parked_sent(self.jobs)
        self.assertEqual(
            n_cell + n_parked, applied,
            "「已投递」那一格加上搁置区里投过的，对不上投过的总数 —— "
            "中间那几个既不在格子里也没被说出来")

    def test_the_snapshot_matches_what_the_code_says(self):
        """导出的那两个键，就是代码现在会算出来的那两个值。

        少了这条，上面几条全在验一份可能过时的 JSON。"""
        n, note = ex._parked_sent(self.jobs)
        self.assertEqual(self.step.get("parked") or 0, n,
                         "快照里的数和代码现在算的对不上（该重导了）")
        self.assertEqual(self.step.get("parkedNote") or "", note)

    def test_it_says_so_when_it_drops_any(self):
        n, note = ex._parked_sent(self.jobs)
        if not n:
            self.assertEqual(note, "", "一个都没落下，却还有话说")
            return
        self.assertIn(str(n), note, "说了有几个，句子里却没有那个数")
        self.assertIn("搁置", note, "没说它们去哪儿了")


class TheReasonIsCounted(unittest.TestCase):
    """理由是**现数**出来的，不是写死的一句。"""

    def _note(self, jobs):
        return ex._parked_sent(jobs)[1]

    def test_out_verdict_only(self):
        n, note = ex._parked_sent([_job(applied={"status": "applied"},
                                        verdict="硬门 FAIL")])
        self.assertEqual(n, 1)
        self.assertIn("不满足硬性条件", note)
        self.assertNotIn("你标了不投", note)

    def test_skipped_only(self):
        n, note = ex._parked_sent([_job(applied={"status": "applied"},
                                        verdict="值得投", skipped=True)])
        self.assertEqual(n, 1)
        self.assertIn("你标了不投", note)
        self.assertNotIn("不满足硬性条件", note)

    def test_nothing_parked_says_nothing(self):
        n, note = ex._parked_sent([_job(applied={"status": "applied"},
                                        verdict="值得投", materials={"dir": "x"})])
        self.assertEqual((n, note), (0, ""), "没落下谁，就不该有话")

    def test_it_does_not_count_the_unapplied(self):
        n, _ = ex._parked_sent([_job(verdict="硬门 FAIL")])
        self.assertEqual(n, 0, "没投过的岗不该算进「投过但搁置」")


class ThePanelPrintsIt(unittest.TestCase):

    def test_the_field_is_declared(self):
        i = TYPES.index("parkedNote?: string;")
        self.assertGreater(i, 0)
        self.assertIn("parked?: number;", TYPES)

    def test_the_rail_renders_it(self):
        """既要有那道「有才印」的闸门，也要真把它印出来。

        只查名字出现过是不够的：变异实测把闸门改成 `{false && (`，名字
        还在正文里，那一条照样绿 —— 而屏幕上那句话已经没了。"""
        self.assertGreaterEqual(
            APP.count("s.parkedNote"), 2,
            "那句话要么没闸门、要么没印出来 —— 两处都该出现它")

    def test_it_sits_with_the_other_such_line(self):
        """和「另有 N 个被你关掉了」同一个位置、同一种样式 —— 那是同一类话。"""
        i = APP.index("s.parkedNote")
        seg = APP[max(0, i - 800):i + 200]
        self.assertIn("rail-filtered", seg)


if __name__ == "__main__":
    unittest.main()
