# -*- coding: utf-8 -*-
"""封控不会自己解开 —— 只有人能放行。

2026-08-26 本人裁定：「cli 被封后，你应该显示实际获取的信息，然后只有用户
手动点继续 cli 后，才能继续 cli」。

## 为什么归人

解封的前提是**外面那件事真的变了**，而工具两件都看不见：

- **浏览器那条**要他本人过完验证（短信、滑块、联系客服）；
- **CLI 那条**要他换掉这个网络出口的 IP —— 限的是 IP，不是账号。
  08-24、08-25 各撞一次，第二次就是冷却刚过撞的：到点换的还是同一个 IP。

按时间自动放行等于替他赌平台自己消气了，而那两天赌输两次。

## 这条规则来回翻过三次

1. 最早写的就是「工具永远不自动解」；
2. 2026-08-25 发现代码相反（`_one_lane` 到点就返回 `NOT_BLOCKED`），
   于是**把文档改成迁就代码**；
3. 2026-08-26 本人裁定，代码改回来。

第 2 次最贵：那天核的是「文档和代码对不对得上」，**没核哪一边才是对的**。
"""
import datetime as dt
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import portal_budget as pb  # noqa: E402

NOW = dt.datetime(2026, 8, 26, 12, 0, 0)


class ItNeverLetsGoOnItsOwn(unittest.TestCase):
    def test_time_alone_never_releases_it(self):
        for site in pb.PORTALS:
            for days in (1, 2, 7, 90):
                with self.subTest(site=site, days=days):
                    data = {}
                    pb.block(data, site, "撞了", NOW)
                    later = NOW + dt.timedelta(days=days)
                    self.assertTrue(pb.block_state(data, site, later)["blocked"],
                                    f"{site} 在 {days} 天后自己解开了")

    def test_a_person_can_release_it(self):
        """反面：人点了就要真的解开，否则这条规则就成了死锁。"""
        data = {}
        pb.block(data, "BOSS", "撞了", NOW)
        pb.clear(data, "BOSS", NOW + dt.timedelta(minutes=5))
        self.assertTrue(pb.check(data, "BOSS", NOW + dt.timedelta(minutes=5))[0])

    def test_the_message_says_it_will_not_self_heal(self):
        """拒绝语要说清两件事：不会自动解、该做什么才能继续。"""
        for chan, act in (("liepin-search", "IP"), ("liepin-browser", "验证")):
            with self.subTest(chan=chan):
                data = {}
                pb.block(data, chan, "撞了", NOW)
                ok, why = pb.check(data, chan, NOW + dt.timedelta(hours=2))
                self.assertFalse(ok)
                self.assertIn("不会自动解", why)
                self.assertIn(act, why, "没说清要他做什么")
                self.assertIn("--clear", why, "没给该敲的那条命令")

    def test_it_says_how_long_not_how_much_longer(self):
        """时间那一栏答的是「已经封了多久」。

        「还剩多久」在这套语义下没有落点，而且它读起来就是「等一等」——
        那正是 08-24、08-25 白等两天的那句话。
        """
        data = {}
        pb.block(data, "猎聘", "撞了", NOW)
        st = pb.block_state(data, "猎聘", NOW + dt.timedelta(hours=40))
        self.assertEqual(st["held_minutes"], 40 * 60)
        self.assertNotIn("minutes_left", st, "倒计时字段又回来了")
        _ok, why = pb.check(data, "liepin-search", NOW + dt.timedelta(hours=40))
        self.assertIn("已经封了 40 小时", why)
        self.assertNotIn("还剩", why)


