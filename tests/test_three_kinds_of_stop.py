# -*- coding: utf-8 -*-
"""退出码 1 有三种含义，只有一种该跳过。

2026-08-26 一天之内为这件事栽了三次，三次同一个形状：**工具报了一个不存在的
「停」，而流程教的是见 1 就收尾**，于是整条通着的渠道闲置一天。

1. **记账把自己劝退了。** `--note` 记完之后才问闸门，拿刚写下的那条动作跟
   自己比间隔，gap 恒等于 0.x 秒 —— 四家全中，每记一次账就回一次
   「记下了，但到线了」并返回退出码 1。
2. **额度是我们自己拍的。** 每轮 10 次、每天 2 轮、每天 60 次请求，
   没有一个来自平台。当天猎聘和 BOSS 都是被「今天已经跑满 2 轮」停掉的，
   而两条通道都是好的。**这四个数 2026-08-26 已经全删了**（本人裁定：额度该由
   平台判，我们只管两次动作之间的间隔），现在的闸门是 `GAP_S` 的 8/4/3 秒 +
   撞了才冷却 24 小时 —— 上面那几个数只是这次事故的现场，不是现行约束。
3. **名字给错了当成整家没戏。** 敲的是 `--round liepin`，而 `liepin` 在这套
   命名里指 CLI 那条通道（`CLI_CHANNELS`），不是整家。

第 3 条最值得记：文档里**早就写着**「渠道名要给准」，照样栽了。一条只在出错
之后才想得起来的规则等于没有规则 —— 所以它现在和另外两种停摆在同一张表里。

这个文件钉两件事：**三种停在消息上真的分得开**（不然那张表没法执行），
以及**那张表还在正本里**。
"""
import datetime as dt
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import portal_budget as pb  # noqa: E402

NOW = dt.datetime(2026, 8, 26, 12, 0, 0)
SCRAPE = (ROOT / "workflows" / "job-scrape.md").read_text(encoding="utf-8")


class TheThreeShapesAreDistinguishable(unittest.TestCase):
    """判据只有两个词：**「太密」= 等，「停着」= 真封**。分不开这张表就没法执行。"""

    def test_a_gap_refusal_says_dense_and_never_says_blocked(self):
        for site in pb.PORTALS:
            with self.subTest(site=site):
                data = {}
                pb.note(data, site, 1, NOW, "navigate")
                ok, why = pb.check(data, site, NOW + dt.timedelta(seconds=1))
                self.assertFalse(ok)
                self.assertIn("太密", why)
                self.assertNotIn("停着", why,
                                 "等一下的消息里出现了「停着」——执行者会当成真封")

    def test_a_real_block_says_blocked_and_never_says_dense(self):
        data = {}
        pb.block(data, "BOSS", "要短信验证", NOW)
        ok, why = pb.check(data, "BOSS", NOW)
        self.assertFalse(ok)
        self.assertIn("停着", why)
        self.assertNotIn("太密", why)

    def test_asking_the_wrong_lane_does_not_condemn_the_site(self):
        """**第 3 次那一栽。** 问 CLI 得到「停着」，而浏览器那条一直通着。"""
        data = {}
        pb.block(data, "liepin-search", "CLI 撞 RATE_LIMITED", NOW)
        self.assertFalse(pb.check(data, "liepin-search", NOW)[0])
        self.assertTrue(pb.check(data, "liepin-browser", NOW)[0],
                        "浏览器那条被 CLI 的封控连坐了")
        self.assertTrue(pb.check(data, "猎聘", NOW)[0],
                        "问整家却答成了 CLI 那条 —— 那正是把通着的渠道判死")

    def test_the_alias_that_caused_it_still_means_the_cli_lane(self):
        """`liepin` 指的是 CLI 那条，不是整家 —— 这不是 bug，是命名。

        判据钉住它，是因为**表里第二行就是照它写的**：哪天它改成落到整家，
        那一行的举例（「你要开浏览器，它说的是 CLI」）就无声地过期了。
        """
        self.assertIn("liepin", pb.CLI_CHANNELS)
        self.assertEqual(pb.lane_of("liepin"), "cli")
        self.assertEqual(pb.site_of("liepin"), "猎聘")

    def test_bookkeeping_never_produces_a_stop(self):
        """第 1 次那一栽的反面：记一笔账不许自己变成一次「停」。"""
        for site in pb.PORTALS:
            with self.subTest(site=site):
                data = {}
                pb.note(data, site, 1, NOW, "navigate")
                self.assertTrue(pb.check(data, site, NOW, after_acting=True)[0])


class TheRuleIsInTheSourceOfTruth(unittest.TestCase):
    def test_the_table_is_in_job_scrape(self):
        self.assertIn("工具说「停手」时，**先分清是哪一种停**", SCRAPE)
        for kind in ("**等**，不是停", "**名字给错了**", "**真封着**"):
            with self.subTest(kind=kind):
                self.assertIn(kind, SCRAPE)

    def test_it_says_how_to_tell_them_apart(self):
        i = SCRAPE.index("工具说「停手」时")
        seg = SCRAPE[i:i + 2000]
        self.assertIn("「太密」", seg, "没给区分「等」的那个词")
        self.assertIn("「停着」", seg, "没给区分「真封」的那个词")
        self.assertIn("接着看它点的是不是你要走的那条", seg,
                      "少了第二步 —— 光看「停着」分不出问错渠道那一种")

    def test_job_auto_points_here_instead_of_repeating(self):
        """`job-auto` 只许指过来，不许再抄一份（抄件与正本必然各自演化）。"""
        auto = (ROOT / "workflows" / "job-auto.md").read_text(encoding="utf-8")
        self.assertIn("先分清工具在说哪一种「停」", auto)
        self.assertIn("job-scrape.md", auto.split("先分清工具在说哪一种「停」")[1][:400])
        self.assertNotIn("| 「动作太密", auto, "把正本那张表抄过来了")

    def test_the_three_incidents_are_on_record(self):
        """规则要带着它的代价，否则下一轮会被当成洁癖删掉。"""
        i = SCRAPE.index("工具说「停手」时")
        seg = SCRAPE[i:i + 3000]
        self.assertIn("2026-08-26", seg)
        self.assertIn("渠道名要给准", seg, "没记「文档早写了照样栽」那一条")


class AWaitIsNotANextStep(unittest.TestCase):
    """`AGENTS.md`：倒计时不能当「下一步」。"""

    def test_the_rule_is_written_down(self):
        a = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("**「等」不是下一步。**", a)
        i = a.index("**「等」不是下一步。**")
        self.assertIn("等的时候能做什么", a[i:i + 400])
        self.assertIn("等完之后敲哪条", a[i:i + 400])

    def test_the_gate_obeys_it(self):
        """真拿闸门验一遍：拒绝语里不许只有倒计时。"""
        data = {}
        pb.block(data, "liepin-search", "CLI 撞 RATE_LIMITED", NOW)
        _ok, why = pb.check(data, "liepin-search", NOW + dt.timedelta(hours=5))
        self.assertNotIn("还剩", why, "倒计时又被当成下一步了")
        self.assertIn("--clear", why, "没给等完之后该敲的那条")
        self.assertIn("浏览器", why, "没说等的时候能做什么")


if __name__ == "__main__":
    unittest.main()
