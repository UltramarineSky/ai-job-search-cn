# -*- coding: utf-8 -*-
"""52 份深评把「缺口」写成了表格，`parse_gaps` 只认项目符号，于是面板说「没有缺口」。

`parse_gaps` 自己的 docstring 里就写着这类错误有多贵：

> 这个字段原来**根本没有解析器**……于是深评明明写了缺口和不能吹的说法，
> 页面却对每个岗都渲染「这个岗没有（对不上的地方）」——**把「上游丢了数据」
> 说成「核对过没问题」**，正是 GateStamp 注释里点名的最危险错误类。

**同一件事又在它自己身上发生了一次**，只是这次不是「没有解析器」，
是解析器只认一种形状。

实测活动用户 2026-08-23：264 份有缺口小节的深评里，**52 份写成了三列表格**
（`| 缺口 | 严重程度 | 怎么讲 |`），共 **137 条缺口**一条都没进面板。

## 这次跑偏的是写手，不是解析器 —— 但仍然收下

和 `parse_quality` 那次相反：那次规格给的就是纯文本项目符号、而解析器要粗体标题；
这次规格给的是 `- ...`、而那 52 份自己长出了表格。

照样收，两条理由：**那 137 条已经写在盘上了**，拒收只是继续丢；而且表格
**比 bullet 多一列**（严重程度），扔掉不划算。

## 严重程度放进 `kind`

实测面板上原有 719 条缺口的 `kind` **全是空的** —— 那个 chip 一次都没渲染过。
所以两种来源共用它不会撞车。判据统一成「写手在那个位置放的短标签，原样显示」。

改完：**256 份 / 856 条**（原 212 / 719）。
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import export_web_data as ex  # noqa: E402

EX = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
EVAL = (ROOT / "workflows" / "reference"
        / "04-job-evaluation.md").read_text(encoding="utf-8")

TABLE = """## 缺口
| 缺口 | 严重程度 | 怎么讲 |
|---|---|---|
| 薪资低于底线 | **决定性**（一眼可见） | 开场白第一件事就把区间对齐 |
| 与算法团队深度对话 | 中 | 这是你写明的能力边界，如实说 |

## 下一节
"""

#: **列顺序换过**。按下标取会把「怎么讲」当成缺口名 —— 这份夹具专治那个。
SHUFFLED = """## 缺口
| 怎么讲 | 缺口 | 严重程度 |
|---|---|---|
| 如实说，别绕 | 没带过十人以上团队 | 高 |

## 下一节
"""

#: **下一节里也有项目符号**。不在 `##` 处停的话会把它们一起收进来。
SPILL = """## 缺口
- 本节的一条——实情

## 建议
- 下一节的一条，不该算进缺口
"""

BOTH_FIXTURE = """## 缺口
| 缺口 | 严重程度 | 怎么讲 |
|---|---|---|
| 表格来的 | 中 | 说法 |
- 项目符号来的——实情

## 下一节
"""


BULLETS = """## 缺口
- 「要求原文」——你的实情
- 核心职责：带过团队——只带过两个人

