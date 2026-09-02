# -*- coding: utf-8 -*-
"""面板上「N 个岗 · M 个可以投」里那个 M 是**存量残余**，而它被读成**产能**。

`sellable` 减掉了已投、已下线、他自己跳过的 —— 也就是说**越给力的渠道，
这个数被吃得越干净**。单印它，结论会反过来。

实测活动用户 2026-08-24：

    渠道      抓到    还剩能投   累计判过能投
    猎聘      2232      5          104
    BOSS       125      1           16
    智联         86      0            4
    前程无忧    194      0            0

按「还剩」读：猎聘 2232 → 5，四家里最差。
按「累计」读：猎聘一家占了全部可投岗的 **83%**（104/124），是其余三家总和的 5.2 倍。

**而他把猎聘关掉了**，同一块面板还在劝他「旺季用来补新的」——
关掉的那家上一轮贡献了 150 个新岗，开着的三家合计 87 个。

## 命中率不能单独用来做取舍

那条 note 原来的结论是「一百个岗里只有五个能投——**抓得多不等于捞得多**」。
命中率没错，结论错：BOSS 命中率 30% 最高，可它**一次只给 15 个、没有下一页**
（它自己那条 note 就写着）。率再高也乘不上去 —— 取舍要看**率 × 产量上限**。

## 这是这个仓库点过名的那一类

「一个数说的是一件事，措辞说的是另一件事」——同「这家你已经投过 N 个岗」
那条（数的是有史以来，说的是「短期内」）。修法也一样：**两个口径都给，
各自说清是什么。**
"""
import json
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import export_web_data as ex  # noqa: E402

EX = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
TSX = (ROOT / "web" / "src" / "components"
       / "Portals.tsx").read_text(encoding="utf-8")
TYPES = (ROOT / "web" / "src" / "types.ts").read_text(encoding="utf-8")


def flat(s: str) -> str:
    s = " ".join(re.sub(r"^\s*(?:>|#:?|//:?|\*)\s?", "", s, flags=re.M).split())
    return re.sub(r"(?<=[一-鿿，。；：、（）「」])"
                  r" +(?=[一-鿿，。；：、（）「」])", "", s)


def portals():
    p = ROOT / "web" / "public" / "data.json"
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8")).get("portals")


class BothMeaningsAreShipped(unittest.TestCase):
    def test_the_cumulative_count_exists(self):
        """**盘上那份 `data.json` 是产物，不是源码。**

        第一版只查它 —— 而它是上一次导出留下的文件，把这个字段从 payload 里
        整个删掉、不重跑导出，它照样在（变异实测）。所以先钉源码里那一行，
        再拿产物做一次现算校验。
        """
        self.assertIn('"everSellable": by[name]["everSellable"],', EX,
                      "payload 里不再带这个字段了")
        ps = portals()
        if not ps:
            self.skipTest("还没导出过面板数据")
        for p in ps:
            with self.subTest(p=p["name"]):
                self.assertIn("everSellable", p)

    def test_it_does_not_subtract_the_ones_he_acted_on(self):
        """**这是它和 `sellable` 唯一的区别，也是它存在的全部理由。**"""
        i = EX.index("ever_ids = {j.get(")
        body = EX[i:i + 200]
        self.assertNotIn("applied", body)
        self.assertNotIn("expired", body)
        self.assertNotIn("skipped", body)

    def test_it_still_drops_duplicates(self):
        """重复挂牌算两个就是虚高 —— 那一项两个口径都要减。"""
        i = EX.index("ever_ids = {j.get(")
        self.assertIn("dupOf", EX[i:i + 200])

    def test_it_is_never_smaller_than_what_is_left(self):
        """现算：累计是「还剩」的超集，反过来就是算错了。"""
        ps = portals()
        if not ps:
            self.skipTest("还没导出过面板数据")
        for p in ps:
            with self.subTest(p=p["name"]):
                self.assertGreaterEqual(p["everSellable"], p["sellable"])

    def test_the_reason_is_recorded(self):
        i = EX.index("ever_ids = {j.get(")
        seg = flat(EX[max(0, i - 1600):i])
        self.assertRegex(seg, r"是「现在还剩几个能投」，不是「这家给过我几个」")
        self.assertRegex(seg, r"越是给力的渠道，这个数被吃得越干净")
        self.assertIn("2026-08-24", seg)

    def test_the_reason_carries_both_readings(self):
        i = EX.index("ever_ids = {j.get(")
        seg = flat(EX[max(0, i - 1600):i])
        self.assertRegex(seg, r"按「还剩」读：猎聘 2232→5 是四家里最差的一个")
        self.assertRegex(seg, r"按「累计」读")

    def test_the_reason_names_the_cap_asymmetry(self):
        """命中率不能单独用来做取舍 —— 这是整条的落点。"""
        i = EX.index("ever_ids = {j.get(")
        seg = flat(EX[max(0, i - 1600):i])
        self.assertRegex(seg, r"一次只给 15 个、没有下一页")
        self.assertRegex(seg, r"率再高也乘不上去")


