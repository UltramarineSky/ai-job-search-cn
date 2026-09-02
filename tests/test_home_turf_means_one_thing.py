# -*- coding: utf-8 -*-
"""「主场」在这个仓库里只许有一个意思。

它曾经有两个，而且两边的业务域阈值都是 60，**看着更像该一致**：

    面板「市场怎么读你的简历」   只看业务域 ≥60            107 个
    `gap_split` 四格 / `/job-upskill` / `query_yield`
                              业务域 ≥60 **且** 专业能力 ≥70    41 个

（上面这两个数是 2026-08-22 当时的。专业能力那条线 2026-08-23 从 70 改成 60
——70 不是框架里任何一档的下沿，判据见 `gap_split.STACK_OK`。窄口径因此变成
51 个。**这里不跟着改数**：它记的是当时那次对比，改了就成了伪造的历史；
这条测试要钉的是「两个口径不许共用『主场』这个名字」，与具体数值无关。）

实测 2026-08-22：宽的那个算出 107 个，而其中 **66 个（61%）专业能力其实不够** ——
「主场」这个词的意思是「两样都对得上」，用它称呼只查了一维的结果是**名过其实**。

窄的那个保留「主场」（它本来就是那个意思），宽的那个改叫「行业对口的岗」。
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import export_web_data as X  # noqa: E402
import gap_split as gs  # noqa: E402

#: 用户看得见的字在这几处。注释里可以照常讨论两者的分别 ——
#: 那正是这条规矩要留下的东西（前几轮栽过三次「测试禁止把理由写下来」）。
_TSX = (ROOT / "web" / "src" / "components"
        / "ResumeRead.tsx").read_text(encoding="utf-8")
#: 两种注释都要剥：`{/* … */}`（JSX）和 `/** … */`（文件头 JSDoc）。
#: 只剥前一种时，残留的是文件头那段说明 —— 而那正是最该能自由讨论两个定义的地方。
_TSX_CODE = re.sub(r"\{/\*[\s\S]*?\*/\}|/\*[\s\S]*?\*/", "", _TSX)
_APP = (ROOT / "web" / "src" / "App.tsx").read_text(encoding="utf-8")


class TheWideOneIsNotCalledHomeTurf(unittest.TestCase):
    def test_the_panel_section_says_what_it_measured(self):
        self.assertIn("行业对口的岗", _TSX_CODE, "面板那一栏没改名")
        self.assertNotIn("主场", _TSX_CODE, "面板上还在管只看一维的结果叫「主场」")

    def test_the_collapsible_header_too(self):
        """标题行上那个数是不点开也能看见的 —— 名字错在那儿最贵。"""
        i = _APP.index("resumeInsight.sweetSpot.count")
        self.assertIn("行业对口", _APP[max(0, i - 120):i], "折叠标题上还写着「主场」")

    def test_the_two_definitions_really_differ(self):
        """判据的前提：两者真的不是一回事。哪天它们合并了，这个文件就该删。"""
        self.assertEqual(X.SWEET_SPOT_DOMAIN, 60)
        # 业务域够、专业能力不够 —— 宽的算它，窄的不算
        self.assertGreaterEqual(65, X.SWEET_SPOT_DOMAIN)
        self.assertNotEqual(gs.quadrant(50, 65), gs.HOME,
                            "专业能力 50 也算主场的话，两个定义就一样了")
        self.assertEqual(gs.quadrant(80, 65), gs.HOME)


class TheNarrowOneKeepsTheName(unittest.TestCase):
    def test_gap_split_still_calls_it_home(self):
        self.assertEqual(gs.HOME, "主场")

    def test_the_upskill_table_spells_out_the_difference(self):
        """同一个文件里两个概念都要用到 —— 不写清楚，下一个读的人还得再推一遍。"""
        up = (ROOT / "workflows" / "job-upskill.md").read_text(encoding="utf-8")
        self.assertIn("行业对口的岗", up, "宽的那个在文档里没改名")
        self.assertRegex(up, r"这张表里的「主场」\s*=\s*两样都对得上",
                         "四格表旁边没说清它的「主场」是窄义")

    def test_no_doc_still_defines_home_as_domain_only(self):
        """「主场岗（业务域 ≥60）」这种写法是旧的宽义 —— 不许再出现。"""
        for name in ("job-upskill.md", "job-resume.md"):
            p = ROOT / "workflows" / name
            with self.subTest(doc=name):
                self.assertNotRegex(
                    p.read_text(encoding="utf-8"), r"主场岗（业务域",
                    f"{name} 里还留着按一维定义的「主场」")


if __name__ == "__main__":
    unittest.main()
