# -*- coding: utf-8 -*-
"""闸门按**通道**判，人按**家**想 —— 这一轮跑哪几条，让工具列出来。

## 规则写了四处，还是连错两次

- `AGENTS.md`「取数渠道的顺位」第 2 层；
- `job-scrape.md` Step 0.44 的五行渠道表（连同三处交叉引用、两段实测代价）；
- `job-scrape.md` Step 0.46「跳的是通道，不是整家」；
- `portal_budget.py` 的 `--check liepin-search` 回话里就写着
  「这段时间走浏览器那条（放慢：间隔 ×3）…… **但放慢不等于不走**」。

实测代价两次：

    2026-08-25   补 JD 时 CLI 第一个请求就 RATE_LIMITED，执行者把**整个猎聘**
                 跳过，报告写「CLI 在冷却，明天再说」。用户当场纠正：
                 「CLI 停了不要紧，你可以用浏览器的啊」。
    2026-08-30   同一件事再来一次：那天 liepin-browser **0 次查询**，
                 而猎聘占这个职位库语料的大头。

**差的不是规则。** 要把「家」和「通道」两个粒度对上，得逐条跑 `--check`
（5 次）再和 `portals.json` 交叉一遍 —— 全是机械活，而机械活交给人就会漏。

## 所以这一条守的是那张单子

`--round` 把两件事一次算完，并在主通道被挡住时明写「一家的主通道被挡住 ≠
这一轮没有这家」。
"""
import datetime as dt
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
from _live import user_or_skip  # noqa: E402
import portal_budget as pb  # noqa: E402

SCRAPE = (ROOT / "workflows" / "job-scrape.md").read_text(encoding="utf-8")
NOW = dt.datetime(2026, 8, 30, 12, 0)


def _plan(data, off=()):
    """跑一次 `round_plan`，把用户开关替换成给定的集合。"""
    saved = pb.switched_off
    try:
        pb.switched_off = lambda user: set(off)
        return pb.round_plan(data, "nobody", NOW)
    finally:
        pb.switched_off = saved


class ABlockedPrimaryDoesNotHideTheFamily(unittest.TestCase):
    """**这一条就是那两次事故。**"""

    def _cli_blocked(self):
        data = pb.load_empty() if hasattr(pb, "load_empty") else {}
        pb.block(data, "liepin-search", "CLI 撞 RATE_LIMITED", NOW)
        return data

    def test_the_browser_lane_still_runs(self):
        rows = _plan(self._cli_blocked())
        by = {name: ok for ok, name, _w in rows}
        self.assertFalse(by["liepin-search"], "CLI 该是停着的（前提没搭好）")
        self.assertTrue(by["liepin-browser"],
                        "CLI 停着就把浏览器那条也跳了 —— 正是 08-25 和 08-30 那两次")

    def test_the_other_families_are_untouched(self):
        by = {n: ok for ok, n, _w in _plan(self._cli_blocked())}
        for name in ("boss-browser", "zhaopin-browser", "51job-browser"):
            with self.subTest(name=name):
                self.assertTrue(by[name], "一家撞限流，别家跟着停")

    def test_the_blocked_lane_is_still_listed(self):
        """挡住的照样列出来 —— 不列就等于把「这一轮为什么没有这家」藏了。"""
        names = [n for _ok, n, _w in _plan(self._cli_blocked())]
        self.assertIn("liepin-search", names)


class TheSwitchIsTheUsersNotTheGates(unittest.TestCase):
    def test_a_switched_off_family_drops_out(self):
        names = [n for _ok, n, _w in _plan({}, off={"BOSS"})]
        self.assertNotIn("boss-browser", names)
        self.assertIn("zhaopin-browser", names)

    def test_all_five_lanes_when_nothing_is_off(self):
        names = [n for _ok, n, _w in _plan({})]
        self.assertEqual(sorted(names),
                         sorted(["liepin-search", "liepin-browser",
                                 "boss-browser", "zhaopin-browser",
                                 "51job-browser"]))

    def test_families_with_one_lane_get_one_row(self):
        """BOSS / 智联 / 前程只有浏览器一条 —— 别凭空多出一条 cli。"""
        names = [n for _ok, n, _w in _plan({})]
        for bogus in ("boss-cli", "zhaopin-cli", "51job-cli"):
            with self.subTest(bogus=bogus):
                self.assertNotIn(bogus, names)


class TheCliSaysIt(unittest.TestCase):
    def _run(self, *args):
        r = subprocess.run([sys.executable, str(ROOT / "tools" / "portal_budget.py"),
                            *args], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=90)
        return (r.stdout or "") + (r.stderr or "")

    def test_the_flag_exists(self):
        self.assertIn("--round", self._run("--help"))

    def test_it_prints_one_line_per_lane(self):
        user_or_skip()   # 没有真实数据可读时 skip（见 tests/_live.py）
        out = self._run("--round")
        for name in ("liepin-search", "liepin-browser", "boss-browser",
                     "zhaopin-browser", "51job-browser"):
            with self.subTest(name=name):
                self.assertIn(name, out)

    def test_it_spells_out_the_lesson_when_a_primary_is_blocked(self):
        """真封着的时候，那句话要出现在屏幕上 —— 它是这条命令存在的理由。"""
        out = self._run("--round")
        if "✗ liepin-search" in out:
            self.assertIn("一家的主通道被挡住 ≠ 这一轮没有这家", out)


class TheWorkflowPointsAtIt(unittest.TestCase):
    def test_step_044_runs_it(self):
        self.assertIn("python tools/portal_budget.py --round", SCRAPE)

    def test_it_says_not_to_hand_roll_the_list(self):
        i = SCRAPE.index("### Step 0.44")
        seg = " ".join(SCRAPE[i:i + 1800].split())
        self.assertIn("不要自己拼", seg)

    def test_the_table_survives(self):
        """表答的是「为什么」，单子答的是「这一轮跑哪几条」—— 两件事，都要在。"""
        i = SCRAPE.index("### Step 0.44")
        seg = SCRAPE[i:i + 3000]
        for row in ("liepin-search", "liepin-browser", "只有这条路"):
            with self.subTest(row=row):
                self.assertIn(row, seg)

    def test_both_incidents_are_recorded(self):
        """不写代价，下一个人会把这条命令当成多余的一步删掉。"""
        i = SCRAPE.index("### Step 0.44")
        seg = " ".join(SCRAPE[i:i + 1800].split())
        self.assertIn("2026-08-30", seg)
        self.assertIn("2026-08-25", seg)


if __name__ == "__main__":
    unittest.main()
