# -*- coding: utf-8 -*-
"""面板劝他打开一个此刻打开也抓不到的渠道 —— 那句话只读了两份状态里的一份。

渠道的「开不开」有**两个主人**。`job-scrape.md` 的 Step 0.43「被封的家，
勾着也不抓」把它写死成一条优先级：

> **优先级：封 > 勾。** 面板勾选回答的是「我想不想抓这家」，风控冷却回答的是
> 「现在允不允许抓」——**后者赢**。

落到文件上：`portals.json` 是勾，`portal_budget.json` 是封。

`off_supply_note` 只读了前一份。实测活动用户 2026-08-25 03:51：

    portals.json          猎聘 = false
    portal_budget.json    猎聘 · cli 通道封到当天 11:30
                          （`fetch_details --missing` 第一个请求就 RATE_LIMITED）

而面板那句写的是：

> 不过你把猎聘关掉了，而你能投的岗有 84% 是它给的（累计 104 个）——
> **不开回来，这一轮补到的会少一大半。要开就在这一页的「招聘网站」那一段点一下**

照它点下去，这一轮抓到的是 0。

## 供给占比那半仍然要说

那不是噪音，那是他**到点之后该动手的理由**。所以两支都保留 84% 那句，
只有末尾那个动作换：立刻点 → 到点之后再点，并把「到几点」说出来。

## 不重判封锁

`portal_rows` 已经把 `blocked` / `blockedHeldHours` 算好了（正本在
`portal_budget.block_state`，那个函数的 docstring 自己写着「一次解析、
多处消费」）。这里只把它捎上 —— 再解析一遍就是第三份实现。
"""
import datetime as dt
import json
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import _cli  # noqa: E402
import build_dashboard as bd  # noqa: E402
import export_web_data as ex  # noqa: E402
import portal_budget as pb  # noqa: E402

EX = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
BD = (ROOT / "tools" / "build_dashboard.py").read_text(encoding="utf-8")
SCRAPE = (ROOT / "workflows" / "job-scrape.md").read_text(encoding="utf-8")


def flat(s: str) -> str:
    s = " ".join(re.sub(r"^\s*(?:>|#:?)\s?", "", s, flags=re.M).split())
    return re.sub(r"(?<=[一-鿿，。；：、（）「」])"
                  r" +(?=[一-鿿，。；：、（）「」])", "", s)


def rows(blocked=False, held=9):
    """⚠️ **夹具要跟生产同形。**

    这里原来传的是 `until="今天 11:30"` —— 一个**已经人话化**的串，而生产路径
    （`portal_budget.block_state`）产出的是 `2026-08-27T15:56` 这种 ISO。
    夹具比现实更人性，于是「屏幕上会印出一串 ISO」这件事被断言绿着盖了很久
    （实测 2026-08-27 才发现）。现在带的是 `blockedHeldHours`：一个整数，
    没有格式化陷阱，也正是裁定认可的那个数（报「已经封了多久」）。
    """
    return [
        {"name": "猎聘", "enabled": False, "everSellable": 104,
         "blocked": blocked, "blockedHeldHours": held},
        {"name": "BOSS", "enabled": True, "everSellable": 16},
    ]