class LegacyRecordsKeepTheRulesTheyWereWrittenUnder(unittest.TestCase):
    """**存量记录按写它时的规矩算。**

    2026-08-26 之前的记录是在「满 24 小时自动放行」下写的 —— 到点那一刻
    它们已经放行过了。改成永不到期若一视同仁，等于把历史改写。

    实测当天：一条 161 小时前的 BOSS 记录当场把 BOSS 整家判停，
    而同一天刚用浏览器读完它 6 个职位页 —— 那条早就不成立了。
    """

    def _legacy(self, hours_ago: float) -> dict:
        """老格式：有 `until`，**没有** `since`。"""
        until = (NOW - dt.timedelta(hours=hours_ago - 24)).isoformat(timespec="seconds")
        return {"BOSS": {"blocks": {"browser": {"until": until, "why": "老记录"}}}}

    def test_an_expired_legacy_record_stays_released(self):
        data = self._legacy(161)
        self.assertFalse(pb.block_state(data, "BOSS", NOW)["blocked"],
                         "老记录被追认成永久封控 —— 那是改写历史")

    def test_a_legacy_record_still_inside_its_day_is_still_blocked(self):
        data = self._legacy(3)
        self.assertTrue(pb.block_state(data, "BOSS", NOW)["blocked"],
                        "老记录还在 24 小时内，不该放行")

    def test_new_records_are_not_covered_by_the_migration(self):
        """迁移只对**没有 `since`** 的老记录开口，别顺手把新记录也放了。"""
        data = {}
        pb.block(data, "BOSS", "新撞的", NOW)
        rec = data["BOSS"]["blocks"]["browser"]
        self.assertIn("since", rec, "新记录没记撞上的时刻，迁移判据就失去依据")
        self.assertTrue(pb.block_state(data, "BOSS", NOW + dt.timedelta(days=9))["blocked"])


class TheHarvestIsShown(unittest.TestCase):
    """**「cli 被封后，你应该显示实际获取的信息」** —— 同一句裁定的前半。

    撞停那一趟不是白跑：前面抓到的 JD 已经落库了。不把这个数说出来，
    终端和面板上就只剩「CLI 撞 RATE_LIMITED」，读起来像颗粒无收 ——
    而用户下一步该做什么（先补剩下的，还是先去换 IP）正取决于它。
    """

    def test_the_block_reason_carries_it(self):
        src = (ROOT / "tools" / "fetch_details.py").read_text(encoding="utf-8")
        seg = src.split("for i, e in enumerate(entries):")[1]
        self.assertIn("撞停前已抓到", seg, "封控记录里没写这一趟拿到了什么")
        self.assertIn("{ok}", seg, "写的是句固定话，不是真实数目")

    def test_the_terminal_says_it_too(self):
        src = (ROOT / "tools" / "fetch_details.py").read_text(encoding="utf-8")
        self.assertIn("实际拿到", src)
        self.assertIn("没有白跑", src)

    def test_it_does_not_tell_you_to_wait(self):
        """**不许说「等一段时间再跑一次」。** 那是这条路上最贵的一句话。

        **只扫会上屏的那些，不扫注释。** 第一版没剥，于是在变异之前就红了 ——
        因为上面那句禁令自己引用了它。「断言撞上解释自己的文字」这个形状
        在这个仓库里已经出现第七次：判据一旦禁止某个字符串，讲这条规则的
        文字就没法引用它，规则也就没法解释自己。
        """
        raw = (ROOT / "tools" / "fetch_details.py").read_text(encoding="utf-8")
        src = re.sub(r'"""[\s\S]*?"""|#[^\n]*', "", raw)
        self.assertNotIn("等一段时间再跑", src)
        self.assertIn("不会自动解", src)
        self.assertIn("--clear liepin-search", src, "没给该敲的那条")
        self.assertIn("--browser-list", src, "没说这段时间浏览器那条还通着")


if __name__ == "__main__":
    unittest.main()