## 下一节
"""


class TheTableShapeIsRead(unittest.TestCase):
    def test_it_yields_one_entry_per_row(self):
        got = ex.parse_gaps(TABLE)
        self.assertEqual(len(got), 2, f"表格没读进来：{got}")

    def test_the_header_row_is_not_an_entry(self):
        self.assertNotIn("严重程度",
                         [g["claim"] for g in ex.parse_gaps(TABLE)])

    def test_the_claim_comes_from_the_first_column(self):
        got = ex.parse_gaps(TABLE)
        self.assertEqual(got[0]["claim"], "薪资低于底线")

    def test_the_severity_lands_in_kind(self):
        got = ex.parse_gaps(TABLE)
        self.assertEqual(got[1]["kind"], "中")

    def test_markdown_is_stripped_from_the_severity(self):
        """`**决定性**` 进的是纯文本节点，星号会一起显示。

        ⚠️ **这一条主要是文档性的**：`parse_table` 已经对每个单元格跑过
        `clean()`，星号在上游就没了（变异实测：这里改成 `row[i_sev].strip()`
        照样绿）。真正要钉的是**这一支走了显示层那道 `plain()`** ——
        它还管内部词换成人话，那个 `clean()` 不管。"""
        got = ex.parse_gaps(TABLE)
        self.assertNotIn("*", got[0]["kind"])
        self.assertIn("决定性", got[0]["kind"])
        i = EX.index('sev = plain(')
        self.assertLess(EX.index("def parse_gaps("), i)

    def test_the_how_column_becomes_the_detail(self):
        got = ex.parse_gaps(TABLE)
        self.assertIn("开场白第一件事", got[0]["detail"])

    def test_an_empty_severity_leaves_the_chip_off(self):
        """`——` 是「这一格没填」，不是一个标签。"""
        got = ex.parse_gaps("## 缺口\n| 缺口 | 严重程度 | 怎么讲 |\n|---|---|---|\n"
                            "| 某缺口 | —— | 如实说 |\n\n## 下一节\n")
        self.assertEqual(got[0]["kind"], "")

    def test_columns_are_matched_by_header_not_position(self):
        """列顺序不保证。按下标取会把「怎么讲」当成缺口名（变异实测：
        把 `_col(...)` 换成 `0` 时，只有正序夹具的话照样绿）。"""
        got = ex.parse_gaps(SHUFFLED)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["claim"], "没带过十人以上团队")
        self.assertEqual(got[0]["kind"], "高")
        self.assertIn("如实说", got[0]["detail"])

    def test_a_row_with_no_claim_is_skipped(self):
        got = ex.parse_gaps("## 缺口\n| 缺口 | 严重程度 | 怎么讲 |\n|---|---|---|\n"
                            "|  | 中 | 空的 |\n| 真缺口 | 低 | 有 |\n\n## 下一节\n")
        self.assertEqual([g["claim"] for g in got], ["真缺口"])


class TheBulletShapeStillWorks(unittest.TestCase):
    """规格给的就是它 —— 表格那一支不许把它挤掉。"""

    def test_bullets_still_parse(self):
        got = ex.parse_gaps(BULLETS)
        self.assertEqual(len(got), 2)

    def test_the_dash_split_survives(self):
        got = ex.parse_gaps(BULLETS)
        self.assertEqual(got[0]["claim"], "「要求原文」")
        self.assertEqual(got[0]["detail"], "你的实情")

    def test_the_bullet_prefix_still_becomes_kind(self):
        got = ex.parse_gaps(BULLETS)
        self.assertEqual(got[1]["kind"], "核心职责")

    def test_no_section_yields_nothing(self):
        self.assertEqual(ex.parse_gaps("## 别的\n- 一条\n"), [])

    def test_it_stops_at_the_next_heading(self):
        """**下一节里得真有项目符号**，否则「不 break」和「break」看不出差别
        （变异实测：把 `break` 去掉，只用没有后续 bullet 的夹具照样绿）。"""
        got = ex.parse_gaps(SPILL)
        self.assertEqual([g["claim"] for g in got], ["本节的一条"])


class BothShapesInOneSectionAreBothKept(unittest.TestCase):
    """实测 0 份这样写，但没理由拒绝 —— 两种都是缺口内容。

    第一版在表格分支后面 `return out`，两种共存时会把项目符号那批丢掉。
    去掉之后两种都收；一个 `|` 行不可能被 `- ` 正则认走，不会重复计数。
    """

    BOTH = BOTH_FIXTURE


    def test_both_land(self):
        got = ex.parse_gaps(self.BOTH)
        self.assertEqual([g["claim"] for g in got], ["表格来的", "项目符号来的"])

    def test_nothing_is_counted_twice(self):
        self.assertEqual(len(ex.parse_gaps(self.BOTH)), 2)

    def test_the_reason_is_at_the_code(self):
        i = EX.index("def parse_gaps(")
        seg = " ".join(EX[i:EX.index("\ndef ", i + 10)].replace("#", " ").split())
        self.assertRegex(seg, r"不提前返回")
        self.assertRegex(seg, r"不会重复计数")


class TheTableBranchUsesTheSharedTableReader(unittest.TestCase):
    """表头认法不许再写一套 —— `parse_gates` 已经有一份。"""

    def _body(self) -> str:
        i = EX.index("def parse_gaps(")
        return EX[i:EX.index("\ndef ", i + 10)]

    def test_it_calls_parse_table(self):
        self.assertIn("parse_table(", self._body())

    def test_it_uses_the_shared_column_matcher(self):
        self.assertIn("_col(header,", self._body())

    def test_it_does_not_hand_roll_a_pipe_split(self):
        self.assertNotIn('.split("|")', self._body(),
                         "又手写了一遍表格切分")


class TheReasonIsRecorded(unittest.TestCase):
    def _doc(self) -> str:
        i = EX.index("def parse_gaps(")
        return " ".join(EX[i:EX.index("    lines = text.splitlines()", i)].split())

    def test_it_names_the_dangerous_class(self):
        seg = self._doc()
        self.assertRegex(seg, r"把「上游丢了数据」 说成「核对过没问题」"
                              r"|把「上游丢了数据」说成「核对过没问题」")
        self.assertRegex(seg, r"它就在这个函数自己身上发生了")

    def test_it_carries_the_measurement(self):
        seg = self._doc()
        self.assertRegex(seg, r"\*\*52 份写成了表格\*\*")
        self.assertRegex(seg, r"\*\*137 条缺口\*\*一条都没进面板")
        self.assertIn("2026-08-23", seg)

    def test_it_says_who_is_off_spec_this_time(self):
        """和 `parse_quality` 那次方向相反 —— 不写清会被当成同一件事。"""
        seg = self._doc()
        self.assertRegex(seg, r"这次跑偏的是写手，不是解析器")

    def test_it_justifies_accepting_the_off_spec_shape(self):
        seg = self._doc()
        self.assertRegex(seg, r"已经写在盘上了")
        self.assertRegex(seg, r"比 bullet 多一列")

    def test_it_says_why_kind_is_safe_to_share(self):
        seg = self._doc()
        self.assertRegex(seg, r"719 条缺口的 `kind` 全是空的")
        self.assertRegex(seg, r"不编造分类")

    def test_the_spec_still_prescribes_a_bullet(self):
        """规格给的仍是 bullet（表格那一支是写手长出来的，不是规格）。

        2026-08-25 那一行加了个尾巴（`；能说清不能写成什么就带上……`）——
        **加尾巴可以，把 bullet 换成表格不行**。所以这里不再钉整行原文，
        钉的是「以 `- ...（如实写，不美化` 开头」这个形状。
        """
        i = EVAL.index("### 缺口")
        seg = EVAL[i:EVAL.index("### 职位真伪信号", i)]
        self.assertRegex(seg, r"(?m)^- \.\.\.（如实写，不美化[；)）]")


if __name__ == "__main__":
    unittest.main()
