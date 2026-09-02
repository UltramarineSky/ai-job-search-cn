# -*- coding: utf-8 -*-
"""重跑搜索词那一节读了两列，而决定该换词的是第三个问题。

`/job-setup --section search` 的重跑块已经很像样：先跑 `query_yield`，
把「其中高匹配」（分够不够高）和「其中主场」（行业经验对不对得上）分开看，
还专门写了「只看一列会推荐反方向的词」。

**但两列都答不出「这个词抓来的岗在不在他赛道上」。** 那是 `gap_split` 的
「两样都差」那一格，2026-08-23 起它的结论行会直接点名跑偏最多的几个词。

反例就在同一批数据里：

    词           高匹配   主场            跑偏
    开发者工具      2      5（最高）       9/18（50%）
    企业AI应用     11（最高） 2            14/29（48%）
    AI工具         0      0            16/18（89%）

「主场」最高的那个词，抓回来的东西**一半不在他赛道上** —— 因为「主场 5」说的是
「有 5 个行业也对口」，没说另外 13 个是什么。剩下那些可能是「选岗问题」
（专业够、行业不对，还值得改投递面），也可能是「两样都差」（换个词才对）。
**两种该做的事完全相反，而前两列分不出来。**

对这个用户这一列尤其要紧：607 份语料里 374 个（62%）落在「两样都差」。
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
import gap_split as G  # noqa: E402
import query_yield as Q  # noqa: E402

SETUP = (ROOT / "workflows" / "job-setup.md").read_text(encoding="utf-8")


def _rerun() -> str:
    i = SETUP.index("#### 第 2 组：目标岗位与关键词")
    j = SETUP.index("**问：主要岗位方向**", i)
    return SETUP[i:j]


class TheRerunBlockAsksAllThree(unittest.TestCase):
    def test_it_runs_gap_split_too(self):
        self.assertIn("python tools/gap_split.py", _rerun(),
                      "重跑那一节还是只看 query_yield 两列")

    def test_the_table_has_a_row_for_it(self):
        """**只看第一张表。** 这一块下面还有一张反例表，按「从表头往后数第 N 行」
        取会数到那张的表头上去（第一版就是）。切到第一张表结束为止。"""
        seg = _rerun()
        i = seg.index("| 看哪儿 |")
        first = seg[i:]
        end = first.index("\n>\n")            # 表后面那一行只有 `>` 的空行
        rows = [ln for ln in first[:end].splitlines()
                if "|" in ln and "---" not in ln]
        self.assertEqual(len(rows), 4, f"第一张表不是表头 + 三行：{rows}")
        self.assertIn("在不在他这条赛道上", rows[3])
        self.assertIn("gap_split", rows[3], "第三行没说清判据出自哪个工具")

    def test_each_row_says_when_to_look_at_it(self):
        """三列并排摆着而不说各自什么时候看，等于把判断推回给读者 ——
        这一节原来就是靠第三列「什么时候看它」立住的。"""
        seg = _rerun()
        i = seg.index("| 看哪儿 |")
        block = seg[i:i + 700]
        for when in ("短名单不够长", "投出去没回音", "「两样都差」占了大头"):
            with self.subTest(when=when):
                self.assertIn(when, block)

    def test_it_says_the_third_is_not_derivable(self):
        """不写这一句，读者会以为看完两列就覆盖了。"""
        self.assertIn("第三列不是前两列的推论", _rerun())

    def test_the_counterexample_is_there(self):
        """一句「不是推论」没有说服力。要给出那个反着来的词，**连着三个数**。

        **别只验「开发者工具」出现过。** 这一块原来就有一句
        「『开发者工具』高匹配 1、主场 3」—— 把反例整行删掉，那个词照样在，绿。
        变异实测抓到的。"""
        seg = " ".join(_rerun().split())
        self.assertIn("| 开发者工具 | 2 | **5**（这批里最高） | **9/18（50%）** |", seg,
                      "反例那一行没了 —— 只剩一句「不是推论」，没有证据")
        self.assertIn("一半不在他赛道上", seg)

    def test_it_explains_why_the_home_column_cannot_tell(self):
        """「主场 5」说的是有 5 个对口，没说另外 13 个是什么 ——
        这才是两列失效的机理，不写下来下一版会把这一行当冗余删掉。"""
        seg = " ".join(_rerun().split())
        self.assertRegex(seg, r"没说另外 13 个是什么")
        self.assertRegex(seg, r"两种该做的事完全相反")

    def test_the_two_original_columns_survive(self):
        """原来那两列答的是别的问题，不许被这次改动挤掉。"""
        seg = _rerun()
        self.assertIn("分够不够高", seg)
        self.assertIn("行业经验对不对得上", seg)
        self.assertIn("只看一列会推荐反方向的词", seg)
        self.assertIn("query_yield.n_home", seg, "相关系数那条判据的出处没了")

    def test_the_new_word_half_survives(self):
        """「两张表只能给现有的词打分，给不出新词」那半答的是另一个问题。"""
        seg = _rerun()
        self.assertIn("sweetSpot.industries", seg)
        self.assertIn("别直接拿行业名当查询词", seg)


class TheThreeToolsReallyAnswerThreeQuestions(unittest.TestCase):
    """文档说它们不是一回事 —— 这几条盯着代码那边别哪天合成了一个。"""

    def test_gap_split_exposes_the_words(self):
        self.assertTrue(hasattr(G, "off_direction_words"))

    def test_query_yield_still_reports_both_columns(self):
        src = (ROOT / "tools" / "query_yield.py").read_text(encoding="utf-8")
        self.assertIn("其中高匹配", src)
        self.assertIn("其中主场", src)

    def test_a_word_can_be_home_heavy_and_off_heavy_at_once(self):
        """机理测试：主场高不代表跑偏少 —— 两者数的是不同的格。
        「主场」= 专业够 + 行业对口；「跑偏」= 两样都差。
        同一个词可以两头都占，那正是 `开发者工具` 的形状。"""
        def e(skill, dom):
            return {"status": "ranked", "title": "岗", "company": "某公司",
                    "found_by": "甲词",
                    "rank_breakdown": {"四维": f"专业能力{skill}×0.6+业务域{dom}×0.4"}}
        seen = {}
        for i in range(6):                       # 主场：两样都对
            seen[f"h{i}"] = e(90, 80)
        for i in range(14):                      # 两样都差
            seen[f"o{i}"] = e(50, 30)
        box = G.split(seen)
        self.assertEqual(len(box[G.HOME]), 6, "主场那格数错了")
        got = dict((w, off) for w, _n, off in G.off_direction_words(box))
        self.assertEqual(got["甲词"], 14,
                         "有主场就不算跑偏了 —— 两个格被合成了一个")

    def test_the_command_the_block_prints_actually_exists(self):
        """文档让敲的命令必须真能跑 —— 指一条跑不了的命令等于没写。"""
        cmd = re.search(r"python (tools/\w+\.py)", _rerun())
        self.assertTrue((ROOT / "tools" / "gap_split.py").is_file())
        self.assertTrue(cmd and (ROOT / cmd.group(1)).is_file())


if __name__ == "__main__":
    unittest.main()
