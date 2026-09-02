# -*- coding: utf-8 -*-
"""命令帮助要分两层：新手照着走的那条脊梁，和每条命令的具体说明。

用户 2026-08-13：「在命令说明里提供供新手简单使用的命令和具体的每个命令的说明，
适合后期进阶」。原来只有一层——20 条命令平铺，各带几个敲法举例。
两头都不够用：新手不知道从哪条开始，老手不知道**不填参数会怎样**。

第二件事尤其重要：裸命令是**最常被敲的形式**（不知道填什么的时候人就先敲一下看看），
而它的行为原来只写在 `workflows/<名>.md` 里——要读那个文件才知道，
而面板存在的意义正是消灭这个动作。
"""

import re
import sys
from difflib import SequenceMatcher
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "tools"))

import jsx  # noqa: E402  两标记切片，别再写第二份

import export_web_data as ex  # noqa: E402


class EveryCommandSaysWhatBareDoes(unittest.TestCase):

    def setUp(self):
        self.items = [it for g in ex.parse_commands() for it in g["items"]]
        self.assertGreaterEqual(len(self.items), 15, "索引像是没解析出来")

    def test_all_have_the_fourth_column(self):
        miss = [it["name"] for it in self.items if not (it.get("bare") or "").strip()]
        self.assertEqual(miss, [],
                         "这些命令没写「不给参数时」，用户得去翻 workflows 才知道：\n  "
                         + "\n  ".join(miss))

    def test_it_is_a_sentence_not_a_shrug(self):
        """「见文档」「同上」这类等于没写。"""
        bad = [f"{it['name']}：{it['bare']}" for it in self.items
               if len(it["bare"]) < 6 or re.search(r"见文档|同上|待补|TODO|无$", it["bare"])]
        self.assertEqual(bad, [], "\n  ".join(bad))

    def test_it_does_not_just_repeat_the_description(self):
        """第四列复述第一列 = 白占一行。

        实测四条这样：`/job-resume` 的「审你那份主简历，只报问题不改数字」
        对着说明「审一遍你的主简历，只报问题、不改你的数字」，一个字没多给。
        该写的是取值、范围、边界——默认取哪个数、扫哪些文件、跑到什么时候停。
        """
        def norm(x):
            return re.sub(r"[，。、：（）「」·\s*`]", "", x)
        bad = []
        for it in self.items:
            r = SequenceMatcher(None, norm(it["does"]), norm(it["bare"])).ratio()
            if r > 0.45:
                bad.append(f"{it['name']}（{r:.2f} 相似）：{it['bare']}")
        self.assertEqual(bad, [],
                         "这几条第四列只是把说明换了个说法：\n  " + "\n  ".join(bad))

    def test_the_similarity_check_can_fail(self):
        """变异内建：真复述必须被抓到，真补充必须放行。"""
        def norm(x):
            return re.sub(r"[，。、：（）「」·\s*`]", "", x)
        same = SequenceMatcher(None, norm("审一遍你的主简历，只报问题、不改你的数字"),
                               norm("审你那份主简历，只报问题不改数字")).ratio()
        self.assertGreater(same, 0.45, "复述没被判为重复，这条检查是摆设")
        diff = SequenceMatcher(None, norm("审一遍你的主简历，只报问题、不改你的数字"),
                               norm("审的是主简历 resume/main.typ，不是某次投递的定制版；只出报告，一个字不改")).ratio()
        self.assertLess(diff, 0.45, "真正的补充信息被误判成重复了")

    def test_no_internal_jargon_leaks(self):
        """这一列直接印在面板上，内部词不许出现（同 AGENTS.md 那张对照表）。"""
        BAD = ["硬门", "四维", "判词", "台账", "驾驶舱", "短名单", "能力边界"]
        hit = [f"{it['name']}：「{w}」" for it in self.items
               for w in BAD if w in it["bare"]]
        self.assertEqual(hit, [], "\n  ".join(hit))

    def test_the_parser_tolerates_a_three_column_table(self):
        """老表只有三列时不能炸，也不许凭空编一个默认行为。"""
        from build_dashboard import parse_commands  # noqa: F401
        src = (ROOT / "tools" / "build_dashboard.py").read_text(encoding="utf-8")
        self.assertIn('if len(cells) > 3 else ""', src,
                      "第四列缺失时没有兜底，三列的老表会 IndexError")

    def test_the_panel_actually_renders_it(self):
        """有数据没人渲染等于没有。"""
        tsx = (ROOT / "web" / "src" / "components" / "CommandBook.tsx").read_text(encoding="utf-8")
        self.assertIn("it.bare", tsx)
        self.assertIn("不填参数", tsx)
        types = (ROOT / "web" / "src" / "types.ts").read_text(encoding="utf-8")
        self.assertIn("bare?: string", types)


class TheBeginnerLayerExists(unittest.TestCase):
    """第一层：新手照着敲的脊梁那几条，必须和下面平铺的全集区分开。

    **这里不写死是几条** —— 那个数的正本是
    `test_the_spine_is_three_commands.SPINE`，写死第二份就等着它们分叉
    （这个文件自己就栽过：2026-09-03 脊梁改成三条时，这里还断言着「两条」）。
    """

    def test_panel_has_a_spine_block(self):
        tsx = (ROOT / "web" / "src" / "components" / "CommandBook.tsx").read_text(encoding="utf-8")
        self.assertIn("cmdbook-spine", tsx)
        # **切到渲染出来的那个块再查。** 对整份文件搜的话，命中的是文件顶部
        # JSDoc 注释里那句「日常就这三条」——注释和界面各说各的时它照样绿，
        # 而判据本来就是要看用户屏幕上那行字。
        block = jsx.between(tsx, "cmdbook-spine", "{!spineOnly")
        # 脊梁数跟着 `AGENTS.md`「一次跑到头」走——这里只确认块还在、kicker 还在，
        # 数对不对由 `test_the_spine_is_three_commands.ThePanelSpineAgreesToo` 管。
        self.assertRegex(block, r"日常就这[一两三四五]条")

    def test_the_spine_is_visually_separated(self):
        """和下面 18 条一样平铺就等于没突出。"""
        css = (ROOT / "web" / "src" / "theme" / "cockpit.css").read_text(encoding="utf-8")
        self.assertIn(".cmdbook-spine", css)


if __name__ == "__main__":
    unittest.main()