class TheLedgerRemembersHowManyTimes(unittest.TestCase):
    """**「cli 实际已经封了几天，你每次都是一尝试就又封了吧」**（2026-08-26 本人问）。

    ——是。而**工具当时答不出这句话**：封控记录只有 `{until, why, where}`
    三个字段，每撞一次就把上一次原样覆盖掉，`users/<user>/job_scraper/`
    底下也没有第二处留痕。于是屏幕上永远只有「已经封了 16 小时」，
    读起来像个刚发生的小毛病。

    **两个读数会导出相反的决定**：16 小时 → 再等等；三天撞了 3 次、
    每次放行后几分钟又中 → 这个出口不会好了，换 IP 或者走浏览器那条。
    """

    def test_every_hit_is_recorded_even_while_already_blocked(self):
        """本来就封着时再撞一次**也要记** —— 那正是「探一次限一次」的证据。

        `block()` 对已经停着的通道只更新原因、不动起算时刻（那是对的），
        第一版顺手把流水也一起跳过了，于是探失败这件事一次都没留下。
        """
        data = {}
        t = dt.datetime(2026, 8, 24, 16, 0)
        pb.block(data, "liepin-search", "第一次", t)
        pb.block(data, "liepin-search", "探了一次还在限流", t + dt.timedelta(hours=2))
        hits = [e for e in pb.block_log(data, "猎聘", "cli") if e["act"] == "hit"]
        self.assertEqual(len(hits), 2, "封着时再撞一次没记进流水")

    def test_the_log_survives_a_release(self):
        """**放行不许把流水抹掉。** 流水存在的全部理由就是「解过之后又撞上」。

        所以它挂在行上，不挂在 `blocks[lane]` 里 —— 后者一解封整条弹掉。
        """
        data = {}
        t = dt.datetime(2026, 8, 24, 16, 0)
        pb.block(data, "liepin-search", "第一次", t)
        pb.clear(data, "liepin-search", t + dt.timedelta(hours=24))
        pb.block(data, "liepin-search", "又中了", t + dt.timedelta(hours=24, minutes=3))
        log = pb.block_log(data, "猎聘", "cli")
        self.assertEqual([e["act"] for e in log], ["hit", "clear", "hit"])

    def test_the_refusal_says_it_is_not_the_first_time(self):
        data = {}
        t = dt.datetime(2026, 8, 24, 16, 0)
        pb.block(data, "liepin-search", "撞了", t)
        pb.clear(data, "liepin-search", t + dt.timedelta(hours=24))
        pb.block(data, "liepin-search", "又中了", t + dt.timedelta(hours=24, minutes=3))
        _ok, why = pb.check(data, "liepin-search", t + dt.timedelta(hours=30))
        self.assertIn("不是第一次", why)
        self.assertIn("08-24 起", why, "没说清从哪天开始")
        self.assertIn("撞了 2 次", why)
        self.assertIn("3 分钟就又撞上", why, "没说放行后多快又中 —— 那是最关键的一个数")

    def test_one_hit_says_nothing_extra(self):
        """只撞过一次就别说这句 —— 一句永远都在的警告等于没有。"""
        data = {}
        t = dt.datetime(2026, 8, 24, 16, 0)
        pb.block(data, "liepin-search", "撞了", t)
        _ok, why = pb.check(data, "liepin-search", t + dt.timedelta(hours=2))
        self.assertNotIn("不是第一次", why)
        self.assertEqual(pb.streak_note(data, "猎聘", "cli", t), "")

    def test_a_broken_log_does_not_crash_the_gate(self):
        """流水读不出来就一个字不说 —— 它是给人看的注脚，不该拖垮闸门。"""
        for junk in ("oops", ["a"], 5, None, {"cli": "nope"}):
            with self.subTest(junk=junk):
                data = {"猎聘": {"blocks": {}, "block_log": junk}}
                self.assertEqual(pb.block_log(data, "猎聘", "cli"), [])
                self.assertTrue(pb.check(data, "liepin-browser",
                                         dt.datetime(2026, 8, 26, 12, 0))[0])

    def test_the_panel_gets_it_too(self):
        exp = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        self.assertIn("pb.streak_note(", exp, "面板没拿到这句话")
        tsx = (ROOT / "web" / "src" / "components" / "Portals.tsx").read_text(encoding="utf-8")
        self.assertIn("b.streak", tsx, "面板拿到了却不渲染")