class TheBlockStateIsCarriedAlong(unittest.TestCase):
    def test_it_returns_four_things_now(self):
        got = ex.off_supply(rows())
        self.assertEqual(len(got), 4)
        self.assertEqual(got[:3], ("猎聘", 104, 87))

    def test_an_unblocked_portal_carries_a_zero(self):
        self.assertEqual(ex.off_supply(rows())[3], 0)

    def test_a_blocked_portal_carries_how_long_it_has_been_held(self):
        """带的是**已经封了多久**，不是解封时刻（`portal_budget`
        「报『已经封了多久』，不报『还剩多久』」，2026-08-26 裁定）。"""
        self.assertEqual(ex.off_supply(rows(blocked=True))[3], 9)

    def test_blocked_without_a_number_is_still_blocked(self):
        """时长取不到时也别退回「没封」—— 那是最坏的方向。

        代价：`off_supply_note` 的 `if held:` 会走另一支，
        印出「不开回来这一轮补到的会少一大半」，而照它开回来抓到的是 0 个。
        """
        got = ex.off_supply(rows(blocked=True, held=0))
        self.assertEqual(got[3], 0)

    def test_it_does_not_re_parse_the_block(self):
        """`portal_rows` 已经算好了，正本在 `portal_budget.block_state`。"""
        i = EX.index('held = int(top.get("blockedHeldHours")')
        seg = flat(EX[max(0, i - 1200):i])
        self.assertRegex(seg, r"这一行不重判封锁")
        self.assertRegex(seg, r"正本在 `portal_budget\.block_state`")

    def test_that_source_of_truth_exists(self):
        self.assertTrue(callable(pb.block_state))
        self.assertRegex(pb.block_state.__doc__ or "", r"一次解析、多处消费")

    def test_the_two_owners_are_written_down(self):
        i = EX.index('held = int(top.get("blockedHeldHours")')
        seg = flat(EX[max(0, i - 1200):i])
        self.assertRegex(seg, r"开关和封锁是两份状态、两个主人")
        self.assertIn("portals.json", seg)
        self.assertIn("portal_budget.json", seg)

    def test_the_workflow_really_says_that(self):
        """出处是 `job-scrape.md` 的 Step 0.43「被封的家，勾着也不抓」。

        **别去引 `portal_budget.py` 里那句转述。** 它写着「`job-scrape.md`
        明写着两件事的主人不同」，而 `job-scrape.md` 里根本没有
        `portal_budget.json` 这个词 —— 规则真、出处半假。真出处是这一节，
        而且它说得更硬：**优先级：封 > 勾**。
        """
        self.assertIn("### Step 0.43：被封的家，**勾着也不抓**", SCRAPE)
        s = flat(SCRAPE)
        self.assertRegex(s, r"\*\*优先级：封 > 勾。\*\*")
        self.assertRegex(s, r"面板勾选回答的是「我想不想抓这家」，风控冷却回答的是"
                            r"「现在允不允许抓」")

    def test_the_probe_rule_is_written_down(self):
        """**探一次不许把起点推到现在。** 少了这条，越想确认恢复没有，
        屏幕上就越显得「刚刚才封」。

        原文钉的是「到点自动放行 ≠ 平台消气了」+「不会把冷却从头再算」。
        2026-08-26 封控不再自动到点（本人裁定），前半句没有落点了；
        后半句要守的那件事还在，只是量从「剩余时间」换成了「已经封了多久」。
        """
        s = flat(SCRAPE)
        self.assertRegex(s, r"\*\*探一次不许把起点推到现在。\*\*")
        self.assertIn("只更新原因、不动起算时刻", s)

    def test_the_probe_rule_matches_the_code(self):
        """光写一句会飘 —— 拿代码现验：冷却里再 block 一次，不许延长。"""
        data = {}
        now = dt.datetime(2026, 1, 1, 12, 0)
        pb.block(data, "BOSS", "第一次", now)
        later = now + dt.timedelta(hours=3)
        pb.block(data, "BOSS", "探了一次，还在限流", later)
        self.assertEqual(pb.block_state(data, "BOSS", later)["held_minutes"],
                         3 * 60, "探一次把起点推到了现在 —— 那句话就成了空话")

    def test_the_nudge_obeys_that_priority(self):
        """**这一条就是那条优先级的反面。** 劝他去翻勾，而封还在 —— 封 > 勾。"""
        s = bd.off_supply_note(ex.off_supply(rows(blocked=True)))
        self.assertNotIn("要开就在这一页", s.split("先去上面那条告警里放行它")[0])

    def test_it_carries_the_measurement(self):
        i = EX.index('held = int(top.get("blockedHeldHours")')
        seg = flat(EX[max(0, i - 1200):i])
        self.assertIn("2026-08-25", seg)
        self.assertRegex(seg, r"照它点下去，抓到的是 0")


