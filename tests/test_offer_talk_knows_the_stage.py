# -*- coding: utf-8 -*-
"""谈 offer 的那三个数，有一个对应届生不存在。

`/job-offer` Step 1 摆三个数：底线 / 期望 / **当前**。而「当前」那一格写着
「涨幅的分母，也是背调会核的那个数」—— **应届生没有这个数**。整张表的涨幅、
背调核薪都挂在那一格上，硬套的结果是让一个还没工作过的人去算「涨幅百分比」。

国内校招 offer 的结构也不一样：**base 多半按职级定死**（同职级同价，HR 手里
没有改它的权限），能谈的在别处 —— 签字费、职级档位、落户名额与安家费。
而谈法本身也不同：社招是价格连续可调（开口价 / 可守价 / 走人价），
**校招是档位制** —— 谈的不是「多给两千」，是「能不能上一档」。

这是同一条轴上的第三处：简历章节顺序（`05`）、季节日历（`season_note`）、
这里。**工具是照「有经验的社招」写的**，每处都要单独补。
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OFF = (ROOT / "workflows" / "job-offer.md").read_text(encoding="utf-8")


def _grad() -> str:
    i = OFF.index("### 应届生：上面那三个数里有一个不存在")
    return OFF[i:OFF.index("\n### ", i + 4)]


class TheMissingNumberIsCalledOut(unittest.TestCase):
    def test_the_table_row_flags_it(self):
        """在那张表里就说，不要等读者自己发现「当前」填不出来。

        **2026-08-24 放宽：不再要求它点名「应届生」。** 填不出这一格的远不止
        应届生（自有公司经营、自由职业、长期空窗、不愿报），按身份判会把那几种
        全漏掉 —— 实测活动用户那一行写的是「不报：自有公司经营所得」，
        而他的求职状态是「离职」。判据改成「表里说了这一格常常填不出」。
        """
        i = OFF.index("涨幅的分母")
        seg = OFF[i:i + 220]
        self.assertIn("这一格常常给不出一个数", seg,
                      "「当前」那一格没标出它常常填不出来")
        self.assertIn("判据是填不出数，不是身份", seg,
                      "又退回按身份分流了 —— 那会漏掉非应届的那几种")

    def test_the_branch_starts_from_the_profile_field(self):
        """判据和季节日历同源 —— 认「求职状态」，不猜。"""
        self.assertIn("求职状态", _grad(), "没说清按哪个字段分流")


class TheCampusLeversAreNamed(unittest.TestCase):
    def test_it_lists_what_is_actually_movable(self):
        for lever in ("签字费", "职级", "落户"):
            with self.subTest(lever=lever):
                self.assertIn(lever, _grad(), f"没提「{lever}」这条能谈的")

    def test_it_says_what_is_not_movable(self):
        """不说清 base 谈不动，人就会在最没希望的那一项上耗时间。"""
        self.assertRegex(_grad(), r"基本不能|同职级同价",
                         "没说清 base 本身谈不动")

    def test_it_replaces_the_price_frame_with_the_tier_frame(self):
        """社招是价格连续可调，校招是档位制 —— 这是谈法的根本差别。"""
        self.assertRegex(_grad(), r"档位制", "没点出校招是档位制")
        self.assertRegex(_grad(), r"能不能上一档", "没给出对应的问法")

    def test_the_tripartite_penalty_is_folded_in(self):
        """三方违约金是换 offer 的实打实成本，算区间时不能不提。"""
        self.assertIn("三方协议", _grad())

    def test_it_ships_no_amounts(self):
        """违约金各校各企差得远 —— 写一个数就是编。"""
        self.assertRegex(_grad(), r"以他手上那份为准|各校各企差得远",
                         "没说清金额要以他自己那份为准")


class TheSocialPathIsUntouched(unittest.TestCase):
    """多数用户是社招 —— 加分支不能把主路改了。"""

    def test_the_three_numbers_are_still_there(self):
        for n in ("底线", "期望", "当前"):
            self.assertIn(n, OFF)

    def test_the_three_prices_survive(self):
        for n in ("开口价", "可守价", "走人价"):
            self.assertIn(n, OFF)


if __name__ == "__main__":
    unittest.main()
