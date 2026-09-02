# -*- coding: utf-8 -*-
"""批大小跟着通道走 —— 别拿会限流那条的数去卡不限流的那条。

## 规则早就写下来了，只是没接进代码

`job-rank.md`「通道决定批大小，不是拍一个数」：

    `--fetch` 的默认 12 是**为猎聘 CLI 的详情限流定的**

    | 通道 | 限流 | 每批 |
    | 猎聘 CLI detail | 会 | 12，撞到就停 |
    | 猎聘详情页 · 浏览器 | 实测**不限** | 可放大到 20-30 |
    | BOSS / 智联 / 前程 · 浏览器 | 未撞到 | 15 左右 |

    **走浏览器时不必沿用为 CLI 定的保守值。**

而在 2026-09-02 之前，代码里唯一的数是 `DEFAULT_LIMIT = 12`，那张表只存在于文档里。

## 实测代价

`--browser-list` 按它自己的说明「**不发任何请求**」，却用 `args.limit or 40`
取上限 —— 而 `args.limit` 的默认就是那个 12。于是：**待补 100 个，只印 12 条**，
剩下 88 个跟着一句「用 --limit 调」折起来。照这份被截过的名单走，一轮只补得动
12 个，**而截它的那个数来自一条当天根本没在跑的通道**：猎聘 CLI 从 2026-08-27
起 6 天撞了 3 次限流，当时已封 35 小时。

用户当天问的就是这件事：「auto 为跑一次多少，当前默认有点少吧」。

## 判据

三件：**CLI 那条仍然是 12**（它真的会限流，别顺手放大）、
**只读的清单不被它截**、**浏览器通道的数比 CLI 的大**。措辞不钉。
"""

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import fetch_details as fd  # noqa: E402


class TheCliLaneKeepsItsCap(unittest.TestCase):
    """猎聘 CLI 那条**真的会限流**，它的 12 不许被顺手放大。"""

    def test_the_cli_default_is_still_twelve(self):
        self.assertEqual(fd.DEFAULT_LIMIT, 12)

    def test_it_says_where_the_number_came_from(self):
        """这个数的出处要写在它旁边 —— 不然下一个人只看到一个裸常数。"""
        src = (ROOT / "tools" / "fetch_details.py").read_text(encoding="utf-8")
        i = src.index("DEFAULT_LIMIT = 12")
        self.assertIn("CLI", src[max(0, i - 1200):i],
                      "没写清 12 是给猎聘 CLI 定的")


class TheBrowserLanesGetTheirOwnNumbers(unittest.TestCase):

    def test_they_are_bigger_than_the_cli_cap(self):
        """整张表的要点就是这个：浏览器不该沿用 CLI 的保守值。"""
        self.assertGreater(fd.BROWSER_BATCH_DEFAULT, fd.DEFAULT_LIMIT)
        for portal, n in fd.BROWSER_BATCH.items():
            with self.subTest(portal=portal):
                self.assertGreater(n, fd.DEFAULT_LIMIT)

    def test_liepin_browser_is_the_biggest(self):
        """表里只有它写着「实测不限，可放大到 20-30」。"""
        self.assertGreater(fd.BROWSER_BATCH["liepin-browser"],
                           fd.BROWSER_BATCH_DEFAULT)

    def test_the_numbers_are_in_the_documented_range(self):
        """20-30 与「15 左右」—— 不是随便一个更大的数。"""
        self.assertIn(fd.BROWSER_BATCH["liepin-browser"], range(20, 31))
        self.assertIn(fd.BROWSER_BATCH_DEFAULT, range(12, 21))


class TheReadOnlyListIsNotCappedByTheCli(unittest.TestCase):
    """`--browser-list` 不发任何请求，用限流通道的数截它没有道理。"""

    def _run(self, *extra):
        r = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "fetch_details.py"),
             "--browser-list", *extra],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
            errors="replace")
        return r.stdout or ""

    def test_it_lists_everything_by_default(self):
        out = self._run()
        if "没有要补 JD 的岗" in out or not out.strip():
            self.skipTest("这台机器上没有要补 JD 的岗")
        listed = sum(1 for ln in out.splitlines() if ln.startswith("  ["))
        head = [ln for ln in out.splitlines() if "待补 JD" in ln]
        self.assertTrue(head, "没印总数那一行")
        total = int("".join(c for c in head[0] if c.isdigit()) or 0)
        if total <= fd.DEFAULT_LIMIT:
            self.skipTest("待补数本来就不到 12，截不截看不出来")
        self.assertEqual(
            listed, total,
            f"待补 {total} 个只印了 {listed} 条 —— 又拿 CLI 的 "
            f"{fd.DEFAULT_LIMIT} 截了一份只发零个请求的清单")

    def test_an_explicit_limit_still_works(self):
        """显式给了 `--limit` 还是要听 —— 修的是默认值，不是这个开关。"""
        out = self._run("--limit", "3")
        # 干净 clone 里没有活动用户，这条命令把话印到 stderr、stdout 是空的
        # （`_run` 只收 stdout）—— 空串也当「没有要补的岗」跳过，别在空输出上断言。
        if "没有要补 JD 的岗" in out or not out.strip():
            self.skipTest("这台机器上没有要补 JD 的岗")
        listed = sum(1 for ln in out.splitlines() if ln.startswith("  ["))
        self.assertLessEqual(listed, 3)

    def test_it_prints_the_per_channel_plan(self):
        """光不截还不够 —— 要直接给出「这一轮每条通道取几个」。"""
        out = self._run()
        # 干净 clone 里没有活动用户 → stdout 为空（话印在 stderr），照 sibling
        # 一样把空串当「没有要补的岗」跳过。少了这半句，本机绿、clean clone 红。
        if "没有要补 JD 的岗" in out or not out.strip():
            self.skipTest("这台机器上没有要补 JD 的岗")
        self.assertIn("通道上限", out, "没有按通道给出本轮该取几个")
        self.assertIn("本轮取", out)
        # **抬头那句也要在。** 只查上面两个词的话，删掉抬头、留着数据行
        # 照样能过 —— 变异 ④ 实测就是这么钻过去的（2026-09-02）。
        # 那句抬头是这几个数的出处，读的人靠它知道这不是拍的。
        self.assertIn("通道决定批大小", out,
                      "没写这几个数的出处 —— 读的人会以为是拍的")
        self.assertIn("合计", out, "没给这一轮的总数")


if __name__ == "__main__":
    unittest.main()