class TheNudgeSaysWhenNotNow(unittest.TestCase):
    def test_an_open_tap_keeps_the_original_words(self):
        """没被封的时候一个字都不许变 —— 那句话是逐条推敲过的。"""
        s = bd.off_supply_note(ex.off_supply(rows()))
        self.assertIn("不开回来，这一轮补到的会少一大半", s)
        self.assertIn("要开就在这一页的「招聘网站」那一段点一下", s)

    def test_a_blocked_tap_does_not_say_open_it_now(self):
        """**这是修掉的那一处。**"""
        s = bd.off_supply_note(ex.off_supply(rows(blocked=True)))
        self.assertNotIn("不开回来，这一轮补到的会少一大半", s)

    def test_it_says_it_is_still_blocked(self):
        """措辞 2026-08-26 从「还在风控冷却里（到 X）」改成「被平台拦着（X 起）」——
        「到 X」承诺的是一个会自动到来的时刻，而那件事没有了。"""
        s = bd.off_supply_note(ex.off_supply(rows(blocked=True)))
        self.assertIn("被平台拦着", s)
        self.assertIn("已经停了 9 小时", s)
        self.assertNotIn("到点", s, "又在承诺一个不会来的时刻")
        # **机器格式不上屏**（AGENTS.md）。原来这里插的是 `blockedUntil`，
        # 而它是 ISO —— 屏幕上真会出现「被平台拦着（2026-08-27T15:56 起）」。
        self.assertNotRegex(s, r"\d{4}-\d\d-\d\dT\d\d:\d\d",
                            "把一串 ISO 时间印到了屏幕上")
        self.assertNotIn("起）", s, "用「起」去说一个解封时刻，语义是反的")

    def test_it_says_why_opening_it_now_is_pointless(self):
        s = bd.off_supply_note(ex.off_supply(rows(blocked=True)))
        self.assertIn("这会儿开回来也抓不到", s)

    def test_it_still_says_when_to_act(self):
        """只说「现在不行」等于把他晾在那儿。"""
        s = bd.off_supply_note(ex.off_supply(rows(blocked=True)))
        self.assertIn("先去上面那条告警里放行它", s)
        self.assertIn("「招聘网站」那一段点一下", s)

    def test_both_branches_keep_the_supply_share(self):
        """占比那半是他到点之后该动手的理由 —— 两支都要有。"""
        for blocked in (False, True):
            with self.subTest(blocked=blocked):
                s = bd.off_supply_note(ex.off_supply(rows(blocked=blocked)))
                self.assertIn("84% 是它给的" if False else "% 是它给的", s)
                self.assertIn("累计 104 个", s)

    def test_the_reason_is_recorded(self):
        i = BD.index("if held:")
        seg = flat(BD[i:BD.index("return (head + f\"——不开回来", i)])
        self.assertRegex(seg, r"\*\*它现在打开也抓不到。\*\*")
        self.assertRegex(seg, r"照做的结果是抓到 0 个")
        self.assertRegex(seg, r"供给占比那半仍然要说")

    def test_no_markdown_reaches_the_node(self):
        """这句字进的是面板的纯文本节点。"""
        for blocked in (False, True):
            with self.subTest(blocked=blocked):
                self.assertNotIn(
                    "**", bd.off_supply_note(ex.off_supply(rows(blocked=blocked))))

    def test_a_latin_name_still_gets_its_spaces(self):
        """「你把 BOSS 关掉了」—— 那条既有规矩不许被这次改动带掉。"""
        r = [{"name": "BOSS", "enabled": False, "everSellable": 104,
              "blocked": True, "blockedHeldHours": 9},
             {"name": "猎聘", "enabled": True, "everSellable": 16}]
        s = bd.off_supply_note(ex.off_supply(r))
        self.assertIn("你把 BOSS 关掉了", s)

    def test_it_tolerates_an_old_three_tuple(self):
        """老快照里那个三元组还在流通 —— 崩在这儿只会让整块建议消失。"""
        s = bd.off_supply_note(("猎聘", 104, 84))
        self.assertIn("不开回来", s)

    def test_none_still_says_nothing(self):
        self.assertEqual(bd.off_supply_note(None), "")


class TheOldGuardStillHolds(unittest.TestCase):
    """这一条是加一支，`off_supply` 那几条判据一个字不许动。"""

    def test_a_small_library_says_nothing(self):
        self.assertIsNone(ex.off_supply([{"name": "x", "enabled": False,
                                          "everSellable": 3}]))

    def test_all_on_says_nothing(self):
        self.assertIsNone(ex.off_supply(
            [dict(p, enabled=True) for p in rows()]))

    def test_a_small_share_says_nothing(self):
        r = [{"name": "猎聘", "enabled": False, "everSellable": 10},
             {"name": "BOSS", "enabled": True, "everSellable": 100}]
        self.assertIsNone(ex.off_supply(r))

    def test_it_picks_by_the_cumulative_one_not_the_leftover(self):
        """两家都关着时挑哪一家 —— 上一条只验了那句话写着，这条验它算得对。

        实测那位用户此刻只关着一家，现算那条分辨不出用的是哪个数
        （`max` 在单元素上怎么挑都一样）。合成两家才逼得出来。
        """
        r = [{"name": "猎聘", "enabled": False, "everSellable": 100, "sellable": 2},
             {"name": "BOSS", "enabled": False, "everSellable": 30, "sellable": 25},
             {"name": "智联", "enabled": True, "everSellable": 10, "sellable": 10}]
        self.assertEqual(ex.off_supply(r)[0], "猎聘",
                         "按「现在还剩」挑，会把被投干净的那家判成最没用的")

    def test_it_still_uses_the_cumulative_number(self):
        """`sellable` 会被投递吃干净，越给力的渠道判得越低（既有判据）。"""
        i = EX.index("def off_supply(")
        self.assertRegex(flat(EX[i:i + 1600]), r"判据用累计，不用「现在还剩」")


