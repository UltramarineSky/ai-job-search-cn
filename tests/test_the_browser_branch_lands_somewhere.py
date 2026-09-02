# -*- coding: utf-8 -*-
"""「要登录 → 走浏览器那条路，**不是死路**」—— 然后就没有下文了。

`/job-add-portal` Step 2 侦察完会分流：有免登录接口的落第 1 层（脚手架 CLI），
要登录或撞反爬的落第 2 层（浏览器扩展）。那段分流写得很好，还专门反驳了
「这个平台接不了」的说法：**仓库里恰好有现成的路**（BOSS / 智联 / 前程无忧
就是这么抓的）。

**可 Step 5「注册」只写了 CLI 那一支**，Step 6 的收尾照旧报
「portal 技能 `<name>` 已生成并验证通过」—— 对浏览器那一支，那是一句假话，
而且用户拿不到任何「接下来动哪儿」的指引。那句「不是死路」在这里断掉了。

## 浏览器那一支真正要动的四处

实测（照 BOSS / 智联 / 前程无忧现在的接法反推）：

    workflows/reference/cdp-portals.md 「各渠道入口」   页面结构、字段位置、登录态检查
    tools/query_yield.py 的 PORTALS / PORTAL_ALIAS      平台列 + 各驱动方式的别名
    tools/export_web_data.py 的平台元信息               how / needsLogin / jd / note
    workflows/reference/search-queries.md              `site:` 兜底

**`PORTALS` 那一处漏了最难查**：`portal_budget` 从它 import，额度闸门、
状态行、面板那几行全按它遍历。不加进去，这家抓回来的岗落进「其它」、
跑过的格子不留痕，而 `query_yield` 会**永远**把它当成「还没跑过的平台」推荐。
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import portal_budget as PB  # noqa: E402
import query_yield as Q  # noqa: E402

ADD = (ROOT / "workflows" / "job-add-portal.md").read_text(encoding="utf-8")
CDP = (ROOT / "workflows" / "reference"
       / "cdp-portals.md").read_text(encoding="utf-8")


def _step5() -> str:
    i = ADD.index("## Step 5: 注册")
    return ADD[i:ADD.index("## Step 6", i)]


def _step6() -> str:
    i = ADD.index("## Step 6")
    return ADD[i:ADD.index("## 设计原则", i)]


class TheBrowserBranchHasSomewhereToGo(unittest.TestCase):
    def test_step5_splits_by_layer(self):
        self.assertIn("落在第 2 层（浏览器）的，走这一节的另一支", _step5(),
                      "注册那一步仍然只认 CLI")

    def test_it_lists_every_place_to_touch(self):
        seg = _step5()
        for where in ("cdp-portals.md", "PORTALS", "PORTAL_ALIAS",
                      "export_web_data.py", "search-queries.md"):
            with self.subTest(where=where):
                self.assertIn(where, seg, f"没说要动 {where}")

    def test_it_says_which_omission_is_worst(self):
        """四处并列摆着，漏哪个都一样吗 —— 不一样，`PORTALS` 漏了最难查。"""
        seg = " ".join(_step5().split())
        self.assertRegex(seg, r"`PORTALS` 那一处漏了最难查")
        self.assertRegex(seg, r"永远\*\*把它当成「还没跑过的平台」推荐",
                         "没说清漏了会怎样")

    def test_it_points_at_an_existing_example_for_each(self):
        """「照谁写」比「写什么」有用得多 —— 三家现成的就在那儿。"""
        seg = _step5()
        i = seg.index("| 动哪儿 |")
        table = seg[i:i + 900]
        self.assertIn("照谁写", table, "表里没有「照谁写」这一列")
        self.assertRegex(table, r"那一节现有的三家")
        self.assertIn('"BOSS"', table, "元信息那一行没给样板")

    def test_it_replaces_the_cli_smoke_test(self):
        """Step 4 的联调是 CLI 专属的。浏览器那支没有 CLI 可跑，
        不换一个验收就等于没有验收。"""
        seg = " ".join(_step5().split())
        self.assertRegex(seg, r"没有 CLI 可跑，也就没有 Step 4 的联调")
        self.assertRegex(seg, r"真跑一次搜索")

    def test_it_names_the_dangling_promise(self):
        """这一段看着像补充说明，理由要挨着写：那句「不是死路」原来断在这儿。"""
        self.assertRegex(" ".join(_step5().split()),
                         r"那句「不是死路」在这里就断了")


class TheSummaryDoesNotClaimASkillWasBuilt(unittest.TestCase):
    def test_it_branches_first(self):
        self.assertRegex(" ".join(_step6().split()), r"先看这家落在第几层")

    def test_the_browser_summary_says_browser(self):
        seg = _step6()
        self.assertIn("走浏览器渠道（要你在 Chrome 里登录）", seg)

    def test_it_calls_the_cli_wording_a_lie_for_that_branch(self):
        self.assertRegex(" ".join(_step6().split()), r"照 CLI 那套报会是一句假话")

    def test_the_browser_summary_tells_him_where_it_lives(self):
        """收尾要说清东西落在哪，否则下次抓不到他不知道去哪看。"""
        seg = _step6()
        self.assertIn("cdp-portals.md", seg)
        self.assertRegex(" ".join(seg.split()), r"是不是被勾掉了")

    def test_the_cli_summary_survives(self):
        """第 1 层那份收尾一个字不能少 —— 它是这条命令的主路。"""
        seg = _step6()
        self.assertIn("portal 技能 `<name>` 已生成并验证通过", seg)
        self.assertIn("cli/src/cli.ts search", seg)


class TheFourPlacesReallyAreTheFourPlaces(unittest.TestCase):
    """文档说动这四处 —— 那四处得真的存在，而且真的按平台遍历。"""

    def test_portals_is_a_list_of_display_names(self):
        self.assertIn("BOSS", Q.PORTALS)
        self.assertIn("猎聘", Q.PORTALS)

    def test_the_budget_shares_that_list(self):
        """漏登记最贵的那一处 —— 额度闸门和状态行都按它遍历。"""
        self.assertIs(PB.PORTALS, Q.PORTALS)

    def test_the_alias_table_folds_every_driver(self):
        """同一家的 CLI / cdp / browser 要归同一列，否则跑过的格子不留痕。"""
        for alias in ("boss-browser", "boss-cdp", "BOSS直聘"):
            with self.subTest(alias=alias):
                self.assertEqual(Q.PORTAL_ALIAS[alias], "BOSS")

    def test_every_alias_target_is_a_known_portal(self):
        for alias, name in Q.PORTAL_ALIAS.items():
            with self.subTest(alias=alias):
                self.assertIn(name, Q.PORTALS,
                              f"{alias} 指向的「{name}」不在 PORTALS 里")

    def test_the_panel_meta_covers_every_portal(self):
        """面板那几行漏一家，它在「招聘网站」那一块就勾不上。"""
        src = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        for name in Q.PORTALS:
            with self.subTest(portal=name):
                self.assertRegex(src, rf'"{re.escape(name)}": {{"how"',
                                 f"{name} 没有面板元信息")

    def test_the_cdp_reference_has_a_per_portal_section(self):
        self.assertIn("## 各渠道入口", CDP)
        i = CDP.index("## 各渠道入口")
        seg = CDP[i:]
        for name in ("BOSS", "智联", "前程无忧"):
            with self.subTest(portal=name):
                self.assertIn(name, seg, f"{name} 在「各渠道入口」里没有一节")


class TheLayerRoutingItDependsOnIsIntact(unittest.TestCase):
    """这一支的前提是 Step 2 真的会把人分流过来。"""

    def test_step2_still_routes_login_walls_to_layer_two(self):
        i = ADD.index("## Step 2")
        seg = ADD[i:ADD.index("## Step 3", i)]
        self.assertRegex(" ".join(seg.split()), r"要登录才看得到列表 → 这套模式到此为止")
        self.assertIn("不是死路", seg)

    def test_step2_still_refuses_to_bypass_anti_bot(self):
        """绕过 WAF 换来的是封号和一条随时会碎的链路 —— 这条不许被这次改动稀释。"""
        i = ADD.index("## Step 2")
        seg = ADD[i:ADD.index("## Step 3", i)]
        self.assertIn("绝不绕过挑战", seg)

    def test_the_layer_table_still_exists(self):
        i = ADD.index("## Step 2")
        seg = ADD[i:ADD.index("## Step 3", i)]
        self.assertIn("| 侦察结果 | 落在哪一层 | 本命令怎么办 |", seg)


if __name__ == "__main__":
    unittest.main()
