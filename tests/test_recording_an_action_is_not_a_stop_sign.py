# -*- coding: utf-8 -*-
"""记一笔账不是「到线了」。

2026-08-26 实测：`--note` 在**记完之后**问 `check()`，于是拿刚写下的那条动作
跟自己比间隔，gap 恒等于 0.x 秒 —— BOSS / 智联 / 前程无忧 / 猎聘四家全中，
记之前一律「可以动」，记之后一律「动作太密：……要隔 8 秒，现在才 0.4 秒」。

代价不在那句话本身，在它的**退出码**：`--note` 把这个 `False` 印成
「记下了，但到线了」并 `return 1`，而 `job-scrape.md` 教的是见 1 就收尾。
于是每记一次账就被劝退一次 —— 今天已经栽过两次的同一个形状
（工具说停 → 整条渠道一天没人动）。

间隔仍然要守。它只是**等**，不是**停**：真睡在 `--wait` 那一处，
这里只负责把那条命令写出来（`AGENTS.md`「每一处引导都要写出该敲的命令」）。

**判据全部跑在合成数据上，不读用户那份额度文件。** 第一版读了，于是当天
下午猎聘刚跑满两轮，`test_without_the_flag_it_still_reads_dense` 就红了 ——
轮上限先于间隔判据返回，断言等的那句「太密」根本没机会出现。
判据要问的是「这段逻辑对不对」，不是「此刻额度剩多少」。
"""
import datetime as dt
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import portal_budget as pb  # noqa: E402

NOW = dt.datetime(2026, 8, 26, 14, 0, 0)


class RecordingIsNotAStopSign(unittest.TestCase):
    def test_every_portal_survives_its_own_bookkeeping(self):
        """四家都要活过「记一笔」——这条判据当初是四家一起红的。"""
        for site in pb.PORTALS:
            with self.subTest(site=site):
                data = {}
                pb.note(data, site, 1, NOW, "navigate")
                ok, why = pb.check(data, site, NOW, after_acting=True)
                self.assertTrue(ok, f"{site} 记完账就被自己劝退了：{why}")
                self.assertNotIn("太密", why)

    def test_without_the_flag_it_still_reads_dense(self):
        """反过来也要成立，否则这条判据在变异之前就是绿的。"""
        for site in pb.PORTALS:
            with self.subTest(site=site):
                data = {}
                pb.note(data, site, 1, NOW, "navigate")
                ok, why = pb.check(data, site, NOW)
                self.assertFalse(ok)
                self.assertIn("太密", why)

    # 原来这儿有一条 `test_a_real_ceiling_still_stops`，验的是「本轮动作上限
    # 照旧要拦」—— 那个上限 2026-08-26 删了（没有固定额度）。
    # 它守的那件事没丢：`after_acting` 不许把**真会让人停手**的判据也跳过。
    # 现在真会让人停手的只剩一条，就是下面那条冷却。

    def test_a_cooldown_still_stops(self):
        """冷却同理：`after_acting` 不许把封控也一起跳过。

        **要两条通道都封才算这家停了。** 只封主通道时判据会红，而红得对：
        那正是 2026-08-21 定下的不对称（CLI 封 ≠ 这家不能动）。
        """
        site = pb.PORTALS[0]
        data = {}
        for chan in (c for c in pb.PORTAL_ALIAS if pb.site_of(c) == site):
            pb.block(data, chan, "测试用", NOW)
        pb.block(data, site, "测试用", NOW)
        ok, why = pb.check(data, site, NOW, after_acting=True)
        self.assertFalse(ok, f"两条通道都封着还说能动：{why}")

    def test_the_cli_points_at_wait_instead_of_stopping(self):
        """命令行那一头：记完不许再印「到线了」，而要写出**该敲的下一条命令**。"""
        src = (ROOT / "tools" / "portal_budget.py").read_text(encoding="utf-8")
        branch = src.split("if a.note:")[1].split('\n    print(f"招聘网站额度')[0]
        self.assertIn("after_acting=True", branch, "--note 还在拿自己刚写的动作比间隔")
        self.assertIn("--wait", branch, "没把 --wait 那条命令写给执行器")
        self.assertIn("--portal", branch, "--wait 不给 --portal 就落不到这家头上")
        self.assertEqual(branch.count("到线了"), 1,
                         "「到线了」不止一处 —— 记账那条又把它印回来了")


class TheFlagIsDocumented(unittest.TestCase):
    def test_check_says_which_question_it_answers(self):
        doc = pb.check.__doc__ or ""
        self.assertIn("after_acting", doc, "新开的口没写进 check 的说明")
        self.assertIn("等", doc)


if __name__ == "__main__":
    unittest.main()