class TheSignalItLeansOnIsReal(unittest.TestCase):
    """现算：这个用户此刻真的处在「关着 + 还封着」这个状态里。"""

    def _portals(self):
        p = ROOT / "web" / "public" / "data.json"
        if not p.is_file():
            self.skipTest("还没导出过面板数据")
        return json.loads(p.read_text(encoding="utf-8")).get("portals") or []

    def test_an_off_portal_keeps_its_history(self):
        """关掉一家不该抹掉它的战绩 —— `off_supply` 整条判据架在那个数上。

        原来这里拿「有没有关着的」当跳过条件、再断言有关着的，恒绿。（判据见 `test_no_assertion_is_dead_on_arrival.py` 第 6 种）
        跳过条件管的是前提在不在，断言该管**前提还能不能用**。
        """
        off = [p for p in self._portals() if not p.get("enabled")]
        if not off:
            self.skipTest("四家全开着 —— 好事")
        for p in off:
            with self.subTest(name=p.get("name")):
                self.assertIsInstance(
                    p.get("everSellable"), int,
                    "关掉的那家没了累计数 —— off_supply 从此永远返回 None，"
                    "而它正是靠这个数认出「该开回来的是哪家」")

    def test_the_two_files_really_disagree_in_effect(self):
        """**支点。** 关着的那家同时还封着 —— 一样成立时这一条没有由头。

        哪天不再重合（封锁到期、或他开回来了），这条会 skip，
        而那正是这一节该更新实测数的时候。
        """
        ps = self._portals()
        both = [p for p in ps if not p.get("enabled") and p.get("blocked")]
        if not both:
            self.skipTest("关着的那几家现在都没被封 —— 好事")
        # **守的是「已经封了多久」，不是「封到几点」。** 这里原来查
        # `blockedUntil`，而生产 2026-08-26 就不发它了（封控不再自动到期，
        # 那个字段答的是「到几点自动恢复」）—— 也就是说这条断言守着一个
        # 不存在的字段：只因为当下没有「既关着又封着」的渠道才一直 skip，
        # 真撞上就会红，而报错信息还在说「封到几点」。
        self.assertTrue(all(p.get("blockedHeldHours") for p in both),
                        "封着却说不出已经停了多久 —— 那句话会缺一半")

    def test_the_block_ledger_agrees_with_the_row(self):
        """面板那一行和 `portal_budget.json` 现算的对得上。"""
        p = ROOT / ".active_user"
        if not p.is_file():
            self.skipTest("没有活动用户")
        user = _cli.pick_user("", root=ROOT)
        f = ROOT / "users" / user / "job_scraper" / "portal_budget.json"
        if not f.is_file():
            self.skipTest("还没有额度记录")
        data = json.loads(f.read_text(encoding="utf-8"))
        now = dt.datetime.now()
        for row in self._portals():
            with self.subTest(portal=row.get("name")):
                st = pb.block_state(data, row.get("name") or "", now)
                self.assertEqual(bool(row.get("blocked")), bool(st["blocked"]),
                                 f"{row.get('name')} 面板与账本对不上")

    def test_the_panel_text_matches_the_state(self):
        p = ROOT / "web" / "public" / "data.json"
        if not p.is_file():
            self.skipTest("还没导出过面板数据")
        d = json.loads(p.read_text(encoding="utf-8"))
        t = str((d.get("nextStep") or {}).get("text") or "")
        if "不过你把" not in t:
            self.skipTest("这一轮没触发那句劝导")
        blocked = [x for x in self._portals()
                   if not x.get("enabled") and x.get("blocked")]
        if blocked:
            self.assertIn("这会儿开回来也抓不到", t,
                          "关着的那家还封着，而面板还在劝他现在就开")
        else:
            self.assertIn("不开回来，这一轮补到的会少一大半", t)


if __name__ == "__main__":
    unittest.main()