class ThePanelPrintsThemApart(unittest.TestCase):
    def test_both_are_rendered(self):
        self.assertIn("累计 {p.everSellable} 个能投", TSX)
        self.assertIn("现在还剩 {p.sellable} 个", TSX)

    def test_the_leftover_one_is_labelled(self):
        """光印一个数字，读的人会按自己的默认理解去读 —— 而那个默认是反的。"""
        i = TSX.index("{p.sellable} 个")
        self.assertIn("现在还剩", TSX[max(0, i - 40):i])

    def test_the_cumulative_one_comes_first(self):
        """产能是做取舍时该先看的那个。"""
        self.assertLess(TSX.index("everSellable} 个能投"),
                        TSX.index("现在还剩 {p.sellable}"))

    def test_the_reason_is_recorded_next_to_it(self):
        """开头那句和后面的解释都要钉 —— 只钉后半句，把开头换成
        「两个数。」照样绿（变异实测），而开头那句才是说清区别的那一句。"""
        i = TSX.index("p.everSellable > 0")
        seg = flat(TSX[max(0, i - 900):i])
        self.assertRegex(seg, r"\*\*两个口径分开印。\*\*")
        self.assertRegex(seg, r"是「现在还剩几个能投」")
        self.assertRegex(seg, r"越给力的渠道\s*这个数被吃得越干净")
        self.assertRegex(seg, r"单印它会得出反的结论")

    def test_the_type_says_which_is_which(self):
        for k, want in (("sellable: number;", r"现在\*\*还剩\*\*几个能投"),
                        ("everSellable: number;", r"\*\*这个才是产能。\*\*")):
            with self.subTest(k=k):
                i = TYPES.index("  " + k)
                self.assertRegex(flat(TYPES[max(0, i - 700):i]), want)


class TheNoteStopsConcludingFromTheRate(unittest.TestCase):
    def _note(self) -> str:
        return ex.PORTAL_FACTS["猎聘"]["note"]

    def test_it_no_longer_ends_on_the_wrong_conclusion(self):
        """「抓得多不等于捞得多」把 83% 的供给劝退了。"""
        self.assertNotIn("抓得多不等于捞得多", self._note())

    def test_it_still_states_the_low_rate(self):
        """命中率是真的，不许为了纠偏把它藏掉。"""
        self.assertIn("一百个岗里只有五个能投", self._note())

    def test_it_states_the_share_that_matters(self):
        self.assertRegex(self._note(), r"能投的岗有八成来自它")

    def test_it_names_why_the_rate_alone_misleads(self):
        # 「封顶」是 `test_web_copy` 词表里的内部词 —— 这句话直接上面板，
        # 换成人话（第一版就栽在这儿）。
        self.assertRegex(self._note(), r"别家一次就给那么多，命中率再高也乘不上去")

    def test_no_markdown_reaches_the_panel(self):
        """这几条 note 直接进纯文本节点（`AGENTS.md`「给用户看的措辞」末尾那条）。"""
        for name, f in ex.PORTAL_FACTS.items():
            with self.subTest(name=name):
                self.assertNotIn("**", f["note"])
                self.assertNotIn(chr(96), f["note"])

    def test_the_capped_portal_still_says_it_is_capped(self):
        """这一整条建立在 BOSS 那条 note 上 —— 它没了，「封顶」就没了依据。"""
        self.assertRegex(ex.PORTAL_FACTS["BOSS"]["note"],
                         r"一次只给 15 个、没有下一页")


class TheSignalItLeansOnIsReal(unittest.TestCase):
    """现算：两个口径真的给出相反的排名。"""

    def _ps(self):
        ps = portals()
        if not ps:
            self.skipTest("还没导出过面板数据")
        if sum(p["everSellable"] for p in ps) < 20:
            self.skipTest("可投的岗太少，排不出名次")
        return ps

    def test_the_two_readings_disagree(self):
        """**这是整条的支点。** 两个口径给出同一个第一名时，这条就没必要了。"""
        ps = self._ps()
        by_left = max(ps, key=lambda p: p["sellable"])["name"]
        by_ever = max(ps, key=lambda p: p["everSellable"])["name"]
        if by_left == by_ever:
            self.skipTest("两个口径现在指向同一家 —— 那这一节的实测数该更新了")
        self.assertNotEqual(by_left, by_ever)

    def test_one_portal_dominates_the_cumulative_yield(self):
        ps = self._ps()
        tot = sum(p["everSellable"] for p in ps)
        top = max(p["everSellable"] for p in ps)
        self.assertGreater(
            top, tot * 0.5,
            f"没有哪一家占大头了（最高 {top}/{tot}）—— "
            f"这一节引的 83% 过时了，去更新")

    def test_the_dominant_one_is_switched_off(self):
        """**这才是它现在真的在伤人的地方。** 他哪天开回来，这条会 skip。"""
        ps = self._ps()
        top = max(ps, key=lambda p: p["everSellable"])
        if top["enabled"]:
            self.skipTest("贡献最大的那家已经开着了 —— 好事")
        # 跳过条件只保证「贡献最大的那家关着」。该断言的是**那句劝导指的就是它**
        # —— 判据一旦换回 `sellable`，它会指向另一家（这一整节说的就是这件事），
        # 那时这条才红得出来。原来这里再判一遍 `enabled`，两条路都不会红。（判据见 `test_no_assertion_is_dead_on_arrival.py` 第 6 种）
        got = ex.off_supply(ps)
        self.assertIsNotNone(got, "关着的那家占了大头，面板却一个字都不说")
        self.assertEqual(
            got[0], top["name"],
            f"面板劝他开的是「{got[0]}」，而累计贡献最大的是「{top['name']}」")


if __name__ == "__main__":
    unittest.main()
