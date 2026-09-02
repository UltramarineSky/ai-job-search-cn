# -*- coding: utf-8 -*-
"""猎聘 CLI 那条封的是 IP，等不掉——而工具一直在报「还剩 N 小时」。

2026-08-26 本人：「猎聘 cli 封 ip 了，需要手动更换 ip 而不是等冷却。
在停止时间使用猎聘浏览器获取」。

## 为什么「还剩 N 小时」是有害的

冷却计时本身没问题——它挡的是「别再往同一个出口上撞」。**问题在于那句话
读起来像解法**：等到点就能用了。而限的是这个网络出口的 IP，到点换的还是
同一个 IP，探一次限一次，然后再封一天，如此循环。

实测：活动用户 2026-08-24 与 08-25 各撞一次、各封一天，**第二次就是冷却
刚过撞的**——正是这个循环。

## 该说的是两个动作，跟钟表无关

1. 换 IP，再 `--clear liepin-search` 或探一次；
2. 这段时间走猎聘浏览器——**它是该走的那条，不是备胎**。放慢照旧
   （间隔 ×3 —— 取值只有一处：`SLOW_GAP_FACTOR`；原来还叠一条「每轮上限 3」，
   2026-08-26 随固定额度一起删了），但放慢不等于不走。实测 08-25：CLI 封着时
   猎聘浏览器搜一页 40 张卡、新增 36 个，而同一天另外三家合计才 50 个。
"""
import datetime as dt
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import portal_budget as PB  # noqa: E402

SCRAPE = (ROOT / "workflows" / "job-scrape.md").read_text(encoding="utf-8")
SRC = (ROOT / "tools" / "portal_budget.py").read_text(encoding="utf-8")


def _blocked_cli(hours=8):
    """一条**新格式**封控记录（带 `since`）。

    `since` 不是可有可无的：`_one_lane` 拿它区分新老记录 —— 没有 `since`
    的是 2026-08-26 之前写的，照老规矩满 24 小时自动释放。第一版夹具漏了它，
    于是「25 小时后还封着吗」那条子测被**迁移分支**放行，测的不是它要测的东西。
    """
    now = dt.datetime(2026, 8, 26, 10, 0)
    since = (now - dt.timedelta(hours=24 - hours)).isoformat(timespec="minutes")
    until = (now + dt.timedelta(hours=hours)).isoformat(timespec="minutes")
    data = {"猎聘": {"blocks": {"cli": {"until": until, "since": since,
                                     "why": "CLI 撞 RATE_LIMITED"}}}}
    return data, now


class TheRefusalSaysWhatToDo(unittest.TestCase):
    def test_it_says_the_clock_will_not_fix_it(self):
        """钟表解决不了 —— 这句话 2026-08-26 从「等不掉」升级成事实：
        **它根本不会自动解**。本人当天裁定「只有用户手动点继续 cli 后，
        才能继续 cli」。"""
        data, now = _blocked_cli()
        ok, msg = PB.check(data, "liepin-search", now)
        self.assertFalse(ok)
        self.assertIn("不会自动解", msg, "还在让人等")
        for h in (25, 24 * 30):
            with self.subTest(hours=h):
                self.assertFalse(
                    PB.check(data, "liepin-search", now + dt.timedelta(hours=h))[0],
                    f"{h} 小时后它自己解开了 —— 那正是被裁掉的那件事")

    def test_it_names_the_real_action(self):
        data, now = _blocked_cli()
        _ok, msg = PB.check(data, "liepin-search", now)
        self.assertIn("换", msg, "没说要换 IP")
        self.assertIn("IP", msg)
        self.assertIn("--clear liepin-search", msg, "没给换完之后该敲的那条")

    def test_it_still_points_at_the_browser_lane(self):
        """**CLI 封着时浏览器是该走的那条**，refusal 里必须带上它。"""
        data, now = _blocked_cli()
        _ok, msg = PB.check(data, "liepin-search", now)
        self.assertIn("浏览器", msg)
        self.assertIn("放慢不等于不走", msg, "读起来还像是「先别动」")

    def test_it_says_how_long_it_has_been_held(self):
        """时间那一栏没删，是**换了方向**：从「还剩多久」变成「已经封了多久」。

        这条判据 2026-08-25 写的时候盯的是「别把倒计时顺手删了」，理由是
        它回答「这个出口还要晾多久」。第二天倒计时本身被裁掉了 —— 因为
        封控不再自动到期，「还剩」没有落点。而那一栏要答的问题还在：
        **这个出口晾了多久了**，用户据此判断换 IP 值不值得现在做。
        """
        data, now = _blocked_cli()
        _ok, msg = PB.check(data, "liepin-search", now)
        self.assertIn("已经封了", msg, "时间那一栏被顺手删了")
        self.assertNotIn("还剩", msg, "倒计时又回来了 —— 它读起来就是「等一等」")


class TheBrowserLaneIsNotDemoted(unittest.TestCase):
    """反向：别把「放慢」改成「停」。那是 2026-08-21 本人裁定过的。"""

    def test_browser_still_passes_while_cli_cools(self):
        data, now = _blocked_cli()
        ok, msg = PB.check(data, "liepin-browser", now)
        self.assertTrue(ok, f"CLI 封着把浏览器也拦了：{msg}")

    def test_the_slowdown_numbers_survive(self):
        """放慢原来是两件事叠的（间隔 ×3 + 每轮上限 10→3）。
        2026-08-26 固定额度删了，只剩间隔这一项 —— 判据跟着只剩一条。"""
        self.assertGreater(PB.SLOW_GAP_FACTOR, 1)
        self.assertFalse(hasattr(PB, "SLOW_ACTIONS_PER_ROUND"),
                         "每轮上限又回来了 —— 固定额度是被裁掉的那件事")


class TheWorkflowSaysItToo(unittest.TestCase):
    def test_scrape_records_the_ip_fact(self):
        self.assertIn("限流是 IP 级的，等不掉", SCRAPE, "流程正本里没记这件事")

    def test_it_forbids_writing_wait_as_the_next_step(self):
        i = SCRAPE.index("限流是 IP 级的，等不掉")
        seg = SCRAPE[i:i + 1400]
        self.assertIn("别把「等冷却」写进报告当下一步", seg,
                      "没拦住「明天再说」那种报告——那会让人白等一天")
        self.assertIn("该走的那条", seg, "没说清这段时间浏览器不是备胎")


if __name__ == "__main__":
    unittest.main()
